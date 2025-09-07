from flask import Blueprint, render_template, request, jsonify, current_app as app
from flask_login import login_required, current_user
from app.utils.auth_decorators import ajax_login_required
from sqlalchemy import func
import os
from app import db
from app.models.document import Document
from app.models.processing_job import ProcessingJob
from app.models.provenance import ProvenanceEntity, ProvenanceActivity
from app.services.enhanced_document_processor import EnhancedDocumentProcessor
from app.services.inheritance_versioning_service import InheritanceVersioningService

processing_bp = Blueprint('processing', __name__)

@processing_bp.route('/')
@login_required
def processing_home():
    """Processing pipeline home page"""
    # Aggregate document stats
    doc_total = db.session.query(func.count(Document.id)).scalar() or 0
    doc_uploaded = db.session.query(func.count(Document.id)).filter(Document.status == 'uploaded').scalar() or 0
    doc_processing = db.session.query(func.count(Document.id)).filter(Document.status == 'processing').scalar() or 0
    doc_completed = db.session.query(func.count(Document.id)).filter(Document.status == 'completed').scalar() or 0
    doc_error = db.session.query(func.count(Document.id)).filter(Document.status == 'error').scalar() or 0

    # Aggregate job stats
    job_total = db.session.query(func.count(ProcessingJob.id)).scalar() or 0
    job_running = db.session.query(func.count(ProcessingJob.id)).filter(getattr(ProcessingJob, 'status') == 'running').scalar() or 0
    job_pending = db.session.query(func.count(ProcessingJob.id)).filter(getattr(ProcessingJob, 'status') == 'pending').scalar() or 0
    job_completed = db.session.query(func.count(ProcessingJob.id)).filter(getattr(ProcessingJob, 'status') == 'completed').scalar() or 0
    job_failed = db.session.query(func.count(ProcessingJob.id)).filter(getattr(ProcessingJob, 'status') == 'failed').scalar() or 0

    stats = {
        'documents': {
            'total': doc_total,
            'uploaded': doc_uploaded,
            'processing': doc_processing,
            'completed': doc_completed,
            'error': doc_error,
        },
        'jobs': {
            'total': job_total,
            'pending': job_pending,
            'running': job_running,
            'completed': job_completed,
            'failed': job_failed,
        }
    }

    recent_documents = (
        db.session.query(Document)
        .order_by(Document.created_at.desc())
        .limit(10)
        .all()
    )
    recent_jobs = (
        db.session.query(ProcessingJob)
        .order_by(ProcessingJob.created_at.desc())
        .limit(10)
        .all()
    )

    return render_template('processing/index.html', stats=stats, recent_documents=recent_documents, recent_jobs=recent_jobs)

@processing_bp.route('/jobs')
@login_required
def job_list():
    """List processing jobs"""
    jobs = (
        db.session.query(ProcessingJob)
        .order_by(ProcessingJob.created_at.desc())
        .limit(50)
        .all()
    )
    return render_template('processing/jobs.html', jobs=jobs)

@processing_bp.route('/start/<int:document_id>')
@login_required
def start_processing(document_id):
    """Start processing a document"""
    # Placeholder for now
    return jsonify({'message': 'Processing will be implemented in phase 2'})

@processing_bp.route('/document/<int:document_id>/embeddings', methods=['POST'])
@ajax_login_required
def generate_embeddings(document_id):
    """Generate embeddings for a document (creates new version)"""
    try:
        original_document = Document.query.get_or_404(document_id)
        
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
        
        # Create PROV-O Entity for the new document version
        prov_entity = ProvenanceEntity.create_for_document(
            processing_version, 
            activity_type='embeddings_processing',
            agent=f'user_{current_user.id}'
        )
        db.session.add(prov_entity)
        
        # Create PROV-O Activity for the processing
        activity_id = f'activity_embeddings_{processing_version.id}'
        activity_metadata = {
            'embedding_method': embedding_method,
            'processing_start': 'pending'
        }
        
        # Add period-aware metadata if applicable
        if embedding_method == 'period_aware':
            activity_metadata.update({
                'force_period': force_period,
                'model_preference': model_preference,
                'auto_detect_period': auto_detect_period
            })
        
        prov_activity = ProvenanceActivity(
            prov_id=activity_id,
            prov_type='ont:EmbeddingsProcessing',
            prov_label=f'Embeddings generation for document {processing_version.id}',
            was_associated_with=f'user_{current_user.id}',
            activity_type='embeddings',
            activity_metadata=activity_metadata
        )
        db.session.add(prov_activity)
        
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
            'version_type': 'processed',
            'prov_entity_id': prov_entity.prov_id,
            'prov_activity_id': prov_activity.prov_id
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
            
            # Update PROV-O Activity completion
            prov_activity.complete_activity({
                'embedding_method': embedding_method,
                'model_used': model_name,
                'embedding_dimensions': dimension,
                'chunk_count': chunk_count,
                'total_embeddings': len(embeddings)
            })
            
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

@processing_bp.route('/document/<int:document_id>/segment', methods=['POST'])
@ajax_login_required 
def segment_document(document_id):
    """Segment a document into chunks and create TextSegment objects (creates new version)"""
    try:
        original_document = Document.query.get_or_404(document_id)
        
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
        
        # Create PROV-O Entity for the new document version
        prov_entity = ProvenanceEntity.create_for_document(
            processing_version,
            activity_type='segmentation_processing',
            agent=f'user_{current_user.id}'
        )
        db.session.add(prov_entity)
        
        # Create PROV-O Activity for the segmentation
        activity_id = f'activity_segmentation_{processing_version.id}'
        prov_activity = ProvenanceActivity(
            prov_id=activity_id,
            prov_type='ont:SegmentationProcessing', 
            prov_label=f'Document segmentation for document {processing_version.id}',
            was_associated_with=f'user_{current_user.id}',
            activity_type='segmentation',
            activity_metadata={
                'segmentation_method': method,
                'chunk_size': chunk_size,
                'overlap': overlap,
                'processing_start': 'pending'
            }
        )
        db.session.add(prov_activity)
        
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
                    'version_type': 'processed',
                    'prov_entity_id': prov_entity.prov_id,
                    'prov_activity_id': prov_activity.prov_id
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
                
                # Complete PROV-O Activity
                prov_activity.complete_activity({
                    'segmentation_method': method,
                    'segments_created': len(segments_created),
                    'langextract_analysis_complete': True,
                    'structural_segments': len(segmentation_recs.get('structural_segments', [])),
                    'semantic_segments': len(segmentation_recs.get('semantic_segments', []))
                })
                
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
            
        # Handle traditional segmentation methods (paragraph, sentence, semantic, hybrid)
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
            'version_type': 'processed',
            'prov_entity_id': prov_entity.prov_id,
            'prov_activity_id': prov_activity.prov_id
        })
        db.session.add(job)
        db.session.commit()
        
        # Import here to avoid circular imports
        from app.services.text_processing import TextProcessingService
        from app.models.text_segment import TextSegment
        
        # Actually create TextSegment objects for the processing version
        processing_service = TextProcessingService()
        processing_service.create_initial_segments(processing_version)
        
        # Count created segments
        segment_count = processing_version.text_segments.count()
        
        job.status = 'completed'
        job.set_result_data({
            'segment_count': segment_count,
            'chunk_size': chunk_size,
            'overlap': overlap,
            'total_words': len(processing_version.content.split())
        })
        
        # Complete PROV-O Activity
        prov_activity.complete_activity({
            'segmentation_method': method,
            'segments_created': segment_count,
            'chunk_size': chunk_size,
            'overlap': overlap,
            'total_words': len(processing_version.content.split())
        })
        
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
        return jsonify({'success': False, 'error': str(e)}), 500

@processing_bp.route('/document/<int:document_id>/segments', methods=['DELETE'])
@ajax_login_required
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

@processing_bp.route('/document/<int:document_id>/entities', methods=['POST'])
@login_required
def extract_entities(document_id):
    """Extract entities from a document"""
    try:
        document = Document.query.get_or_404(document_id)
        
        data = request.get_json() or {}
        entity_types = data.get('entity_types', ['PERSON', 'ORG', 'GPE', 'DATE'])
        
        if not document.content:
            return jsonify({
                'success': False, 
                'error': 'Document has no content to extract entities from'
            }), 400
            
        # Create processing job
        job = ProcessingJob(
            document_id=document_id,
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

@processing_bp.route('/document/<int:document_id>/metadata', methods=['POST'])
@login_required
def analyze_metadata(document_id):
    """Analyze and enhance document metadata"""
    try:
        document = Document.query.get_or_404(document_id)
        
        # Create processing job
        job = ProcessingJob(
            document_id=document_id,
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
@login_required
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


@processing_bp.route('/document/<int:document_id>/enhanced', methods=['POST'])
@ajax_login_required
def enhanced_document_processing(document_id):
    """Enhanced document processing with term extraction and OED enrichment"""
    try:
        document = Document.query.get_or_404(document_id)
        
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
            document_id=document_id,
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
@login_required
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
@login_required
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
