"""Version changelog model for tracking document version changes."""

from app import db


class VersionChangelog(db.Model):
    """Model for tracking what changed in each document version."""

    __tablename__ = 'version_changelog'

    id = db.Column(db.Integer, primary_key=True)
    document_id = db.Column(db.Integer, db.ForeignKey('documents.id', ondelete='CASCADE'), nullable=False)
    version_number = db.Column(db.Integer, nullable=False)
    change_type = db.Column(db.String(50), nullable=False)
    change_description = db.Column(db.Text)
    previous_version = db.Column(db.Integer)
    created_at = db.Column(db.DateTime, nullable=False, server_default=db.func.now())
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    processing_metadata = db.Column(db.JSON)

    # Indexes and constraints
    __table_args__ = (
        db.Index('idx_version_changelog_document_version', 'document_id', 'version_number'),
        db.Index('idx_version_changelog_change_type', 'change_type'),
        db.UniqueConstraint('document_id', 'version_number', 'change_type', name='unique_document_version_change'),
    )

    def __repr__(self):
        return f'<VersionChangelog doc={self.document_id} v{self.version_number} {self.change_type}>'

    def to_dict(self):
        """Convert to dictionary for API responses."""
        return {
            'id': self.id,
            'document_id': self.document_id,
            'version_number': self.version_number,
            'change_type': self.change_type,
            'change_description': self.change_description,
            'previous_version': self.previous_version,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'created_by': self.created_by,
            'processing_metadata': self.processing_metadata
        }
