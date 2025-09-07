from datetime import datetime
import json
from app import db

class ProcessingJob(db.Model):
    """Model for tracking LLM and processing jobs"""
    
    __tablename__ = 'processing_jobs'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # Job identification
    job_type = db.Column(db.String(50), nullable=False)  # 'entity_extraction', 'langextract', 'ontology_mapping', etc.
    job_name = db.Column(db.String(100))
    
    # Processing configuration
    provider = db.Column(db.String(20))  # 'anthropic', 'openai', 'google'
    model = db.Column(db.String(50))
    parameters = db.Column(db.Text)  # JSON string of processing parameters
    
    # Job status
    status = db.Column(db.String(20), default='pending', nullable=False)
    # Status values: 'pending', 'running', 'completed', 'failed', 'cancelled'
    
    # Progress tracking
    progress_percent = db.Column(db.Integer, default=0)
    current_step = db.Column(db.String(100))
    total_steps = db.Column(db.Integer)
    
    # Results
    result_data = db.Column(db.Text)  # JSON string of results
    result_summary = db.Column(db.Text)
    
    # Error handling
    error_message = db.Column(db.Text)
    error_details = db.Column(db.Text)  # JSON string of error details
    retry_count = db.Column(db.Integer, default=0)
    max_retries = db.Column(db.Integer, default=3)
    
    # Resource usage
    tokens_used = db.Column(db.Integer)
    processing_time = db.Column(db.Float)  # in seconds
    cost_estimate = db.Column(db.Float)  # in USD
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    started_at = db.Column(db.DateTime)
    completed_at = db.Column(db.DateTime)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Foreign keys
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    document_id = db.Column(db.Integer, db.ForeignKey('documents.id'), nullable=False, index=True)
    parent_job_id = db.Column(db.Integer, db.ForeignKey('processing_jobs.id'), index=True)  # For job chains
    
    # Relationships
    child_jobs = db.relationship('ProcessingJob', backref=db.backref('parent_job', remote_side=[id]), lazy='dynamic')
    extracted_entities = db.relationship('ExtractedEntity', backref='processing_job', lazy='dynamic')
    
    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
    
    def set_parameters(self, params_dict):
        """Set processing parameters from dictionary"""
        self.parameters = json.dumps(params_dict)
    
    def get_parameters(self):
        """Get processing parameters as dictionary"""
        if self.parameters:
            try:
                return json.loads(self.parameters)
            except json.JSONDecodeError:
                return {}
        return {}
    
    def set_result_data(self, data):
        """Set result data from dictionary or object"""
        if isinstance(data, (dict, list)):
            self.result_data = json.dumps(data)
        else:
            self.result_data = str(data)
    
    def get_result_data(self):
        """Get result data as dictionary"""
        if self.result_data:
            try:
                return json.loads(self.result_data)
            except json.JSONDecodeError:
                return self.result_data
        return None
    
    def set_error_details(self, error_dict):
        """Set error details from dictionary"""
        if isinstance(error_dict, dict):
            self.error_details = json.dumps(error_dict)
        else:
            self.error_details = str(error_dict)
    
    def get_error_details(self):
        """Get error details as dictionary"""
        if self.error_details:
            try:
                return json.loads(self.error_details)
            except json.JSONDecodeError:
                return self.error_details
        return None
    
    def set_status(self, status, commit=True):
        """Set job status directly"""
        self.status = status
        self.updated_at = datetime.utcnow()
        if commit:
            db.session.commit()
    
    def set_error_message(self, error_message, commit=True):
        """Set error message directly"""
        self.error_message = error_message
        self.updated_at = datetime.utcnow()
        if commit:
            db.session.commit()
    
    def start_job(self):
        """Mark job as started"""
        self.status = 'running'
        self.started_at = datetime.utcnow()
        db.session.commit()
    
    def complete_job(self, result_data=None, result_summary=None):
        """Mark job as completed"""
        self.status = 'completed'
        self.completed_at = datetime.utcnow()
        self.progress_percent = 100
        
        if result_data:
            self.set_result_data(result_data)
        if result_summary:
            self.result_summary = result_summary
        
        # Calculate processing time
        if self.started_at:
            self.processing_time = (self.completed_at - self.started_at).total_seconds()
        
        db.session.commit()
    
    def fail_job(self, error_message, error_details=None):
        """Mark job as failed"""
        self.status = 'failed'
        self.error_message = error_message
        self.completed_at = datetime.utcnow()
        
        if error_details:
            self.set_error_details(error_details)
        
        db.session.commit()
    
    def update_progress(self, percent, current_step=None):
        """Update job progress"""
        self.progress_percent = percent
        if current_step:
            self.current_step = current_step
        self.updated_at = datetime.utcnow()
        db.session.commit()
    
    def can_retry(self):
        """Check if job can be retried"""
        return self.status == 'failed' and self.retry_count < self.max_retries
    
    def increment_retry(self):
        """Increment retry count"""
        self.retry_count += 1
        self.status = 'pending'
        self.error_message = None
        self.error_details = None
        self.progress_percent = 0
        self.current_step = None
        db.session.commit()
    
    def get_duration(self):
        """Get job duration in seconds"""
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        elif self.started_at:
            return (datetime.utcnow() - self.started_at).total_seconds()
        return 0
    
    def to_dict(self):
        """Convert processing job to dictionary for API responses"""
        return {
            'id': self.id,
            'job_type': self.job_type,
            'job_name': self.job_name,
            'provider': self.provider,
            'model': self.model,
            'status': self.status,
            'progress_percent': self.progress_percent,
            'current_step': self.current_step,
            'total_steps': self.total_steps,
            'result_summary': self.result_summary,
            'error_message': self.error_message,
            'retry_count': self.retry_count,
            'max_retries': self.max_retries,
            'tokens_used': self.tokens_used,
            'processing_time': self.processing_time,
            'cost_estimate': self.cost_estimate,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'document_id': self.document_id,
            'parent_job_id': self.parent_job_id,
            'duration': self.get_duration(),
            'parameters': self.get_parameters()
        }
    
    def __repr__(self):
        return f'<ProcessingJob {self.id}: {self.job_type} - {self.status}>'
