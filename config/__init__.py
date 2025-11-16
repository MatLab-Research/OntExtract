import os
from pathlib import Path
from dotenv import load_dotenv, find_dotenv

# Load environment variables in priority order:
# 1. shared/.env (shared across all applications)
# 2. .env (app-specific configuration)
# 3. .env.local (local overrides)
# 4. local.env (alternative local overrides)

# Load shared environment first
current_dir = Path(__file__).parent
workspace_root = current_dir.parent.parent
shared_env = workspace_root / "shared" / ".env"

if shared_env.exists():
    load_dotenv(shared_env, override=False)
    print(f"✅ Loaded shared environment config: {shared_env}")

# Load app-specific .env
base_env = find_dotenv(filename=".env")
if base_env:
    load_dotenv(base_env, override=True)  # App-specific overrides shared
    print(f"✅ Loaded local environment config: .env")

# Load local overrides
local_env = find_dotenv(filename=".env.local")
if local_env:
    load_dotenv(local_env, override=True)

alt_local_env = find_dotenv(filename="local.env")
if alt_local_env:
    load_dotenv(alt_local_env, override=True)

class Config:
    """Base configuration class"""
    
    # Flask Core Settings
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    
    # Database Configuration
    DATABASE_URL = os.environ.get('DATABASE_URL') or 'postgresql://localhost/ontextract_db'
    SQLALCHEMY_DATABASE_URI = DATABASE_URL
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_pre_ping': True,
        'pool_recycle': 300,
    }
    
    
    # File Upload Configuration
    UPLOAD_FOLDER = os.environ.get('ONTEXTRACT_UPLOAD_FOLDER', 'uploads')
    MAX_CONTENT_LENGTH = int(os.environ.get('MAX_CONTENT_LENGTH', 16 * 1024 * 1024))  # 16MB
    ALLOWED_EXTENSIONS = set(os.environ.get('ALLOWED_EXTENSIONS', 'txt,pdf,docx,html,md').split(','))
    
    # LLM Provider Configuration
    ANTHROPIC_API_KEY = os.environ.get('ANTHROPIC_API_KEY')
    OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY')
    DEFAULT_LLM_PROVIDER = os.environ.get('DEFAULT_LLM_PROVIDER', 'anthropic')
    
    # Claude Model Configuration (Latest: Sonnet 4.5 - Sep 2025, Haiku 4.5 - Oct 2025)
    # Verified Nov 2025 with latest stable releases
    CLAUDE_DEFAULT_MODEL = os.environ.get('CLAUDE_DEFAULT_MODEL', 'claude-sonnet-4-5-20250929')
    CLAUDE_API_VERSION = os.environ.get('CLAUDE_API_VERSION', '2023-06-01')
    CLAUDE_EMBEDDING_MODEL = os.environ.get('CLAUDE_EMBEDDING_MODEL', 'claude-3-embedding')

    # Task-Specific LLM Model Configuration
    # Updated November 16, 2025 with verified latest stable models
    # Different tasks require different model characteristics (speed vs. capability, context length, specialization)
    # Model verification: gemini-2.5-flash (stable), claude-sonnet-4-5-20250929, claude-haiku-4-5-20251001, gpt-5-mini

    # Structured Extraction (LangExtract): Fast, good at structured output, cost-effective
    # Use case: Extracting definitions, temporal markers, domain indicators from documents
    # Requirements: JSON output, consistent format, reasonable cost for high volume
    # Model: gemini-2.5-flash (stable as of June 2025) - Fast, structured output, $0.10/$0.40 per 1M tokens
    LLM_EXTRACTION_PROVIDER = os.environ.get('LLM_EXTRACTION_PROVIDER', 'gemini')
    LLM_EXTRACTION_MODEL = os.environ.get('LLM_EXTRACTION_MODEL', 'gemini-2.5-flash')

    # Semantic Analysis & Synthesis: Capable models for complex reasoning
    # Use case: Cross-document synthesis, semantic drift analysis, philosophical reasoning
    # Requirements: Deep understanding, nuanced analysis, high-quality output
    # Model: claude-sonnet-4-5-20250929 (Sep 29, 2025) - Best for complex analysis, 200k context, $3/$15 per 1M tokens
    LLM_SYNTHESIS_PROVIDER = os.environ.get('LLM_SYNTHESIS_PROVIDER', 'anthropic')
    LLM_SYNTHESIS_MODEL = os.environ.get('LLM_SYNTHESIS_MODEL', 'claude-sonnet-4-5-20250929')

    # Orchestration & Routing: Fast model for tool selection decisions
    # Use case: Deciding which NLP tools to use, routing tasks, confidence scoring
    # Requirements: Good reasoning, fast response, cost-effective for frequent decisions
    # Model: claude-haiku-4-5-20251001 (Oct 15, 2025) - Faster than Haiku 3.5, 1/3 the cost of Sonnet, $1/$5 per 1M tokens
    # Alternative: gpt-5-mini for OpenAI preference
    LLM_ORCHESTRATION_PROVIDER = os.environ.get('LLM_ORCHESTRATION_PROVIDER', 'anthropic')
    LLM_ORCHESTRATION_MODEL = os.environ.get('LLM_ORCHESTRATION_MODEL', 'claude-haiku-4-5-20251001')

    # OED Parsing: Structured extraction from complex dictionary entries
    # Use case: Parsing OED entries, extracting etymologies, definitions, quotations
    # Requirements: JSON output, handle complex nested structures, reliable
    # Model: gemini-2.5-pro (stable) - Best for complex structured extraction, 1M token context
    LLM_OED_PARSING_PROVIDER = os.environ.get('LLM_OED_PARSING_PROVIDER', 'gemini')
    LLM_OED_PARSING_MODEL = os.environ.get('LLM_OED_PARSING_MODEL', 'gemini-2.5-pro')

    # Long Context Processing: Models with large context windows for full document analysis
    # Use case: Processing long historical documents, multi-document comparison
    # Requirements: Large context window (100k+ tokens), good at long-range reasoning
    # Model: claude-sonnet-4-5-20250929 - 200k context window, best for extended focus (30+ hours on complex tasks)
    LLM_LONG_CONTEXT_PROVIDER = os.environ.get('LLM_LONG_CONTEXT_PROVIDER', 'anthropic')
    LLM_LONG_CONTEXT_MODEL = os.environ.get('LLM_LONG_CONTEXT_MODEL', 'claude-sonnet-4-5-20250929')

    # Classification & Categorization: Fastest models for simple classification tasks
    # Use case: Domain classification, period classification, document type detection
    # Requirements: Fast, consistent, cost-effective for high volume
    # Model: gemini-2.5-flash-lite (stable Nov 13, 2025) - Fastest/cheapest, $0.10/$0.40 per 1M tokens
    LLM_CLASSIFICATION_PROVIDER = os.environ.get('LLM_CLASSIFICATION_PROVIDER', 'gemini')
    LLM_CLASSIFICATION_MODEL = os.environ.get('LLM_CLASSIFICATION_MODEL', 'gemini-2.5-flash-lite')

    # Fallback models when primary provider is unavailable
    # Model: gpt-5.1 (Nov 2025) - Latest stable GPT, most recent release
    LLM_FALLBACK_PROVIDER = os.environ.get('LLM_FALLBACK_PROVIDER', 'openai')
    LLM_FALLBACK_MODEL = os.environ.get('LLM_FALLBACK_MODEL', 'gpt-5.1')

    # OED Researcher API Configuration (use env; do not commit secrets)
    OED_USE_API = os.environ.get('OED_USE_API', 'False').lower() in {'true', '1', 'yes', 'on', 'y', 't'}
    OED_APP_ID = os.environ.get('OED_APP_ID')  # set in .env.local
    OED_ACCESS_KEY = os.environ.get('OED_ACCESS_KEY')  # set in .env.local
    OED_API_BASE_URL = os.environ.get('OED_API_BASE_URL', '').rstrip('/')  # optional override
    OED_API_TIMEOUT = float(os.environ.get('OED_API_TIMEOUT', '15'))

    # Reference metadata enrichment flags
    PREFILL_METADATA = os.environ.get('PREFILL_METADATA', 'True').lower() in {'true','1','yes','on','y','t'}
    PREFILL_USE_LANGEXTRACT = os.environ.get('PREFILL_USE_LANGEXTRACT', 'False').lower() in {'true','1','yes','on','y','t'}
    PREFILL_USE_ZOTERO = os.environ.get('PREFILL_USE_ZOTERO', 'False').lower() in {'true','1','yes','on','y','t'}
    ZOTERO_API_KEY = os.environ.get('ZOTERO_API_KEY')
    ZOTERO_USER_ID = os.environ.get('ZOTERO_USER_ID')
    
    # Google Cloud Configuration
    GOOGLE_APPLICATION_CREDENTIALS = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS')
    GOOGLE_PROJECT_ID = os.environ.get('GOOGLE_PROJECT_ID')
    GOOGLE_LOCATION = os.environ.get('GOOGLE_LOCATION', 'us-central1')
    GOOGLE_LANGUAGE_SERVICE_ENABLED = os.environ.get('GOOGLE_LANGUAGE_SERVICE_ENABLED', 'True').lower() == 'true'
    GOOGLE_TRANSLATE_SERVICE_ENABLED = os.environ.get('GOOGLE_TRANSLATE_SERVICE_ENABLED', 'True').lower() == 'true'
    GOOGLE_GEMINI_API_KEY = os.environ.get('GOOGLE_GEMINI_API_KEY')
    
    # Processing Configuration
    ENABLE_BATCH_PROCESSING = os.environ.get('ENABLE_BATCH_PROCESSING', 'True').lower() == 'true'
    MAX_CONCURRENT_JOBS = int(os.environ.get('MAX_CONCURRENT_JOBS', 3))
    
    # RAG Configuration
    EMBEDDING_MODEL = os.environ.get('EMBEDDING_MODEL', 'sentence-transformers/all-MiniLM-L6-v2')
    VECTOR_DIMENSION = int(os.environ.get('VECTOR_DIMENSION', 384))
    SIMILARITY_THRESHOLD = float(os.environ.get('SIMILARITY_THRESHOLD', 0.7))
    
    # Redis Configuration
    REDIS_URL = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
    
    # Logging Configuration
    LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')
    LOG_FILE = os.environ.get('LOG_FILE', 'logs/ontextract.log')
    
    # WTF Configuration
    WTF_CSRF_ENABLED = os.environ.get('WTF_CSRF_ENABLED', 'True').lower() == 'true'

class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True
    TESTING = False

class ProductionConfig(Config):
    """Production configuration"""
    DEBUG = False
    TESTING = False

class TestingConfig(Config):
    """Testing configuration"""
    TESTING = True
    WTF_CSRF_ENABLED = False
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'

# Configuration mapping
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}
