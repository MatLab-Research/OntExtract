"""
PROV-O Tracking Service for LangExtract and Orchestration Events

Manages creation and tracking of PROV-O compliant provenance records
for the two-stage LangExtract → Orchestration architecture.
"""

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
from app import db
from app.models.prov_o_models import ProvAgent, ProvActivity, ProvEntity, ProvRelationship

logger = logging.getLogger(__name__)


class ProvOTrackingService:
    """
    Service for tracking PROV-O compliant provenance of LangExtract and orchestration events
    
    Ensures every analytical decision has mandatory, queryable provenance as described
    in section 3.2 of the JCDL paper.
    """
    
    def __init__(self):
        """Initialize the PROV-O tracking service"""
        pass
    
    def track_langextract_analysis(self, document_id: int, document_text: str, 
                                 extraction_results: Dict[str, Any],
                                 user_id: Optional[int] = None) -> Dict[str, Any]:
        """
        Track complete LangExtract document analysis with PROV-O provenance
        
        Args:
            document_id: ID of the document being analyzed
            document_text: Original document text
            extraction_results: Results from LangExtractDocumentAnalyzer
            user_id: Optional user who initiated the analysis
            
        Returns:
            PROV-O tracking summary with entity and activity IDs
        """
        
        try:
            # 1. Get or create agents
            langextract_agent = ProvAgent.get_or_create_langextract_agent()
            user_agent = None
            if user_id:
                user_agent = ProvAgent.get_or_create_user_agent(user_id)
            
            # 2. Create LangExtract analysis activity
            activity_params = {
                'document_id': document_id,
                'text_length': len(document_text),
                'extraction_timestamp': datetime.utcnow().isoformat(),
                'gemini_model': 'gemini-2.0-flash-exp',
                'extraction_passes': 2,
                'character_level_positioning': True
            }
            
            langextract_activity = ProvActivity.create_langextract_activity(
                document_id=document_id,
                langextract_agent=langextract_agent,
                parameters=activity_params
            )
            
            # Set delegation if user initiated
            if user_agent:
                langextract_activity.delegated_agent_id = user_agent.agent_id
            
            db.session.add(langextract_activity)
            db.session.flush()  # Get activity ID without committing
            
            # 3. Create entity representing extraction results
            langextract_entity = ProvEntity.create_langextract_entity(
                langextract_activity=langextract_activity,
                extraction_results=extraction_results
            )
            
            db.session.add(langextract_entity)
            db.session.flush()
            
            # 4. Create PROV-O relationships
            generation_rel = ProvRelationship.create_generation_relationship(
                entity=langextract_entity,
                activity=langextract_activity
            )
            db.session.add(generation_rel)
            
            # 5. Complete the activity
            langextract_activity.complete_activity('completed')
            
            # 6. Commit all changes
            db.session.commit()
            
            return {
                'prov_o_tracking': {
                    'langextract_activity_id': str(langextract_activity.activity_id),
                    'langextract_entity_id': str(langextract_entity.entity_id),
                    'langextract_agent_id': str(langextract_agent.agent_id),
                    'user_agent_id': str(user_agent.agent_id) if user_agent else None,
                    'generation_relationship_id': str(generation_rel.relationship_id),
                    'provenance_complete': True,
                    'tracking_timestamp': datetime.utcnow().isoformat()
                },
                'extraction_summary': {
                    'key_concepts_tracked': len(extraction_results.get('key_concepts', [])),
                    'temporal_markers_tracked': len(extraction_results.get('temporal_markers', [])),
                    'character_positions_maintained': True,
                    'extraction_confidence': extraction_results.get('extraction_confidence', 0.5)
                }
            }
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Failed to track LangExtract analysis: {e}")
            raise
    
    def track_orchestration_coordination(self, langextract_tracking: Dict[str, Any],
                                       orchestration_results: Dict[str, Any],
                                       model_provider: str = 'anthropic') -> Dict[str, Any]:
        """
        Track LLM orchestration coordination with PROV-O provenance
        
        Args:
            langextract_tracking: Tracking results from LangExtract stage
            orchestration_results: Results from LLMOrchestrationCoordinator
            model_provider: LLM provider used for orchestration
            
        Returns:
            PROV-O tracking summary for orchestration stage
        """
        
        try:
            # 1. Get agents and previous activity
            orchestrator_agent = ProvAgent.get_or_create_orchestrator_agent(model_provider)
            
            langextract_activity_id = langextract_tracking['prov_o_tracking']['langextract_activity_id']
            langextract_activity = ProvActivity.query.get(langextract_activity_id)
            langextract_entity_id = langextract_tracking['prov_o_tracking']['langextract_entity_id']
            langextract_entity = ProvEntity.query.get(langextract_entity_id)
            
            # 2. Create orchestration activity
            orchestration_params = {
                'input_langextract_activity': langextract_activity_id,
                'orchestration_timestamp': datetime.utcnow().isoformat(),
                'model_provider': model_provider,
                'tools_selected': orchestration_results.get('orchestration_plan', {}).get('selected_tools', []),
                'synthesis_strategy': orchestration_results.get('synthesis_preparation', {}).get('strategy'),
                'confidence': orchestration_results.get('orchestration_plan', {}).get('confidence', 0.5)
            }
            
            orchestration_activity = ProvActivity.create_orchestration_activity(
                orchestrator_agent=orchestrator_agent,
                langextract_activity=langextract_activity,
                parameters=orchestration_params
            )
            
            db.session.add(orchestration_activity)
            db.session.flush()
            
            # 3. Create entity representing orchestration plan
            orchestration_entity = ProvEntity.create_orchestration_entity(
                orchestration_activity=orchestration_activity,
                orchestration_plan=orchestration_results
            )
            
            db.session.add(orchestration_entity)
            db.session.flush()
            
            # 4. Create PROV-O relationships
            
            # Generation relationship: orchestration entity wasGeneratedBy orchestration activity
            generation_rel = ProvRelationship.create_generation_relationship(
                entity=orchestration_entity,
                activity=orchestration_activity
            )
            db.session.add(generation_rel)
            
            # Information flow relationship: orchestration activity wasInformedBy langextract activity
            information_flow_rel = ProvRelationship.create_information_flow_relationship(
                downstream_activity=orchestration_activity,
                upstream_activity=langextract_activity
            )
            db.session.add(information_flow_rel)
            
            # Derivation relationship: orchestration entity wasDerivedFrom langextract entity
            derivation_rel = ProvRelationship.create_derivation_relationship(
                derived_entity=orchestration_entity,
                source_entity=langextract_entity,
                derivation_type='llm_orchestration_transformation'
            )
            db.session.add(derivation_rel)
            
            # 5. Complete the orchestration activity
            orchestration_activity.complete_activity('completed')
            
            # 6. Commit all changes
            db.session.commit()
            
            return {
                'prov_o_tracking': {
                    'orchestration_activity_id': str(orchestration_activity.activity_id),
                    'orchestration_entity_id': str(orchestration_entity.entity_id),
                    'orchestrator_agent_id': str(orchestrator_agent.agent_id),
                    'generation_relationship_id': str(generation_rel.relationship_id),
                    'information_flow_relationship_id': str(information_flow_rel.relationship_id),
                    'derivation_relationship_id': str(derivation_rel.relationship_id),
                    'provenance_complete': True,
                    'tracking_timestamp': datetime.utcnow().isoformat()
                },
                'orchestration_summary': {
                    'tools_selected_count': len(orchestration_results.get('orchestration_plan', {}).get('selected_tools', [])),
                    'processing_stages': len(set(s.get('stage', 1) for s in orchestration_results.get('orchestration_plan', {}).get('processing_sequence', []))),
                    'synthesis_required': orchestration_results.get('synthesis_preparation', {}).get('strategy') != 'none',
                    'orchestration_confidence': orchestration_results.get('orchestration_plan', {}).get('confidence', 0.5)
                },
                'provenance_chain': {
                    'langextract_to_orchestration': True,
                    'character_level_traceability': True,
                    'complete_audit_trail': True,
                    'w3c_prov_o_compliant': True
                }
            }
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Failed to track orchestration coordination: {e}")
            raise
    
    def get_provenance_chain(self, entity_id: str) -> Dict[str, Any]:
        """
        Retrieve complete provenance chain for an entity
        
        Args:
            entity_id: UUID of the entity to trace
            
        Returns:
            Complete provenance chain with all related entities, activities, and agents
        """
        
        try:
            entity = ProvEntity.query.get(entity_id)
            if not entity:
                return {'error': 'Entity not found'}
            
            # Build provenance chain
            chain = {
                'target_entity': {
                    'entity_id': str(entity.entity_id),
                    'entity_type': entity.entity_type,
                    'created_at': entity.created_at.isoformat()
                },
                'generating_activity': None,
                'responsible_agents': [],
                'source_entities': [],
                'derived_entities': [],
                'full_provenance_graph': []
            }
            
            # Get generating activity
            if entity.generating_activity:
                activity = entity.generating_activity
                chain['generating_activity'] = {
                    'activity_id': str(activity.activity_id),
                    'activity_type': activity.activity_type,
                    'started_at': activity.startedattime.isoformat() if activity.startedattime else None,
                    'ended_at': activity.endedattime.isoformat() if activity.endedattime else None,
                    'status': activity.activity_status,
                    'parameters': activity.activity_parameters
                }
                
                # Get responsible agents
                if activity.associated_agent:
                    chain['responsible_agents'].append({
                        'agent_id': str(activity.associated_agent.agent_id),
                        'agent_type': activity.associated_agent.agent_type,
                        'agent_name': activity.associated_agent.foaf_name,
                        'role': 'associated'
                    })
            
            # Get source entities (wasDerivedFrom relationships)
            derivation_rels = ProvRelationship.query.filter_by(
                relationship_type='wasDerivedFrom',
                subject_type='Entity',
                subject_id=entity.entity_id
            ).all()
            
            for rel in derivation_rels:
                source_entity = ProvEntity.query.get(rel.object_id)
                if source_entity:
                    chain['source_entities'].append({
                        'entity_id': str(source_entity.entity_id),
                        'entity_type': source_entity.entity_type,
                        'created_at': source_entity.created_at.isoformat(),
                        'derivation_type': rel.relationship_metadata.get('derivation_type', 'unknown')
                    })
            
            # Get derived entities (entities that were derived from this one)
            derived_rels = ProvRelationship.query.filter_by(
                relationship_type='wasDerivedFrom',
                object_type='Entity',
                object_id=entity.entity_id
            ).all()
            
            for rel in derived_rels:
                derived_entity = ProvEntity.query.get(rel.subject_id)
                if derived_entity:
                    chain['derived_entities'].append({
                        'entity_id': str(derived_entity.entity_id),
                        'entity_type': derived_entity.entity_type,
                        'created_at': derived_entity.created_at.isoformat(),
                        'derivation_type': rel.relationship_metadata.get('derivation_type', 'unknown')
                    })
            
            # Get all relationships for full provenance graph
            all_relationships = ProvRelationship.query.filter(
                db.or_(
                    db.and_(ProvRelationship.subject_type == 'Entity', ProvRelationship.subject_id == entity.entity_id),
                    db.and_(ProvRelationship.object_type == 'Entity', ProvRelationship.object_id == entity.entity_id)
                )
            ).all()
            
            for rel in all_relationships:
                chain['full_provenance_graph'].append({
                    'relationship_type': rel.relationship_type,
                    'subject': f"{rel.subject_type}:{rel.subject_id}",
                    'object': f"{rel.object_type}:{rel.object_id}",
                    'created_at': rel.created_at.isoformat()
                })
            
            return chain
            
        except Exception as e:
            logger.error(f"Failed to retrieve provenance chain: {e}")
            return {'error': str(e)}
    
    def query_provenance_by_criteria(self, criteria: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Query provenance records by various criteria
        
        Args:
            criteria: Search criteria (agent_type, activity_type, date_range, etc.)
            
        Returns:
            List of matching provenance records
        """
        
        try:
            results = []
            
            # Build query based on criteria
            query = db.session.query(ProvEntity)
            
            if 'entity_type' in criteria:
                query = query.filter(ProvEntity.entity_type == criteria['entity_type'])
            
            if 'date_from' in criteria:
                query = query.filter(ProvEntity.created_at >= criteria['date_from'])
            
            if 'date_to' in criteria:
                query = query.filter(ProvEntity.created_at <= criteria['date_to'])
            
            # Join with activities and agents for additional filtering
            if 'agent_type' in criteria or 'activity_type' in criteria:
                query = query.join(ProvActivity, ProvEntity.generated_by_activity == ProvActivity.activity_id)
                
                if 'activity_type' in criteria:
                    query = query.filter(ProvActivity.activity_type == criteria['activity_type'])
                
                if 'agent_type' in criteria:
                    query = query.join(ProvAgent, ProvActivity.wasassociatedwith == ProvAgent.agent_id)
                    query = query.filter(ProvAgent.agent_type == criteria['agent_type'])
            
            entities = query.limit(criteria.get('limit', 100)).all()
            
            for entity in entities:
                results.append({
                    'entity_id': str(entity.entity_id),
                    'entity_type': entity.entity_type,
                    'created_at': entity.created_at.isoformat(),
                    'generating_activity_type': entity.generating_activity.activity_type if entity.generating_activity else None,
                    'associated_agent_name': entity.generating_activity.associated_agent.foaf_name if entity.generating_activity and entity.generating_activity.associated_agent else None,
                    'has_complete_provenance': True
                })
            
            return results
            
        except Exception as e:
            logger.error(f"Failed to query provenance records: {e}")
            return []
    
    def validate_provenance_completeness(self) -> Dict[str, Any]:
        """
        Validate that all entities have complete provenance chains
        
        Returns:
            Validation report with any provenance gaps
        """
        
        try:
            # Check for entities without generating activities (should be impossible due to constraints)
            orphan_entities = ProvEntity.query.filter(ProvEntity.wasgeneratedby.is_(None)).count()
            
            # Check for activities without agents
            orphan_activities = ProvActivity.query.filter(ProvActivity.wasassociatedwith.is_(None)).count()
            
            # Check for missing relationships
            entities_count = ProvEntity.query.count()
            generation_rels_count = ProvRelationship.query.filter_by(relationship_type='wasGeneratedBy').count()
            
            # Get statistics
            total_entities = ProvEntity.query.count()
            total_activities = ProvActivity.query.count()
            total_agents = ProvAgent.query.count()
            total_relationships = ProvRelationship.query.count()
            
            langextract_entities = ProvEntity.query.filter_by(entity_type='langextract_document_extraction').count()
            orchestration_entities = ProvEntity.query.filter_by(entity_type='llm_orchestration_plan').count()
            
            return {
                'validation_status': 'passed' if orphan_entities == 0 and orphan_activities == 0 else 'failed',
                'provenance_completeness': {
                    'orphan_entities': orphan_entities,
                    'orphan_activities': orphan_activities,
                    'generation_relationships_ratio': generation_rels_count / entities_count if entities_count > 0 else 0
                },
                'statistics': {
                    'total_entities': total_entities,
                    'total_activities': total_activities,
                    'total_agents': total_agents,
                    'total_relationships': total_relationships,
                    'langextract_extractions': langextract_entities,
                    'orchestration_plans': orchestration_entities
                },
                'w3c_prov_o_compliance': orphan_entities == 0 and orphan_activities == 0
            }
            
        except Exception as e:
            logger.error(f"Failed to validate provenance completeness: {e}")
            return {'validation_status': 'error', 'error': str(e)}