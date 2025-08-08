from datetime import datetime
import json
from app import db

class TextSegment(db.Model):
    """Model for storing segmented text portions for processing"""
    
    __tablename__ = 'text_segments'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # Segment content
    content = db.Column(db.Text, nullable=False)
    segment_type = db.Column(db.String(50), default='paragraph')  # 'paragraph', 'sentence', 'section', etc.
    
    # Position information
    segment_number = db.Column(db.Integer)  # Order within document
    start_position = db.Column(db.Integer)  # Character position in original document
    end_position = db.Column(db.Integer)    # End character position
    
    # Hierarchy information
    parent_segment_id = db.Column(db.Integer, db.ForeignKey('text_segments.id'), index=True)
    level = db.Column(db.Integer, default=0)  # Nesting level (0 = top level)
    
    # Content metadata
    word_count = db.Column(db.Integer)
    character_count = db.Column(db.Integer)
    sentence_count = db.Column(db.Integer)
    
    # Language and processing
    language = db.Column(db.String(10))
    language_confidence = db.Column(db.Float)
    
    # Embedding for RAG
    embedding = db.Column(db.String)  # JSON serialized embedding vector
    embedding_model = db.Column(db.String(100))  # Model used for embedding
    
    # Processing status
    processed = db.Column(db.Boolean, default=False)
    processing_notes = db.Column(db.Text)
    
    # Semantic annotations
    topics = db.Column(db.Text)  # JSON array of identified topics
    keywords = db.Column(db.Text)  # JSON array of keywords
    sentiment_score = db.Column(db.Float)  # Sentiment analysis score
    complexity_score = db.Column(db.Float)  # Text complexity score
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    processed_at = db.Column(db.DateTime)
    
    # Foreign keys
    document_id = db.Column(db.Integer, db.ForeignKey('documents.id'), nullable=False, index=True)
    
    # Relationships
    child_segments = db.relationship('TextSegment', backref=db.backref('parent_segment', remote_side=[id]), lazy='dynamic')
    extracted_entities = db.relationship('ExtractedEntity', backref='text_segment', lazy='dynamic')
    
    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
        
        # Auto-calculate metadata
        if self.content:
            self.character_count = len(self.content)
            self.word_count = len(self.content.split())
            self.sentence_count = len([s for s in self.content.split('.') if s.strip()])
    
    def set_topics(self, topics_list):
        """Set topics from list"""
        if isinstance(topics_list, list):
            self.topics = json.dumps(topics_list)
        else:
            self.topics = str(topics_list)
    
    def get_topics(self):
        """Get topics as list"""
        if self.topics:
            try:
                return json.loads(self.topics)
            except json.JSONDecodeError:
                return []
        return []
    
    def set_keywords(self, keywords_list):
        """Set keywords from list"""
        if isinstance(keywords_list, list):
            self.keywords = json.dumps(keywords_list)
        else:
            self.keywords = str(keywords_list)
    
    def get_keywords(self):
        """Get keywords as list"""
        if self.keywords:
            try:
                return json.loads(self.keywords)
            except json.JSONDecodeError:
                return []
        return []
    
    def set_embedding(self, embedding_vector, model_name=None):
        """Set embedding vector and model"""
        if isinstance(embedding_vector, list):
            self.embedding = json.dumps(embedding_vector)
        else:
            self.embedding = str(embedding_vector)
        
        if model_name:
            self.embedding_model = model_name
    
    def get_embedding(self):
        """Get embedding as list"""
        if self.embedding:
            try:
                return json.loads(self.embedding)
            except json.JSONDecodeError:
                return []
        return []
    
    def get_preview(self, max_length=200):
        """Get preview of segment content"""
        if not self.content:
            return ""
        
        if len(self.content) <= max_length:
            return self.content
        
        return self.content[:max_length] + "..."
    
    def get_hierarchy_path(self):
        """Get full hierarchy path as list of segment numbers"""
        path = [self.segment_number]
        current = self.parent_segment
        
        while current:
            path.insert(0, current.segment_number)
            current = current.parent_segment
        
        return path
    
    def mark_processed(self, notes=None):
        """Mark segment as processed"""
        self.processed = True
        self.processed_at = datetime.utcnow()
        if notes:
            self.processing_notes = notes
        db.session.commit()
    
    def is_leaf_segment(self):
        """Check if this is a leaf segment (no children)"""
        return self.child_segments.count() == 0
    
    def get_all_descendant_segments(self):
        """Get all descendant segments recursively"""
        descendants = []
        for child in self.child_segments:
            descendants.append(child)
            descendants.extend(child.get_all_descendant_segments())
        return descendants
    
    def to_dict(self, include_content=True):
        """Convert text segment to dictionary for API responses"""
        result = {
            'id': self.id,
            'segment_type': self.segment_type,
            'segment_number': self.segment_number,
            'start_position': self.start_position,
            'end_position': self.end_position,
            'parent_segment_id': self.parent_segment_id,
            'level': self.level,
            'word_count': self.word_count,
            'character_count': self.character_count,
            'sentence_count': self.sentence_count,
            'language': self.language,
            'language_confidence': self.language_confidence,
            'embedding_model': self.embedding_model,
            'processed': self.processed,
            'processing_notes': self.processing_notes,
            'topics': self.get_topics(),
            'keywords': self.get_keywords(),
            'sentiment_score': self.sentiment_score,
            'complexity_score': self.complexity_score,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'processed_at': self.processed_at.isoformat() if self.processed_at else None,
            'document_id': self.document_id,
            'hierarchy_path': self.get_hierarchy_path(),
            'is_leaf_segment': self.is_leaf_segment(),
            'child_count': self.child_segments.count()
        }
        
        if include_content:
            result['content'] = self.content
            result['content_preview'] = self.get_preview()
        else:
            result['content_preview'] = self.get_preview()
        
        return result
    
    @classmethod
    def get_segments_by_type(cls, document_id, segment_type=None, level=None):
        """Get segments filtered by type and/or level"""
        query = cls.query.filter_by(document_id=document_id)
        if segment_type:
            query = query.filter_by(segment_type=segment_type)
        if level is not None:
            query = query.filter_by(level=level)
        return query.order_by(cls.segment_number).all()
    
    @classmethod
    def get_top_level_segments(cls, document_id):
        """Get only top-level segments for a document"""
        return cls.query.filter_by(document_id=document_id, level=0)\
            .order_by(cls.segment_number).all()
    
    def __repr__(self):
        preview = self.get_preview(50)
        return f'<TextSegment {self.id}: {self.segment_type} - "{preview}">'
