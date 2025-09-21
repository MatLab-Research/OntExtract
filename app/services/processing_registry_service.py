"""Processing Registry Service

Provides helper functions for creating and retrieving ProcessingArtifactGroup
records and related grouped artifacts (initially text segments). This is the
first layer enabling multi-method coexistence for segmentation, embeddings,
and other artifact types in the hub-and-spoke architecture.

Design goals:
 - Idempotent creation (create_or_get semantics) keyed by (document, type, method)
 - Simple listing / filtering API for upcoming REST endpoint
 - Minimal coupling: does not execute processing, only registers and queries
 - Extensible: future add register_embedding_group, etc.
"""

from typing import List, Optional, Dict, Any
from sqlalchemy.exc import IntegrityError

from app import db
from app.models.processing_artifact_group import ProcessingArtifactGroup
from app.models.text_segment import TextSegment


class ProcessingRegistryService:
    """Service for registering and querying processing artifact groups."""

    def create_or_get_group(
        self,
        document_id: int,
        artifact_type: str,
        method_key: str,
        processing_job_id: Optional[int] = None,
        parent_method_keys: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        include_in_composite: bool = True,
    ) -> ProcessingArtifactGroup:
        """Get existing group or create a new one.

        Idempotent: if another transaction creates the row first, we fetch it.
        """
        group = (
            ProcessingArtifactGroup.query.filter_by(
                document_id=document_id,
                artifact_type=artifact_type,
                method_key=method_key,
            ).first()
        )
        if group:
            return group

        group = ProcessingArtifactGroup(
            document_id=document_id,
            artifact_type=artifact_type,
            method_key=method_key,
            processing_job_id=processing_job_id,
            parent_method_keys=parent_method_keys or [],
            metadata_json=metadata or {},
            include_in_composite=include_in_composite,
            status="pending" if processing_job_id else "completed",
        )
        db.session.add(group)
        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            # Race: someone else inserted it
            group = (
                ProcessingArtifactGroup.query.filter_by(
                    document_id=document_id,
                    artifact_type=artifact_type,
                    method_key=method_key,
                ).first()
            )
        return group

    def list_groups_for_document(
        self,
        document_id: int,
        artifact_type: Optional[str] = None,
        include_disabled: bool = False,
    ) -> List[ProcessingArtifactGroup]:
        """List artifact groups for a document, optionally filtered by type."""
        query = ProcessingArtifactGroup.query.filter_by(document_id=document_id)
        if artifact_type:
            query = query.filter_by(artifact_type=artifact_type)
        if not include_disabled:
            query = query.filter_by(include_in_composite=True)
        return query.order_by(ProcessingArtifactGroup.created_at.asc()).all()

    def get_group(self, group_id: int) -> Optional[ProcessingArtifactGroup]:
        return db.session.get(ProcessingArtifactGroup, group_id)

    def summarize_groups(self, groups: List[ProcessingArtifactGroup]) -> List[Dict[str, Any]]:
        """Return a summary payload for API responses."""
        results = []
        for g in groups:
            segment_count = 0
            if g.artifact_type == "segmentation":
                # Count segments efficiently
                segment_count = (
                    TextSegment.query.filter_by(group_id=g.id).count()
                )
            d = g.to_dict()  # retains 'metadata' key for API compatibility
            d["segment_count"] = segment_count
            results.append(d)
        return results

    def ensure_legacy_group_for_segment(self, segment: TextSegment) -> Optional[ProcessingArtifactGroup]:
        """Backfill helper: if a legacy segment lacks group link, create group.

        Called opportunistically when exposing data via API until full reprocessing.
        """
        if segment.group_id:
            return segment.artifact_group
        if not segment.processing_method:
            return None
        group = self.create_or_get_group(
            document_id=segment.document_id,
            artifact_type="segmentation",
            method_key=segment.processing_method,
        )
        segment.group_id = group.id
        db.session.commit()
        return group


processing_registry_service = ProcessingRegistryService()
