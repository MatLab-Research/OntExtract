from app import db

# Import all models here for easy access
from .user import User
from .document import Document
from .processing_job import ProcessingJob
from .extracted_entity import ExtractedEntity
from .ontology_mapping import OntologyMapping
from .text_segment import TextSegment
from .experiment import Experiment

# Term management models
from .term import Term, TermVersion, FuzzinessAdjustment
from .context_anchor import ContextAnchor
from .semantic_drift import SemanticDriftActivity, AnalysisAgent, ProvenanceChain

__all__ = [
    'User', 
    'Document', 
    'ProcessingJob', 
    'ExtractedEntity', 
    'OntologyMapping', 
    'TextSegment',
    'Experiment',
    # Term management models
    'Term',
    'TermVersion', 
    'FuzzinessAdjustment',
    'ContextAnchor',
    'SemanticDriftActivity',
    'AnalysisAgent',
    'ProvenanceChain'
]
