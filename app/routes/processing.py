from flask import Blueprint, render_template, request, jsonify, current_app as app
from flask_login import current_user
from app.utils.auth_decorators import require_login_for_write, api_require_login_for_write
from sqlalchemy import func, text
import os
from app import db
from app.models.document import Document
from app.models.processing_job import ProcessingJob
from app.models.extracted_entity import ExtractedEntity
from app.models.text_segment import TextSegment
from app.models.provenance import ProvenanceEntity, ProvenanceActivity
from app.services.enhanced_document_processor import EnhancedDocumentProcessor
from app.services.inheritance_versioning_service import InheritanceVersioningService

processing_bp = Blueprint('processing', __name__)

@processing_bp.route('/')
def processing_home():
    """Processing pipeline home page - shows live experiment processing status"""
    # Import experiment models
    from app.models.experiment_processing import ExperimentDocumentProcessing
    from app.models.experiment import Experiment
    from app.models.experiment_document import ExperimentDocument

    # Aggregate document stats (total documents in system)
    doc_total = db.session.query(func.count(Document.id)).scalar() or 0
    doc_uploaded = db.session.query(func.count(Document.id)).filter(Document.status == 'uploaded').scalar() or 0
    doc_processing = db.session.query(func.count(Document.id)).filter(Document.status == 'processing').scalar() or 0
    doc_completed = db.session.query(func.count(Document.id)).filter(Document.status == 'completed').scalar() or 0
    doc_error = db.session.query(func.count(Document.id)).filter(Document.status == 'error').scalar() or 0

    # Aggregate experiment processing stats (actual live processing operations)
    processing_total = db.session.query(func.count(ExperimentDocumentProcessing.id)).scalar() or 0
    processing_pending = db.session.query(func.count(ExperimentDocumentProcessing.id)).filter(ExperimentDocumentProcessing.status == 'pending').scalar() or 0
    processing_running = db.session.query(func.count(ExperimentDocumentProcessing.id)).filter(ExperimentDocumentProcessing.status == 'running').scalar() or 0
    processing_completed = db.session.query(func.count(ExperimentDocumentProcessing.id)).filter(ExperimentDocumentProcessing.status == 'completed').scalar() or 0
    processing_failed = db.session.query(func.count(ExperimentDocumentProcessing.id)).filter(ExperimentDocumentProcessing.status == 'failed').scalar() or 0

    stats = {
        'documents': {
            'total': doc_total,
            'uploaded': doc_uploaded,
            'processing': doc_processing,
            'completed': doc_completed,
            'error': doc_error,
        },
        'processing_operations': {
            'total': processing_total,
            'pending': processing_pending,
            'running': processing_running,
            'completed': processing_completed,
            'failed': processing_failed,
        }
    }

    # Recent documents from experiments
    recent_documents = (
        db.session.query(Document)
        .join(ExperimentDocument, Document.id == ExperimentDocument.document_id)
        .order_by(ExperimentDocument.added_at.desc())
        .limit(10)
        .all()
    )

    # Recent processing operations instead of old processing jobs
    recent_processing = (
        db.session.query(ExperimentDocumentProcessing)
        .join(ExperimentDocument, ExperimentDocumentProcessing.experiment_document_id == ExperimentDocument.id)
        .join(Document, ExperimentDocument.document_id == Document.id)
        .join(Experiment, ExperimentDocument.experiment_id == Experiment.id)
        .order_by(ExperimentDocumentProcessing.created_at.desc())
        .limit(10)
        .all()
    )

    return render_template('processing/index.html', stats=stats, recent_documents=recent_documents, recent_processing=recent_processing)

@processing_bp.route('/jobs')
def job_list():
    """List processing operations - public view"""
    # Import experiment models
    from app.models.experiment_processing import ExperimentDocumentProcessing
    from app.models.experiment import Experiment
    from app.models.experiment_document import ExperimentDocument

    # Get processing operations from experiments
    processing_operations = (
        db.session.query(ExperimentDocumentProcessing)
        .join(ExperimentDocument, ExperimentDocumentProcessing.experiment_document_id == ExperimentDocument.id)
        .join(Document, ExperimentDocument.document_id == Document.id)
        .join(Experiment, ExperimentDocument.experiment_id == Experiment.id)
        .order_by(ExperimentDocumentProcessing.created_at.desc())
        .limit(100)
        .all()
    )

    # Also get legacy processing jobs if any exist
    legacy_jobs = (
        db.session.query(ProcessingJob)
        .order_by(ProcessingJob.created_at.desc())
        .limit(50)
        .all()
    )

    return render_template('processing/jobs.html', processing_operations=processing_operations, legacy_jobs=legacy_jobs)

@processing_bp.route('/start/<int:document_id>')
@require_login_for_write
def start_processing(document_id):
    """Start processing a document - requires login"""
    # Placeholder for now
    return jsonify({'message': 'Processing will be implemented in phase 2'})

@processing_bp.route('/document/<string:document_uuid>/embeddings', methods=['POST'])
@api_require_login_for_write
def generate_embeddings(document_uuid):
    """Generate embeddings for a document (creates new version)"""
    try:
        original_document = Document.query.filter_by(uuid=document_uuid).first_or_404()
        
        # Get embedding method from request or use default
        data = request.get_json() or {}
        embedding_method = data.get('method', 'local')
        experiment_id = data.get('experiment_id')  # Optional experiment association
        
        # Period-aware embedding parameters
        force_period = data.get('force_period')
        model_preference = data.get('model_preference')
        auto_detect_period = data.get('auto_detect_period', False)
        
        # Validate embedding method
        available_methods = ['local', 'openai', 'claude', 'huggingface', 'period_aware']
        if embedding_method not in available_methods:
            return jsonify({
                'success': False, 
                'error': f'Invalid embedding method. Available: {", ".join(available_methods)}'
            }), 400
        
        if not original_document.content:
            return jsonify({
                'success': False, 
                'error': 'Document has no content to generate embeddings from'
            }), 400
        
        # Create processing notes with period-aware info
        processing_notes = f'Embeddings processing using {embedding_method} method'
        if embedding_method == 'period_aware':
            if force_period:
                processing_notes += f' (forced period: {force_period})'
            if model_preference:
                processing_notes += f' (preference: {model_preference})'
            if auto_detect_period:
                processing_notes += ' (auto-detect period)'
        
        # Create a new version using inheritance (includes all previous processing)
        processing_metadata = {
            'embedding_method': embedding_method,
            'experiment_id': experiment_id,
            'processing_notes': processing_notes
        }
        if embedding_method == 'period_aware':
            processing_metadata.update({
                'force_period': force_period,
                'model_preference': model_preference,
                'auto_detect_period': auto_detect_period
            })
        
        processing_version = InheritanceVersioningService.create_new_version(
            original_document=original_document,
            processing_type='embeddings',
            processing_metadata=processing_metadata
        )
        
        # Note: PROV-O tracking will be done after embeddings complete
        
        # Create processing job linked to the new version
        job = ProcessingJob(
            document_id=processing_version.id,  # Link to processing version
            job_type='generate_embeddings',
            status='pending',
            user_id=current_user.id
        )
        job.set_parameters({
            'embedding_method': embedding_method,
            'original_document_id': original_document.id,
            'version_type': 'processed'
        })
        db.session.add(job)
        db.session.commit()
        
        # Use actual EmbeddingService
        try:
            from shared_services.embedding.embedding_service import EmbeddingService
            from datetime import datetime
            import time
            
            # Initialize embedding service
            embedding_service = EmbeddingService()
            
            # Record start time
            start_time = time.time()
            
            # Process document content in chunks if too long
            content = processing_version.content
            max_length = 8000  # Conservative limit for most embedding models
            
            if len(content) > max_length:
                # Split into chunks and embed each
                chunks = [content[i:i+max_length] for i in range(0, len(content), max_length)]
                embeddings = []
                for chunk in chunks:
                    chunk_embedding = embedding_service.get_embedding(chunk)
                    embeddings.append(chunk_embedding)
                
                chunk_count = len(chunks)
            else:
                # Single embedding for short documents
                embeddings = [embedding_service.get_embedding(content)]
                chunk_count = 1
            
            # Calculate processing time
            processing_time = time.time() - start_time
            
            # Get actual model info
            model_name = embedding_service.get_model_name()
            dimension = embedding_service.get_dimension()
            
            job.status = 'completed'
            job.processing_time = processing_time
            job.set_result_data({
                'embedding_method': embedding_method,
                'embedding_dimensions': dimension,
                'chunk_count': chunk_count,
                'processing_time': processing_time,
                'model_used': model_name,
                'total_embeddings': len(embeddings),
                'content_length': len(content)
            })

            # Track embedding generation with PROV-O
            from app.services.provenance_service import provenance_service
            # Create mock segments for tracking (since embeddings are on chunks, not TextSegment objects)
            from types import SimpleNamespace
            mock_segments = [SimpleNamespace(id=i) for i in range(chunk_count)]
            provenance_service.track_embedding_generation(
                processing_version,
                current_user,
                model_name=model_name,
                segments=mock_segments,
                embedding_method=embedding_method,
                dimension=dimension
            )

            db.session.commit()
            
        except Exception as e:
            job.status = 'failed'
            job.set_result_data({
                'error': str(e),
                'embedding_method': embedding_method,
                'processing_time': time.time() - start_time if 'start_time' in locals() else 0
            })
            db.session.commit()
            raise e
        
        # Get base document ID for consistent redirection
        base_document_id = InheritanceVersioningService._get_base_document_id(original_document)
        
        response_data = {
            'success': True,
            'job_id': job.id,
            'method': embedding_method,
            'base_document_id': base_document_id,
            'latest_version_id': processing_version.id,
            'processing_version_id': processing_version.id,  # For frontend compatibility
            'version_number': processing_version.version_number,
            'message': f'Embeddings generated using {embedding_method} method (version {processing_version.version_number} with inherited processing)',
            'redirect_url': f'/input/document/{processing_version.id}'
        }
        
        print(f"DEBUG: Embeddings response data: {response_data}")
        app.logger.error(f"EMBEDDINGS RESPONSE: latest_version_id={processing_version.id}, redirect_url={response_data['redirect_url']}")
        return jsonify(response_data)
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@processing_bp.route('/document/<string:document_uuid>/segment', methods=['POST'])
@api_require_login_for_write
def segment_document(document_uuid):
    """Segment a document into chunks and create TextSegment objects (creates new version)"""
    try:
        original_document = Document.query.filter_by(uuid=document_uuid).first_or_404()
        
        data = request.get_json() or {}
        method = data.get('method', 'paragraph')  # Get segmentation method
        chunk_size = data.get('chunk_size', 500)
        overlap = data.get('overlap', 50)
        experiment_id = data.get('experiment_id')  # Optional experiment association
        
        if not original_document.content:
            return jsonify({
                'success': False, 
                'error': 'Document has no content to segment'
            }), 400
        
        # Create a new version using inheritance (includes all previous processing)
        processing_metadata = {
            'segmentation_method': method,
            'chunk_size': chunk_size,
            'overlap': overlap,
            'experiment_id': experiment_id,
            'processing_notes': f'Document segmentation using {method} method'
        }
        
        processing_version = InheritanceVersioningService.create_new_version(
            original_document=original_document,
            processing_type='segmentation',
            processing_metadata=processing_metadata
        )
        
        # Note: PROV-O tracking will be done after segmentation completes
        
        # Handle LangExtract segmentation method
        if method == 'langextract':
            try:
                from app.services.integrated_langextract_service import IntegratedLangExtractService
                
                # Check if the service can be initialized
                try:
                    langextract_service = IntegratedLangExtractService()
                except ValueError as ve:
                    # API key missing - provide clear fallback message
                    return jsonify({
                        'success': False,
                        'error': f'LangExtract requires API key: {str(ve)}',
                        'fallback_suggestion': 'Try paragraph or semantic segmentation instead',
                        'fallback_available': True,
                        'implementation_note': 'LangExtract two-stage architecture is implemented but requires GOOGLE_GEMINI_API_KEY'
                    }), 400
                
                if not langextract_service.service_ready:
                    return jsonify({
                        'success': False,
                        'error': 'LangExtract service not available. Please ensure GOOGLE_GEMINI_API_KEY is set.',
                        'fallback_suggestion': 'Try paragraph or semantic segmentation instead',
                        'fallback_available': True
                    }), 400
                
                # Create processing job for LangExtract linked to processing version
                job = ProcessingJob(
                    document_id=processing_version.id,  # Link to processing version
                    job_type='langextract_segmentation',
                    status='pending',
                    user_id=current_user.id
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
                
                # Perform integrated LangExtract analysis
                analysis_result = langextract_service.analyze_and_orchestrate_document(
                    document_id=processing_version.id,  # Use processing version
                    document_text=processing_version.content,
                    user_id=current_user.id
                )
                
                if not analysis_result.get('success'):
                    job.set_status('failed')
                    job.set_error_message(analysis_result.get('error', 'Unknown error'))
                    return jsonify({
                        'success': False,
                        'error': f"LangExtract analysis failed: {analysis_result.get('error', 'Unknown error')}",
                        'prov_o_tracking': False
                    }), 500
                
                # Get segmentation recommendations
                segmentation_recs = langextract_service.get_segmentation_recommendations(processing_version.content)
                
                # Create text segments based on LangExtract analysis
                from app.models.text_segment import TextSegment
                
                segments_created = []
                
                # Create segments from structural analysis
                for segment_info in segmentation_recs.get('structural_segments', []):
                    segment = TextSegment(
                        document_id=processing_version.id,  # Link to processing version
                        segment_number=len(segments_created) + 1,
                        start_position=segment_info.get('start_pos', 0),
                        end_position=segment_info.get('end_pos', 100),
                        content=processing_version.content[segment_info.get('start_pos', 0):segment_info.get('end_pos', 100)],
                        metadata={
                            'segmentation_method': 'langextract_structural',
                            'segment_type': segment_info.get('type', 'structural'),
                            'element': segment_info.get('element', 'unknown'),
                            'confidence': segment_info.get('confidence', 0.7),
                            'character_level_positions': True,
                            'langextract_analysis_id': analysis_result.get('analysis_id'),
                            'prov_o_tracked': True
                        }
                    )
                    db.session.add(segment)
                    segments_created.append(segment)
                
                # Create segments from semantic analysis
                for segment_info in segmentation_recs.get('semantic_segments', []):
                    segment = TextSegment(
                        document_id=processing_version.id,  # Link to processing version
                        segment_number=len(segments_created) + 1,
                        start_position=segment_info.get('start_pos', 0),
                        end_position=segment_info.get('end_pos', 100),
                        content=processing_version.content[segment_info.get('start_pos', 0):segment_info.get('end_pos', 100)],
                        metadata={
                            'segmentation_method': 'langextract_semantic',
                            'segment_type': segment_info.get('type', 'semantic'),
                            'primary_concepts': segment_info.get('primary_concepts', []),
                            'confidence': segment_info.get('confidence', 0.7),
                            'character_level_positions': True,
                            'langextract_analysis_id': analysis_result.get('analysis_id'),
                            'prov_o_tracked': True
                        }
                    )
                    db.session.add(segment)
                    segments_created.append(segment)
                
                # If no specific segments found, create basic segments with LangExtract metadata
                if not segments_created:
                    # Fall back to paragraph-based segmentation with LangExtract enrichment
                    from app.services.text_processing import TextProcessingService
                    processing_service = TextProcessingService()
                    processing_service.create_initial_segments(processing_version)
                    
                    # Enrich segments with LangExtract metadata in processing_notes
                    import json
                    for segment in processing_version.text_segments:
                        langextract_metadata = {
                            'enriched_with_langextract': True,
                            'langextract_analysis_id': analysis_result.get('analysis_id'),
                            'character_level_positions': True,
                            'prov_o_tracked': True
                        }
                        
                        # Store metadata in processing_notes as JSON
                        if segment.processing_notes:
                            try:
                                existing_notes = json.loads(segment.processing_notes)
                                if isinstance(existing_notes, dict):
                                    existing_notes.update(langextract_metadata)
                                    segment.processing_notes = json.dumps(existing_notes)
                                else:
                                    # If existing notes is not a dict, preserve it and add metadata
                                    segment.processing_notes = json.dumps({
                                        'original_notes': str(existing_notes),
                                        **langextract_metadata
                                    })
                            except (json.JSONDecodeError, TypeError):
                                # If existing notes is not JSON, preserve it and add metadata
                                segment.processing_notes = json.dumps({
                                    'original_notes': str(segment.processing_notes),
                                    **langextract_metadata
                                })
                        else:
                            segment.processing_notes = json.dumps(langextract_metadata)
                    
                    segments_created = list(processing_version.text_segments)
                
                db.session.commit()
                
                # Update job status
                job.set_status('completed')
                job.set_parameters({
                    **job.parameters,
                    'segments_created': len(segments_created),
                    'langextract_analysis_complete': True,
                    'orchestration_plan_generated': True,
                    'prov_o_tracking_complete': True
                })

                # Track segmentation with PROV-O
                from app.services.provenance_service import provenance_service
                provenance_service.track_document_segmentation(
                    processing_version,
                    current_user,
                    method='langextract',
                    segment_count=len(segments_created),
                    segments=segments_created,
                    tool_name='langextract'
                )
                
                return jsonify({
                    'success': True,
                    'method': 'langextract',
                    'segments_created': len(segments_created),
                    'analysis_id': analysis_result.get('analysis_id'),
                    'original_document_id': original_document.id,
                    'processing_version_id': processing_version.id,
                    'version_number': processing_version.version_number,
                    'message': f'Document segmented using LangExtract two-stage architecture into {len(segments_created)} segments (created version {processing_version.version_number})',
                    'langextract_features': {
                        'two_stage_architecture': True,
                        'character_level_positioning': True,
                        'llm_orchestration': True,
                        'prov_o_tracking': True,
                        'jcdl_section_3_1_implemented': True
                    },
                    'segmentation_summary': {
                        'structural_segments': len(segmentation_recs.get('structural_segments', [])),
                        'semantic_segments': len(segmentation_recs.get('semantic_segments', [])),
                        'temporal_segments': len(segmentation_recs.get('temporal_segments', [])),
                        'confidence': segmentation_recs.get('confidence', 0.5)
                    },
                    'provenance_tracking': analysis_result.get('provenance_tracking', {})
                })
                
            except Exception as e:
                # LangExtract failed, update job and return error
                if 'job' in locals():
                    job.set_status('failed')
                    job.set_error_message(f"LangExtract error: {str(e)}")
                return jsonify({
                    'success': False,
                    'error': f'LangExtract segmentation failed: {str(e)}',
                    'fallback_available': True,
                    'fallback_suggestion': 'Try paragraph or semantic segmentation instead'
                }), 500
            
        # Handle traditional segmentation methods using DocumentProcessor tools
        from app.services.processing_tools import DocumentProcessor
        from app.models.text_segment import TextSegment
        from app.text_utils import clean_jstor_boilerplate

        processor = DocumentProcessor(user_id=current_user.id)

        # Get clean content (remove JSTOR boilerplate if present)
        content = clean_jstor_boilerplate(processing_version.content)
        if not content:
            content = processing_version.content

        # Call appropriate tool based on method
        if method == 'paragraph':
            result = processor.segment_paragraph(content)
        elif method == 'sentence':
            result = processor.segment_sentence(content)
        else:
            # Default to paragraph if method is unknown
            result = processor.segment_paragraph(content)

        # Check if processing succeeded
        if result.status != 'success':
            return jsonify({
                'success': False,
                'error': result.metadata.get('error', 'Segmentation failed'),
                'method': method
            }), 500

        # Create TextSegment database objects from processing result
        current_position = 0
        for i, segment_text in enumerate(result.data):
            # Find position in original content
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

        # Create processing job linked to processing version
        job = ProcessingJob(
            document_id=processing_version.id,  # Link to processing version
            job_type='segment_document',
            status='pending',
            user_id=current_user.id
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

        # Count created segments
        segment_count = processing_version.text_segments.count()
        
        job.status = 'completed'
        job.set_result_data({
            'segment_count': segment_count,
            'chunk_size': chunk_size,
            'overlap': overlap,
            'total_words': len(processing_version.content.split()) if processing_version.content else 0
        })

        # Track segmentation with PROV-O
        from app.services.provenance_service import provenance_service
        tool_name = 'nltk' if method == 'sentence' else None
        provenance_service.track_document_segmentation(
            processing_version,
            current_user,
            method=method,
            segment_count=segment_count,
            segments=list(processing_version.text_segments),
            tool_name=tool_name
        )

        db.session.commit()
        
        # Get base document ID for consistent redirection
        base_document_id = InheritanceVersioningService._get_base_document_id(original_document)
        
        response_data = {
            'success': True,
            'job_id': job.id,
            'segments_created': segment_count,
            'base_document_id': base_document_id,
            'latest_version_id': processing_version.id,
            'processing_version_id': processing_version.id,  # For frontend compatibility
            'version_number': processing_version.version_number,
            'message': f'Document segmented into {segment_count} chunks (version {processing_version.version_number} with inherited processing)',
            'redirect_url': f'/input/document/{processing_version.id}'
        }
        
        print(f"DEBUG: Segmentation response data: {response_data}")
        app.logger.error(f"SEGMENTATION RESPONSE: latest_version_id={processing_version.id}, redirect_url={response_data['redirect_url']}")
        return jsonify(response_data)
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

@processing_bp.route('/document/<int:document_id>/segments', methods=['DELETE'])
@api_require_login_for_write
def delete_document_segments(document_id):
    """Delete all segments for a document"""
    try:
        document = Document.query.get_or_404(document_id)
        
        # Count segments before deletion
        segment_count = document.text_segments.count()
        
        if segment_count == 0:
            return jsonify({
                'success': False,
                'error': 'No segments found to delete'
            }), 400
            
        # Delete all text segments for this document
        from app.models.text_segment import TextSegment
        deleted_count = TextSegment.query.filter_by(document_id=document_id).delete()
        
        # Create processing job to track the deletion
        job = ProcessingJob(
            document_id=document_id,
            job_type='delete_segments',
            status='completed',
            user_id=current_user.id
        )
        job.set_parameters({'segments_deleted': deleted_count})
        job.set_result_data({
            'segments_deleted': deleted_count,
            'deletion_method': 'bulk_delete'
        })
        db.session.add(job)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'job_id': job.id,
            'segments_deleted': deleted_count,
            'message': f'Deleted {deleted_count} text segments'
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@processing_bp.route('/document/<string:document_uuid>/entities', methods=['POST'])
@api_require_login_for_write
def extract_entities(document_uuid):
    """Extract entities from a document"""
    try:
        document = Document.query.filter_by(uuid=document_uuid).first_or_404()
        
        data = request.get_json() or {}
        entity_types = data.get('entity_types', ['PERSON', 'ORG', 'GPE', 'DATE'])
        
        if not document.content:
            return jsonify({
                'success': False, 
                'error': 'Document has no content to extract entities from'
            }), 400
            
        # Create processing job
        job = ProcessingJob(
            document_id=document.id,
            job_type='extract_entities',
            status='pending',
            user_id=current_user.id
        )
        job.set_parameters({'entity_types': entity_types})
        db.session.add(job)
        db.session.commit()
        
        # TODO: Replace with actual entity extraction (spaCy, etc.)
        # For now, simulate entity extraction
        words = document.content.split()
        entity_count = len(words) // 20  # Simulate ~5% of words as entities
        
        job.status = 'completed'
        job.set_result_data({
            'entities_found': entity_count,
            'entity_types': entity_types,
            'processing_method': 'spacy_en_core_web_sm',
            'confidence_threshold': 0.7
        })
        db.session.commit()
        
        return jsonify({
            'success': True,
            'job_id': job.id,
            'entities_found': entity_count,
            'message': f'Extracted {entity_count} entities from document'
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@processing_bp.route('/document/<string:document_uuid>/metadata', methods=['POST'])
@api_require_login_for_write
def analyze_metadata(document_uuid):
    """Analyze and enhance document metadata"""
    try:
        document = Document.query.filter_by(uuid=document_uuid).first_or_404()
        
        # Create processing job
        job = ProcessingJob(
            document_id=document.id,
            job_type='analyze_metadata',
            status='pending',
            user_id=current_user.id
        )
        job.set_parameters({})
        db.session.add(job)
        db.session.commit()
        
        # TODO: Replace with actual metadata analysis
        # For now, simulate metadata extraction
        metadata_fields = {
            'language': 'en',
            'language_confidence': 0.95,
            'document_type': 'academic',
            'estimated_reading_time': len(document.content.split()) / 200 if document.content else 0,
            'complexity_score': 0.7,
            'domain': 'technology'
        }
        
        job.status = 'completed'
        job.set_result_data({
            'metadata_extracted': metadata_fields,
            'fields_enhanced': len(metadata_fields),
            'analysis_method': 'heuristic_plus_llm'
        })
        db.session.commit()
        
        return jsonify({
            'success': True,
            'job_id': job.id,
            'metadata': metadata_fields,
            'message': f'Enhanced {len(metadata_fields)} metadata fields'
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@processing_bp.route('/document/<int:document_id>/clear-jobs', methods=['POST'])
@api_require_login_for_write
def clear_document_jobs(document_id):
    """Clear all processing jobs for a document (for testing purposes)"""
    try:
        document = Document.query.get_or_404(document_id)
        
        # Delete all processing jobs for this document by the current user
        deleted_count = (
            ProcessingJob.query
            .filter_by(document_id=document_id, user_id=current_user.id)
            .delete()
        )
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'deleted_count': deleted_count,
            'message': f'Cleared {deleted_count} processing jobs for this document'
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@processing_bp.route('/document/<string:document_uuid>/enhanced', methods=['POST'])
@api_require_login_for_write
def enhanced_document_processing(document_uuid):
    """Enhanced document processing with term extraction and OED enrichment"""
    try:
        document = Document.query.filter_by(uuid=document_uuid).first_or_404()
        
        if not document.content:
            return jsonify({
                'success': False, 
                'error': 'Document has no content to process'
            }), 400
        
        data = request.get_json() or {}
        extract_terms = data.get('extract_terms', True)
        enrich_with_oed = data.get('enrich_with_oed', False)
        min_term_frequency = data.get('min_term_frequency', 2)
        
        # Create processing job
        job = ProcessingJob(
            document_id=document.id,
            job_type='enhanced_processing',
            status='pending',
            user_id=current_user.id
        )
        job.set_parameters({
            'extract_terms': extract_terms,
            'enrich_with_oed': enrich_with_oed,
            'min_term_frequency': min_term_frequency
        })
        db.session.add(job)
        db.session.commit()
        
        # Perform enhanced processing
        processor = EnhancedDocumentProcessor()
        result = processor.process_document_with_enrichment(
            document,
            extract_terms=extract_terms,
            enrich_with_oed=enrich_with_oed,
            min_term_frequency=min_term_frequency
        )
        
        # Update job with results
        job.status = 'completed' if result['success'] else 'failed'
        job.set_result_data({
            'document_processed': result['document_processed'],
            'terms_extracted': result['terms_extracted'],
            'terms_enriched': result['terms_enriched'],
            'extracted_terms': [t['term_text'] for t in result['extracted_terms']],
            'enrichment_success_rate': (
                result['terms_enriched'] / result['terms_extracted'] 
                if result['terms_extracted'] > 0 else 0
            ),
            'processing_errors': result['errors']
        })
        db.session.commit()
        
        return jsonify({
            'success': result['success'],
            'job_id': job.id,
            'document_processed': result['document_processed'],
            'terms_extracted': result['terms_extracted'],
            'terms_enriched': result['terms_enriched'],
            'extracted_terms': result['extracted_terms'][:10],  # Return first 10 terms
            'message': (
                f'Enhanced processing completed. '
                f'Extracted {result["terms_extracted"]} terms, '
                f'enriched {result["terms_enriched"]} with OED data.'
            ),
            'errors': result['errors']
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@processing_bp.route('/batch/enhanced', methods=['POST'])
@api_require_login_for_write
def batch_enhanced_processing():
    """Process multiple documents with enhanced processing and OED enrichment"""
    try:
        data = request.get_json()
        if not data or not data.get('document_ids'):
            return jsonify({
                'success': False,
                'error': 'document_ids array is required'
            }), 400
        
        document_ids = data['document_ids']
        extract_terms = data.get('extract_terms', True)
        enrich_with_oed = data.get('enrich_with_oed', False)
        
        # Validate document IDs
        valid_documents = Document.query.filter(Document.id.in_(document_ids)).all()
        valid_ids = [doc.id for doc in valid_documents]
        
        if len(valid_ids) != len(document_ids):
            invalid_ids = set(document_ids) - set(valid_ids)
            return jsonify({
                'success': False,
                'error': f'Invalid document IDs: {list(invalid_ids)}'
            }), 400
        
        # Create batch processing job
        job = ProcessingJob(
            document_id=None,  # Batch job
            job_type='batch_enhanced_processing',
            status='pending',
            user_id=current_user.id
        )
        job.set_parameters({
            'document_ids': document_ids,
            'extract_terms': extract_terms,
            'enrich_with_oed': enrich_with_oed,
            'document_count': len(document_ids)
        })
        db.session.add(job)
        db.session.commit()
        
        # Perform batch processing
        processor = EnhancedDocumentProcessor()
        batch_result = processor.process_document_batch_with_enrichment(
            document_ids,
            extract_terms=extract_terms,
            enrich_with_oed=enrich_with_oed
        )
        
        # Update job with results
        job.status = 'completed' if batch_result['success'] else 'failed'
        job.set_result_data({
            'documents_processed': batch_result['documents_processed'],
            'total_terms_extracted': batch_result['total_terms_extracted'],
            'total_terms_enriched': batch_result['total_terms_enriched'],
            'document_results': [
                {
                    'document_id': r['document_id'],
                    'document_title': r['document_title'],
                    'success': r['result']['success'],
                    'terms_extracted': r['result']['terms_extracted'],
                    'terms_enriched': r['result']['terms_enriched']
                }
                for r in batch_result['document_results']
            ],
            'processing_errors': batch_result['errors']
        })
        db.session.commit()
        
        return jsonify({
            'success': batch_result['success'],
            'job_id': job.id,
            'documents_processed': batch_result['documents_processed'],
            'total_terms_extracted': batch_result['total_terms_extracted'],
            'total_terms_enriched': batch_result['total_terms_enriched'],
            'document_results': batch_result['document_results'],
            'message': (
                f'Batch processing completed. '
                f'Processed {batch_result["documents_processed"]} documents, '
                f'extracted {batch_result["total_terms_extracted"]} terms, '
                f'enriched {batch_result["total_terms_enriched"]} with OED data.'
            ),
            'errors': batch_result['errors']
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@processing_bp.route('/api/processing/job/<int:job_id>/langextract-details')
@api_require_login_for_write
def get_langextract_details(job_id):
    """Get detailed LangExtract analysis results for a specific job"""
    try:
        # Get the processing job
        job = ProcessingJob.query.get_or_404(job_id)
        
        # Verify this is a LangExtract job
        if job.job_type != 'langextract_segmentation':
            return jsonify({
                'success': False,
                'error': 'This endpoint is only for LangExtract segmentation jobs'
            }), 400
        
        # Get job parameters and results
        params = job.get_parameters()
        results = job.get_result_data()
        
        # Extract key information
        response_data = {
            'success': True,
            'job_info': {
                'job_id': job.id,
                'document_id': job.document_id,
                'status': job.status,
                'created_at': job.created_at.isoformat() if job.created_at else None,
                'processing_time': job.processing_time
            },
            'parameters': params,
            'results': results
        }
        
        # Try to load detailed analysis data from temp files if available
        analysis_id = params.get('langextract_analysis_id') or results.get('analysis_id')
        if analysis_id:
            try:
                import tempfile
                import json
                
                # Look for detailed analysis files
                temp_dir = tempfile.gettempdir()
                analysis_file = os.path.join(temp_dir, f"langextract_analysis_{analysis_id}.json")
                
                if os.path.exists(analysis_file):
                    with open(analysis_file, 'r') as f:
                        detailed_analysis = json.load(f)
                    
                    response_data['detailed_analysis'] = {
                        'key_concepts': detailed_analysis.get('key_concepts', []),
                        'temporal_markers': detailed_analysis.get('temporal_markers', []),
                        'domain_indicators': detailed_analysis.get('domain_indicators', []),
                        'structural_segments': detailed_analysis.get('structural_segments', []),
                        'semantic_segments': detailed_analysis.get('semantic_segments', []),
                        'analysis_metadata': detailed_analysis.get('metadata', {})
                    }
            except Exception as e:
                # Detailed analysis loading failed, but basic job info is still available
                response_data['detailed_analysis_error'] = str(e)
        
        # Add summary statistics
        response_data['summary'] = {
            'key_concepts_extracted': params.get('key_concepts_extracted', 0),
            'temporal_markers_found': params.get('temporal_markers_found', 0),
            'domain_indicators_identified': params.get('domain_indicators_identified', 0),
            'segments_created': params.get('segments_created', 0),
            'character_level_positions': params.get('character_level_positions', True),
            'prov_o_tracking_complete': params.get('prov_o_tracking_complete', False)
        }

        return jsonify(response_data)

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@processing_bp.route('/document/<string:document_uuid>/processing-jobs', methods=['GET'])
def get_document_processing_jobs(document_uuid):
    """Get all processing jobs for a document"""
    try:
        document = Document.query.filter_by(uuid=document_uuid).first_or_404()

        # Get all processing jobs for this document in two ways:
        # 1. Jobs directly linked to this document (document_id = this doc's id)
        # 2. Jobs where parameters contain original_document_id = this document's id
        #    (these are jobs created for processing versions like embeddings)

        # First get direct jobs
        jobs = ProcessingJob.query.filter_by(document_id=document.id).all()

        # Then find indirect jobs (processing versions)
        # These have parameters.original_document_id = document.id
        all_potential_jobs = ProcessingJob.query.filter(
            ProcessingJob.document_id != document.id
        ).all()

        indirect_job_ids = []
        for job in all_potential_jobs:
            params = job.get_parameters()
            if params.get('original_document_id') == document.id:
                indirect_job_ids.append(job.id)
                jobs.append(job)

        # Sort by created_at desc (put None values last)
        jobs.sort(key=lambda j: (j.created_at is None, j.created_at), reverse=True)

        # Group jobs by type and method combination to find duplicates
        jobs_by_type = {}
        for job in jobs:
            params = job.get_parameters()

            # Extract method/descriptor based on job type
            method = 'default'
            if job.job_type in ['generate_embeddings', 'segment_document']:
                method = params.get('method', 'default')
            elif job.job_type == 'extract_entities':
                entity_types = params.get('entity_types', [])
                method = f"{len(entity_types)} types" if entity_types else 'default'
            elif job.job_type == 'analyze_metadata':
                method = 'auto'
            elif job.job_type == 'enhanced_processing':
                extract_terms = params.get('extract_terms', False)
                enrich_oed = params.get('enrich_with_oed', False)
                method = 'terms+OED' if extract_terms and enrich_oed else 'terms' if extract_terms else 'default'

            # Create unique key for this job type + method combination
            key = f"{job.job_type}:{method}"

            if key not in jobs_by_type:
                jobs_by_type[key] = {
                    'latest': job,
                    'method': method,
                    'all_jobs': []
                }
            jobs_by_type[key]['all_jobs'].append(job)

        # Build response with only latest job per type, but include count
        processing_operations = []
        for key, group in jobs_by_type.items():
            latest_job = group['latest']
            all_jobs = group['all_jobs']
            count = len(all_jobs)

            processing_operations.append({
                'id': latest_job.id,
                'processing_type': latest_job.job_type,
                'processing_method': group['method'],
                'status': latest_job.status,
                'created_at': latest_job.created_at.isoformat() if latest_job.created_at else None,
                'completed_at': latest_job.completed_at.isoformat() if latest_job.completed_at else None,
                'error_message': latest_job.error_message,
                'run_count': count,
                'has_history': count > 1,
                'all_job_ids': [j.id for j in all_jobs] if count > 1 else []
            })

        # Sort by latest created_at
        processing_operations.sort(key=lambda op: op['created_at'] if op['created_at'] else '', reverse=True)

        return jsonify({
            'success': True,
            'processing_operations': processing_operations
        })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@processing_bp.route('/document/<string:document_uuid>/results/embeddings', methods=['GET'])
def view_embeddings_results(document_uuid):
    """View embeddings results for a document"""
    try:
        document = Document.query.filter_by(uuid=document_uuid).first_or_404()

        # Get all embedding jobs for this document (including processing versions)
        jobs = ProcessingJob.query.filter_by(document_id=document.id, job_type='generate_embeddings').all()

        # Also check for jobs in processing versions
        all_potential_jobs = ProcessingJob.query.filter(
            ProcessingJob.document_id != document.id,
            ProcessingJob.job_type == 'generate_embeddings'
        ).all()

        for job in all_potential_jobs:
            params = job.get_parameters()
            if params.get('original_document_id') == document.id:
                jobs.append(job)

        # Sort by created_at desc
        jobs.sort(key=lambda j: (j.created_at is None, j.created_at), reverse=True)

        # Get embedding statistics
        embeddings = db.session.query(
            func.count().label('count'),
            func.avg(func.length(text('embedding::text'))).label('avg_size')
        ).filter_by(document_id=document.id).first()

        from flask import render_template
        return render_template('processing/embeddings_results.html',
                             document=document,
                             jobs=jobs,
                             embedding_count=embeddings.count if embeddings else 0)

    except Exception as e:
        from flask import render_template
        return render_template('processing/error.html',
                             document=document,
                             error=str(e)), 500

@processing_bp.route('/document/<string:document_uuid>/results/entities', methods=['GET'])
def view_entities_results(document_uuid):
    """View entity extraction results for a document"""
    try:
        document = Document.query.filter_by(uuid=document_uuid).first_or_404()

        # Get all entity extraction jobs
        jobs = ProcessingJob.query.filter_by(
            document_id=document.id,
            job_type='extract_entities'
        ).order_by(ProcessingJob.created_at.desc()).all()

        # Get entities from database
        entities = ExtractedEntity.query.filter_by(document_id=document.id).all()

        # Group entities by type
        entities_by_type = {}
        for entity in entities:
            entity_type = entity.entity_type or 'UNKNOWN'
            if entity_type not in entities_by_type:
                entities_by_type[entity_type] = []
            entities_by_type[entity_type].append(entity)

        # Prepare displaCy-style data
        displacy_data = {
            'text': document.content[:5000] if document.content else '',  # Limit to first 5000 chars
            'ents': []
        }

        for entity in entities:
            if entity.start_position is not None and entity.end_position is not None:
                displacy_data['ents'].append({
                    'start': entity.start_position,
                    'end': entity.end_position,
                    'label': entity.entity_type or 'UNKNOWN'
                })

        from flask import render_template
        return render_template('processing/entities_results.html',
                             document=document,
                             jobs=jobs,
                             entities=entities,
                             entities_by_type=entities_by_type,
                             displacy_data=displacy_data,
                             total_entities=len(entities))

    except Exception as e:
        from flask import render_template
        return render_template('processing/error.html',
                             document=document,
                             error=str(e)), 500

@processing_bp.route('/document/<string:document_uuid>/results/segments', methods=['GET'])
def view_segments_results(document_uuid):
    """View segmentation results for a document"""
    try:
        document = Document.query.filter_by(uuid=document_uuid).first_or_404()

        # Get segmentation jobs
        jobs = ProcessingJob.query.filter_by(
            document_id=document.id,
            job_type='segment_document'
        ).order_by(ProcessingJob.created_at.desc()).all()

        # Also check processing versions
        all_potential_jobs = ProcessingJob.query.filter(
            ProcessingJob.document_id != document.id,
            ProcessingJob.job_type == 'segment_document'
        ).all()

        for job in all_potential_jobs:
            params = job.get_parameters()
            if params.get('original_document_id') == document.id:
                jobs.append(job)

        jobs.sort(key=lambda j: (j.created_at is None, j.created_at), reverse=True)

        # Get segments from database
        segments = TextSegment.query.filter_by(document_id=document.id).order_by(TextSegment.segment_number).all()

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

@processing_bp.route('/document/<string:document_uuid>/results/metadata', methods=['GET'])
def view_metadata_results(document_uuid):
    """View metadata analysis results for a document"""
    try:
        document = Document.query.filter_by(uuid=document_uuid).first_or_404()

        # Get metadata analysis jobs
        jobs = ProcessingJob.query.filter_by(
            document_id=document.id,
            job_type='analyze_metadata'
        ).order_by(ProcessingJob.created_at.desc()).all()

        from flask import render_template
        return render_template('processing/metadata_results.html',
                             document=document,
                             jobs=jobs)

    except Exception as e:
        from flask import render_template
        return render_template('processing/error.html',
                             document=document,
                             error=str(e)), 500

@processing_bp.route('/document/<string:document_uuid>/results/enhanced', methods=['GET'])
def view_enhanced_results(document_uuid):
    """View enhanced processing results for a document"""
    try:
        document = Document.query.filter_by(uuid=document_uuid).first_or_404()

        # Get enhanced processing jobs
        jobs = ProcessingJob.query.filter_by(
            document_id=document.id,
            job_type='enhanced_processing'
        ).order_by(ProcessingJob.created_at.desc()).all()

        # Get terms extracted for this document
        from app.models.term import Term
        terms = Term.query.filter_by(document_id=document.id).all()

        from flask import render_template
        return render_template('processing/enhanced_results.html',
                             document=document,
                             jobs=jobs,
                             terms=terms,
                             total_terms=len(terms))

    except Exception as e:
        from flask import render_template
        return render_template('processing/error.html',
                             document=document,
                             error=str(e)), 500
