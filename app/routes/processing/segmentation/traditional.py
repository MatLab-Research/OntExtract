"""Traditional paragraph and sentence segmentation workflow."""

from app import db
from app.models.processing_job import ProcessingJob
from app.models.text_segment import TextSegment
from app.services.processing_tools import DocumentProcessor
from app.services.provenance_service import provenance_service
from app.text_utils import clean_jstor_boilerplate


def run_traditional_segmentation(
    processing_version,
    original_document,
    user,
    method,
    chunk_size,
    overlap,
):
    """Create traditional text segments and their processing job."""
    processor = DocumentProcessor(user_id=user.id)

    content = clean_jstor_boilerplate(processing_version.content)
    if not content:
        content = processing_version.content

    if method == 'paragraph':
        result = processor.segment_paragraph(content)
    elif method == 'sentence':
        result = processor.segment_sentence(content)
    else:
        result = processor.segment_paragraph(content)

    if result.status != 'success':
        return {
            'success': False,
            'error': result.metadata.get('error', 'Segmentation failed'),
            'method': method
        }, 500

    current_position = 0
    for i, segment_text in enumerate(result.data):
        start_pos = content.find(segment_text, current_position)
        if start_pos == -1:
            start_pos = current_position
        end_pos = start_pos + len(segment_text)

        segment = TextSegment(
            document_id=processing_version.id,
            content=segment_text,
            segment_type=method,
            segment_number=i + 1,
            start_position=start_pos,
            end_position=end_pos,
            level=0,
            language=processing_version.detected_language
        )
        db.session.add(segment)
        current_position = end_pos

    job = ProcessingJob(
        document_id=processing_version.id,
        job_type='segment_document',
        status='pending',
        user_id=user.id
    )
    job.set_parameters({
        'method': method,
        'chunk_size': chunk_size,
        'overlap': overlap,
        'original_document_id': original_document.id,
        'version_type': 'processed'
    })
    db.session.add(job)
    db.session.commit()

    segment_count = processing_version.text_segments.count()

    job.status = 'completed'
    job.set_result_data({
        'segment_count': segment_count,
        'chunk_size': chunk_size,
        'overlap': overlap,
        'total_words': (
            len(processing_version.content.split())
            if processing_version.content else 0
        )
    })

    tool_name = 'nltk' if method == 'sentence' else None
    provenance_service.track_document_segmentation(
        processing_version,
        user,
        method=method,
        segment_count=segment_count,
        segments=list(processing_version.text_segments),
        tool_name=tool_name
    )

    db.session.commit()
    return {'job': job, 'segment_count': segment_count}, 200
