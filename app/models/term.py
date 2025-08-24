from sqlalchemy import text, func
from sqlalchemy.dialects.postgresql import UUID, JSON, ARRAY
from datetime import datetime
from app import db
import uuid

# Association table for many-to-many relationship between term versions and context anchors
term_version_anchors = db.Table('term_version_anchors',
    db.Column('id', UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
    db.Column('term_version_id', UUID(as_uuid=True), db.ForeignKey('term_versions.id'), nullable=False),
    db.Column('context_anchor_id', UUID(as_uuid=True), db.ForeignKey('context_anchors.id'), nullable=False),
    db.Column('similarity_score', db.Numeric(4,3)),
    db.Column('rank_in_neighborhood', db.Integer),
    db.Column('created_at', db.DateTime(timezone=True), default=datetime.utcnow),
    db.UniqueConstraint('term_version_id', 'context_anchor_id')
)


class Term(db.Model):
    """Core terms model for storing anchor terms for semantic change analysis"""
    
    __tablename__ = 'terms'
    
    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    term_text = db.Column(db.String(255), nullable=False)
    entry_date = db.Column(db.DateTime(timezone=True), default=datetime.utcnow)
    status = db.Column(db.String(20), default='active', nullable=False)
    
    # Foreign keys
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), index=True)
    updated_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    
    # Timestamps
    created_at = db.Column(db.DateTime(timezone=True), default=datetime.utcnow)
    updated_at = db.Column(db.DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Metadata
    description = db.Column(db.Text)
    etymology = db.Column(db.Text)
    notes = db.Column(db.Text)
    
    # Research context
    research_domain = db.Column(db.String(100), index=True)
    selection_rationale = db.Column(db.Text)
    historical_significance = db.Column(db.Text)
    
    # Relationships
    versions = db.relationship('TermVersion', backref='term', lazy='dynamic', cascade='all, delete-orphan')
    creator = db.relationship('User', foreign_keys=[created_by], backref='created_terms')
    updater = db.relationship('User', foreign_keys=[updated_by], backref='updated_terms')
    
    # Constraints
    __table_args__ = (
        db.UniqueConstraint('term_text', 'created_by'),
        db.CheckConstraint("status IN ('active', 'provisional', 'deprecated')")
    )
    
    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
    
    def get_current_version(self):
        """Get the current version of the term"""
        return self.versions.filter_by(is_current=True).first()
    
    def get_all_versions_ordered(self):
        """Get all versions ordered by temporal period"""
        return self.versions.order_by(TermVersion.temporal_start_year.asc()).all()
    
    def get_version_count(self):
        """Get total number of versions"""
        return self.versions.count()
    
    def has_provisional_versions(self):
        """Check if term has any provisional versions"""
        return self.versions.filter_by(confidence_level='low').count() > 0
    
    def get_semantic_drift_activities(self):
        """Get all semantic drift activities involving this term"""
        from app.models.semantic_drift import SemanticDriftActivity
        version_ids = [v.id for v in self.versions]
        return SemanticDriftActivity.query.filter(
            (SemanticDriftActivity.used_entity.in_(version_ids)) |
            (SemanticDriftActivity.generated_entity.in_(version_ids))
        ).all()
    
    def to_dict(self, include_versions=False):
        """Convert term to dictionary for API responses"""
        current_version = self.get_current_version()
        result = {
            'id': str(self.id),
            'term_text': self.term_text,
            'status': self.status,
            'entry_date': self.entry_date.isoformat() if self.entry_date else None,
            'description': self.description,
            'etymology': self.etymology,
            'notes': self.notes,
            'research_domain': self.research_domain,
            'selection_rationale': self.selection_rationale,
            'historical_significance': self.historical_significance,
            'version_count': self.get_version_count(),
            'has_provisional_versions': self.has_provisional_versions(),
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'creator': self.creator.username if self.creator else None
        }
        
        if current_version:
            result['current_version'] = {
                'temporal_period': current_version.temporal_period,
                'meaning_description': current_version.meaning_description,
                'fuzziness_score': float(current_version.fuzziness_score) if current_version.fuzziness_score else None,
                'confidence_level': current_version.confidence_level
            }
        
        if include_versions:
            result['versions'] = [v.to_dict() for v in self.get_all_versions_ordered()]
        
        return result
    
    @staticmethod
    def search_terms(query, status=None, research_domain=None, created_by=None):
        """Search terms with various filters"""
        filters = []
        
        if query:
            filters.append(Term.term_text.ilike(f'%{query}%'))
        if status:
            filters.append(Term.status == status)
        if research_domain:
            filters.append(Term.research_domain == research_domain)
        if created_by:
            filters.append(Term.created_by == created_by)
        
        if filters:
            return Term.query.filter(*filters).order_by(Term.term_text)
        return Term.query.order_by(Term.term_text)
    
    def __repr__(self):
        return f'<Term {self.term_text}>'


class TermVersion(db.Model):
    """PROV-O Entity: Different temporal versions of term meanings"""
    
    __tablename__ = 'term_versions'
    
    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    term_id = db.Column(UUID(as_uuid=True), db.ForeignKey('terms.id'), nullable=False, index=True)
    
    # Temporal context
    temporal_period = db.Column(db.String(50), nullable=False, index=True)
    temporal_start_year = db.Column(db.Integer, index=True)
    temporal_end_year = db.Column(db.Integer, index=True)
    
    # Semantic content
    meaning_description = db.Column(db.Text, nullable=False)
    context_anchor = db.Column(JSON)  # Array of related terms
    original_context_anchor = db.Column(JSON)  # Preserved original neighborhood
    
    # Fuzziness and uncertainty metrics
    fuzziness_score = db.Column(db.Numeric(4,3))
    confidence_level = db.Column(db.String(10), default='medium')
    certainty_notes = db.Column(db.Text)
    
    # Corpus and source information
    corpus_source = db.Column(db.String(100), index=True)
    source_documents = db.Column(JSON)
    extraction_method = db.Column(db.String(50))
    
    # PROV-O compliance
    generated_at_time = db.Column(db.DateTime(timezone=True), default=datetime.utcnow)
    was_derived_from = db.Column(UUID(as_uuid=True), db.ForeignKey('term_versions.id'))
    derivation_type = db.Column(db.String(30))
    
    # Version control
    version_number = db.Column(db.Integer, default=1)
    is_current = db.Column(db.Boolean, default=True, index=True)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    created_at = db.Column(db.DateTime(timezone=True), default=datetime.utcnow)
    
    # Semantic neighborhood analysis
    neighborhood_overlap = db.Column(db.Numeric(4,3))
    positional_change = db.Column(db.Numeric(4,3))
    similarity_reduction = db.Column(db.Numeric(4,3))
    
    # Relationships
    creator = db.relationship('User', backref='created_term_versions')
    parent_version = db.relationship('TermVersion', remote_side=[id], backref='derived_versions')
    context_anchors = db.relationship('ContextAnchor', secondary=term_version_anchors, 
                                    backref='term_versions', lazy='dynamic')
    
    # Constraints
    __table_args__ = (
        db.CheckConstraint("confidence_level IN ('high', 'medium', 'low')"),
        db.CheckConstraint("fuzziness_score >= 0 AND fuzziness_score <= 1"),
        db.CheckConstraint("neighborhood_overlap >= 0 AND neighborhood_overlap <= 1"),
        db.CheckConstraint("positional_change >= 0 AND positional_change <= 1"),
        db.CheckConstraint("similarity_reduction >= 0 AND similarity_reduction <= 1")
    )
    
    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
    
    def add_context_anchor(self, anchor_term, similarity_score=None, rank=None):
        """Add a context anchor term to this version"""
        from app.models.context_anchor import ContextAnchor
        anchor = ContextAnchor.get_or_create(anchor_term)
        
        # Check if already exists
        existing = db.session.execute(
            text("SELECT 1 FROM term_version_anchors WHERE term_version_id = :version_id AND context_anchor_id = :anchor_id"),
            {'version_id': str(self.id), 'anchor_id': str(anchor.id)}
        ).first()
        
        if not existing:
            db.session.execute(
                text("INSERT INTO term_version_anchors (term_version_id, context_anchor_id, similarity_score, rank_in_neighborhood) VALUES (:version_id, :anchor_id, :score, :rank)"),
                {
                    'version_id': str(self.id), 
                    'anchor_id': str(anchor.id),
                    'score': similarity_score,
                    'rank': rank
                }
            )
    
    def get_context_anchor_terms(self):
        """Get list of context anchor terms"""
        return [anchor.anchor_term for anchor in self.context_anchors]
    
    def get_drift_metrics_summary(self):
        """Get summary of drift metrics for this version"""
        return {
            'neighborhood_overlap': float(self.neighborhood_overlap) if self.neighborhood_overlap else None,
            'positional_change': float(self.positional_change) if self.positional_change else None,
            'similarity_reduction': float(self.similarity_reduction) if self.similarity_reduction else None,
            'fuzziness_score': float(self.fuzziness_score) if self.fuzziness_score else None
        }
    
    def calculate_semantic_stability(self):
        """Calculate overall semantic stability score"""
        metrics = self.get_drift_metrics_summary()
        stable_metrics = [m for m in metrics.values() if m is not None]
        if not stable_metrics:
            return None
        return sum(stable_metrics) / len(stable_metrics)
    
    def to_dict(self, include_anchors=False):
        """Convert version to dictionary for API responses"""
        result = {
            'id': str(self.id),
            'term_id': str(self.term_id),
            'temporal_period': self.temporal_period,
            'temporal_start_year': self.temporal_start_year,
            'temporal_end_year': self.temporal_end_year,
            'meaning_description': self.meaning_description,
            'fuzziness_score': float(self.fuzziness_score) if self.fuzziness_score else None,
            'confidence_level': self.confidence_level,
            'certainty_notes': self.certainty_notes,
            'corpus_source': self.corpus_source,
            'extraction_method': self.extraction_method,
            'version_number': self.version_number,
            'is_current': self.is_current,
            'generated_at_time': self.generated_at_time.isoformat() if self.generated_at_time else None,
            'was_derived_from': str(self.was_derived_from) if self.was_derived_from else None,
            'derivation_type': self.derivation_type,
            'drift_metrics': self.get_drift_metrics_summary(),
            'semantic_stability': self.calculate_semantic_stability(),
            'creator': self.creator.username if self.creator else None
        }
        
        if include_anchors:
            result['context_anchors'] = self.get_context_anchor_terms()
        
        return result
    
    @staticmethod
    def get_by_temporal_range(start_year, end_year):
        """Get versions within a temporal range"""
        return TermVersion.query.filter(
            TermVersion.temporal_start_year <= end_year,
            TermVersion.temporal_end_year >= start_year
        ).all()
    
    def __repr__(self):
        return f'<TermVersion {self.term.term_text} ({self.temporal_period})>'


class FuzzinessAdjustment(db.Model):
    """Audit trail for manual adjustments to fuzziness scores"""
    
    __tablename__ = 'fuzziness_adjustments'
    
    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    term_version_id = db.Column(UUID(as_uuid=True), db.ForeignKey('term_versions.id'), nullable=False, index=True)
    original_score = db.Column(db.Numeric(4,3), nullable=False)
    adjusted_score = db.Column(db.Numeric(4,3), nullable=False)
    adjustment_reason = db.Column(db.Text, nullable=False)
    adjusted_by = db.Column(db.Integer, db.ForeignKey('users.id'), index=True)
    created_at = db.Column(db.DateTime(timezone=True), default=datetime.utcnow)
    
    # Relationships
    term_version = db.relationship('TermVersion', backref='fuzziness_adjustments')
    adjuster = db.relationship('User', backref='fuzziness_adjustments')
    
    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
    
    def to_dict(self):
        """Convert adjustment to dictionary"""
        return {
            'id': str(self.id),
            'term_version_id': str(self.term_version_id),
            'original_score': float(self.original_score),
            'adjusted_score': float(self.adjusted_score),
            'adjustment_reason': self.adjustment_reason,
            'adjusted_by': self.adjuster.username if self.adjuster else None,
            'created_at': self.created_at.isoformat()
        }
    
    def __repr__(self):
        return f'<FuzzinessAdjustment {self.original_score} → {self.adjusted_score}>'