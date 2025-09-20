"""
Composite Versioning Service

Handles creation and management of composite documents that combine
processing results from multiple document versions.
"""

from app import db
from app.models import Document, TextSegment
from sqlalchemy import text
from datetime import datetime
import json
import logging

logger = logging.getLogger(__name__)

class CompositeVersioningService:
    """Service for managing composite document versions"""

    @staticmethod
    def create_composite_from_versions(original_document, source_versions, composite_name=None):
        """
        Create a composite document that combines processing from multiple source versions.

        Args:
            original_document: The root document
            source_versions: List of Document objects to combine
            composite_name: Optional name for the composite

        Returns:
            composite_document: The new composite document
        """
        try:
            # Create the composite document
            composite_metadata = {
                'creation_method': 'manual_composite',
                'source_versions': [v.id for v in source_versions],
                'processing_types': list(set(v.version_type for v in source_versions)),
                'created_at': datetime.utcnow().isoformat(),
                'total_sources': len(source_versions)
            }

            composite_doc = original_document.create_composite_version(
                source_versions=source_versions,
                composite_metadata=composite_metadata
            )

            # Merge segments from all source versions
            CompositeVersioningService._merge_segments(composite_doc, source_versions)

            # Merge embeddings from all source versions
            CompositeVersioningService._merge_embeddings(composite_doc, source_versions)

            # Update composite title if provided
            if composite_name:
                composite_doc.title = composite_name
            else:
                processing_types = [v.version_type for v in source_versions]
                type_summary = ', '.join(set(processing_types))
                composite_doc.title = f"{original_document.title} (Composite: {type_summary})"

            db.session.commit()

            logger.info(f"Created composite document {composite_doc.id} from {len(source_versions)} source versions")
            return composite_doc

        except Exception as e:
            db.session.rollback()
            logger.error(f"Failed to create composite document: {str(e)}")
            raise

    @staticmethod
    def _merge_segments(composite_doc, source_versions):
        """
        Merge text segments from multiple source versions into the composite document.
        Handles conflicts and deduplication.
        """
        all_segments = []

        for source_version in source_versions:
            # Get segments from this version
            segments = TextSegment.query.filter_by(document_id=source_version.id).all()

            for segment in segments:
                # Create a copy of the segment for the composite
                composite_segment = TextSegment(
                    document_id=composite_doc.id,
                    segment_type=segment.segment_type,
                    content=segment.content,
                    start_position=segment.start_position,
                    end_position=segment.end_position,
                    segment_metadata={
                        **(segment.segment_metadata or {}),
                        'source_version_id': source_version.id,
                        'source_version_type': source_version.version_type,
                        'merged_into_composite': True
                    },
                    embedding=segment.embedding,
                    embedding_model=segment.embedding_model,
                    entities=segment.entities,
                    temporal_markers=segment.temporal_markers
                )
                all_segments.append(composite_segment)

        # Add all segments to the composite document
        for segment in all_segments:
            db.session.add(segment)

    @staticmethod
    def _merge_embeddings(composite_doc, source_versions):
        """
        Merge embeddings from multiple source versions.
        Creates a unified embedding representation.
        """
        # For now, we'll use the embedding from the most recent processed version
        # Future enhancement: create aggregate embeddings
        latest_processed = None

        for version in source_versions:
            if version.version_type == 'processed':
                if latest_processed is None or version.created_at > latest_processed.created_at:
                    latest_processed = version

        if latest_processed and hasattr(latest_processed, 'embedding') and latest_processed.embedding:
            # Copy the embedding to the composite
            composite_doc.embedding = latest_processed.embedding
            composite_doc.processing_metadata = {
                **(composite_doc.processing_metadata or {}),
                'embedding_source': latest_processed.id,
                'embedding_merged': True
            }

    @staticmethod
    def get_composite_summary(composite_doc):
        """
        Get a summary of what the composite document contains
        """
        if not composite_doc.is_composite():
            return None

        sources = composite_doc.get_composite_sources()
        segment_count = TextSegment.query.filter_by(document_id=composite_doc.id).count()

        return {
            'composite_id': composite_doc.id,
            'source_count': len(sources),
            'source_types': [s.version_type for s in sources],
            'segment_count': segment_count,
            'has_embedding': bool(composite_doc.embedding),
            'created_at': composite_doc.created_at.isoformat() if composite_doc.created_at else None
        }

    @staticmethod
    def update_composite_from_new_version(composite_doc, new_version):
        """
        Update an existing composite to include a newly processed version
        """
        try:
            # Add the new version to composite sources
            current_sources = composite_doc.composite_sources or []
            if new_version.id not in current_sources:
                current_sources.append(new_version.id)
                composite_doc.composite_sources = current_sources

                # Update metadata
                metadata = composite_doc.composite_metadata or {}
                metadata['source_versions'] = current_sources
                metadata['last_updated'] = datetime.utcnow().isoformat()
                metadata['total_sources'] = len(current_sources)
                composite_doc.composite_metadata = metadata

                # Merge new segments
                CompositeVersioningService._merge_segments_from_single_version(composite_doc, new_version)

                # Update embeddings if needed
                CompositeVersioningService._merge_embeddings(composite_doc, [new_version])

                db.session.commit()

                logger.info(f"Updated composite {composite_doc.id} to include version {new_version.id}")

        except Exception as e:
            db.session.rollback()
            logger.error(f"Failed to update composite: {str(e)}")
            raise

    @staticmethod
    def _merge_segments_from_single_version(composite_doc, source_version):
        """
        Merge segments from a single version into an existing composite
        """
        segments = TextSegment.query.filter_by(document_id=source_version.id).all()

        for segment in segments:
            # Check if similar segment already exists
            existing_segment = TextSegment.query.filter_by(
                document_id=composite_doc.id,
                content=segment.content,
                segment_type=segment.segment_type
            ).first()

            if not existing_segment:
                # Create new segment
                composite_segment = TextSegment(
                    document_id=composite_doc.id,
                    segment_type=segment.segment_type,
                    content=segment.content,
                    start_position=segment.start_position,
                    end_position=segment.end_position,
                    segment_metadata={
                        **(segment.segment_metadata or {}),
                        'source_version_id': source_version.id,
                        'source_version_type': source_version.version_type,
                        'added_to_existing_composite': True
                    },
                    embedding=segment.embedding,
                    embedding_model=segment.embedding_model,
                    entities=segment.entities,
                    temporal_markers=segment.temporal_markers
                )
                db.session.add(composite_segment)
            else:
                # Update existing segment with additional metadata
                metadata = existing_segment.segment_metadata or {}
                metadata['additional_sources'] = metadata.get('additional_sources', [])
                metadata['additional_sources'].append({
                    'version_id': source_version.id,
                    'version_type': source_version.version_type,
                    'added_at': datetime.utcnow().isoformat()
                })
                existing_segment.segment_metadata = metadata