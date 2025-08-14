import os
from dotenv import load_dotenv, find_dotenv

# Load environment variables from .env and local overrides
# Order: .env (base) -> .env.local (overrides) -> local.env (overrides)
base_env = find_dotenv(filename=".env")
if base_env:
    load_dotenv(base_env, override=False)

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
