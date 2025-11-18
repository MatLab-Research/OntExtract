from datetime import datetime
from sqlalchemy.dialects.postgresql import UUID
from app import db
import uuid
import json

class ExperimentDocumentProcessing(db.Model):
    """Stores individual processing operations applied to documents within experiments"""

    __tablename__ = 'experiment_document_processing'

    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Foreign keys
    experiment_document_id = db.Column(db.Integer, db.ForeignKey('experiment_documents_v2.id'), nullable=False, index=True)

    # Processing details
    processing_type = db.Column(db.String(50), nullable=False)  # 'embeddings', 'segmentation', 'entities'
    processing_method = db.Column(db.String(50), nullable=False)  # 'openai', 'local', 'paragraph', 'sentence', etc.

    # Status tracking
    status = db.Column(db.String(20), default='pending', nullable=False)  # 'pending', 'running', 'completed', 'failed'

    # Configuration and results
    configuration_json = db.Column(db.Text)  # JSON of parameters used
    results_summary_json = db.Column(db.Text)  # JSON summary of results (counts, metrics, etc.)
    error_message = db.Column(db.Text)  # Error details if failed

    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    started_at = db.Column(db.DateTime)
    completed_at = db.Column(db.DateTime)

    # Relationships
    experiment_document = db.relationship('ExperimentDocument', backref='processing_operations')

    def get_configuration(self):
        """Get configuration as dict"""
        if self.configuration_json:
            try:
                return json.loads(self.configuration_json)
            except json.JSONDecodeError:
                return {}
        return {}

    def set_configuration(self, config_dict):
        """Set configuration from dict"""
        self.configuration_json = json.dumps(config_dict)

    def get_results_summary(self):
        """Get results summary as dict"""
        if self.results_summary_json:
            try:
                return json.loads(self.results_summary_json)
            except json.JSONDecodeError:
                return {}
        return {}

    def set_results_summary(self, results_dict):
        """Set results summary from dict"""
        self.results_summary_json = json.dumps(results_dict)

    def mark_started(self):
        """Mark processing as started"""
        self.status = 'running'
        self.started_at = datetime.utcnow()

    def mark_completed(self, results_summary=None):
        """Mark processing as completed"""
        self.status = 'completed'
        self.completed_at = datetime.utcnow()
        if results_summary:
            self.set_results_summary(results_summary)

    def mark_failed(self, error_message):
        """Mark processing as failed"""
        self.status = 'failed'
        self.completed_at = datetime.utcnow()
        self.error_message = error_message

    def to_dict(self):
        """Convert to dictionary for API responses"""
        return {
            'id': str(self.id),
            'experiment_document_id': self.experiment_document_id,
            'processing_type': self.processing_type,
            'processing_method': self.processing_method,
            'status': self.status,
            'configuration': self.get_configuration(),
            'results_summary': self.get_results_summary(),
            'error_message': self.error_message,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None
        }

    def __repr__(self):
        return f'<ExperimentProcessing {self.processing_type}:{self.processing_method} status:{self.status}>'


class ProcessingArtifact(db.Model):
    """Stores the actual results of processing operations (segments, embeddings, entities)"""

    __tablename__ = 'processing_artifacts'

    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Links to the processing operation that created this artifact
    processing_id = db.Column(UUID(as_uuid=True), db.ForeignKey('experiment_document_processing.id'), nullable=False, index=True)

    # Links to the original document for reference
    document_id = db.Column(db.Integer, db.ForeignKey('documents.id'), nullable=False, index=True)

    # Artifact details
    artifact_type = db.Column(db.String(50), nullable=False)  # 'text_segment', 'embedding_vector', 'extracted_entity'
    artifact_index = db.Column(db.Integer)  # Order/position within the processing result set

    # Content storage
    content_json = db.Column(db.Text)  # The actual artifact data (segment text, embedding vector, entity data)
    metadata_json = db.Column(db.Text)  # Additional metadata (positions, confidence scores, etc.)

    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    processing_operation = db.relationship('ExperimentDocumentProcessing', backref='artifacts')
    document = db.relationship('Document', backref='processing_artifacts')

    def get_content(self):
        """Get content as dict"""
        if self.content_json:
            try:
                return json.loads(self.content_json)
            except json.JSONDecodeError:
                return {}
        return {}

    def set_content(self, content_dict):
        """Set content from dict"""
        try:
            self.content_json = json.dumps(content_dict)
        except TypeError as e:
            # If JSON serialization fails, try to identify the problem
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Failed to serialize content_dict: {e}")
            logger.error(f"Content dict keys: {content_dict.keys() if hasattr(content_dict, 'keys') else 'N/A'}")
            # Try to serialize individual items to find the culprit
            if hasattr(content_dict, 'items'):
                for key, value in content_dict.items():
                    try:
                        json.dumps({key: value})
                    except TypeError:
                        logger.error(f"Non-serializable value for key '{key}': {type(value)} - {value}")
            raise

    def get_metadata(self):
        """Get metadata as dict"""
        if self.metadata_json:
            try:
                return json.loads(self.metadata_json)
            except json.JSONDecodeError:
                return {}
        return {}

    def set_metadata(self, metadata_dict):
        """Set metadata from dict"""
        try:
            self.metadata_json = json.dumps(metadata_dict)
        except TypeError as e:
            # If JSON serialization fails, try to identify the problem
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Failed to serialize metadata_dict: {e}")
            logger.error(f"Metadata dict keys: {metadata_dict.keys() if hasattr(metadata_dict, 'keys') else 'N/A'}")
            # Try to serialize individual items to find the culprit
            if hasattr(metadata_dict, 'items'):
                for key, value in metadata_dict.items():
                    try:
                        json.dumps({key: value})
                    except TypeError:
                        logger.error(f"Non-serializable value for key '{key}': {type(value)} - {value}")
            raise

    def to_dict(self):
        """Convert to dictionary for API responses"""
        return {
            'id': str(self.id),
            'processing_id': str(self.processing_id),
            'document_id': self.document_id,
            'artifact_type': self.artifact_type,
            'artifact_index': self.artifact_index,
            'content': self.get_content(),
            'metadata': self.get_metadata(),
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

    def __repr__(self):
        return f'<ProcessingArtifact {self.artifact_type} idx:{self.artifact_index}>'


class DocumentProcessingIndex(db.Model):
    """Index table for quickly finding all processing done on a document across experiments"""

    __tablename__ = 'document_processing_index'

    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Foreign keys
    document_id = db.Column(db.Integer, db.ForeignKey('documents.id'), nullable=False, index=True)
    experiment_id = db.Column(db.Integer, db.ForeignKey('experiments.id'), nullable=False, index=True)
    processing_id = db.Column(UUID(as_uuid=True), db.ForeignKey('experiment_document_processing.id'), nullable=False, index=True)

    # Quick lookup fields (denormalized for performance)
    processing_type = db.Column(db.String(50), nullable=False, index=True)
    processing_method = db.Column(db.String(50), nullable=False)
    status = db.Column(db.String(20), nullable=False, index=True)

    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    document = db.relationship('Document')
    experiment = db.relationship('Experiment')
    processing_operation = db.relationship('ExperimentDocumentProcessing')

    # Unique constraint to prevent duplicates
    __table_args__ = (
        db.UniqueConstraint('document_id', 'processing_id', name='unique_doc_processing'),
        db.Index('idx_document_processing_lookup', 'document_id', 'processing_type', 'status'),
    )

    def to_dict(self):
        """Convert to dictionary for API responses"""
        return {
            'id': str(self.id),
            'document_id': self.document_id,
            'experiment_id': self.experiment_id,
            'processing_id': str(self.processing_id),
            'processing_type': self.processing_type,
            'processing_method': self.processing_method,
            'status': self.status,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

    def __repr__(self):
        return f'<DocProcessingIndex doc:{self.document_id} exp:{self.experiment_id} {self.processing_type}:{self.processing_method}>'