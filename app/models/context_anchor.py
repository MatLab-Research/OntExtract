from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime
from app import db
import uuid


class ContextAnchor(db.Model):
    """Reusable context anchor terms for autocomplete and consistency"""
    
    __tablename__ = 'context_anchors'
    
    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    anchor_term = db.Column(db.String(255), nullable=False, unique=True, index=True)
    frequency = db.Column(db.Integer, default=1, index=True)
    first_used_in = db.Column(UUID(as_uuid=True), db.ForeignKey('term_versions.id'))
    last_used_in = db.Column(UUID(as_uuid=True), db.ForeignKey('term_versions.id'))
    created_at = db.Column(db.DateTime(timezone=True), default=datetime.utcnow)
    
    # Relationships
    first_version = db.relationship('TermVersion', foreign_keys=[first_used_in], 
                                   backref='first_anchor_usages', post_update=True)
    last_version = db.relationship('TermVersion', foreign_keys=[last_used_in],
                                  backref='last_anchor_usages', post_update=True)
    
    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
    
    @classmethod
    def get_or_create(cls, anchor_term):
        """Get existing anchor or create new one"""
        anchor = cls.query.filter_by(anchor_term=anchor_term).first()
        if not anchor:
            anchor = cls(anchor_term=anchor_term)
            db.session.add(anchor)
            db.session.commit()
        return anchor
    
    @staticmethod
    def search_anchors(query, limit=50):
        """Search anchor terms for autocomplete"""
        if not query:
            return ContextAnchor.query.order_by(ContextAnchor.frequency.desc()).limit(limit).all()
        
        return ContextAnchor.query.filter(
            ContextAnchor.anchor_term.ilike(f'%{query}%')
        ).order_by(ContextAnchor.frequency.desc()).limit(limit).all()
    
    @staticmethod
    def get_most_frequent(limit=100):
        """Get most frequently used anchor terms"""
        return ContextAnchor.query.order_by(ContextAnchor.frequency.desc()).limit(limit).all()
    
    @staticmethod
    def get_recent_anchors(limit=50):
        """Get recently used anchor terms"""
        return ContextAnchor.query.order_by(ContextAnchor.created_at.desc()).limit(limit).all()
    
    def increment_frequency(self, term_version_id=None):
        """Increment usage frequency and update last used"""
        self.frequency += 1
        if term_version_id:
            self.last_used_in = term_version_id
    
    def decrement_frequency(self):
        """Decrement usage frequency (when removing from term version)"""
        if self.frequency > 0:
            self.frequency -= 1
    
    def get_related_terms(self, limit=10):
        """Get terms that frequently use this anchor"""
        from app.models.term import TermVersion
        from sqlalchemy import func, desc
        
        # Get term versions that use this anchor, grouped by term
        results = db.session.query(
            TermVersion.term_id,
            func.count(TermVersion.id).label('usage_count')
        ).join(
            TermVersion.context_anchors
        ).filter(
            ContextAnchor.id == self.id
        ).group_by(
            TermVersion.term_id
        ).order_by(
            desc('usage_count')
        ).limit(limit).all()
        
        return results
    
    def to_dict(self, include_related=False):
        """Convert anchor to dictionary for API responses"""
        result = {
            'id': str(self.id),
            'anchor_term': self.anchor_term,
            'frequency': self.frequency,
            'created_at': self.created_at.isoformat(),
            'first_used_in': str(self.first_used_in) if self.first_used_in else None,
            'last_used_in': str(self.last_used_in) if self.last_used_in else None
        }
        
        if include_related:
            result['related_terms'] = [
                {
                    'term_id': str(item[0]),
                    'usage_count': item[1]
                }
                for item in self.get_related_terms()
            ]
        
        return result
    
    def __repr__(self):
        return f'<ContextAnchor {self.anchor_term} (freq: {self.frequency})>'