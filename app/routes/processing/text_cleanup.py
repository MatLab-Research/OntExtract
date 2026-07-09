"""Asynchronous text-cleanup and reviewed-text persistence routes."""

from flask import current_app as app, jsonify, request
from flask_login import current_user

from app import db
from app.models.document import Document
from app.models.processing_job import ProcessingJob
from app.services.inheritance_versioning_service import InheritanceVersioningService
from app.services.text_cleanup_service import TextCleanupService
from app.utils.auth_decorators import api_require_login_for_write

from . import processing_bp


@processing_bp.route('/document/<string:document_uuid>/clean-text', methods=['POST'])
@api_require_login_for_write
def clean_text(document_uuid):
    """Clean text using LLM to fix OCR errors, formatting, spelling (runs asynchronously)"""
    import threading

    try:
        document = Document.query.filter_by(uuid=document_uuid).first_or_404()

        if not document.content:
            return jsonify({
                'success': False,
                'error': 'Document has no content to clean'
            }), 400

        # Create processing job
        job = ProcessingJob(
            document_id=document.id,
            job_type='clean_text',
            status='running',
            user_id=current_user.id
        )
        job.set_parameters({
            'original_length': len(document.content),
            'current_chunk': 0,
            'total_chunks': 1,
            'progress_message': 'Starting text cleanup...'
        })
        db.session.add(job)
        db.session.commit()

        job_id = job.id
        document_content = document.content

        # Define background processing function
        def process_in_background():
            from app import create_app, db
            from app.models.processing_job import ProcessingJob

            # Create new app context for background thread
            background_app = create_app()
            with background_app.app_context():
                try:
                    # Get job in this thread's session
                    job = ProcessingJob.query.get(job_id)

                    # Progress callback to update job parameters
                    def update_progress(current_chunk, total_chunks):
                        job_refresh = ProcessingJob.query.get(job_id)
                        job_refresh.set_parameters({
                            'original_length': len(document_content),
                            'current_chunk': current_chunk,
                            'total_chunks': total_chunks,
                            'progress_message': f'Processing chunk {current_chunk} of {total_chunks}...'
                        })
                        db.session.commit()

                    # Use TextCleanupService to clean the text
                    cleanup_service = TextCleanupService()
                    cleaned_text, metadata = cleanup_service.clean_text(
                        document_content,
                        progress_callback=update_progress
                    )

                    # Update job with success
                    job.status = 'completed'
                    job.completed_at = db.func.now()
                    job.set_parameters({
                        'original_length': len(document_content),
                        'cleaned_length': len(cleaned_text),
                        'model': metadata.get('model'),
                        'input_tokens': metadata.get('input_tokens'),
                        'output_tokens': metadata.get('output_tokens'),
                        'chunks_processed': metadata.get('chunks_processed', 1),
                        'current_chunk': metadata.get('chunks_processed', 1),
                        'total_chunks': metadata.get('chunks_processed', 1),
                        'progress_message': 'Cleanup complete'
                    })
                    job.set_result_data({
                        'original_text': document_content,
                        'cleaned_text': cleaned_text,
                        'metadata': metadata
                    })
                    db.session.commit()

                except Exception as e:
                    # Update job with failure
                    job_refresh = ProcessingJob.query.get(job_id)
                    job_refresh.status = 'failed'
                    job_refresh.completed_at = db.func.now()
                    job_refresh.set_parameters({
                        'error': str(e),
                        'original_length': len(document_content),
                        'progress_message': f'Error: {str(e)}'
                    })
                    db.session.commit()
                    app.logger.error(f"Background text cleanup failed: {e}")

        # Start background thread
        thread = threading.Thread(target=process_in_background, daemon=True)
        thread.start()

        # Return job ID immediately for polling
        return jsonify({
            'success': True,
            'job_id': job_id,
            'status': 'running',
            'message': 'Text cleanup started. Poll for progress updates.'
        })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@processing_bp.route('/document/<string:document_uuid>/save-cleaned-text', methods=['POST'])
@api_require_login_for_write
def save_cleaned_text(document_uuid):
    """Save cleaned text after user review, creating a new document version"""
    try:
        document = Document.query.filter_by(uuid=document_uuid).first_or_404()
        data = request.get_json()

        if not data:
            return jsonify({
                'success': False,
                'error': 'No data provided'
            }), 400

        cleaned_content = data.get('cleaned_content')
        if not cleaned_content:
            return jsonify({
                'success': False,
                'error': 'No cleaned content provided'
            }), 400

        changes_accepted = data.get('changes_accepted', 0)
        changes_rejected = data.get('changes_rejected', 0)
        original_length = data.get('original_length', 0)
        cleaned_length = data.get('cleaned_length', len(cleaned_content))

        # Create new document version with cleaned text
        versioning_service = InheritanceVersioningService()
        metadata = {
            'changes_accepted': changes_accepted,
            'changes_rejected': changes_rejected,
            'cleanup_method': 'llm_claude',
            'original_length': original_length,
            'cleaned_length': cleaned_length
        }

        cleaned_version = versioning_service.create_new_version(
            original_document=document,
            processing_type='text_cleanup',
            processing_metadata=metadata
        )

        # Set version_type to 'cleaned' - this is a canonical cleaned version
        # that can be used as the source for experimental versions
        cleaned_version.version_type = 'cleaned'

        # Update the content with the cleaned version
        cleaned_version.content = cleaned_content
        cleaned_version.content_preview = cleaned_content[:500] if cleaned_content else None
        cleaned_version.character_count = len(cleaned_content)
        cleaned_version.word_count = len(cleaned_content.split()) if cleaned_content else 0

        # Flush immediately to persist all changes and avoid autoflush issues
        # when querying related documents later
        db.session.flush()

        # Find the original cleanup job to get model and token information
        original_cleanup_job = ProcessingJob.query.filter_by(
            document_id=document.id,
            job_type='clean_text',
            status='completed'
        ).order_by(ProcessingJob.created_at.desc()).first()

        # Create a processing job for the new version to track the cleanup
        cleanup_job = ProcessingJob(
            document_id=cleaned_version.id,
            job_type='clean_text',
            status='completed',
            user_id=current_user.id,
            completed_at=db.func.now()
        )

        # Copy parameters from original job if available
        if original_cleanup_job:
            original_params = original_cleanup_job.get_parameters()
            cleanup_job.set_parameters({
                'original_length': original_length,
                'cleaned_length': cleaned_length,
                'changes_accepted': changes_accepted,
                'changes_rejected': changes_rejected,
                'model': original_params.get('model', 'claude-sonnet-4-5-20250929'),
                'input_tokens': original_params.get('input_tokens', 0),
                'output_tokens': original_params.get('output_tokens', 0),
                'chunks_processed': original_params.get('chunks_processed', 1),
                'cleanup_method': 'llm_claude_reviewed'
            })
        else:
            cleanup_job.set_parameters({
                'original_length': original_length,
                'cleaned_length': cleaned_length,
                'changes_accepted': changes_accepted,
                'changes_rejected': changes_rejected,
                'model': 'claude-sonnet-4-5-20250929',
                'cleanup_method': 'llm_claude_reviewed'
            })

        db.session.add(cleanup_job)
        db.session.flush()  # Flush to get cleanup_job.id

        # Create experiment processing index entries for all experiments associated with this document family
        # This makes the processing visible in the "Related Experiments" section of the document detail page
        from app.models.experiment_document import ExperimentDocument
        from app.models.experiment_processing import ExperimentDocumentProcessing, DocumentProcessingIndex

        # Get root document to find experiment associations
        root_doc = cleaned_version.get_root_document()
        all_versions = root_doc.get_all_versions()
        all_doc_ids = [v.id for v in all_versions]

        # Find all experiments associated with any version in this document family
        experiment_docs = ExperimentDocument.query.filter(
            ExperimentDocument.document_id.in_(all_doc_ids)
        ).all()

        # Get unique experiment IDs
        experiment_ids = set(exp_doc.experiment_id for exp_doc in experiment_docs)

        # Add the new cleaned version to all experiments that have this document
        # NOTE: The cleaned version is added with NO processing records because the text has changed
        # and old processing results (embeddings, entities, etc.) are no longer valid.
        # Users must re-run processing tools on the cleaned version to get accurate results.
        for experiment_id in experiment_ids:
            # Check if the cleaned version is already in this experiment
            existing_exp_doc = ExperimentDocument.query.filter_by(
                experiment_id=experiment_id,
                document_id=cleaned_version.id
            ).first()

            if not existing_exp_doc:
                # Add the cleaned version to the experiment (no processing records)
                new_exp_doc = ExperimentDocument(
                    experiment_id=experiment_id,
                    document_id=cleaned_version.id
                )
                db.session.add(new_exp_doc)
                db.session.flush()  # Flush to get the ID
                app.logger.info(f"Added cleaned version {cleaned_version.id} to experiment {experiment_id} (no processing records)")

        db.session.commit()

        return jsonify({
            'success': True,
            'version_uuid': str(cleaned_version.uuid),
            'message': f'Saved cleaned text ({changes_accepted} changes accepted, {changes_rejected} rejected)',
            'document_id': cleaned_version.id,
            'job_id': cleanup_job.id
        })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
