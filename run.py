#!/usr/bin/env python3
"""
OntExtract Application Runner

This script starts the OntExtract Flask application with shared services enabled.
"""

import os
from dotenv import load_dotenv

# Load environment variables from .env BEFORE any app imports
# This ensures API keys are available when services are initialized
load_dotenv()

# Fix for libblis/SpaCy threading crash - must be set before importing any NLP libraries
os.environ.setdefault('OPENBLAS_NUM_THREADS', '1')
os.environ.setdefault('OMP_NUM_THREADS', '1')
os.environ.setdefault('MKL_NUM_THREADS', '1')

from app import create_app

# Expose a module-level Flask app for Gunicorn (run:app)
app = create_app()

def main():
    """Main entry point for the application."""
    
    # Set environment variables if not already set
    os.environ.setdefault('FLASK_ENV', 'development')
    os.environ.setdefault('FLASK_DEBUG', '1')
    
    # Use the module-level app
    global app
    
    # Print startup information
    print("=" * 60)
    print("🚀 Starting OntExtract with Shared Services")
    print("=" * 60)
    
    # Test shared services
    try:
        from app.services.text_processing import TextProcessingService
        service = TextProcessingService()
        status = service.get_service_status()
        
        print(f"📊 Enhanced Features: {'✅ Enabled' if status['enhanced_features_enabled'] else '❌ Disabled'}")
        print(f"📚 Shared Services: {'✅ Available' if status['shared_services_available'] else '❌ Unavailable'}")
        
        if status.get('embedding_providers'):
            available_embedding = [name for name, available in status['embedding_providers'].items() if available]
            print(f"🧠 Embedding Providers: {', '.join(available_embedding) if available_embedding else 'None'}")
        
        if status.get('llm_providers'):
            available_llm = [name for name, available in status['llm_providers'].items() if available]
            print(f"🤖 LLM Providers: {', '.join(available_llm) if available_llm else 'None'}")
        
        if status.get('file_processor_types'):
            print(f"📄 File Types: {', '.join(status['file_processor_types'])}")
        
        if status.get('available_ontologies') is not None:
            print(f"🔗 Ontologies: {status['available_ontologies']} available")
        
    except Exception as e:
        print(f"⚠️  Warning: Could not check service status: {e}")
    
    print("=" * 60)
    print("🌐 Starting Flask development server...")
    print("📍 Access the application at: http://localhost:8765")
    print("🛑 Press Ctrl+C to stop the server")
    print("=" * 60)
    
    # Show OED API configuration status
    try:
        oed_enabled = bool(app.config.get('OED_USE_API'))
        app_id_set = bool(app.config.get('OED_APP_ID'))
        key_set = bool(app.config.get('OED_ACCESS_KEY'))
        print(f"🔎 OED API: {'Enabled' if oed_enabled else 'Disabled'} | Credentials: {'Present' if (app_id_set and key_set) else 'Missing'}")
    except Exception as _:
        pass

    # Run the Flask app
    # Note: use_reloader disabled to prevent killing long-running orchestration workflows
    # Enable with FLASK_USE_RELOADER=1 if needed for active development
    use_reloader = os.environ.get('FLASK_USE_RELOADER', '0') == '1'

    app.run(
        host='0.0.0.0',
        port=8765,
        debug=True,
        use_reloader=use_reloader
    )

if __name__ == '__main__':
    main()
