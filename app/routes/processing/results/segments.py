"""Segmentation result views."""

from flask import render_template

from app.models.document import Document
from app.models.processing_job import ProcessingJob
from app.models.text_segment import TextSegment
from app.services.processing_results import (
    append_experiment_jobs,
    get_document_family_ids,
)

from .. import processing_bp


@processing_bp.route('/document/<string:document_uuid>/results/segments', methods=['GET'])
def view_segments_results(document_uuid):
    """View segmentation results for a document (supports both manual and experiment processing)"""
    try:
        document = Document.query.filter_by(uuid=document_uuid).first_or_404()

        # Get segmentation jobs for this document AND all its versions
        all_version_ids = get_document_family_ids(document)

        # Get segmentation jobs from all versions (manual processing)
        jobs = ProcessingJob.query.filter(
            ProcessingJob.document_id.in_(all_version_ids),
            ProcessingJob.job_type == 'segment_document'
        ).order_by(ProcessingJob.created_at.desc()).all()

        # Also check for jobs that reference this document as original_document_id
        all_potential_jobs = ProcessingJob.query.filter(
            ProcessingJob.document_id.notin_(all_version_ids),
            ProcessingJob.job_type == 'segment_document'
        ).all()

        for job in all_potential_jobs:
            params = job.get_parameters()
            if params.get('original_document_id') in all_version_ids:
                jobs.append(job)

        append_experiment_jobs(jobs, all_version_ids, 'segmentation')

        # Get segments from all versions (prioritize latest version by document_id DESC)
        # Check both old TextSegment table and new ProcessingArtifact table
        old_segments = TextSegment.query.filter(
            TextSegment.document_id.in_(all_version_ids)
        ).order_by(TextSegment.document_id.desc(), TextSegment.segment_number).all()

        # Also get segments from ProcessingArtifact (new experiment processing)
        from app.models.experiment_processing import ProcessingArtifact
        new_artifacts = ProcessingArtifact.query.filter(
            ProcessingArtifact.document_id.in_(all_version_ids),
            ProcessingArtifact.artifact_type == 'text_segment'
        ).order_by(ProcessingArtifact.artifact_index).all()

        # Create a wrapper class to make ProcessingArtifact look like TextSegment
        class SegmentWrapper:
            def __init__(self, artifact):
                content_data = artifact.get_content()
                metadata = artifact.get_metadata() or {}
                self.segment_number = artifact.artifact_index + 1

                # Content can be a string (segment text) or dict with 'text' key
                if isinstance(content_data, str):
                    self.content = content_data
                else:
                    self.content = content_data.get('text', '') if content_data else ''

                self.word_count = metadata.get('word_count', len(self.content.split()))
                self.character_count = len(self.content)

                # Determine segmentation method from tool_name in metadata
                # tool_name will be 'segment_paragraph' or 'segment_sentence'
                tool_name = metadata.get('tool_name', '')
                if 'paragraph' in tool_name.lower():
                    self.segmentation_method = 'paragraph'
                elif 'sentence' in tool_name.lower():
                    self.segmentation_method = 'sentence'
                else:
                    # Fallback: check other metadata fields
                    self.segmentation_method = content_data.get('segment_type') if isinstance(content_data, dict) else None
                    if not self.segmentation_method:
                        self.segmentation_method = metadata.get('method', 'unknown')

        # Combine old and new segments, adding segmentation_method to old segments
        segments = []
        for seg in old_segments:
            # Add segmentation_method attribute to old TextSegment objects
            # Try to infer from segmentation_type field if it exists, otherwise 'paragraph'
            if hasattr(seg, 'segmentation_type'):
                seg.segmentation_method = seg.segmentation_type
            else:
                # Default to paragraph for old segments without type info
                seg.segmentation_method = 'paragraph'
            segments.append(seg)

        for artifact in new_artifacts:
            segments.append(SegmentWrapper(artifact))

        # Sort by segment number
        segments.sort(key=lambda s: s.segment_number)

        # Calculate statistics
        if segments:
            avg_length = sum(s.character_count or 0 for s in segments) / len(segments)
            avg_words = sum(s.word_count or 0 for s in segments) / len(segments)
        else:
            avg_length = 0
            avg_words = 0

        from flask import render_template
        return render_template('processing/segments_results.html',
                             document=document,
                             jobs=jobs,
                             segments=segments,
                             total_segments=len(segments),
                             avg_length=avg_length,
                             avg_words=avg_words)

    except Exception as e:
        from flask import render_template
        return render_template('processing/error.html',
                             document=document,
                             error=str(e)), 500
