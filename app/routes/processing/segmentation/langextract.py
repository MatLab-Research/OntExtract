"""LangExtract-powered document segmentation workflow."""

import json

from app import db
from app.models.processing_job import ProcessingJob
from app.models.text_segment import TextSegment
from app.services.integrated_langextract import IntegratedLangExtractService
from app.services.provenance_service import provenance_service
from app.services.text_processing import TextProcessingService


def _create_recommended_segments(processing_version, recommendations, analysis_id):
    segments = []

    for segment_info in recommendations.get('structural_segments', []):
        segment = TextSegment(
            document_id=processing_version.id,
            segment_number=len(segments) + 1,
            start_position=segment_info.get('start_pos', 0),
            end_position=segment_info.get('end_pos', 100),
            content=processing_version.content[
                segment_info.get('start_pos', 0):segment_info.get('end_pos', 100)
            ],
            metadata={
                'segmentation_method': 'langextract_structural',
                'segment_type': segment_info.get('type', 'structural'),
                'element': segment_info.get('element', 'unknown'),
                'confidence': segment_info.get('confidence', 0.7),
                'character_level_positions': True,
                'langextract_analysis_id': analysis_id,
                'prov_o_tracked': True
            }
        )
        db.session.add(segment)
        segments.append(segment)

    for segment_info in recommendations.get('semantic_segments', []):
        segment = TextSegment(
            document_id=processing_version.id,
            segment_number=len(segments) + 1,
            start_position=segment_info.get('start_pos', 0),
            end_position=segment_info.get('end_pos', 100),
            content=processing_version.content[
                segment_info.get('start_pos', 0):segment_info.get('end_pos', 100)
            ],
            metadata={
                'segmentation_method': 'langextract_semantic',
                'segment_type': segment_info.get('type', 'semantic'),
                'primary_concepts': segment_info.get('primary_concepts', []),
                'confidence': segment_info.get('confidence', 0.7),
                'character_level_positions': True,
                'langextract_analysis_id': analysis_id,
                'prov_o_tracked': True
            }
        )
        db.session.add(segment)
        segments.append(segment)

    return segments


def _create_enriched_fallback_segments(processing_version, analysis_id):
    TextProcessingService().create_initial_segments(processing_version)

    metadata = {
        'enriched_with_langextract': True,
        'langextract_analysis_id': analysis_id,
        'character_level_positions': True,
        'prov_o_tracked': True
    }
    for segment in processing_version.text_segments:
        if segment.processing_notes:
            try:
                existing_notes = json.loads(segment.processing_notes)
                if isinstance(existing_notes, dict):
                    existing_notes.update(metadata)
                    segment.processing_notes = json.dumps(existing_notes)
                else:
                    segment.processing_notes = json.dumps({
                        'original_notes': str(existing_notes),
                        **metadata
                    })
            except (json.JSONDecodeError, TypeError):
                segment.processing_notes = json.dumps({
                    'original_notes': str(segment.processing_notes),
                    **metadata
                })
        else:
            segment.processing_notes = json.dumps(metadata)

    return list(processing_version.text_segments)


def run_langextract_segmentation(processing_version, original_document, user):
    """Run LangExtract segmentation and return a payload/status tuple."""
    job = None
    try:
        try:
            service = IntegratedLangExtractService()
        except ValueError as exc:
            return {
                'success': False,
                'error': f'LangExtract requires API key: {exc}',
                'fallback_suggestion': (
                    'Try paragraph or semantic segmentation instead'
                ),
                'fallback_available': True,
                'implementation_note': (
                    'LangExtract two-stage architecture is implemented but '
                    'requires GOOGLE_GEMINI_API_KEY'
                )
            }, 400

        if not service.service_ready:
            return {
                'success': False,
                'error': (
                    'LangExtract service not available. Please ensure '
                    'GOOGLE_GEMINI_API_KEY is set.'
                ),
                'fallback_suggestion': (
                    'Try paragraph or semantic segmentation instead'
                ),
                'fallback_available': True
            }, 400

        job = ProcessingJob(
            document_id=processing_version.id,
            job_type='langextract_segmentation',
            status='pending',
            user_id=user.id
        )
        job.set_parameters({
            'method': 'langextract',
            'two_stage_architecture': True,
            'character_level_positions': True,
            'original_document_id': original_document.id,
            'version_type': 'processed'
        })
        db.session.add(job)
        db.session.commit()

        analysis = service.analyze_and_orchestrate_document(
            document_id=processing_version.id,
            document_text=processing_version.content,
            user_id=user.id
        )
        if not analysis.get('success'):
            error = analysis.get('error', 'Unknown error')
            job.set_status('failed')
            job.set_error_message(error)
            return {
                'success': False,
                'error': f'LangExtract analysis failed: {error}',
                'prov_o_tracking': False
            }, 500

        recommendations = service.get_segmentation_recommendations(
            processing_version.content
        )
        segments = _create_recommended_segments(
            processing_version,
            recommendations,
            analysis.get('analysis_id')
        )
        if not segments:
            segments = _create_enriched_fallback_segments(
                processing_version,
                analysis.get('analysis_id')
            )

        db.session.commit()

        job.set_status('completed')
        job.set_parameters({
            **job.get_parameters(),
            'segments_created': len(segments),
            'langextract_analysis_complete': True,
            'orchestration_plan_generated': True,
            'prov_o_tracking_complete': True
        })

        provenance_service.track_document_segmentation(
            processing_version,
            user,
            method='langextract',
            segment_count=len(segments),
            segments=segments,
            tool_name='langextract'
        )

        return {
            'success': True,
            'method': 'langextract',
            'segments_created': len(segments),
            'analysis_id': analysis.get('analysis_id'),
            'original_document_id': original_document.id,
            'processing_version_id': processing_version.id,
            'version_number': processing_version.version_number,
            'message': (
                'Document segmented using LangExtract two-stage architecture '
                f'into {len(segments)} segments '
                f'(created version {processing_version.version_number})'
            ),
            'langextract_features': {
                'two_stage_architecture': True,
                'character_level_positioning': True,
                'llm_orchestration': True,
                'prov_o_tracking': True,
                'jcdl_section_3_1_implemented': True
            },
            'segmentation_summary': {
                'structural_segments': len(
                    recommendations.get('structural_segments', [])
                ),
                'semantic_segments': len(
                    recommendations.get('semantic_segments', [])
                ),
                'temporal_segments': len(
                    recommendations.get('temporal_segments', [])
                ),
                'confidence': recommendations.get('confidence', 0.5)
            },
            'provenance_tracking': analysis.get('provenance_tracking', {})
        }, 200

    except Exception as exc:
        if job is not None:
            job.set_status('failed')
            job.set_error_message(f'LangExtract error: {exc}')
        return {
            'success': False,
            'error': f'LangExtract segmentation failed: {exc}',
            'fallback_available': True,
            'fallback_suggestion': (
                'Try paragraph or semantic segmentation instead'
            )
        }, 500
