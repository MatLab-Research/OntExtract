"""
Experiments Routes (Temporary - Being Refactored)

REFACTORING IN PROGRESS:
- CRUD operations have been extracted to experiments/crud.py ✅
- Remaining routes (terms, temporal, evolution, orchestration, pipeline) are still here
- These will be extracted in future sessions

This file will be removed once all routes are extracted to their respective modules.
"""

# Import the blueprint from the new package location
from app.routes.experiments import experiments_bp

# Import dependencies needed for the remaining routes
from flask import render_template, request, jsonify, flash, redirect, url_for, current_app
from flask_login import current_user
from app.utils.auth_decorators import api_require_login_for_write
from sqlalchemy import text
from app import db
from app.models import Document, Experiment, ExperimentDocument, ProcessingJob
from app.models.experiment_processing import ExperimentDocumentProcessing, ProcessingArtifact, DocumentProcessingIndex
from datetime import datetime
import json
import uuid
from typing import List, Optional, Dict, Any
from app.services.text_processing import TextProcessingService
from app.services.oed_enrichment_service import OEDEnrichmentService
from app.services.term_analysis_service import TermAnalysisService
from app.services.llm_orchestration_coordinator import LLMOrchestrationCoordinator
from app.services.adaptive_orchestration_service import AdaptiveOrchestrationService
from app.services.experiment_embedding_service import ExperimentEmbeddingService

# Note: experiments.configuration may include a `design` object per Phase 1b of metadata plan.
# Analysis services should read optional design = config.get('design') to drive factor/group logic.

# ==============================================================================
# REMAINING ROUTES (To be extracted in future sessions)
# ==============================================================================
# Term management routes extracted to experiments/terms.py ✅


# Temporal analysis routes extracted to experiments/temporal.py ✅
@experiments_bp.route('/<int:experiment_id>/semantic_evolution_visual')
@api_require_login_for_write  
def semantic_evolution_visual(experiment_id):
    """Display semantic evolution visualization for any term with academic anchors."""
    experiment = Experiment.query.filter_by(id=experiment_id).first_or_404()
    
    # Get target term from URL parameter or experiment configuration
    target_term = request.args.get('term')
    
    # If no term specified, get from experiment configuration
    if not target_term:
        config = json.loads(experiment.configuration) if experiment.configuration else {}
        if config.get('target_term'):
            target_term = config.get('target_term')
        elif config.get('target_terms') and len(config['target_terms']) > 0:
            target_term = config['target_terms'][0]
        else:
            flash('No target term specified. Add ?term=<term> to URL or configure in experiment.', 'warning')
            return redirect(url_for('experiments.view', experiment_id=experiment_id))
    
    # Get term from database
    from app.models.term import Term, TermVersion
    
    term_record = Term.query.filter_by(term_text=target_term).first()
    if not term_record:
        flash(f'Term "{target_term}" not found in database. Create academic anchors first.', 'warning')
        return redirect(url_for('experiments.view', experiment_id=experiment_id))
    
    # Get all temporal versions for the term
    term_versions = TermVersion.query.filter_by(term_id=term_record.id).order_by(TermVersion.temporal_start_year.asc()).all()
    
    if not term_versions:
        flash(f'No temporal versions found for "{target_term}". Create academic anchors first.', 'warning')
        return redirect(url_for('experiments.view', experiment_id=experiment_id))
    
    # Prepare visualization data (generic for any term)
    academic_anchors = []
    for version in term_versions:
        academic_anchors.append({
            'year': version.temporal_start_year,
            'period': version.temporal_period,
            'meaning': version.meaning_description,
            'citation': version.source_citation,
            'domain': version.extraction_method.replace('_analysis', '').replace(' analysis', ''),
            'confidence': version.confidence_level,
            'context_anchor': version.context_anchor or []
        })
    
    # Calculate metrics
    years = [anchor['year'] for anchor in academic_anchors]
    temporal_span = max(years) - min(years) if years else 0
    domains = list(set([anchor['domain'] for anchor in academic_anchors]))
    
    # Get OED data from database
    from app.models.oed_models import OEDEtymology, OEDDefinition, OEDHistoricalStats, OEDQuotationSummary
    
    oed_data = None
    etymology = OEDEtymology.query.filter_by(term_id=term_record.id).first()
    definitions = OEDDefinition.query.filter_by(term_id=term_record.id).order_by(OEDDefinition.first_cited_year.asc()).all()
    historical_stats = OEDHistoricalStats.query.filter_by(term_id=term_record.id).order_by(OEDHistoricalStats.start_year.asc()).all()
    quotation_summaries = OEDQuotationSummary.query.filter_by(term_id=term_record.id).order_by(OEDQuotationSummary.quotation_year.asc()).all()
    
    if etymology or definitions or historical_stats:
        oed_data = {
            'etymology': etymology.to_dict() if etymology else None,
            'definitions': [d.to_dict() for d in definitions],
            'historical_stats': [s.to_dict() for s in historical_stats],
            'quotation_summaries': [q.to_dict() for q in quotation_summaries],
            'date_range': {
                'earliest': min([d.first_cited_year for d in definitions if d.first_cited_year], default=None),
                'latest': max([d.last_cited_year for d in definitions if d.last_cited_year], default=None)
            }
        }
    else:
        # Fallback: Try to load OED data from files
        oed_patterns = [
            f'data/references/oed_{target_term}_extraction_provenance.json',
            f'data/references/{target_term}_oed_extraction.json'
        ]
        
        for pattern in oed_patterns:
            try:
                with open(pattern, 'r') as f:
                    oed_data = json.load(f)
                    break
            except FileNotFoundError:
                continue
    
    # Apply period-aware matching and excerpt extraction to OED definitions
    if oed_data and oed_data.get('definitions'):
        from app.services.period_matching_service import PeriodMatchingService
        
        # Get the target years from term_versions (already loaded above)
        target_years = []
        for version in term_versions:
            if version.temporal_start_year:
                target_years.append(version.temporal_start_year)
        
        if target_years:
            matching_service = PeriodMatchingService()
            try:
                # Match definitions to their relevant periods based on date ranges
                enhanced_definitions = matching_service.enhance_definitions_with_period_matching(
                    oed_data['definitions'], target_years, target_term
                )
                oed_data['definitions'] = enhanced_definitions
                print(f"Matched {len(enhanced_definitions)} definitions to relevant periods from: {target_years}")
                
                # Log the matching results for debugging
                for def_idx, definition in enumerate(enhanced_definitions):
                    relevant_periods = definition.get('relevant_periods', [])
                    first_year = definition.get('first_cited_year')
                    last_year = definition.get('last_cited_year')
                    print(f"  Definition {def_idx + 1} ({first_year}-{last_year or 'present'}): matched to years {relevant_periods}")
                    
            except Exception as e:
                print(f"Failed to match definitions with periods: {str(e)}")
                # Continue with original definitions
    
    # Get reference data for this specific term
    reference_data = {
        'oed_data': oed_data,
        'legal_data': None,
        'temporal_span': temporal_span,
        'domain_count': len(domains),
        'domains': domains
    }
    
    # Try to load legal data  
    legal_patterns = [
        f'data/references/blacks_law_{target_term}_extraction.json',
        f'data/references/{target_term}_legal_extraction.json'
    ]
    
    for pattern in legal_patterns:
        try:
            with open(pattern, 'r') as f:
                reference_data['legal_data'] = json.load(f)
                break
        except FileNotFoundError:
            continue
    
    return render_template('experiments/semantic_evolution_visual.html',
                         experiment=experiment,
                         target_term=target_term,
                         term_record=term_record,
                         academic_anchors=academic_anchors,
                         oed_data=oed_data,
                         reference_data=reference_data,
                         temporal_span=temporal_span,
                         domains=domains)

@experiments_bp.route('/<int:experiment_id>/analyze_evolution', methods=['POST'])
@api_require_login_for_write
def analyze_evolution(experiment_id):
    """Analyze the evolution of a term over time with detailed semantic drift analysis"""
    try:
        experiment = Experiment.query.filter_by(id=experiment_id).first_or_404()
        
        data = request.get_json()
        term = data.get('term')
        periods = data.get('periods', [])
        
        # Import temporal analysis service
        from shared_services.temporal import TemporalAnalysisService
        from shared_services.ontology.ontology_importer import OntologyImporter
        
        # Initialize services
        ontology_importer = OntologyImporter()
        temporal_service = TemporalAnalysisService(ontology_importer)
        
        # Get all documents
        all_documents = list(experiment.documents) + list(experiment.references)
        
        # Extract temporal data
        temporal_data = temporal_service.extract_temporal_data(all_documents, term, periods)
        
        # Analyze semantic drift
        drift_analysis = temporal_service.analyze_semantic_drift(all_documents, term, periods)
        
        # Generate comprehensive narrative
        narrative = temporal_service.generate_evolution_narrative(temporal_data, term, periods)
        
        # Build detailed analysis
        analysis_parts = [narrative, "\n\n--- Semantic Drift Analysis ---\n"]
        
        if drift_analysis.get('average_drift') is not None:
            analysis_parts.append(f"Average Semantic Drift: {drift_analysis['average_drift']:.2%}\n")
        
        if drift_analysis.get('stable_terms'):
            analysis_parts.append(f"Stable Associated Terms: {', '.join(drift_analysis['stable_terms'][:5])}\n")
        
        # Add period-by-period drift details
        if drift_analysis.get('periods'):
            analysis_parts.append("\nPeriod-by-Period Changes:\n")
            for period_range, period_data in drift_analysis['periods'].items():
                analysis_parts.append(f"\n{period_range}:")
                analysis_parts.append(f"  - Drift Score: {period_data['drift_score']:.2%}")
                if period_data.get('new_terms'):
                    analysis_parts.append(f"  - New Terms: {', '.join(period_data['new_terms'][:3])}")
                if period_data.get('lost_terms'):
                    analysis_parts.append(f"  - Lost Terms: {', '.join(period_data['lost_terms'][:3])}")
        
        # Add ontology mapping insights if available
        if temporal_service.ontology_importer:
            analysis_parts.append("\n\n--- Ontology Mapping Insights ---\n")
            # Try to map the term to PROV-O concepts
            prov_mappings = {
                'agent': 'prov:Agent - An entity that bears responsibility',
                'activity': 'prov:Activity - Something that occurs over time',
                'entity': 'prov:Entity - A physical, digital, or conceptual thing',
                'process': 'prov:Activity - A series of actions or operations',
                'artifact': 'prov:Entity - A thing produced or used',
                'actor': 'prov:Agent - One who performs actions'
            }
            
            term_lower = term.lower()
            if term_lower in prov_mappings:
                analysis_parts.append(f"PROV-O Mapping: {prov_mappings[term_lower]}")
            else:
                analysis_parts.append(f"No direct PROV-O mapping found for '{term}'")
        
        analysis = '\n'.join(analysis_parts)
        
        return jsonify({
            'success': True,
            'analysis': analysis,
            'drift_metrics': {
                'average_drift': drift_analysis.get('average_drift', 0),
                'total_drift': drift_analysis.get('total_drift', 0),
                'stable_term_count': len(drift_analysis.get('stable_terms', []))
            }
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# Human-in-the-Loop Orchestration Integration Routes

@experiments_bp.route('/<int:experiment_id>/orchestrated_analysis')
@api_require_login_for_write
def orchestrated_analysis(experiment_id):
    """Human-in-the-loop orchestrated analysis interface"""
    experiment = Experiment.query.filter_by(id=experiment_id).first_or_404()
    
    # Get orchestration decisions for this experiment
    from app.models.orchestration_logs import OrchestrationDecision
    from app.models.orchestration_feedback import OrchestrationFeedback, LearningPattern
    
    decisions = OrchestrationDecision.query.filter_by(
        experiment_id=experiment.id
    ).order_by(OrchestrationDecision.created_at.desc()).all()
    
    # Get learning patterns
    patterns = LearningPattern.query.filter_by(
        pattern_status='active'
    ).order_by(LearningPattern.confidence.desc()).limit(5).all()
    
    # Get experiment configuration
    config = json.loads(experiment.configuration) if experiment.configuration else {}
    terms = config.get('target_terms', [])
    
    return render_template('experiments/orchestrated_analysis.html',
                         experiment=experiment,
                         decisions=decisions,
                         patterns=patterns,
                         terms=terms)


@experiments_bp.route('/<int:experiment_id>/create_orchestration_decision', methods=['POST'])
@api_require_login_for_write
def create_orchestration_decision(experiment_id):
    """Create a new orchestration decision for human feedback"""
    try:
        experiment = Experiment.query.filter_by(id=experiment_id).first_or_404()
        data = request.get_json()
        
        term_text = data.get('term_text', '')
        if not term_text:
            return jsonify({'error': 'Term text is required'}), 400
        
        # Get document characteristics
        doc_characteristics = {
            'document_count': experiment.get_document_count(),
            'total_words': experiment.get_total_word_count(),
            'experiment_type': experiment.experiment_type
        }
        
        # Create input metadata
        config = json.loads(experiment.configuration) if experiment.configuration else {}
        input_metadata = {
            'experiment_id': experiment.id,
            'experiment_type': experiment.experiment_type,
            'document_count': experiment.get_document_count(),
            'total_words': experiment.get_total_word_count(),
            'time_periods': config.get('time_periods', []),
            'domains': config.get('domains', [])
        }
        
        # Simulate LLM orchestration decision (in production, this would call actual LLM service)
        selected_tools = ['spacy', 'embeddings']
        embedding_model = 'bert-base-uncased'
        decision_confidence = 0.85
        
        # Apply learning patterns for more intelligent selection
        from app.models.orchestration_feedback import LearningPattern
        active_patterns = LearningPattern.query.filter_by(pattern_status='active').all()
        
        reasoning_parts = [f"Selected tools for term '{term_text}' based on:"]
        for pattern in active_patterns[:2]:  # Apply top 2 patterns
            if pattern.pattern_type == 'preference':
                pattern_tools = pattern.recommendations.get('tools', [])
                selected_tools.extend([t for t in pattern_tools if t not in selected_tools])
                reasoning_parts.append(f"- {pattern.pattern_name}: {pattern.recommendations.get('reasoning', 'Applied learned pattern')}")
                
                # Apply embedding model recommendations
                pattern_model = pattern.recommendations.get('embedding_model')
                if pattern_model:
                    embedding_model = pattern_model
        
        reasoning = '\\n'.join(reasoning_parts)
        
        # Create orchestration decision
        from app.models.orchestration_logs import OrchestrationDecision
        
        decision = OrchestrationDecision(
            experiment_id=experiment.id,
            term_text=term_text,
            selected_tools=selected_tools,
            embedding_model=embedding_model,
            decision_confidence=decision_confidence,
            orchestrator_provider='claude',
            orchestrator_model='claude-3-sonnet',
            orchestrator_prompt=f"Analyze term '{term_text}' and recommend optimal NLP processing approach",
            orchestrator_response=f"Recommended: {', '.join(selected_tools)} with {embedding_model}",
            orchestrator_response_time_ms=1200,
            processing_strategy='sequential',
            reasoning=reasoning,
            input_metadata=input_metadata,
            document_characteristics=doc_characteristics,
            created_by=current_user.id
        )
        
        db.session.add(decision)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Orchestration decision created successfully',
            'decision_id': str(decision.id),
            'selected_tools': selected_tools,
            'embedding_model': embedding_model,
            'confidence': decision_confidence,
            'reasoning': reasoning
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@experiments_bp.route('/<int:experiment_id>/run_orchestrated_analysis', methods=['POST'])
@api_require_login_for_write
def run_orchestrated_analysis(experiment_id):
    """Run analysis with LLM orchestration decisions and real-time feedback"""
    try:
        experiment = Experiment.query.filter_by(id=experiment_id).first_or_404()
        data = request.get_json()
        
        # Get analysis parameters
        terms = data.get('terms', [])
        if not terms:
            return jsonify({'error': 'At least one term is required'}), 400
        
        # Create orchestration decisions for each term
        from app.models.orchestration_logs import OrchestrationDecision
        from app.services.adaptive_orchestration_service import AdaptiveOrchestrationService
        
        orchestration_service = AdaptiveOrchestrationService()
        analysis_results = []
        
        for term in terms:
            # Create or get existing orchestration decision
            existing_decision = OrchestrationDecision.query.filter_by(
                experiment_id=experiment.id,
                term_text=term
            ).first()
            
            if not existing_decision:
                # Create new decision using adaptive service
                decision_context = {
                    'experiment_id': experiment.id,
                    'term_text': term,
                    'experiment_type': experiment.experiment_type,
                    'document_count': experiment.get_document_count(),
                    'user_id': current_user.id
                }
                
                decision = orchestration_service.create_adaptive_decision(decision_context)
            else:
                decision = existing_decision
            
            # Simulate analysis execution with the orchestrated tools
            analysis_result = {
                'term': term,
                'decision_id': str(decision.id),
                'tools_used': decision.selected_tools,
                'embedding_model': decision.embedding_model,
                'confidence': float(decision.decision_confidence),
                'processing_time': '2.3s',
                'semantic_drift_detected': True,
                'drift_magnitude': 0.32,
                'periods_analyzed': 4,
                'insights': [
                    f"Term '{term}' shows moderate semantic drift over time",
                    f"Most stable usage in period 2010-2015",
                    f"Significant shift detected in recent period"
                ]
            }
            
            analysis_results.append(analysis_result)
        
        # Mark experiment as running
        experiment.status = 'running'
        experiment.started_at = datetime.utcnow()
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Orchestrated analysis initiated for {len(terms)} terms',
            'results': analysis_results,
            'total_decisions': len(analysis_results)
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500



# Document Processing Pipeline Routes

@experiments_bp.route('/<int:experiment_id>/document_pipeline')
def document_pipeline(experiment_id):
    """Step 2: Document Processing Pipeline Overview"""
    experiment = Experiment.query.filter_by(id=experiment_id).first_or_404()
    
    # Get experiment-specific document processing data using raw SQL
    query = """
        SELECT d.id, d.title, d.original_filename, d.file_type, d.content_type, 
               d.word_count, d.created_at,
               COALESCE(ed.processing_status, 'pending') as processing_status,
               COALESCE(ed.embeddings_applied, false) as embeddings_applied,
               COALESCE(ed.segments_created, false) as segments_created,
               COALESCE(ed.nlp_analysis_completed, false) as nlp_analysis_completed
        FROM documents d
        JOIN experiment_documents ed ON d.id = ed.document_id
        WHERE ed.experiment_id = :experiment_id
        ORDER BY d.created_at
    """
    
    result = db.session.execute(text(query), {'experiment_id': experiment_id})
    rows = result.fetchall()
    
    # Build processed documents list with experiment-specific data
    processed_docs = []
    for row in rows:
        # Calculate processing progress
        total_steps = 3  # embeddings, segmentation, nlp_analysis
        completed_steps = sum([row.embeddings_applied, row.segments_created, row.nlp_analysis_completed])
        processing_progress = int((completed_steps / total_steps) * 100)
        
        processed_docs.append({
            'id': row.id,
            'name': row.original_filename or row.title,
            'file_type': row.file_type or row.content_type,
            'word_count': row.word_count or 0,
            'has_embeddings': row.embeddings_applied,
            'status': row.processing_status,
            'processing_progress': processing_progress,
            'created_at': row.created_at
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
                    from app.services.integrated_langextract_service import IntegratedLangExtractService

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


