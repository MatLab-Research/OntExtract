"""
Temporal Experiment Models

Database models for semantic change analysis experiments.
Implements the metacognitive framework from "Managing Semantic Change in Research"
(Rauch et al., 2024)
"""

from sqlalchemy.dialects.postgresql import UUID, JSONB
from datetime import datetime
from app import db
import uuid


class DocumentTemporalMetadata(db.Model):
    """
    Temporal and disciplinary metadata for documents in semantic change experiments.

    Stores classification information that positions documents on timeline and
    identifies their disciplinary contribution to semantic understanding.
    """

    __tablename__ = 'document_temporal_metadata'

    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id = db.Column(db.Integer, db.ForeignKey('documents.id', ondelete='CASCADE'), nullable=False)
    experiment_id = db.Column(db.Integer, db.ForeignKey('experiments.id', ondelete='CASCADE'))

    # Temporal classification
    temporal_period = db.Column(db.String(100))
    temporal_start_year = db.Column(db.Integer)
    temporal_end_year = db.Column(db.Integer)

    # DEPRECATED: Use Document.publication_date instead
    # This field is kept for backward compatibility but new code should use
    # the Document.publication_date field which supports flexible formats (year, year-month, full date)
    publication_year = db.Column(db.Integer)

    # Disciplinary classification
    discipline = db.Column(db.String(100))
    subdiscipline = db.Column(db.String(100))

    # Semantic contribution
    key_definition = db.Column(db.Text)
    semantic_features = db.Column(JSONB)
    semantic_shift_type = db.Column(db.String(50))

    # Timeline visualization
    timeline_position = db.Column(db.Integer)
    timeline_track = db.Column(db.String(50))
    marker_color = db.Column(db.String(20))

    # Metadata extraction
    extraction_method = db.Column(db.String(50))
    extraction_confidence = db.Column(db.Numeric(3, 2))
    reviewed_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    reviewed_at = db.Column(db.DateTime(timezone=True))

    created_at = db.Column(db.DateTime(timezone=True), default=datetime.utcnow)
    updated_at = db.Column(db.DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    document = db.relationship('Document', foreign_keys=[document_id], passive_deletes=True)
    experiment = db.relationship('Experiment', foreign_keys=[experiment_id], passive_deletes=True)
    reviewer = db.relationship('User', foreign_keys=[reviewed_by])

    __table_args__ = (
        db.UniqueConstraint('document_id', 'experiment_id', name='uq_doc_experiment_temporal'),
    )

    def to_dict(self):
        """Convert to dictionary for API responses"""
        return {
            'id': str(self.id),
            'document_id': self.document_id,
            'experiment_id': self.experiment_id,
            'temporal_period': self.temporal_period,
            'publication_year': self.publication_year,
            'discipline': self.discipline,
            'subdiscipline': self.subdiscipline,
            'key_definition': self.key_definition,
            'semantic_features': self.semantic_features,
            'timeline_track': self.timeline_track,
            'reviewed': self.reviewed_by is not None
        }


class OEDTimelineMarker(db.Model):
    """
    Historical timeline data extracted from OED entries for anchor terms.

    Each marker represents a point in time where the term's meaning or usage
    is documented in the OED (etymology, sense, quotation).
    """

    __tablename__ = 'oed_timeline_markers'

    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    term_id = db.Column(UUID(as_uuid=True), db.ForeignKey('terms.id', ondelete='CASCADE'), nullable=False)

    # Temporal information
    year = db.Column(db.Integer)
    period_label = db.Column(db.String(100))
    century = db.Column(db.Integer)

    # Sense/definition information
    sense_number = db.Column(db.String(20))
    definition = db.Column(db.Text, nullable=False)
    definition_short = db.Column(db.Text)

    # Historical attestation
    first_recorded_use = db.Column(db.Text)
    quotation_date = db.Column(db.String(50))
    quotation_author = db.Column(db.String(200))
    quotation_work = db.Column(db.String(200))

    # Semantic classification
    semantic_category = db.Column(db.String(100))
    etymology_note = db.Column(db.Text)

    # Timeline visualization
    marker_type = db.Column(db.String(50))
    display_order = db.Column(db.Integer)

    # Source tracking
    oed_entry_id = db.Column(db.String(100))
    extraction_date = db.Column(db.DateTime(timezone=True), default=datetime.utcnow)
    extracted_by = db.Column(db.String(50))

    created_at = db.Column(db.DateTime(timezone=True), default=datetime.utcnow)

    # Relationships
    term = db.relationship('Term', backref='oed_timeline_markers')

    __table_args__ = (
        db.UniqueConstraint('term_id', 'sense_number', 'year', name='uq_term_sense_year'),
    )

    def to_dict(self):
        """Convert to dictionary for API responses"""
        return {
            'id': str(self.id),
            'term_id': str(self.term_id),
            'year': self.year,
            'period_label': self.period_label,
            'sense_number': self.sense_number,
            'definition': self.definition,
            'definition_short': self.definition_short,
            'quotation': {
                'date': self.quotation_date,
                'author': self.quotation_author,
                'work': self.quotation_work,
                'text': self.first_recorded_use
            } if self.first_recorded_use else None,
            'semantic_category': self.semantic_category,
            'marker_type': self.marker_type
        }


class TermDisciplinaryDefinition(db.Model):
    """
    Disciplinary definitions for metacognitive framework comparison tables.

    Stores how each discipline defines the term, enabling the parallel meanings
    comparison from paper pp. 10-13.
    """

    __tablename__ = 'term_disciplinary_definitions'

    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    term_id = db.Column(UUID(as_uuid=True), db.ForeignKey('terms.id', ondelete='CASCADE'), nullable=False)
    experiment_id = db.Column(db.Integer, db.ForeignKey('experiments.id', ondelete='CASCADE'))

    # Disciplinary context
    discipline = db.Column(db.String(100), nullable=False)
    definition = db.Column(db.Text, nullable=False)
    source_text = db.Column(db.Text)
    source_type = db.Column(db.String(50))

    # Temporal context
    period_label = db.Column(db.String(100))
    start_year = db.Column(db.Integer)
    end_year = db.Column(db.Integer)

    # Semantic analysis
    key_features = db.Column(JSONB)
    distinguishing_features = db.Column(db.Text)
    parallel_meanings = db.Column(JSONB)
    potential_confusion = db.Column(db.Text)

    # Document reference
    document_id = db.Column(db.Integer, db.ForeignKey('documents.id', ondelete='SET NULL'))

    # Metacognitive framework
    resolution_notes = db.Column(db.Text)

    created_at = db.Column(db.DateTime(timezone=True), default=datetime.utcnow)
    updated_at = db.Column(db.DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    term = db.relationship('Term', backref='disciplinary_definitions')
    experiment = db.relationship('Experiment', backref='disciplinary_definitions')
    document = db.relationship('Document', backref='disciplinary_definitions')

    def to_dict(self):
        """Convert to dictionary for API responses"""
        return {
            'id': str(self.id),
            'discipline': self.discipline,
            'definition': self.definition,
            'source': self.source_text,
            'period': self.period_label,
            'year_range': {
                'start': self.start_year,
                'end': self.end_year
            } if self.start_year or self.end_year else None,
            'key_features': self.key_features,
            'distinguishing_features': self.distinguishing_features,
            'potential_confusion': self.potential_confusion
        }


class SemanticShiftAnalysis(db.Model):
    """
    Identified semantic shifts and evolution patterns.

    Tracks diachronic changes, polysemy, interdisciplinary tensions, and
    disciplinary capture instances.
    """

    __tablename__ = 'semantic_shift_analysis'

    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    experiment_id = db.Column(db.Integer, db.ForeignKey('experiments.id', ondelete='CASCADE'), nullable=False)
    term_id = db.Column(UUID(as_uuid=True), db.ForeignKey('terms.id', ondelete='CASCADE'), nullable=False)

    # Shift identification
    shift_type = db.Column(db.String(50), nullable=False)
    from_period = db.Column(db.String(100))
    to_period = db.Column(db.String(100))
    from_discipline = db.Column(db.String(100))
    to_discipline = db.Column(db.String(100))

    # Shift description
    description = db.Column(db.Text, nullable=False)
    evidence = db.Column(db.Text)

    # Linked entities
    from_document_id = db.Column(db.Integer, db.ForeignKey('documents.id', ondelete='SET NULL'))
    to_document_id = db.Column(db.Integer, db.ForeignKey('documents.id', ondelete='SET NULL'))
    from_definition_id = db.Column(UUID(as_uuid=True), db.ForeignKey('term_disciplinary_definitions.id', ondelete='SET NULL'))
    to_definition_id = db.Column(UUID(as_uuid=True), db.ForeignKey('term_disciplinary_definitions.id', ondelete='SET NULL'))

    # Visualization
    edge_type = db.Column(db.String(50))
    edge_label = db.Column(db.Text)

    # Analysis metadata
    detected_by = db.Column(db.String(50))
    confidence = db.Column(db.Numeric(3, 2))

    created_at = db.Column(db.DateTime(timezone=True), default=datetime.utcnow)

    # Relationships
    experiment = db.relationship('Experiment', backref='semantic_shifts')
    term = db.relationship('Term', backref='semantic_shifts')
    from_document = db.relationship('Document', foreign_keys=[from_document_id], backref='shifts_as_source')
    to_document = db.relationship('Document', foreign_keys=[to_document_id], backref='shifts_as_target')
    from_definition = db.relationship('TermDisciplinaryDefinition', foreign_keys=[from_definition_id], backref='shifts_as_source_def')
    to_definition = db.relationship('TermDisciplinaryDefinition', foreign_keys=[to_definition_id], backref='shifts_as_target_def')

    def to_dict(self):
        """Convert to dictionary for API responses"""
        return {
            'id': str(self.id),
            'shift_type': self.shift_type,
            'from_period': self.from_period,
            'to_period': self.to_period,
            'from_discipline': self.from_discipline,
            'to_discipline': self.to_discipline,
            'description': self.description,
            'evidence': self.evidence,
            'edge_type': self.edge_type,
            'confidence': float(self.confidence) if self.confidence else None
        }
