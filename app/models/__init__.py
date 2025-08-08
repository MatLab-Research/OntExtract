from app import db

# Import all models here for easy access
from .user import User
from .document import Document
from .processing_job import ProcessingJob
from .extracted_entity import ExtractedEntity
from .ontology_mapping import OntologyMapping
from .text_segment import TextSegment

__all__ = [
    'User', 
    'Document', 
    'ProcessingJob', 
    'ExtractedEntity', 
    'OntologyMapping', 
    'TextSegment'
]
