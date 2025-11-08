from app import db

# Import all models here for easy access
from .user import User
from .document import Document
from .processing_job import ProcessingJob
from .extracted_entity import ExtractedEntity
from .ontology_mapping import OntologyMapping
from .text_segment import TextSegment
from .experiment import Experiment

# Experiment-document relationship model
from .experiment_document import ExperimentDocument

# Experiment processing models
from .experiment_processing import ExperimentDocumentProcessing, ProcessingArtifact, DocumentProcessingIndex

# Experiment orchestration models
from .experiment_orchestration_run import ExperimentOrchestrationRun

# Term management models
from .term import Term, TermVersion, FuzzinessAdjustment
from .context_anchor import ContextAnchor
from .semantic_drift import SemanticDriftActivity, AnalysisAgent, ProvenanceChain

# Settings and prompt templates
from .app_settings import AppSetting
from .prompt_template import PromptTemplate

# Temporal experiment models for semantic change analysis
from .temporal_experiment import (
    DocumentTemporalMetadata,
    OEDTimelineMarker,
    TermDisciplinaryDefinition,
    SemanticShiftAnalysis
)

__all__ = [
    'User',
    'Document',
    'ProcessingJob',
    'ExtractedEntity',
    'OntologyMapping',
    'TextSegment',
    'Experiment',
    'ExperimentDocument',
    # Experiment processing models
    'ExperimentDocumentProcessing',
    'ProcessingArtifact',
    'DocumentProcessingIndex',
    # Experiment orchestration models
    'ExperimentOrchestrationRun',
    # Term management models
    'Term',
    'TermVersion',
    'FuzzinessAdjustment',
    'ContextAnchor',
    'SemanticDriftActivity',
    'AnalysisAgent',
    'ProvenanceChain',
    # Settings and templates
    'AppSetting',
    'PromptTemplate',
    # Temporal experiment models
    'DocumentTemporalMetadata',
    'OEDTimelineMarker',
    'TermDisciplinaryDefinition',
    'SemanticShiftAnalysis'
]
