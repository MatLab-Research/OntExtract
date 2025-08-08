# Shared Services Architecture for OntExtract

## Overview

This document describes the shared services architecture implemented for OntExtract, designed to provide reusable components that can be shared between ProEthica and OntExtract applications.

## Architecture

### Directory Structure

```
shared_services/
├── __init__.py
├── embedding/
│   ├── __init__.py
│   ├── embedding_service.py      # Multi-provider embedding service
│   └── file_processor.py         # File processing for PDF, DOCX, HTML, etc.
├── ontology/
│   ├── __init__.py
│   └── entity_service.py         # RDF/TTL ontology processing
├── llm/
│   ├── __init__.py
│   ├── base_service.py           # Multi-provider LLM service
│   └── providers/
│       └── __init__.py
└── models/
    └── __init__.py               # Shared data models
```

## Core Services

### 1. EmbeddingService (`shared_services/embedding/embedding_service.py`)

**Features:**
- Multi-provider support (Local sentence-transformers, OpenAI, Claude)
- Automatic fallback between providers
- Configurable priority order via environment variables
- Batch processing capabilities
- Similarity calculation

**Usage:**
```python
from shared_services.embedding.embedding_service import EmbeddingService

service = EmbeddingService()
embedding = service.get_embedding("Your text here")
similarity = service.similarity(embedding1, embedding2)
```

**Environment Variables:**
- `LOCAL_EMBEDDING_MODEL`: Local model name (default: "all-MiniLM-L6-v2")
- `EMBEDDING_PROVIDER_PRIORITY`: Comma-separated priority list (default: "local,openai,claude")
- `OPENAI_API_KEY`: OpenAI API key
- `ANTHROPIC_API_KEY`: Claude API key

### 2. FileProcessingService (`shared_services/embedding/file_processor.py`)

**Supported Formats:**
- PDF files (via PyPDF2)
- DOCX documents (via python-docx)
- HTML files (via BeautifulSoup4)
- Plain text files
- URLs/web pages

**Features:**
- Text chunking with configurable overlap
- Structured text extraction from web pages
- Error handling and fallbacks

**Usage:**
```python
from shared_services.embedding.file_processor import FileProcessingService

processor = FileProcessingService()
text = processor.process_file("document.pdf", "pdf")
chunks = processor.split_text(text, chunk_size=1000, chunk_overlap=200)
```

### 3. OntologyEntityService (`shared_services/ontology/entity_service.py`)

**Features:**
- RDF/TTL ontology parsing using RDFLib
- Dynamic GuidelineConceptType discovery
- Multiple storage backends (file-based, database)
- Entity caching for performance
- Ontology validation

**Usage:**
```python
from shared_services.ontology.entity_service import OntologyEntityService

service = OntologyEntityService(ontology_dir="/path/to/ontologies")
entities = service.get_entities("engineering-ethics")
```

### 4. BaseLLMService (`shared_services/llm/base_service.py`)

**Features:**
- Multi-provider LLM support (OpenAI, Claude)
- Text generation with configurable parameters
- Entity extraction using LLM capabilities
- Text summarization
- Provider status monitoring

**Usage:**
```python
from shared_services.llm.base_service import BaseLLMService

service = BaseLLMService()
response = service.generate_text("Your prompt here")
entities = service.extract_entities("Text to analyze")
summary = service.summarize_text("Long text to summarize")
```

## Integration with OntExtract

The `TextProcessingService` in OntExtract has been enhanced to use these shared services:

### Enhanced Methods

1. **`process_file_content()`** - Uses FileProcessingService for multi-format support
2. **`generate_embeddings()`** - Creates embeddings using EmbeddingService
3. **`extract_ontology_entities()`** - Extracts entities using ontology knowledge
4. **`summarize_with_llm()`** - Generates summaries using LLM service
5. **`calculate_similarity()`** - Uses semantic embeddings for similarity
6. **`get_service_status()`** - Reports status of all shared services

### Graceful Fallbacks

The integration includes graceful fallbacks when shared services aren't available:
- Basic file processing for text files
- Simple keyword extraction instead of entity extraction
- Word overlap similarity instead of semantic similarity
- Text truncation instead of LLM summarization

## Installation

1. Install shared services dependencies:
```bash
pip install -r shared_services_requirements.txt
```

2. Set up environment variables:
```bash
# Optional: Configure provider priority
export EMBEDDING_PROVIDER_PRIORITY="local,openai"
export LLM_PROVIDER_PRIORITY="openai,claude"

# Optional: API keys for external providers
export OPENAI_API_KEY="your-key-here"
export ANTHROPIC_API_KEY="your-key-here"

# Optional: Local model configuration
export LOCAL_EMBEDDING_MODEL="all-MiniLM-L6-v2"
```

## Dependencies

Key dependencies included in `shared_services_requirements.txt`:

**Core:**
- Flask, SQLAlchemy, etc. (web framework)
- sentence-transformers, numpy (embeddings)
- rdflib, owlrl (ontology processing)
- requests (API calls)

**File Processing:**
- PyPDF2 (PDF files)
- python-docx (DOCX files)  
- beautifulsoup4, lxml (HTML/web pages)

**Optional:**
- spacy, transformers, torch (enhanced NLP features)

## Configuration

Services can be configured via environment variables or initialization parameters:

```python
# Custom embedding service configuration
embedding_service = EmbeddingService(
    model_name="custom-model",
    provider_priority=["local", "openai"],
    embedding_dimension=512
)

# Custom ontology service with specific directory
ontology_service = OntologyEntityService(
    ontology_dir="/custom/ontology/path"
)
```

## Extensibility

The architecture is designed for easy extension:

1. **New Embedding Providers:** Implement `BaseEmbeddingProvider`
2. **New LLM Providers:** Implement `BaseLLMProvider`
3. **New File Processors:** Implement `BaseFileProcessor`
4. **New Ontology Stores:** Implement `BaseOntologyStore`

## Performance Considerations

- **Caching:** Ontology entities are cached to avoid repeated parsing
- **Batch Processing:** Embedding service supports batch operations
- **Fallback Performance:** Services gracefully degrade without external APIs
- **Memory Management:** Large files are processed in chunks

## Error Handling

All services include comprehensive error handling:
- Provider availability checking
- Graceful fallbacks between providers
- Detailed error logging
- Recovery mechanisms for transient failures

## Future Enhancements

Planned improvements:
1. **Google LangExtract Integration:** Add support for Google's language extraction
2. **Graph-based Extraction:** Enhanced ontology-driven entity extraction
3. **Caching Layer:** Redis-based caching for improved performance
4. **Monitoring:** Health checks and metrics collection
5. **Testing:** Comprehensive test suite for all services

## Reusability with ProEthica

The shared services are designed to be easily integrated with ProEthica:

1. **Compatible Interfaces:** Services match ProEthica's existing patterns
2. **Configuration Flexibility:** Environment-based configuration supports both apps
3. **Modular Design:** Individual services can be adopted incrementally
4. **Database Integration:** Compatible with existing ProEthica database models

To use with ProEthica, simply:
1. Copy the `shared_services` directory to ProEthica
2. Install the dependencies
3. Update ProEthica's services to import and use shared components
4. Configure environment variables as needed

This architecture provides a solid foundation for advanced text processing capabilities while maintaining compatibility and extensibility.
