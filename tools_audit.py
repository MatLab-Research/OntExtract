#!/usr/bin/env python3
"""
OntExtract Tool Usage Audit Script

Analyzes the codebase to determine which tools are ACTUALLY used in active
routes vs. just present in requirements.txt or legacy code.

Outputs:
1. Active tool stack (used in routes)
2. Legacy tools (imported but not called from routes)
3. Unused dependencies (in requirements.txt but never imported)
"""

import os
import re
import ast
from pathlib import Path
from collections import defaultdict
from typing import Dict, List, Set, Tuple

# Define tool categories
NLP_TOOLS = {
    'spacy': 'Named Entity Recognition',
    'nltk': 'Tokenization & Text Processing',
    'sentence_transformers': 'Semantic Embeddings',
    'langextract': 'Structured Extraction (LLM-based)',
    'transformers': 'HuggingFace Transformers',
}

LLM_APIS = {
    'anthropic': 'Claude API',
    'openai': 'GPT API',
    'google.genai': 'Google Gemini API',
    'langchain': 'LangChain Framework',
}

DATABASE_TOOLS = {
    'pgvector': 'Vector Similarity Search',
    'psycopg2': 'PostgreSQL Driver',
    'sqlalchemy': 'ORM',
}

DOCUMENT_PARSING = {
    'pypdf': 'PDF Parsing',
    'pdfplumber': 'PDF Table Extraction',
    'python-docx': 'DOCX Processing',
    'beautifulsoup4': 'HTML Parsing',
}

ALL_TOOLS = {**NLP_TOOLS, **LLM_APIS, **DATABASE_TOOLS, **DOCUMENT_PARSING}


class CodeAnalyzer:
    """Analyzes Python code for import and usage patterns"""

    def __init__(self, base_path: str):
        self.base_path = Path(base_path)
        self.imports_by_file: Dict[str, Set[str]] = defaultdict(set)
        self.function_calls_by_file: Dict[str, Set[str]] = defaultdict(set)

    def analyze_file(self, filepath: Path) -> Tuple[Set[str], Set[str]]:
        """Extract imports and function calls from a Python file"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
                tree = ast.parse(content, filename=str(filepath))

            imports = set()
            function_calls = set()

            for node in ast.walk(tree):
                # Capture imports
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        imports.add(alias.name.split('.')[0])
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        imports.add(node.module.split('.')[0])

                # Capture function calls (to detect actual usage)
                elif isinstance(node, ast.Call):
                    if isinstance(node.func, ast.Name):
                        function_calls.add(node.func.id)
                    elif isinstance(node.func, ast.Attribute):
                        # Capture module.function() calls
                        if isinstance(node.func.value, ast.Name):
                            function_calls.add(f"{node.func.value.id}.{node.func.attr}")

            return imports, function_calls

        except Exception as e:
            print(f"Error analyzing {filepath}: {e}")
            return set(), set()

    def scan_directory(self, directory: str, pattern: str = "**/*.py"):
        """Scan all Python files in directory"""
        dir_path = self.base_path / directory
        if not dir_path.exists():
            return

        for filepath in dir_path.glob(pattern):
            if '__pycache__' in str(filepath) or 'venv' in str(filepath):
                continue

            rel_path = filepath.relative_to(self.base_path)
            imports, calls = self.analyze_file(filepath)
            self.imports_by_file[str(rel_path)] = imports
            self.function_calls_by_file[str(rel_path)] = calls

    def get_tool_usage(self) -> Dict[str, Dict]:
        """Determine which tools are actually used"""
        tool_usage = {}

        for tool_name, description in ALL_TOOLS.items():
            tool_module = tool_name.replace('-', '_')

            files_importing = []
            files_calling = []

            for filepath, imports in self.imports_by_file.items():
                if tool_module in imports:
                    files_importing.append(filepath)

                    # Check if this file also calls functions from the tool
                    calls = self.function_calls_by_file[filepath]
                    if any(tool_module in call for call in calls):
                        files_calling.append(filepath)

            if files_importing:
                tool_usage[tool_name] = {
                    'description': description,
                    'imported_in': files_importing,
                    'called_in': files_calling,
                    'status': 'ACTIVE' if files_calling else 'IMPORTED_ONLY'
                }

        return tool_usage


def read_requirements(requirements_path: str) -> Set[str]:
    """Parse requirements.txt for installed packages"""
    packages = set()
    try:
        with open(requirements_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    # Extract package name (before ==, @, etc.)
                    pkg = re.split(r'[=@<>]', line)[0].strip()
                    packages.add(pkg)
    except FileNotFoundError:
        print(f"Warning: {requirements_path} not found")
    return packages


def categorize_files(files: List[str]) -> Dict[str, List[str]]:
    """Categorize files by type (routes, services, models, etc.)"""
    categories = {
        'routes': [],
        'services': [],
        'models': [],
        'orchestration': [],
        'tests': [],
        'other': []
    }

    for filepath in files:
        if 'routes/' in filepath:
            categories['routes'].append(filepath)
        elif 'services/' in filepath:
            categories['services'].append(filepath)
        elif 'models/' in filepath:
            categories['models'].append(filepath)
        elif 'orchestration/' in filepath:
            categories['orchestration'].append(filepath)
        elif 'tests/' in filepath:
            categories['tests'].append(filepath)
        else:
            categories['other'].append(filepath)

    return categories


def main():
    base_path = Path(__file__).parent
    analyzer = CodeAnalyzer(str(base_path))

    print("=" * 80)
    print("OntExtract Tool Usage Audit")
    print("=" * 80)
    print()

    # Scan codebase
    print("Scanning codebase...")
    analyzer.scan_directory('app/routes')
    analyzer.scan_directory('app/services')
    analyzer.scan_directory('app/models')
    analyzer.scan_directory('app/orchestration')
    print(f"Analyzed {len(analyzer.imports_by_file)} files\n")

    # Get tool usage
    tool_usage = analyzer.get_tool_usage()

    # Read requirements
    requirements = read_requirements(str(base_path / 'requirements.txt'))

    # Report: Active Tools (used in routes)
    print("=" * 80)
    print("1. ACTIVE TOOLS (Used in Routes)")
    print("=" * 80)
    active_in_routes = {}
    for tool, data in tool_usage.items():
        route_files = [f for f in data['called_in'] if 'routes/' in f]
        if route_files:
            active_in_routes[tool] = {**data, 'route_files': route_files}

    if active_in_routes:
        for tool, data in sorted(active_in_routes.items()):
            print(f"\n{tool.upper()}: {data['description']}")
            print(f"  Status: ✓ ACTIVE (called from routes)")
            print(f"  Routes: {', '.join(data['route_files'])}")
    else:
        print("\n  No tools directly called from routes (orchestration pattern detected)")

    # Report: Service-Level Tools (used in services, maybe called from routes indirectly)
    print("\n")
    print("=" * 80)
    print("2. SERVICE-LEVEL TOOLS (Used in Services)")
    print("=" * 80)
    service_tools = {}
    for tool, data in tool_usage.items():
        service_files = [f for f in data['called_in'] if 'services/' in f]
        if service_files and tool not in active_in_routes:
            service_tools[tool] = {**data, 'service_files': service_files}

    if service_tools:
        for tool, data in sorted(service_tools.items()):
            print(f"\n{tool.upper()}: {data['description']}")
            print(f"  Status: ✓ ACTIVE (via services)")
            print(f"  Services: {', '.join(data['service_files'][:3])}")
            if len(data['service_files']) > 3:
                print(f"           ... and {len(data['service_files']) - 3} more")
    else:
        print("\n  No service-level tools detected")

    # Report: Legacy Tools (imported but not called)
    print("\n")
    print("=" * 80)
    print("3. LEGACY/UNUSED TOOLS (Imported but Not Called)")
    print("=" * 80)
    legacy_tools = {
        tool: data for tool, data in tool_usage.items()
        if data['status'] == 'IMPORTED_ONLY'
    }

    if legacy_tools:
        for tool, data in sorted(legacy_tools.items()):
            print(f"\n{tool.upper()}: {data['description']}")
            print(f"  Status: ⚠ IMPORTED_ONLY (not actually used)")
            files_by_cat = categorize_files(data['imported_in'])
            for cat, files in files_by_cat.items():
                if files:
                    print(f"  {cat.capitalize()}: {', '.join(files[:2])}")
                    if len(files) > 2:
                        print(f"            ... and {len(files) - 2} more")
    else:
        print("\n  ✓ No legacy imports detected")

    # Report: Check for langextract specifically
    print("\n")
    print("=" * 80)
    print("4. LANGEXTRACT STATUS (Paper Concern)")
    print("=" * 80)
    if 'langextract' in tool_usage:
        le_data = tool_usage['langextract']
        print(f"\nStatus: {le_data['status']}")
        print(f"Imported in: {len(le_data['imported_in'])} files")
        print(f"Called in: {len(le_data['called_in'])} files")

        if le_data['called_in']:
            print("\nFiles that actually call langextract:")
            for f in le_data['called_in']:
                print(f"  - {f}")
        else:
            print("\n⚠ LEGACY CODE: langextract is imported but never called")
            print("  Recommendation: Remove from paper description OR activate usage")
    elif 'langextract' in requirements:
        print("\n⚠ langextract in requirements.txt but NOT imported anywhere")
        print("  Recommendation: Remove from requirements.txt AND paper")
    else:
        print("\n✓ langextract not found in codebase")

    # Report: Recommended Paper Description
    print("\n")
    print("=" * 80)
    print("5. RECOMMENDED TOOL STACK FOR PAPER")
    print("=" * 80)

    active_tools = {**active_in_routes, **service_tools}

    print("\nStandalone Mode (No API Required):")
    standalone = []
    for tool in ['spacy', 'nltk', 'sentence_transformers', 'pypdf', 'pdfplumber']:
        if tool in active_tools:
            standalone.append(f"  - {tool}: {active_tools[tool]['description']}")
    if standalone:
        print('\n'.join(standalone))
    else:
        print("  (None detected - check manually)")

    print("\nAPI-Enhanced Mode (LLM Orchestration):")
    api_tools = []
    for tool in ['anthropic', 'openai', 'google.genai', 'langchain']:
        # Check with variations
        tool_variants = [tool, tool.replace('.', '_')]
        for variant in tool_variants:
            if variant in active_tools:
                api_tools.append(f"  - {tool}: {active_tools[variant]['description']}")
                break
    if api_tools:
        print('\n'.join(api_tools))
    else:
        print("  (None detected - check manually)")

    print("\nDatabase & Infrastructure:")
    db_tools = []
    for tool in ['pgvector', 'sqlalchemy', 'psycopg2']:
        tool_variant = tool.replace('-', '_')
        if tool_variant in active_tools or tool in active_tools:
            desc = active_tools.get(tool_variant, active_tools.get(tool, {})).get('description', '')
            db_tools.append(f"  - {tool}: {desc}")
    if db_tools:
        print('\n'.join(db_tools))

    # Summary statistics
    print("\n")
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"\nTotal packages in requirements.txt: {len(requirements)}")
    print(f"Tools analyzed: {len(ALL_TOOLS)}")
    print(f"Active tools (in routes): {len(active_in_routes)}")
    print(f"Service-level tools: {len(service_tools)}")
    print(f"Legacy/unused imports: {len(legacy_tools)}")

    print("\n✓ Audit complete. Use results to update paper description.\n")


if __name__ == '__main__':
    main()
