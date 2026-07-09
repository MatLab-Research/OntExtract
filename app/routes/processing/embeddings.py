"""Document embedding generation routes."""

from flask import current_app as app, jsonify, request
from flask_login import current_user

from app import db
from app.models.document import Document
from app.models.processing_job import ProcessingJob
from app.services.inheritance_versioning_service import InheritanceVersioningService
from app.utils.auth_decorators import api_require_login_for_write

from . import processing_bp


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

        # Create or get experiment version (one version per experiment)
        # If no experiment_id, fall back to old behavior for backward compatibility
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
                processing_type='embeddings',
                processing_metadata=processing_metadata
            )
            app.logger.info(f"Created processed version {processing_version.id} for manual embeddings")

        # Note: PROV-O tracking for embeddings will be done after embeddings complete
        
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

            # Period-aware embedding metadata (populated if using period_aware method)
            period_selection_info = None

            # Initialize embedding service with user-selected method
            # Map method names to provider priority (selected method first, then fallbacks)
            if embedding_method == 'period_aware':
                # Use PeriodAwareEmbeddingService for intelligent model selection
                from app.services.period_aware_embedding_service import get_period_aware_embedding_service
                period_service = get_period_aware_embedding_service()

                # Extract year from document metadata if available
                doc_year = None
                if original_document.publication_date:
                    doc_year = original_document.publication_date.year
                elif force_period:
                    # Try to parse year from force_period parameter
                    import re
                    year_match = re.search(r'\b(1[6-9]\d{2}|20[0-2]\d)\b', str(force_period))
                    if year_match:
                        doc_year = int(year_match.group(1))

                # Get period-appropriate model selection with metadata for later storage
                period_selection_info = period_service.select_model_for_period(
                    year=doc_year,
                    domain=model_preference,  # Use model_preference as domain hint
                    text_sample=processing_version.content[:1000] if auto_detect_period else None
                )
                # Store the detected year in the selection info for result metadata
                period_selection_info['period_detected'] = doc_year

                app.logger.info(f"Period-aware model selection: {period_selection_info['model']} "
                              f"(reason: {period_selection_info['selection_reason']}, "
                              f"confidence: {period_selection_info['selection_confidence']})")

                # Use local provider - the period_selection_info metadata tracks which model was selected
                # In a full implementation, this would configure the embedding service to use
                # the specific model (e.g., HistBERT for historical texts)
                provider_priority = ['local']

            elif embedding_method == 'openai':
                provider_priority = ['openai', 'local']
            elif embedding_method == 'claude':
                provider_priority = ['claude', 'local']
            elif embedding_method == 'local':
                provider_priority = ['local']
            else:
                provider_priority = ['local', 'openai', 'claude']  # Default fallback order

            embedding_service = EmbeddingService(provider_priority=provider_priority)
            
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
            result_data = {
                'embedding_method': embedding_method,
                'embedding_dimensions': dimension,
                'chunk_count': chunk_count,
                'processing_time': processing_time,
                'model_used': model_name,
                'total_embeddings': len(embeddings),
                'content_length': len(content)
            }

            # Add period-aware selection metadata if available
            if period_selection_info:
                result_data['period_aware'] = {
                    'selected_model': period_selection_info.get('model'),
                    'selection_reason': period_selection_info.get('selection_reason'),
                    'selection_confidence': period_selection_info.get('selection_confidence'),
                    'era': period_selection_info.get('era'),
                    'domain': period_selection_info.get('domain'),
                    'handles_archaic': period_selection_info.get('handles_archaic', False),
                    'detected_year': period_selection_info.get('period_detected')
                }

            job.set_result_data(result_data)

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
