"""Read-side timeline, lineage, and graph provenance queries."""

import uuid
from typing import Any, Dict, List

from app import db
from app.models.prov_o_models import (
    ProvActivity,
    ProvAgent,
    ProvEntity,
    ProvRelationship,
)


class ProvenanceQueryMixin:
    @staticmethod
    def get_timeline(
        experiment_id: int = None,
        user_id: int = None,
        activity_type: str = None,
        term_id: str = None,
        document_id: int = None,
        document_ids: List[int] = None,
        limit: int = 100,
        include_invalidated: bool = None
    ) -> List[Dict[str, Any]]:
        """
        Get chronological timeline of activities with entities and agents.

        Args:
            experiment_id: Filter by experiment (optional)
            user_id: Filter by user (optional)
            activity_type: Filter by activity type (optional)
            term_id: Filter by term UUID (optional)
            document_id: Filter by single document (optional, deprecated - use document_ids)
            document_ids: Filter by multiple documents (optional) - for showing all versions
            limit: Maximum number of activities to return
            include_invalidated: Include invalidated (deleted) entities. If None, uses system setting.

        Returns:
            List of timeline entries with full PROV-O context
        """
        # Determine whether to include invalidated entities
        if include_invalidated is None:
            from app.models.app_settings import AppSetting
            include_invalidated = AppSetting.get_setting('show_deleted_in_timeline', default=False)
        query = db.session.query(ProvActivity)\
            .order_by(ProvActivity.startedattime.desc())

        # Apply filters
        if activity_type:
            query = query.filter(ProvActivity.activity_type == activity_type)

        if experiment_id:
            query = query.filter(
                ProvActivity.activity_parameters['experiment_id'].astext == str(experiment_id)
            )

        if term_id:
            # Find activities directly associated with this term
            # AND activities that generated the source entities the term is derived from
            from uuid import UUID
            term_uuid = UUID(term_id) if isinstance(term_id, str) else term_id

            # Get the term entity to find its derivation chain
            term_entity = ProvEntity.query.filter_by(entity_type='term').filter(
                ProvEntity.entity_value['term_id'].astext == str(term_id)
            ).first()

            # Collect all activity IDs that should be included
            related_activity_ids = set()

            # Include activities that generated source entities the term is derived from
            if term_entity and term_entity.wasderivedfrom:
                source_entity = ProvEntity.query.get(term_entity.wasderivedfrom)
                if source_entity and source_entity.wasgeneratedby:
                    related_activity_ids.add(source_entity.wasgeneratedby)

            # Build the filter: term_id in parameters OR activity_id in related activities
            if related_activity_ids:
                query = query.filter(
                    db.or_(
                        ProvActivity.activity_parameters['term_id'].astext == str(term_id),
                        ProvActivity.activity_id.in_(related_activity_ids)
                    )
                )
            else:
                query = query.filter(
                    ProvActivity.activity_parameters['term_id'].astext == str(term_id)
                )

        # Handle document filtering - support both single ID and list of IDs
        if document_ids:
            # Filter for any document in the list (for document family/versions)
            query = query.filter(
                db.or_(*[
                    ProvActivity.activity_parameters['document_id'].astext == str(doc_id)
                    for doc_id in document_ids
                ])
            )
        elif document_id:
            query = query.filter(
                ProvActivity.activity_parameters['document_id'].astext == str(document_id)
            )

        if user_id:
            user_agent = ProvAgent.query.filter_by(
                foaf_name=f'researcher:{user_id}'
            ).first()
            if not user_agent:
                return []
            query = query.filter(
                ProvActivity.wasassociatedwith == user_agent.agent_id
            )

        activities = query.limit(limit).all()

        # Enrich with entities and agents
        timeline = []
        for activity in activities:
            # Get generated entities
            gen_query = ProvEntity.query.filter_by(wasgeneratedby=activity.activity_id)
            if not include_invalidated:
                gen_query = gen_query.filter(ProvEntity.invalidatedattime.is_(None))
            generated = gen_query.all()

            # Get used entities (via relationships)
            used_rels = ProvRelationship.query.filter_by(
                relationship_type='used',
                subject_id=activity.activity_id
            ).all()
            used = []
            for rel in used_rels:
                entity = ProvEntity.query.get(rel.object_id)
                if entity:
                    # Filter out invalidated unless including them
                    if include_invalidated or entity.invalidatedattime is None:
                        used.append(entity)

            # Get agent
            agent = ProvAgent.query.get(activity.wasassociatedwith)

            # Get derived-from entities for generated entities
            derived_from = []
            for entity in generated:
                if entity.wasderivedfrom:
                    source_entity = ProvEntity.query.get(entity.wasderivedfrom)
                    if source_entity:
                        # Include derived-from even if invalidated (for context)
                        derived_from.append({
                            'id': str(source_entity.entity_id),
                            'type': source_entity.entity_type,
                            'value': source_entity.entity_value,
                            'for_entity_id': str(entity.entity_id),
                            'invalidated': source_entity.invalidatedattime is not None
                        })

            # Build entity data with invalidation status
            def entity_to_dict(e):
                return {
                    'id': str(e.entity_id),
                    'type': e.entity_type,
                    'value': e.entity_value,
                    'invalidated': e.invalidatedattime is not None,
                    'invalidated_at': e.invalidatedattime.isoformat() if e.invalidatedattime else None
                }

            timeline.append({
                'activity': {
                    'id': str(activity.activity_id),
                    'type': activity.activity_type,
                    'started_at': activity.startedattime.isoformat() if activity.startedattime else None,
                    'ended_at': activity.endedattime.isoformat() if activity.endedattime else None,
                    'status': activity.activity_status,
                    'parameters': activity.activity_parameters
                },
                'agent': {
                    'id': str(agent.agent_id),
                    'type': agent.agent_type,
                    'name': agent.foaf_name
                } if agent else None,
                'generated': [entity_to_dict(e) for e in generated],
                'used': [entity_to_dict(e) for e in used],
                'derived_from': derived_from
            })

        return timeline

    @staticmethod
    def get_entity_lineage(entity_id: uuid.UUID) -> List[ProvEntity]:
        """
        Get full lineage of an entity (all derivation ancestors).

        Args:
            entity_id: Entity UUID

        Returns:
            List of entities in lineage order (most recent first)
        """
        lineage = []
        current = ProvEntity.query.get(entity_id)

        while current:
            lineage.append(current)
            if current.wasderivedfrom:
                current = ProvEntity.query.get(current.wasderivedfrom)
            else:
                break

        return lineage

    @staticmethod
    def get_graph_data(
        experiment_id: int = None,
        document_id: int = None,
        term_id: str = None,
        limit: int = 50,
        user_id: int = None,
    ) -> Dict[str, Any]:
        """
        Get provenance data formatted for Cytoscape graph visualization.

        Args:
            experiment_id: Filter by experiment (optional)
            document_id: Filter by document (optional)
            term_id: Filter by term UUID (optional)
            limit: Maximum number of activities to include

        Returns:
            Dict with 'nodes' and 'edges' arrays for Cytoscape
        """
        nodes = []
        edges = []
        seen_nodes = set()

        # Build activity query with filters
        query = db.session.query(ProvActivity)\
            .order_by(ProvActivity.startedattime.desc())

        origin_entity_ids = set()
        if experiment_id:
            query = query.filter(
                ProvActivity.activity_parameters['experiment_id'].astext == str(experiment_id)
            )
            from app.models.experiment_document import ExperimentDocument

            associations = ExperimentDocument.query.filter_by(
                experiment_id=experiment_id
            ).all()
            root_document_ids = {
                association.document.get_root_document().id
                for association in associations
                if association.document
            }
            for root_document_id in root_document_ids:
                origin_entity = ProvEntity.query.filter(
                    ProvEntity.entity_type == 'document',
                    ProvEntity.entity_value['document_id'].astext
                    == str(root_document_id),
                ).order_by(ProvEntity.created_at.asc()).first()
                if origin_entity:
                    origin_entity_ids.add(str(origin_entity.entity_id))

        if user_id:
            user_agent = ProvAgent.query.filter_by(
                foaf_name=f'researcher:{user_id}'
            ).first()
            if not user_agent:
                return {
                    'nodes': [],
                    'edges': [],
                    'stats': {'entities': 0, 'activities': 0, 'agents': 0},
                }
            query = query.filter(
                ProvActivity.wasassociatedwith == user_agent.agent_id
            )

        # Track the origin document entity to add as root node
        origin_doc_entity = None

        if document_id:
            # Get all versions of this document
            from app.models.document import Document
            doc = Document.query.get(document_id)
            if doc:
                all_versions = doc.get_all_versions()
                doc_ids = [str(v.id) for v in all_versions]
                query = query.filter(
                    db.or_(*[
                        ProvActivity.activity_parameters['document_id'].astext == doc_id
                        for doc_id in doc_ids
                    ])
                )

                # Find the origin document entity (the original uploaded document)
                # This is the entity created by document_upload activity
                origin_doc = doc.get_original_document() if hasattr(doc, 'get_original_document') else doc
                origin_doc_entity = ProvEntity.query.filter(
                    ProvEntity.entity_type == 'document',
                    ProvEntity.entity_value['document_id'].astext == str(origin_doc.id)
                ).order_by(ProvEntity.created_at.asc()).first()

        if term_id:
            query = query.filter(
                ProvActivity.activity_parameters['term_id'].astext == str(term_id)
            )

        activities = query.limit(limit).all()

        # Add the origin document entity as the root node if filtering by document
        if origin_doc_entity:
            origin_id = str(origin_doc_entity.entity_id)
            if origin_id not in seen_nodes:
                seen_nodes.add(origin_id)

                # Build label from entity value
                origin_label = 'Original Document'
                if origin_doc_entity.entity_value:
                    if 'title' in origin_doc_entity.entity_value:
                        title = origin_doc_entity.entity_value.get('title', '')
                        origin_label = title[:30] + '...' if len(title) > 30 else title
                    elif 'filename' in origin_doc_entity.entity_value:
                        origin_label = origin_doc_entity.entity_value['filename']

                nodes.append({
                    'data': {
                        'id': origin_id,
                        'label': origin_label,
                        'type': 'entity',
                        'description': 'Original uploaded document',
                        'entity_type': 'document',
                        'value': origin_doc_entity.entity_value,
                        'is_origin': True
                    },
                    'classes': 'entity origin'
                })

                # Also add the upload activity and agent if they exist
                if origin_doc_entity.wasgeneratedby:
                    upload_activity = ProvActivity.query.get(origin_doc_entity.wasgeneratedby)
                    if upload_activity:
                        upload_activity_id = str(upload_activity.activity_id)
                        if upload_activity_id not in seen_nodes:
                            seen_nodes.add(upload_activity_id)
                            nodes.append({
                                'data': {
                                    'id': upload_activity_id,
                                    'label': upload_activity.activity_type.replace('_', '\n'),
                                    'type': 'activity',
                                    'description': f"Started: {upload_activity.startedattime.strftime('%Y-%m-%d %H:%M') if upload_activity.startedattime else 'N/A'}",
                                    'full_type': upload_activity.activity_type,
                                    'status': upload_activity.activity_status
                                },
                                'classes': 'activity'
                            })

                        # wasGeneratedBy edge from origin document to upload activity
                        gen_edge_id = f"gen_{origin_id}_{upload_activity_id}"
                        if gen_edge_id not in seen_nodes:
                            seen_nodes.add(gen_edge_id)
                            edges.append({
                                'data': {
                                    'id': gen_edge_id,
                                    'source': origin_id,
                                    'target': upload_activity_id,
                                    'label': 'wasGeneratedBy'
                                },
                                'classes': 'generated'
                            })

                        # Add agent for upload activity
                        if upload_activity.wasassociatedwith:
                            upload_agent = ProvAgent.query.get(upload_activity.wasassociatedwith)
                            if upload_agent:
                                upload_agent_id = str(upload_agent.agent_id)
                                if upload_agent_id not in seen_nodes:
                                    seen_nodes.add(upload_agent_id)
                                    # Add 'person' class for Person agents (purple styling)
                                    agent_classes = 'agent person' if upload_agent.agent_type == 'Person' else 'agent'
                                    # Use username for Person agents, foaf_name for others
                                    if upload_agent.agent_type == 'Person' and upload_agent.agent_metadata:
                                        agent_label = upload_agent.agent_metadata.get('username', upload_agent.foaf_name)
                                    else:
                                        agent_label = upload_agent.foaf_name or 'Unknown'
                                    nodes.append({
                                        'data': {
                                            'id': upload_agent_id,
                                            'label': agent_label,
                                            'type': 'agent',
                                            'description': upload_agent.agent_type,
                                            'agent_type': upload_agent.agent_type
                                        },
                                        'classes': agent_classes
                                    })

                                # wasAssociatedWith edge
                                assoc_edge_id = f"assoc_{upload_activity_id}_{upload_agent_id}"
                                if assoc_edge_id not in seen_nodes:
                                    seen_nodes.add(assoc_edge_id)
                                    edges.append({
                                        'data': {
                                            'id': assoc_edge_id,
                                            'source': upload_activity_id,
                                            'target': upload_agent_id,
                                            'label': 'wasAssociatedWith'
                                        },
                                        'classes': 'associated'
                                    })

        # Collect all agents, activities, and entities
        for activity in activities:
            activity_id = str(activity.activity_id)

            # Add activity node
            if activity_id not in seen_nodes:
                seen_nodes.add(activity_id)
                # Include activity parameters for rich details display
                activity_data = {
                    'id': activity_id,
                    'label': activity.activity_type.replace('_', '\n'),
                    'type': 'activity',
                    'description': f"Started: {activity.startedattime.strftime('%Y-%m-%d %H:%M') if activity.startedattime else 'N/A'}",
                    'full_type': activity.activity_type,
                    'status': activity.activity_status,
                    'started_at': activity.startedattime.isoformat() if activity.startedattime else None,
                    'ended_at': activity.endedattime.isoformat() if activity.endedattime else None
                }
                # Add parameters if available
                if activity.activity_parameters:
                    activity_data['parameters'] = activity.activity_parameters
                nodes.append({
                    'data': activity_data,
                    'classes': 'activity'
                })

            # Add agent node and edge
            if activity.wasassociatedwith:
                agent = ProvAgent.query.get(activity.wasassociatedwith)
                if agent:
                    agent_id = str(agent.agent_id)
                    if agent_id not in seen_nodes:
                        seen_nodes.add(agent_id)
                        # Add 'person' class for Person agents (purple styling)
                        agent_classes = 'agent person' if agent.agent_type == 'Person' else 'agent'
                        # Use username for Person agents, foaf_name for others
                        if agent.agent_type == 'Person' and agent.agent_metadata:
                            agent_label = agent.agent_metadata.get('username', agent.foaf_name)
                        else:
                            agent_label = agent.foaf_name or 'Unknown'
                        nodes.append({
                            'data': {
                                'id': agent_id,
                                'label': agent_label,
                                'type': 'agent',
                                'description': agent.agent_type,
                                'agent_type': agent.agent_type
                            },
                            'classes': agent_classes
                        })

                    # wasAssociatedWith edge
                    edge_id = f"assoc_{activity_id}_{agent_id}"
                    if edge_id not in seen_nodes:
                        seen_nodes.add(edge_id)
                        edges.append({
                            'data': {
                                'id': edge_id,
                                'source': activity_id,
                                'target': agent_id,
                                'label': 'wasAssociatedWith'
                            },
                            'classes': 'associated'
                        })

            # Add generated entities
            generated = ProvEntity.query.filter_by(wasgeneratedby=activity.activity_id).all()
            for entity in generated:
                entity_id = str(entity.entity_id)
                if entity_id not in seen_nodes:
                    seen_nodes.add(entity_id)

                    # Build label from entity value
                    label = entity.entity_type.replace('_', '\n')
                    if entity.entity_value:
                        if 'title' in entity.entity_value:
                            label = entity.entity_value['title'][:20] + '...' if len(str(entity.entity_value.get('title', ''))) > 20 else entity.entity_value.get('title', label)
                        elif 'document_id' in entity.entity_value:
                            label = f"Doc {entity.entity_value['document_id']}"
                        elif 'term_text' in entity.entity_value:
                            label = entity.entity_value['term_text'][:20]

                    entity_classes = (
                        'entity origin'
                        if entity_id in origin_entity_ids
                        else 'entity'
                    )
                    nodes.append({
                        'data': {
                            'id': entity_id,
                            'label': label,
                            'type': 'entity',
                            'description': entity.entity_type,
                            'entity_type': entity.entity_type,
                            'value': entity.entity_value
                        },
                        'classes': entity_classes
                    })

                # wasGeneratedBy edge
                edge_id = f"gen_{entity_id}_{activity_id}"
                if edge_id not in seen_nodes:
                    seen_nodes.add(edge_id)
                    edges.append({
                        'data': {
                            'id': edge_id,
                            'source': entity_id,
                            'target': activity_id,
                            'label': 'wasGeneratedBy'
                        },
                        'classes': 'generated'
                    })

                # wasDerivedFrom edge
                if entity.wasderivedfrom:
                    source_entity = ProvEntity.query.get(entity.wasderivedfrom)
                    if source_entity:
                        source_id = str(source_entity.entity_id)

                        # Add source entity if not seen
                        if source_id not in seen_nodes:
                            seen_nodes.add(source_id)
                            source_label = source_entity.entity_type.replace('_', '\n')
                            if source_entity.entity_value:
                                if 'title' in source_entity.entity_value:
                                    source_label = source_entity.entity_value['title'][:20] + '...' if len(str(source_entity.entity_value.get('title', ''))) > 20 else source_entity.entity_value.get('title', source_label)

                            source_classes = (
                                'entity origin'
                                if source_id in origin_entity_ids
                                else 'entity'
                            )
                            nodes.append({
                                'data': {
                                    'id': source_id,
                                    'label': source_label,
                                    'type': 'entity',
                                    'description': source_entity.entity_type,
                                    'entity_type': source_entity.entity_type
                                },
                                'classes': source_classes
                            })

                        # wasDerivedFrom edge
                        derived_edge_id = f"derived_{entity_id}_{source_id}"
                        if derived_edge_id not in seen_nodes:
                            seen_nodes.add(derived_edge_id)
                            edges.append({
                                'data': {
                                    'id': derived_edge_id,
                                    'source': entity_id,
                                    'target': source_id,
                                    'label': 'wasDerivedFrom'
                                },
                                'classes': 'derived'
                            })

        return {
            'nodes': nodes,
            'edges': edges,
            'stats': {
                'entities': len([n for n in nodes if 'entity' in n['classes']]),
                'activities': len([n for n in nodes if 'activity' in n['classes']]),
                'agents': len([n for n in nodes if 'agent' in n['classes']])
            }
        }
