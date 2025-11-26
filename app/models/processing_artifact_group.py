from datetime import datetime
from app import db

class ProcessingArtifactGroup(db.Model):
    """Logical grouping of processing artifacts (segments, embeddings, entities, etc.) for a document.

    A group represents one execution of a specific method on a document (hub) or a derived version.
    Enables coexistence of multiple segmentation / embedding strategies and explicit provenance.
    """

    __tablename__ = 'processing_artifact_groups'

    id = db.Column(db.Integer, primary_key=True)

    # Core identification
    # ondelete='CASCADE' ensures DB-level cascade when document is deleted
    document_id = db.Column(db.Integer, db.ForeignKey('documents.id', ondelete='CASCADE'), nullable=False, index=True)
    artifact_type = db.Column(db.String(40), nullable=False, index=True)  # segmentation, embeddings, entities, temporal, etc.
    method_key = db.Column(db.String(100), nullable=False)  # e.g. sent_spacy_v1, paragraph_basic, openai_text-embedding-3-large

    # Provenance / dependency
    processing_job_id = db.Column(db.Integer, db.ForeignKey('processing_jobs.id'), index=True)
    parent_method_keys = db.Column(db.JSON)  # JSON array of method_keys this output depends on

    # Configuration & metrics
    # Use metadata_json attribute name; underlying column still named 'metadata'
    metadata_json = db.Column('metadata', db.JSON)  # params, quality metrics, versions
    include_in_composite = db.Column(db.Boolean, default=True, nullable=False)
    status = db.Column(db.String(20), default='completed', index=True)  # pending, running, completed, failed

    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Uniqueness constraint: one method_key per document per artifact_type
    __table_args__ = (
        db.UniqueConstraint('document_id', 'artifact_type', 'method_key', name='uq_artifact_group_method'),
    )

    # Relationships (lazy backrefs defined on related models if needed later)
    # passive_deletes=True lets DB handle cascade delete (via ondelete='CASCADE')
    document = db.relationship('Document', backref=db.backref('artifact_groups', lazy='dynamic', passive_deletes=True))
    processing_job = db.relationship('ProcessingJob', backref=db.backref('artifact_groups', lazy='dynamic'))

    def to_dict(self):
        return {
            'id': self.id,
            'document_id': self.document_id,
            'artifact_type': self.artifact_type,
            'method_key': self.method_key,
            'processing_job_id': self.processing_job_id,
            'parent_method_keys': self.parent_method_keys or [],
            'metadata': self.metadata_json or {},
            'include_in_composite': self.include_in_composite,
            'status': self.status,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }

    def mark_failed(self, reason=None):
        self.status = 'failed'
        if self.metadata_json is None:
            self.metadata_json = {}
        if reason:
            self.metadata_json['failure_reason'] = reason
        db.session.commit()

    def mark_running(self):
        self.status = 'running'
        db.session.commit()

    def mark_completed(self, extra_metadata=None):
        self.status = 'completed'
        if extra_metadata:
            if self.metadata_json is None:
                self.metadata_json = {}
            self.metadata_json.update(extra_metadata)
        db.session.commit()

    def __repr__(self):
        return f'<ProcessingArtifactGroup {self.id} {self.document_id}:{self.artifact_type}:{self.method_key}>'
