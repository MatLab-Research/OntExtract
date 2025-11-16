"""
Experiments Document Processing Pipeline Routes

This module handles document processing pipeline operations for experiments.

Routes:
- GET  /experiments/<id>/document_pipeline                   - Pipeline overview
- GET  /experiments/<id>/process_document/<doc_id>           - Process specific document
- POST /experiments/<id>/document/<doc_id>/apply_embeddings  - Apply embeddings
- POST /api/experiment-processing/start                       - Start processing operation
- GET  /api/experiment-document/<id>/processing-status        - Get processing status
- GET  /api/processing/<id>/artifacts                         - Get processing artifacts
"""

from flask import render_template, request, jsonify, current_app
from flask_login import current_user
from app.utils.auth_decorators import api_require_login_for_write
from sqlalchemy import text
from app import db
from app.models import Document, Experiment, ExperimentDocument
from app.models.experiment_processing import ExperimentDocumentProcessing, ProcessingArtifact, DocumentProcessingIndex
from datetime import datetime

from . import experiments_bp
@experiments_bp.route('/<int:experiment_id>/document_pipeline')
def document_pipeline(experiment_id):
    """Step 2: Document Processing Pipeline Overview"""
    experiment = Experiment.query.filter_by(id=experiment_id).first_or_404()

    # Get experiment documents with new processing model
    from app.models.experiment_document import ExperimentDocument
    from app.models.experiment_processing import ExperimentDocumentProcessing

    exp_docs = ExperimentDocument.query.filter_by(experiment_id=experiment_id).all()

    # Build processed documents list with detailed processing operations
    processed_docs = []
    for exp_doc in exp_docs:
        doc = exp_doc.document

        # Get all processing operations for this document
        operations = ExperimentDocumentProcessing.query.filter_by(
            experiment_document_id=exp_doc.id
        ).all()

        # Count operations by type and status
        operation_types = {}
        for op in operations:
            if op.processing_type not in operation_types:
                operation_types[op.processing_type] = {
                    'total': 0,
                    'completed': 0,
                    'status': 'pending'
                }
            operation_types[op.processing_type]['total'] += 1
            if op.status == 'completed':
                operation_types[op.processing_type]['completed'] += 1
                operation_types[op.processing_type]['status'] = 'completed'

        # Calculate processing progress based on operation types
        total_operation_types = 5  # segmentation, entities, temporal, embeddings, etymology
        completed_operation_types = sum(1 for ot in operation_types.values() if ot['completed'] > 0)
        processing_progress = int((completed_operation_types / total_operation_types) * 100) if total_operation_types > 0 else 0

        # Determine overall status
        if completed_operation_types == total_operation_types:
            status = 'completed'
        elif completed_operation_types > 0:
            status = 'processing'
        else:
            status = 'pending'

        processed_docs.append({
            'id': doc.id,
            'exp_doc_id': exp_doc.id,
            'name': doc.original_filename or doc.title,
            'file_type': doc.file_type or doc.content_type,
            'word_count': doc.word_count or 0,
            'status': status,
            'processing_progress': processing_progress,
            'created_at': doc.created_at,
            'operation_types': operation_types,
            'total_operations': len(operations),
            'completed_operations': sum(1 for op in operations if op.status == 'completed')
        })

    # Calculate overall progress
    completed_count = sum(1 for doc in processed_docs if doc['status'] == 'completed')
    total_count = len(processed_docs)
    progress_percentage = (completed_count / total_count * 100) if total_count > 0 else 0

    return render_template('experiments/document_pipeline.html',
                         experiment=experiment,
                         documents=processed_docs,
                         total_count=total_count,
                         completed_count=completed_count,
                         progress_percentage=progress_percentage)


@experiments_bp.route('/<int:experiment_id>/process_document/<int:document_id>')
def process_document(experiment_id, document_id):
    """Process a specific document with experiment-specific context"""
    experiment = Experiment.query.filter_by(id=experiment_id).first_or_404()

    # Get the experiment-document association
    exp_doc = ExperimentDocument.query.filter_by(
        experiment_id=experiment_id,
        document_id=document_id
    ).first_or_404()

    document = exp_doc.document

    # Get processing operations for this experiment-document combination
    processing_operations = ExperimentDocumentProcessing.query.filter_by(
        experiment_document_id=exp_doc.id
    ).order_by(ExperimentDocumentProcessing.created_at.desc()).all()

    # Get all experiment documents for navigation
    all_exp_docs = ExperimentDocument.query.filter_by(experiment_id=experiment_id).all()
    all_doc_ids = [ed.document_id for ed in all_exp_docs]

    try:
        doc_index = all_doc_ids.index(document_id)
    except ValueError:
        flash('Document not found in this experiment', 'error')
        return redirect(url_for('experiments.document_pipeline', experiment_id=experiment_id))

    # Prepare navigation info
    has_previous = doc_index > 0
    has_next = doc_index < len(all_doc_ids) - 1
    previous_doc_id = all_doc_ids[doc_index - 1] if has_previous else None
    next_doc_id = all_doc_ids[doc_index + 1] if has_next else None

    # Calculate processing progress based on new model
    total_processing_types = 3  # embeddings, segmentation, entities
    completed_types = set()
    for op in processing_operations:
        if op.status == 'completed':
            completed_types.add(op.processing_type)

    processing_progress = int((len(completed_types) / total_processing_types) * 100)

    return render_template('experiments/process_document.html',
                         experiment=experiment,
                         document=document,
                         experiment_document=exp_doc,
                         processing_operations=processing_operations,
                         processing_progress=processing_progress,
                         doc_index=doc_index,
                         total_docs=len(all_doc_ids),
                         has_previous=has_previous,
                         has_next=has_next,
                         previous_doc_id=previous_doc_id,
                         next_doc_id=next_doc_id)


@experiments_bp.route('/<int:experiment_id>/document/<int:document_id>/apply_embeddings', methods=['POST'])
@api_require_login_for_write
def apply_embeddings_to_experiment_document(experiment_id, document_id):
    """Apply embeddings to a document for a specific experiment"""
    try:
        # Get the experiment-document association
        exp_doc = ExperimentDocument.query.filter_by(
            experiment_id=experiment_id, 
            document_id=document_id
        ).first_or_404()
        
        document = exp_doc.document
        
        if not document.content:
            return jsonify({'error': 'Document has no content to process'}), 400
        
        # Initialize embedding service
        try:
            from shared_services.embedding.embedding_service import EmbeddingService
            embedding_service = EmbeddingService()
        except ImportError:
            # Fallback to basic implementation if shared services not available
            return jsonify({'error': 'Embedding service not available'}), 500
        
        # Generate embeddings
        try:
            # Process document content in chunks if too long
            content = document.content
            max_length = 8000  # Conservative limit for most embedding models
            
            if len(content) > max_length:
                # Split into chunks and embed each
                chunks = [content[i:i+max_length] for i in range(0, len(content), max_length)]
                embeddings = []
                for chunk in chunks:
                    chunk_embedding = embedding_service.get_embedding(chunk)
                    embeddings.append(chunk_embedding)
                
                # Store metadata about chunked processing
                embedding_info = {
                    'type': 'chunked',
                    'chunks': len(chunks),
                    'chunk_size': max_length,
                    'model': embedding_service.get_model_name(),
                    'dimension': embedding_service.get_dimension(),
                    'experiment_id': experiment_id
                }
            else:
                # Single embedding for short documents
                embeddings = [embedding_service.get_embedding(content)]
                embedding_info = {
                    'type': 'single',
                    'model': embedding_service.get_model_name(),
                    'dimension': embedding_service.get_dimension(),
                    'experiment_id': experiment_id
                }
            
            # Mark embeddings as applied for this experiment
            exp_doc.mark_embeddings_applied(embedding_info)
            
            # Update word count if not set on original document
            if not document.word_count:
                document.word_count = len(content.split())
                document.updated_at = datetime.utcnow()
            
            db.session.commit()
            
            return jsonify({
                'success': True,
                'message': 'Embeddings applied successfully for this experiment',
                'embedding_info': embedding_info,
                'processing_progress': exp_doc.processing_progress
            })
            
        except Exception as e:
            current_app.logger.error(f"Error generating embeddings: {str(e)}")
            return jsonify({'error': f'Failed to generate embeddings: {str(e)}'}), 500
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error applying embeddings to experiment document: {str(e)}")
        return jsonify({'error': 'An error occurred while applying embeddings'}), 500


# New Experiment Processing API Endpoints

@experiments_bp.route('/api/experiment-processing/start', methods=['POST'])
@api_require_login_for_write
def start_experiment_processing():
    """Start a new processing operation for an experiment document"""
    try:
        data = request.get_json()

        experiment_document_id = data.get('experiment_document_id')
        processing_type = data.get('processing_type')
        processing_method = data.get('processing_method')

        if not all([experiment_document_id, processing_type, processing_method]):
            return jsonify({'error': 'Missing required parameters'}), 400

        # Get the experiment document
        exp_doc = ExperimentDocument.query.filter_by(id=experiment_document_id).first_or_404()

        # Check if processing already exists for this type and method
        existing_processing = ExperimentDocumentProcessing.query.filter_by(
            experiment_document_id=experiment_document_id,
            processing_type=processing_type,
            processing_method=processing_method
        ).first()

        if existing_processing and existing_processing.status == 'completed':
            return jsonify({'error': f'{processing_type} with {processing_method} method already completed'}), 400

        # Create new processing operation
        processing_op = ExperimentDocumentProcessing(
            experiment_document_id=experiment_document_id,
            processing_type=processing_type,
            processing_method=processing_method,
            status='pending'
        )

        # Set configuration
        config = {
            'method': processing_method,
            'created_by': current_user.id,
            'experiment_id': exp_doc.experiment_id,
            'document_id': exp_doc.document_id
        }
        processing_op.set_configuration(config)

        db.session.add(processing_op)
        db.session.flush()  # This assigns the ID to processing_op

        # Create index entry (now processing_op.id is available)
        index_entry = DocumentProcessingIndex(
            document_id=exp_doc.document_id,
            experiment_id=exp_doc.experiment_id,
            processing_id=processing_op.id,
            processing_type=processing_type,
            processing_method=processing_method,
            status='pending'
        )

        db.session.add(index_entry)
        db.session.commit()

        # Start processing (mark as running)
        processing_op.mark_started()
        index_entry.status = 'running'

        # Real processing using embedding service
        if processing_type == 'embeddings':
            try:
                from app.services.experiment_embedding_service import ExperimentEmbeddingService
                embedding_service = ExperimentEmbeddingService()

                # Check if method is available
                if not embedding_service.is_method_available(processing_method):
                    raise RuntimeError(f"Embedding method '{processing_method}' not available")

                # Use first 2000 characters for embedding (to avoid token limits)
                content = exp_doc.document.content or "No content available"
                text_to_embed = content[:2000]

                # Generate real embeddings
                embedding_result = embedding_service.generate_embeddings(text_to_embed, processing_method)

                # Create embedding artifact with real data
                artifact = ProcessingArtifact(
                    processing_id=processing_op.id,
                    document_id=exp_doc.document_id,
                    artifact_type='embedding_vector',
                    artifact_index=0
                )
                artifact.set_content({
                    'text': text_to_embed,
                    'vector': embedding_result['vector'],
                    'model': embedding_result['model']
                })
                artifact.set_metadata({
                    'dimensions': embedding_result['dimensions'],
                    'method': processing_method,
                    'chunk_size': len(text_to_embed),
                    'original_length': len(content),
                    'tokens_used': embedding_result.get('tokens_used', 'N/A')
                })
                db.session.add(artifact)

                # Mark processing as completed with real metrics
                processing_op.mark_completed({
                    'embedding_method': processing_method,
                    'dimensions': embedding_result['dimensions'],
                    'chunks_created': 1,
                    'total_tokens': len(content.split()),
                    'api_tokens_used': embedding_result.get('tokens_used', 'N/A'),
                    'text_processed_length': len(text_to_embed),
                    'model_used': embedding_result['model']
                })
                index_entry.status = 'completed'

            except Exception as e:
                # Mark processing as failed
                error_message = f"Embedding generation failed: {str(e)}"
                processing_op.mark_failed(error_message)
                index_entry.status = 'failed'
                current_app.logger.error(f"Embedding processing failed: {str(e)}")

                # Still commit to save the failed state
                db.session.commit()

                return jsonify({
                    'success': False,
                    'error': error_message,
                    'processing_id': str(processing_op.id)
                }), 400

        elif processing_type == 'segmentation':
            # Create segmentation artifacts using proper NLP libraries
            if exp_doc.document.content:
                import nltk
                from nltk.tokenize import sent_tokenize
                import spacy
                import re

                # Ensure NLTK data is available
                try:
                    nltk.data.find('tokenizers/punkt')
                except LookupError:
                    nltk.download('punkt_tab', quiet=True)

                content = exp_doc.document.content
                segments = []

                if processing_method == 'paragraph':
                    # Enhanced paragraph splitting using NLTK and improved patterns
                    # First normalize line endings and excessive whitespace
                    normalized_content = re.sub(r'\r\n|\r', '\n', content.strip())
                    normalized_content = re.sub(r'\n{3,}', '\n\n', normalized_content)  # Max 2 consecutive newlines

                    # Split by double newlines (traditional paragraph separator)
                    initial_paragraphs = re.split(r'\n\s*\n', normalized_content)

                    # Further process to handle edge cases
                    processed_paragraphs = []
                    for para in initial_paragraphs:
                        para = para.strip()
                        if not para:
                            continue

                        # Skip very short paragraphs that might be headers or fragments
                        if len(para) < 20:
                            continue

                        # Check if paragraph looks like a proper paragraph (has multiple sentences)
                        sentences_in_para = sent_tokenize(para)

                        # If paragraph has multiple sentences, keep as is
                        if len(sentences_in_para) > 1:
                            processed_paragraphs.append(para)
                        # If single sentence but long enough, keep it
                        elif len(para) > 100:
                            processed_paragraphs.append(para)
                        # Otherwise, it might be a list item or header - still include if substantial
                        elif len(para) > 50:
                            processed_paragraphs.append(para)

                    segments = processed_paragraphs

                elif processing_method == 'sentence':
                    # Use NLTK's punkt tokenizer for proper sentence segmentation
                    segments = sent_tokenize(content)
                    # Filter out very short segments that might be list items or fragments
                    segments = [s.strip() for s in segments if len(s.strip()) > 15]

                else:  # semantic or other methods
                    # Use spaCy for semantic chunking
                    nlp = spacy.load('en_core_web_sm')
                    doc = nlp(content)

                    # Group sentences into semantic chunks based on entity boundaries
                    current_chunk = []
                    chunks = []

                    for sent in doc.sents:
                        current_chunk.append(sent.text.strip())
                        # End chunk if we have 2-3 sentences or hit entity boundary
                        if len(current_chunk) >= 3 or (sent.ents and len(current_chunk) >= 2):
                            chunks.append(' '.join(current_chunk))
                            current_chunk = []

                    if current_chunk:
                        chunks.append(' '.join(current_chunk))

                    segments = [c for c in chunks if len(c.strip()) > 20]

                # Process all segments (remove arbitrary limit)
                total_segments = len(segments)

                for i, segment in enumerate(segments):
                    if segment.strip():
                        artifact = ProcessingArtifact(
                            processing_id=processing_op.id,
                            document_id=exp_doc.document_id,
                            artifact_type='text_segment',
                            artifact_index=i
                        )
                        artifact.set_content({
                            'text': segment.strip(),
                            'segment_type': processing_method,
                            'position': i
                        })
                        artifact.set_metadata({
                            'method': processing_method,
                            'length': len(segment),
                            'word_count': len(segment.split())
                        })
                        db.session.add(artifact)

            # Calculate real segmentation metrics
            if segments:
                avg_length = sum(len(seg) for seg in segments) // len(segments)
                total_words = sum(len(seg.split()) for seg in segments)
                avg_words = total_words // len(segments) if segments else 0
            else:
                avg_length = 0
                avg_words = 0

            # Determine the service/model used based on the method
            service_used = "Basic String Splitting"  # Default fallback
            model_info = ""

            if processing_method == 'paragraph':
                service_used = "NLTK-Enhanced Paragraph Detection"
                model_info = "Punkt tokenizer + smart filtering (min length, multi-sentence validation)"
            elif processing_method == 'sentence':
                service_used = "NLTK Punkt Tokenizer"
                model_info = "Pre-trained sentence boundary detection"
            else:  # semantic or other methods
                service_used = "spaCy NLP + NLTK"
                model_info = "en_core_web_sm + punkt tokenizer for entity-aware chunking"

            processing_op.mark_completed({
                'segmentation_method': processing_method,
                'segments_created': total_segments,
                'avg_segment_length': avg_length,
                'avg_words_per_segment': avg_words,
                'total_tokens': sum(len(seg.split()) for seg in segments),
                'service_used': service_used,
                'model_info': model_info
            })
            index_entry.status = 'completed'

        elif processing_type == 'entities':
            # Real entity extraction using spaCy and enhanced methods
            content = exp_doc.document.content
            extracted_entities = []

            if processing_method == 'spacy':
                # Enhanced spaCy entity extraction
                import spacy
                from collections import defaultdict

                nlp = spacy.load('en_core_web_sm')
                doc = nlp(content)

                # Extract standard spaCy entities
                entity_counts = defaultdict(int)
                seen_entities = set()

                for ent in doc.ents:
                    # Normalize entity text
                    entity_text = ent.text.strip()
                    entity_key = (entity_text.lower(), ent.label_)

                    # Skip very short entities (< 2 chars) and duplicates
                    if len(entity_text) < 2 or entity_key in seen_entities:
                        continue

                    seen_entities.add(entity_key)

                    # Get sentence context for the entity
                    sent_text = ent.sent.text.strip()

                    # Calculate start and end positions within the sentence
                    ent_start_in_sent = ent.start_char - ent.sent.start_char
                    ent_end_in_sent = ent.end_char - ent.sent.start_char

                    # Create context window around entity
                    context_start = max(0, ent_start_in_sent - 50)
                    context_end = min(len(sent_text), ent_end_in_sent + 50)
                    context = sent_text[context_start:context_end].strip()

                    extracted_entities.append({
                        'entity': entity_text,
                        'type': ent.label_,
                        'confidence': 0.85,  # spaCy doesn't provide confidence scores for NER
                        'context': context,
                        'start_char': ent.start_char,
                        'end_char': ent.end_char
                    })

                # Also extract noun phrases as potential entities
                for np in doc.noun_chunks:
                    np_text = np.text.strip()
                    np_key = np_text.lower()

                    # Skip if already found as named entity or too short/long
                    if (len(np_text) < 3 or len(np_text) > 100 or
                        any(np_key in seen_ent[0] for seen_ent in seen_entities)):
                        continue

                    # Only include noun phrases that look like proper concepts
                    if (any(token.pos_ in ['PROPN', 'NOUN'] for token in np) and
                        not all(token.is_stop for token in np)):

                        context_start = max(0, np.start_char - 50)
                        context_end = min(len(content), np.end_char + 50)
                        context = content[context_start:context_end].strip()

                        extracted_entities.append({
                            'entity': np_text,
                            'type': 'CONCEPT',
                            'confidence': 0.65,
                            'context': context,
                            'start_char': np.start_char,
                            'end_char': np.end_char
                        })

            elif processing_method == 'nltk':
                # NLTK-based entity extraction
                import nltk
                from nltk.tokenize import sent_tokenize, word_tokenize
                from nltk.tag import pos_tag
                from nltk.chunk import ne_chunk
                from nltk.tree import Tree

                # Ensure required NLTK data
                try:
                    nltk.data.find('tokenizers/punkt')
                except LookupError:
                    nltk.download('punkt_tab', quiet=True)
                try:
                    nltk.data.find('taggers/averaged_perceptron_tagger')
                except LookupError:
                    nltk.download('averaged_perceptron_tagger', quiet=True)
                try:
                    nltk.data.find('chunkers/maxent_ne_chunker')
                except LookupError:
                    nltk.download('maxent_ne_chunker', quiet=True)
                try:
                    nltk.data.find('corpora/words')
                except LookupError:
                    nltk.download('words', quiet=True)

                sentences = sent_tokenize(content)
                char_offset = 0

                for sent in sentences:
                    words = word_tokenize(sent)
                    pos_tags = pos_tag(words)
                    chunks = ne_chunk(pos_tags, binary=False)

                    word_offset = 0
                    for chunk in chunks:
                        if isinstance(chunk, Tree):
                            entity_words = [word for word, pos in chunk.leaves()]
                            entity_text = ' '.join(entity_words)
                            entity_type = chunk.label()

                            # Find character position
                            entity_start = sent.find(entity_text, word_offset)
                            if entity_start != -1:
                                # Create context
                                context_start = max(0, entity_start - 50)
                                context_end = min(len(sent), entity_start + len(entity_text) + 50)
                                context = sent[context_start:context_end].strip()

                                extracted_entities.append({
                                    'entity': entity_text,
                                    'type': entity_type,
                                    'confidence': 0.70,
                                    'context': context,
                                    'start_char': char_offset + entity_start,
                                    'end_char': char_offset + entity_start + len(entity_text)
                                })
                                word_offset = entity_start + len(entity_text)

                    char_offset += len(sent) + 1

            else:  # llm method - LangExtract + Gemini integration
                try:
                    from app.services.integrated_langextract import IntegratedLangExtractService

                    # Initialize LangExtract service
                    langextract_service = IntegratedLangExtractService()

                    if not langextract_service.service_ready:
                        raise Exception(f"LangExtract service not ready: {langextract_service.initialization_error}")

                    # Perform sophisticated entity extraction
                    analysis_result = langextract_service.analyze_document_for_entities(
                        text=content,
                        document_metadata={
                            'document_id': exp_doc.document_id,
                            'experiment_id': exp_doc.experiment_id,
                            'title': exp_doc.document.title
                        }
                    )

                    # Extract entities from LangExtract results
                    if 'entities' in analysis_result:
                        for entity_data in analysis_result['entities']:
                            extracted_entities.append({
                                'entity': entity_data.get('text', ''),
                                'type': entity_data.get('type', 'ENTITY'),
                                'confidence': entity_data.get('confidence', 0.85),
                                'context': entity_data.get('context', ''),
                                'start_char': entity_data.get('start_pos', 0),
                                'end_char': entity_data.get('end_pos', 0)
                            })

                    # Extract key concepts as entities too
                    if 'key_concepts' in analysis_result:
                        for concept in analysis_result['key_concepts']:
                            extracted_entities.append({
                                'entity': concept.get('term', ''),
                                'type': 'CONCEPT',
                                'confidence': concept.get('confidence', 0.80),
                                'context': concept.get('context', ''),
                                'start_char': concept.get('position', [0, 0])[0],
                                'end_char': concept.get('position', [0, 0])[1]
                            })

                except Exception as e:
                    logger.warning(f"LangExtract extraction failed, falling back to pattern-based: {e}")

                    # Fallback to improved pattern-based extraction
                    import re
                    patterns = [
                        r'\b[A-Z][a-z]+ [A-Z][a-z]+\b',  # Proper names
                        r'\b[A-Z]{2,}\b',  # Acronyms
                        r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\s+(?:Inc|Corp|LLC|Ltd|Company|University|Institute)\b',  # Organizations
                        r'\b(?:Dr|Prof|Mr|Ms|Mrs)\.?\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b',  # Titles + names
                    ]

                    for pattern in patterns:
                        matches = re.finditer(pattern, content)
                        for match in matches:
                            entity_text = match.group().strip()
                            start_pos = match.start()
                            end_pos = match.end()
                            context_start = max(0, start_pos - 50)
                            context_end = min(len(content), end_pos + 50)
                            context = content[context_start:context_end].strip()

                            extracted_entities.append({
                                'entity': entity_text,
                                'type': 'ENTITY',
                                'confidence': 0.60,
                                'context': context,
                                'start_char': start_pos,
                                'end_char': end_pos
                            })

            # Remove duplicates and create artifacts
            unique_entities = []
            seen_texts = set()

            for entity in extracted_entities:
                entity_key = entity['entity'].lower().strip()
                if entity_key not in seen_texts and len(entity_key) > 1:
                    seen_texts.add(entity_key)
                    unique_entities.append(entity)

            # Sort by confidence and position
            unique_entities.sort(key=lambda x: (-x['confidence'], x['start_char']))

            # Create artifacts for extracted entities
            for i, entity_data in enumerate(unique_entities):
                artifact = ProcessingArtifact(
                    processing_id=processing_op.id,
                    document_id=exp_doc.document_id,
                    artifact_type='extracted_entity',
                    artifact_index=i
                )
                artifact.set_content({
                    'entity': entity_data['entity'],
                    'entity_type': entity_data['type'],
                    'confidence': entity_data['confidence'],
                    'context': entity_data['context'],
                    'start_char': entity_data['start_char'],
                    'end_char': entity_data['end_char']
                })
                artifact.set_metadata({
                    'method': processing_method,
                    'extraction_confidence': entity_data['confidence'],
                    'character_position': f"{entity_data['start_char']}-{entity_data['end_char']}"
                })
                db.session.add(artifact)

            # Determine service and model info
            service_used = "Unknown"
            model_info = ""

            if processing_method == 'spacy':
                service_used = "spaCy NLP + Enhanced Extraction"
                model_info = "en_core_web_sm + noun phrase extraction"
            elif processing_method == 'nltk':
                service_used = "NLTK Named Entity Chunker"
                model_info = "maxent_ne_chunker + POS tagging"
            else:
                service_used = "LangExtract + Gemini Integration"
                model_info = "Google Gemini-1.5-flash with character-level positioning"

            # Extract unique entity types
            entity_types = list(set([e['type'] for e in unique_entities]))

            processing_op.mark_completed({
                'extraction_method': processing_method,
                'entities_found': len(unique_entities),
                'entity_types': entity_types,
                'service_used': service_used,
                'model_info': model_info,
                'avg_confidence': sum(e['confidence'] for e in unique_entities) / len(unique_entities) if unique_entities else 0
            })
            index_entry.status = 'completed'

        db.session.commit()

        return jsonify({
            'success': True,
            'message': f'{processing_type} processing started successfully',
            'processing_id': str(processing_op.id),
            'status': processing_op.status
        })

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error starting experiment processing: {str(e)}")
        return jsonify({'error': str(e)}), 500


@experiments_bp.route('/api/experiment-document/<int:exp_doc_id>/processing-status')
def get_experiment_document_processing_status(exp_doc_id):
    """Get processing status for an experiment document"""
    try:
        # Get the experiment document
        exp_doc = ExperimentDocument.query.filter_by(id=exp_doc_id).first_or_404()

        # Get all processing operations for this experiment document
        processing_operations = ExperimentDocumentProcessing.query.filter_by(
            experiment_document_id=exp_doc_id
        ).order_by(ExperimentDocumentProcessing.created_at.desc()).all()

        return jsonify({
            'success': True,
            'experiment_document_id': exp_doc_id,
            'processing_operations': [op.to_dict() for op in processing_operations]
        })

    except Exception as e:
        current_app.logger.error(f"Error getting processing status: {str(e)}")
        return jsonify({'error': str(e)}), 500


@experiments_bp.route('/api/processing/<uuid:processing_id>/artifacts')
def get_processing_artifacts(processing_id):
    """Get artifacts for a specific processing operation"""
    try:
        # Get the processing operation
        processing_op = ExperimentDocumentProcessing.query.filter_by(id=processing_id).first_or_404()

        # Get all artifacts for this processing operation
        artifacts = ProcessingArtifact.query.filter_by(
            processing_id=processing_id
        ).order_by(ProcessingArtifact.artifact_index, ProcessingArtifact.created_at).all()

        return jsonify({
            'success': True,
            'processing_id': str(processing_id),
            'processing_type': processing_op.processing_type,
            'processing_method': processing_op.processing_method,
            'artifacts': [artifact.to_dict() for artifact in artifacts]
        })

    except Exception as e:
        current_app.logger.error(f"Error getting processing artifacts: {str(e)}")
        return jsonify({'error': str(e)}), 500
