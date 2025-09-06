from sqlalchemy.dialects.postgresql import UUID, JSON
from datetime import datetime
from app import db
import uuid


class OEDEtymology(db.Model):
    """PROV-O Entity: OED etymology data for terms - origin and language family information"""
    
    __tablename__ = 'oed_etymology'
    
    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    term_id = db.Column(UUID(as_uuid=True), db.ForeignKey('terms.id', ondelete='CASCADE'), nullable=False)
    etymology_text = db.Column(db.Text)
    origin_language = db.Column(db.String(50))
    first_recorded_year = db.Column(db.Integer)
    etymology_confidence = db.Column(db.String(20), default='medium')
    
    # JSON fields for structured data that doesn't violate OED license
    language_family = db.Column(JSON)  # e.g. {"family": "Germanic", "branch": "West Germanic"}
    root_analysis = db.Column(JSON)    # e.g. {"roots": ["ag-", "ent"], "meaning": "to drive, to act"}
    morphology = db.Column(JSON)       # e.g. {"suffixes": ["-ent"], "type": "agent_noun"}
    
    # PROV-O Entity metadata
    generated_at_time = db.Column(db.DateTime(timezone=True), default=datetime.utcnow)
    was_attributed_to = db.Column(db.String(100), default='OED_API_Service')  # prov:wasAttributedTo
    was_derived_from = db.Column(db.String(200))  # OED entry ID or source reference
    derivation_type = db.Column(db.String(50), default='etymology_extraction')
    source_version = db.Column(db.String(50))  # OED version/edition
    
    # System metadata
    created_at = db.Column(db.DateTime(timezone=True), default=datetime.utcnow)
    updated_at = db.Column(db.DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    term = db.relationship('Term', backref='oed_etymology')
    
    # Constraints
    __table_args__ = (
        db.CheckConstraint("etymology_confidence IN ('high', 'medium', 'low')"),
    )
    
    def to_dict(self):
        return {
            'id': str(self.id),
            'term_id': str(self.term_id),
            'etymology_text': self.etymology_text,
            'origin_language': self.origin_language,
            'first_recorded_year': self.first_recorded_year,
            'etymology_confidence': self.etymology_confidence,
            'language_family': self.language_family,
            'root_analysis': self.root_analysis,
            'morphology': self.morphology,
            'source_version': self.source_version,
            # PROV-O metadata
            'generated_at_time': self.generated_at_time.isoformat() if self.generated_at_time else None,
            'was_attributed_to': self.was_attributed_to,
            'was_derived_from': self.was_derived_from,
            'derivation_type': self.derivation_type,
            # System metadata
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class OEDDefinition(db.Model):
    """PROV-O Entity: Historical definitions from OED with temporal context"""
    
    __tablename__ = 'oed_definitions'
    
    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    term_id = db.Column(UUID(as_uuid=True), db.ForeignKey('terms.id', ondelete='CASCADE'), nullable=False)
    definition_number = db.Column(db.String(10))  # e.g. "1.a", "2.b"
    definition_excerpt = db.Column(db.String(300))  # Only first 300 chars
    oed_sense_id = db.Column(db.String(100))  # OED internal sense ID for linking
    oed_url = db.Column(db.String(500))  # Direct link to OED entry/sense
    first_cited_year = db.Column(db.Integer)
    last_cited_year = db.Column(db.Integer)
    part_of_speech = db.Column(db.String(30))
    domain_label = db.Column(db.String(100))  # e.g. "Law", "Philosophy", "Computing"
    status = db.Column(db.String(20), default='current')  # 'current', 'historical', 'obsolete'
    
    # Summary statistics (allowed under fair use)
    quotation_count = db.Column(db.Integer)
    sense_frequency_rank = db.Column(db.Integer)
    
    # Temporal context
    historical_period = db.Column(db.String(50))  # aligned with existing temporal_period
    period_start_year = db.Column(db.Integer)
    period_end_year = db.Column(db.Integer)
    
    # PROV-O Entity metadata
    generated_at_time = db.Column(db.DateTime(timezone=True), default=datetime.utcnow)
    was_attributed_to = db.Column(db.String(100), default='OED_API_Service')
    was_derived_from = db.Column(db.String(200))  # OED entry ID and sense reference
    derivation_type = db.Column(db.String(50), default='definition_extraction')
    definition_confidence = db.Column(db.String(20), default='high')
    
    # System metadata
    created_at = db.Column(db.DateTime(timezone=True), default=datetime.utcnow)
    updated_at = db.Column(db.DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    term = db.relationship('Term', backref='oed_definitions')
    
    # Constraints
    __table_args__ = (
        db.CheckConstraint("definition_confidence IN ('high', 'medium', 'low')"),
        db.CheckConstraint("status IN ('current', 'historical', 'obsolete')"),
        db.Index('idx_oed_definitions_temporal', 'first_cited_year', 'last_cited_year'),
        db.Index('idx_oed_definitions_period', 'historical_period')
    )
    
    def to_dict(self):
        return {
            'id': str(self.id),
            'term_id': str(self.term_id),
            'definition_number': self.definition_number,
            'definition_excerpt': self.definition_excerpt,
            'oed_sense_id': self.oed_sense_id,
            'oed_url': self.oed_url,
            'first_cited_year': self.first_cited_year,
            'last_cited_year': self.last_cited_year,
            'part_of_speech': self.part_of_speech,
            'domain_label': self.domain_label,
            'status': self.status,
            'quotation_count': self.quotation_count,
            'sense_frequency_rank': self.sense_frequency_rank,
            'historical_period': self.historical_period,
            'period_start_year': self.period_start_year,
            'period_end_year': self.period_end_year,
            'definition_confidence': self.definition_confidence,
            # PROV-O metadata
            'generated_at_time': self.generated_at_time.isoformat() if self.generated_at_time else None,
            'was_attributed_to': self.was_attributed_to,
            'was_derived_from': self.was_derived_from,
            'derivation_type': self.derivation_type,
            # System metadata
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class OEDHistoricalStats(db.Model):
    """PROV-O Activity: Aggregated statistics calculation for semantic evolution analysis"""
    
    __tablename__ = 'oed_historical_stats'
    
    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    term_id = db.Column(UUID(as_uuid=True), db.ForeignKey('terms.id', ondelete='CASCADE'), nullable=False)
    time_period = db.Column(db.String(50), nullable=False)
    start_year = db.Column(db.Integer, nullable=False)
    end_year = db.Column(db.Integer, nullable=False)
    
    # Usage statistics (aggregated, non-infringing)
    definition_count = db.Column(db.Integer, default=0)
    sense_count = db.Column(db.Integer, default=0)
    quotation_span_years = db.Column(db.Integer)  # latest - earliest quotation
    earliest_quotation_year = db.Column(db.Integer)
    latest_quotation_year = db.Column(db.Integer)
    
    # Evolution indicators
    semantic_stability_score = db.Column(db.Numeric(4,3))  # calculated from definition changes
    domain_shift_indicator = db.Column(db.Boolean, default=False)
    part_of_speech_changes = db.Column(JSON)  # e.g. ["noun", "verb"] for flexibility changes
    
    # PROV-O Activity metadata
    started_at_time = db.Column(db.DateTime(timezone=True), default=datetime.utcnow)
    ended_at_time = db.Column(db.DateTime(timezone=True), default=datetime.utcnow)
    was_associated_with = db.Column(db.String(100), default='Statistical_Analysis_Service')  # prov:wasAssociatedWith
    used_entity = db.Column(JSON)  # References to OED definitions and quotations used
    generated_entity = db.Column(db.String(200))  # This statistics record itself
    oed_edition = db.Column(db.String(50))
    
    # System metadata
    created_at = db.Column(db.DateTime(timezone=True), default=datetime.utcnow)
    updated_at = db.Column(db.DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    term = db.relationship('Term', backref='oed_historical_stats')
    
    # Constraints
    __table_args__ = (
        db.CheckConstraint("semantic_stability_score >= 0 AND semantic_stability_score <= 1"),
        db.UniqueConstraint('term_id', 'time_period'),
        db.Index('idx_oed_historical_stats_term_period', 'term_id', 'start_year', 'end_year')
    )
    
    def to_dict(self):
        return {
            'id': str(self.id),
            'term_id': str(self.term_id),
            'time_period': self.time_period,
            'start_year': self.start_year,
            'end_year': self.end_year,
            'definition_count': self.definition_count,
            'sense_count': self.sense_count,
            'quotation_span_years': self.quotation_span_years,
            'earliest_quotation_year': self.earliest_quotation_year,
            'latest_quotation_year': self.latest_quotation_year,
            'semantic_stability_score': float(self.semantic_stability_score) if self.semantic_stability_score else None,
            'domain_shift_indicator': self.domain_shift_indicator,
            'part_of_speech_changes': self.part_of_speech_changes,
            'oed_edition': self.oed_edition,
            # PROV-O Activity metadata
            'started_at_time': self.started_at_time.isoformat() if self.started_at_time else None,
            'ended_at_time': self.ended_at_time.isoformat() if self.ended_at_time else None,
            'was_associated_with': self.was_associated_with,
            'used_entity': self.used_entity,
            'generated_entity': self.generated_entity,
            # System metadata
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class OEDQuotationSummary(db.Model):
    """PROV-O Entity: Essential quotation metadata without full text - respects OED licensing"""
    
    __tablename__ = 'oed_quotation_summaries'
    
    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    term_id = db.Column(UUID(as_uuid=True), db.ForeignKey('terms.id', ondelete='CASCADE'), nullable=False)
    oed_definition_id = db.Column(UUID(as_uuid=True), db.ForeignKey('oed_definitions.id', ondelete='CASCADE'))
    quotation_year = db.Column(db.Integer)
    author_name = db.Column(db.String(200))
    work_title = db.Column(db.String(300))
    domain_context = db.Column(db.String(100))  # inferred domain from work
    usage_type = db.Column(db.String(50))  # e.g. "literal", "metaphorical", "technical"
    
    # Metadata only, no full text to respect licensing
    has_technical_usage = db.Column(db.Boolean, default=False)
    represents_semantic_shift = db.Column(db.Boolean, default=False)
    chronological_rank = db.Column(db.Integer)  # position in temporal sequence
    
    # PROV-O Entity metadata
    generated_at_time = db.Column(db.DateTime(timezone=True), default=datetime.utcnow)
    was_attributed_to = db.Column(db.String(100), default='OED_Quotation_Extractor')
    was_derived_from = db.Column(db.String(200))  # Original OED quotation reference
    derivation_type = db.Column(db.String(50), default='metadata_extraction')
    
    # System metadata
    created_at = db.Column(db.DateTime(timezone=True), default=datetime.utcnow)
    updated_at = db.Column(db.DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    term = db.relationship('Term', backref='oed_quotation_summaries')
    oed_definition = db.relationship('OEDDefinition', backref='quotation_summaries')
    
    # Constraints
    __table_args__ = (
        db.Index('idx_oed_quotations_term_year', 'term_id', 'quotation_year'),
        db.Index('idx_oed_quotations_chronological', 'term_id', 'chronological_rank')
    )
    
    def to_dict(self):
        return {
            'id': str(self.id),
            'term_id': str(self.term_id),
            'oed_definition_id': str(self.oed_definition_id) if self.oed_definition_id else None,
            'quotation_year': self.quotation_year,
            'author_name': self.author_name,
            'work_title': self.work_title,
            'domain_context': self.domain_context,
            'usage_type': self.usage_type,
            'has_technical_usage': self.has_technical_usage,
            'represents_semantic_shift': self.represents_semantic_shift,
            'chronological_rank': self.chronological_rank,
            # PROV-O Entity metadata
            'generated_at_time': self.generated_at_time.isoformat() if self.generated_at_time else None,
            'was_attributed_to': self.was_attributed_to,
            'was_derived_from': self.was_derived_from,
            'derivation_type': self.derivation_type,
            # System metadata
            'created_at': self.created_at.isoformat() if self.created_at else None
        }