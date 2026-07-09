"""Document segmentation routes."""

from flask import current_app as app, jsonify, request
from flask_login import current_user

from app import db
from app.models.document import Document
from app.models.processing_job import ProcessingJob
from app.models.text_segment import TextSegment
from app.services.inheritance_versioning_service import InheritanceVersioningService
from app.utils.auth_decorators import api_require_login_for_write

from . import processing_bp


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

        # Create or get experiment version (one version per experiment)
        # If no experiment_id, fall back to old behavior for backward compatibility
        processing_metadata = {
            'segmentation_method': method,
            'chunk_size': chunk_size,
            'overlap': overlap,
            'experiment_id': experiment_id,
            'processing_notes': f'Document segmentation using {method} method'
        }

        if experiment_id:
            # EXPERIMENT VERSIONING: Get or create ONE version for this experiment
            processing_version, version_created = InheritanceVersioningService.get_or_create_experiment_version(
                original_document=original_document,
                experiment_id=experiment_id,
                user=current_user
            )
            # PROV-O: Version creation already tracked if new version was created
            app.logger.info(f"Using experiment version {processing_version.id} for experiment {experiment_id} "
                          f"({'newly created' if version_created else 'existing'})")
        else:
            # BACKWARD COMPATIBILITY: Manual processing outside experiment uses old method
            processing_version = InheritanceVersioningService.create_new_version(
                original_document=original_document,
                processing_type='segmentation',
                processing_metadata=processing_metadata
            )
            app.logger.info(f"Created processed version {processing_version.id} for manual segmentation")

        # Note: PROV-O tracking for segmentation will be done after segmentation completes
        
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
            'processing_version_uuid': processing_version.uuid,  # UUID for version-specific queries
            'version_number': processing_version.version_number,
            'message': f'Document segmented into {segment_count} chunks (version {processing_version.version_number} with inherited processing)',
            'redirect_url': f'/input/document/{processing_version.uuid}'  # Use UUID for proper redirect
        }

        print(f"DEBUG: Segmentation response data: {response_data}")
        app.logger.error(f"SEGMENTATION RESPONSE: latest_version_id={processing_version.id}, processing_version_uuid={processing_version.uuid}, redirect_url={response_data['redirect_url']}")
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
