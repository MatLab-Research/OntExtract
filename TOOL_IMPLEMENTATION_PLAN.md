# OntExtract Tool Implementation Plan (2025)

## Goal
Build processing tools that work in BOTH manual mode AND via MCP function calling, using latest 2025 patterns.

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    OntExtract System                         │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌──────────────────────────────────────────────────────┐  │
│  │           Core Tool Implementations                   │  │
│  │  (Pure Python - No LLM/MCP dependencies)             │  │
│  │                                                        │  │
│  │  • DocumentProcessor class                            │  │
│  │    - segment_paragraph()                              │  │
│  │    - segment_sentence()                               │  │
│  │    - extract_entities_spacy()                         │  │
│  │    - extract_definitions()                            │  │
│  │    - extract_temporal()                               │  │
│  │    - extract_causal()                                 │  │
│  │    - period_aware_embedding()                         │  │
│  └──────────────────────────────────────────────────────┘  │
│                          ↑                                   │
│                          │                                   │
│         ┌────────────────┴────────────────┐                 │
│         │                                  │                 │
│         ↓                                  ↓                 │
│  ┌─────────────────┐              ┌─────────────────┐      │
│  │  Manual UI      │              │  MCP Server     │      │
│  │  (Flask Routes) │              │  (FastMCP)      │      │
│  │                 │              │                 │      │
│  │  User clicks    │              │  @server.tool() │      │
│  │  button →       │              │  decorators     │      │
│  │  POST request → │              │                 │      │
│  │  Tool executes  │              │  Exposed to     │      │
│  └─────────────────┘              │  Claude API     │      │
│                                    └─────────────────┘      │
│                                            ↓                 │
│                                    ┌─────────────────┐      │
│                                    │  LangChain      │      │
│                                    │  Orchestration  │      │
│                                    │                 │      │
│                                    │  .bind_tools()  │      │
│                                    │  with Claude    │      │
│                                    └─────────────────┘      │
└─────────────────────────────────────────────────────────────┘
```

## Implementation Phases

### Phase 1: Core Tool Implementations (Week 1)
**Location:** `app/services/processing_tools.py`

```python
from typing import List, Dict, Any
from dataclasses import dataclass

@dataclass
class ProcessingResult:
    """Standardized tool output format"""
    tool_name: str
    status: str  # success, error, partial
    data: Any
    metadata: Dict[str, Any]
    provenance: Dict[str, Any]  # PROV-O tracking

class DocumentProcessor:
    """Core processing tools - pure Python implementations"""

    def segment_paragraph(self, text: str) -> ProcessingResult:
        """Split text into paragraphs"""
        paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
        return ProcessingResult(
            tool_name="segment_paragraph",
            status="success",
            data=paragraphs,
            metadata={"count": len(paragraphs)},
            provenance=self._generate_provenance("segment_paragraph")
        )

    def segment_sentence(self, text: str) -> ProcessingResult:
        """Split text into sentences using NLTK"""
        import nltk
        sentences = nltk.sent_tokenize(text)
        return ProcessingResult(...)

    def extract_entities_spacy(self, text: str) -> ProcessingResult:
        """Extract named entities using spaCy"""
        import spacy
        nlp = spacy.load("en_core_web_sm")
        doc = nlp(text)
        entities = [
            {"text": ent.text, "label": ent.label_, "start": ent.start_char}
            for ent in doc.ents
        ]
        return ProcessingResult(...)
```

**Tools Priority:**
1. ✅ `segment_paragraph` - Easy, no deps
2. ✅ `segment_sentence` - Easy, NLTK
3. ⏳ `extract_entities_spacy` - Medium, spaCy
4. ⏳ `extract_definitions` - Medium, patterns + LLM
5. ⏳ `extract_temporal` - Hard, SUTime/HeidelTime
6. ⏳ `extract_causal` - Hard, custom NLP
7. ⏳ `period_aware_embedding` - Hard, research needed

### Phase 2: Manual UI Integration (Week 1-2)
**Location:** `app/routes/processing.py`

Wire tools to existing manual processing UI:

```python
@processing_bp.route('/document/<doc_id>/process', methods=['POST'])
def process_document_manual(doc_id):
    """Manual tool execution endpoint"""
    data = request.json
    tool_names = data.get('tools', [])

    processor = DocumentProcessor()
    results = []

    for tool_name in tool_names:
        if hasattr(processor, tool_name):
            tool_func = getattr(processor, tool_name)
            result = tool_func(document.content)
            results.append(result)

    return jsonify({"results": results})
```

**UI Changes:**
- Add tool selection checkboxes
- Show real-time results
- Display provenance info
- Save to database

### Phase 3: MCP Server with FastMCP (Week 2-3)
**Location:** `mcp_server/ontextract_tools.py`

```python
from fastmcp import FastMCP

mcp = FastMCP("OntExtract Processing Tools")

@mcp.tool()
async def segment_paragraph(text: str) -> dict:
    """
    Split document text into paragraphs.

    Args:
        text: The document text to segment

    Returns:
        Dictionary with paragraphs and metadata
    """
    processor = DocumentProcessor()
    result = processor.segment_paragraph(text)
    return result.to_dict()

@mcp.tool()
async def extract_entities_spacy(text: str) -> dict:
    """
    Extract named entities (PERSON, ORG, GPE, DATE) from text.

    Args:
        text: The document text to analyze

    Returns:
        Dictionary with entities and their labels
    """
    processor = DocumentProcessor()
    result = processor.extract_entities_spacy(text)
    return result.to_dict()

# Run server
if __name__ == "__main__":
    mcp.run()
```

**Config for Claude:** `mcp_config.json`
```json
{
  "mcpServers": {
    "ontextract": {
      "command": "python",
      "args": ["/home/chris/onto/OntExtract/mcp_server/ontextract_tools.py"],
      "env": {
        "PYTHONPATH": "/home/chris/onto/OntExtract"
      }
    }
  }
}
```

### Phase 4: LangChain Orchestration (Week 3-4)
**Location:** `app/orchestration/experiment_nodes.py`

Use modern LangChain patterns:

```python
from langchain_anthropic import ChatAnthropic
from langchain_core.tools import tool

# Define tools for LangChain
@tool
def segment_paragraph(text: str) -> dict:
    """Split document text into paragraphs"""
    processor = DocumentProcessor()
    return processor.segment_paragraph(text).to_dict()

@tool
def extract_entities_spacy(text: str) -> dict:
    """Extract named entities from text"""
    processor = DocumentProcessor()
    return processor.extract_entities_spacy(text).to_dict()

# Bind tools to Claude
async def execute_strategy_with_tools(state):
    """Execute strategy using LangChain tool calling"""

    llm = ChatAnthropic(
        model="claude-sonnet-4-5-20250929",
        headers={"anthropic-beta": "mcp-client-2025-04-04"}
    )

    tools = [
        segment_paragraph,
        extract_entities_spacy,
        # ... other tools
    ]

    llm_with_tools = llm.bind_tools(tools)

    # Let LLM decide which tools to call
    response = await llm_with_tools.ainvoke(
        f"Process this document: {document.content}"
    )

    # Handle tool calls
    if response.tool_calls:
        for tool_call in response.tool_calls:
            # Execute tool
            result = await execute_tool(tool_call)
```

## Testing Strategy

### 1. Unit Tests (Each Tool)
```python
def test_segment_paragraph():
    processor = DocumentProcessor()
    result = processor.segment_paragraph("Para 1\n\nPara 2")
    assert result.status == "success"
    assert len(result.data) == 2
```

### 2. Manual UI Tests
- Click buttons in UI
- Verify results display
- Check database persistence

### 3. MCP Server Tests
```bash
# Test MCP server directly
python mcp_server/ontextract_tools.py
# Use Claude Desktop to call tools
```

### 4. Integration Tests
- Full experiment flow
- LLM orchestration
- Results validation

## Dependencies to Install

```bash
# Core NLP
pip install nltk spacy
python -m spacy download en_core_web_sm

# MCP
pip install fastmcp

# LangChain (latest)
pip install langchain langchain-anthropic

# Optional (advanced tools)
pip install sutime  # Temporal extraction
pip install sentence-transformers  # Embeddings
```

## Success Metrics

- ✅ Each tool works standalone
- ✅ Manual UI can run all tools
- ✅ MCP server exposes all tools
- ✅ LangChain can call tools
- ✅ Full experiment completes successfully

## Timeline

- **Week 1**: Core tools + Manual UI (segment_paragraph, segment_sentence)
- **Week 2**: More tools + MCP server (extract_entities, extract_definitions)
- **Week 3**: LangChain integration + Testing
- **Week 4**: Advanced tools + Production deployment

## Next Steps

1. Implement `DocumentProcessor` class with first 2 tools
2. Wire to manual UI for testing
3. Validate results and provenance tracking
4. Build MCP server once tools are proven
