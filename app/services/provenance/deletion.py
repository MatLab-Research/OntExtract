"""PROV-O deletion and invalidation operations."""

import logging
import uuid
from datetime import datetime
from typing import Any, Dict, List

from app import db
from app.models.prov_o_models import ProvActivity, ProvEntity, ProvRelationship

logger = logging.getLogger(__name__)


class ProvenanceDeletionMixin:
    @classmethod
    def delete_or_invalidate_entity(
        cls,
        entity_id: uuid.UUID,
        purge: bool = None,
        deleted_by_user=None
    ) -> Dict[str, Any]:
        """
        Delete or invalidate a provenance entity based on system settings.

        If purge=True: Hard delete the entity and all relationships to/from it.
        If purge=False: Set invalidatedattime to mark as deleted but preserve for audit.

        Args:
            entity_id: UUID of the ProvEntity to delete/invalidate
            purge: Override system setting (None = use system setting)
            deleted_by_user: User who initiated the deletion (for audit)

        Returns:
            Dict with 'success', 'action' ('purged' or 'invalidated'), and counts
        """
        from app.models.app_settings import AppSetting

        # Determine whether to purge or invalidate
        if purge is None:
            purge = AppSetting.get_setting('purge_provenance_on_delete', default=True)

        entity = ProvEntity.query.get(entity_id)
        if not entity:
            return {'success': False, 'error': 'Entity not found'}

        if purge:
            # Hard delete: remove entity and all relationships
            relationships_deleted = ProvRelationship.query.filter(
                db.or_(
                    db.and_(
                        ProvRelationship.subject_type == 'entity',
                        ProvRelationship.subject_id == entity_id
                    ),
                    db.and_(
                        ProvRelationship.object_type == 'entity',
                        ProvRelationship.object_id == entity_id
                    )
                )
            ).delete(synchronize_session=False)

            db.session.delete(entity)
            db.session.commit()

            logger.info(f"Purged provenance entity {entity_id} and {relationships_deleted} relationships")
            return {
                'success': True,
                'action': 'purged',
                'entities_deleted': 1,
                'relationships_deleted': relationships_deleted
            }
        else:
            # Soft delete: set invalidatedattime
            entity.invalidatedattime = datetime.utcnow()
            db.session.commit()

            logger.info(f"Invalidated provenance entity {entity_id}")
            return {
                'success': True,
                'action': 'invalidated',
                'entities_invalidated': 1
            }

    @classmethod
    def delete_or_invalidate_document_provenance(
        cls,
        document_id: int,
        purge: bool = None
    ) -> Dict[str, Any]:
        """
        Delete or invalidate all provenance records for a document.

        Args:
            document_id: ID of the document being deleted
            purge: Override system setting (None = use system setting)

        Returns:
            Dict with counts of affected records
        """
        from app.models.app_settings import AppSetting

        if purge is None:
            purge = AppSetting.get_setting('purge_provenance_on_delete', default=True)

        # Find all entities related to this document
        entities = ProvEntity.query.filter(
            ProvEntity.entity_value['document_id'].astext == str(document_id)
        ).all()

        if not entities:
            return {'success': True, 'entities_affected': 0}

        entity_ids = [e.entity_id for e in entities]
        total_relationships = 0

        if purge:
            # Delete relationships for all entities
            for entity_id in entity_ids:
                rel_count = ProvRelationship.query.filter(
                    db.or_(
                        db.and_(
                            ProvRelationship.subject_type == 'entity',
                            ProvRelationship.subject_id == entity_id
                        ),
                        db.and_(
                            ProvRelationship.object_type == 'entity',
                            ProvRelationship.object_id == entity_id
                        )
                    )
                ).delete(synchronize_session=False)
                total_relationships += rel_count

            # Delete all entities
            for entity in entities:
                db.session.delete(entity)

            db.session.commit()

            logger.info(f"Purged {len(entities)} provenance entities and {total_relationships} relationships for document {document_id}")
            return {
                'success': True,
                'action': 'purged',
                'entities_deleted': len(entities),
                'relationships_deleted': total_relationships
            }
        else:
            # Invalidate all entities
            for entity in entities:
                entity.invalidatedattime = datetime.utcnow()

            db.session.commit()

            logger.info(f"Invalidated {len(entities)} provenance entities for document {document_id}")
            return {
                'success': True,
                'action': 'invalidated',
                'entities_invalidated': len(entities)
            }

    @classmethod
    def delete_or_invalidate_term_provenance(
        cls,
        term_id: uuid.UUID,
        purge: bool = None
    ) -> Dict[str, Any]:
        """
        Delete or invalidate all provenance records for a term.

        Args:
            term_id: UUID of the term being deleted
            purge: Override system setting (None = use system setting)

        Returns:
            Dict with counts of affected records
        """
        from app.models.app_settings import AppSetting

        if purge is None:
            purge = AppSetting.get_setting('purge_provenance_on_delete', default=True)

        # Find all entities related to this term
        entities = ProvEntity.query.filter(
            ProvEntity.entity_value['term_id'].astext == str(term_id)
        ).all()

        if not entities:
            return {'success': True, 'entities_affected': 0}

        entity_ids = [e.entity_id for e in entities]
        total_relationships = 0

        if purge:
            # Delete relationships for all entities
            for entity_id in entity_ids:
                rel_count = ProvRelationship.query.filter(
                    db.or_(
                        db.and_(
                            ProvRelationship.subject_type == 'entity',
                            ProvRelationship.subject_id == entity_id
                        ),
                        db.and_(
                            ProvRelationship.object_type == 'entity',
                            ProvRelationship.object_id == entity_id
                        )
                    )
                ).delete(synchronize_session=False)
                total_relationships += rel_count

            # Delete all entities
            for entity in entities:
                db.session.delete(entity)

            db.session.commit()

            logger.info(f"Purged {len(entities)} provenance entities and {total_relationships} relationships for term {term_id}")
            return {
                'success': True,
                'action': 'purged',
                'entities_deleted': len(entities),
                'relationships_deleted': total_relationships
            }
        else:
            # Invalidate all entities
            for entity in entities:
                entity.invalidatedattime = datetime.utcnow()

            db.session.commit()

            logger.info(f"Invalidated {len(entities)} provenance entities for term {term_id}")
            return {
                'success': True,
                'action': 'invalidated',
                'entities_invalidated': len(entities)
            }

    @classmethod
    def delete_or_invalidate_experiment_provenance(
        cls,
        experiment_id: int,
        document_ids: List[int] = None,
        purge: bool = None
    ) -> Dict[str, Any]:
        """
        Delete or invalidate provenance records for an experiment and its documents.

        Args:
            experiment_id: ID of the experiment being deleted
            document_ids: List of document IDs whose provenance should be affected
            purge: Override system setting (None = use system setting)

        Returns:
            Dict with counts of affected records
        """
        from app.models.app_settings import AppSetting

        if purge is None:
            purge = AppSetting.get_setting('purge_provenance_on_delete', default=True)

        total_entities = 0
        total_activities = 0
        total_relationships = 0

        # Handle experiment's own provenance entities
        exp_entities = ProvEntity.query.filter(
            ProvEntity.entity_value['experiment_id'].astext == str(experiment_id)
        ).all()

        # Handle experiment's own provenance activities
        exp_activities = ProvActivity.query.filter(
            ProvActivity.activity_parameters['experiment_id'].astext == str(experiment_id)
        ).all()

        # Handle document provenance if document_ids provided
        doc_entities = []
        doc_activities = []
        if document_ids:
            for doc_id in document_ids:
                doc_ents = ProvEntity.query.filter(
                    ProvEntity.entity_value['document_id'].astext == str(doc_id)
                ).all()
                doc_entities.extend(doc_ents)

                doc_acts = ProvActivity.query.filter(
                    ProvActivity.activity_parameters['document_id'].astext == str(doc_id)
                ).all()
                doc_activities.extend(doc_acts)

        all_entities = exp_entities + doc_entities
        all_activities = exp_activities + doc_activities

        if not all_entities and not all_activities:
            return {'success': True, 'entities_affected': 0, 'activities_affected': 0}

        entity_ids = [e.entity_id for e in all_entities]
        activity_ids = [a.activity_id for a in all_activities]

        if purge:
            # Delete relationships for all entities
            for entity_id in entity_ids:
                rel_count = ProvRelationship.query.filter(
                    db.or_(
                        db.and_(
                            ProvRelationship.subject_type == 'entity',
                            ProvRelationship.subject_id == entity_id
                        ),
                        db.and_(
                            ProvRelationship.object_type == 'entity',
                            ProvRelationship.object_id == entity_id
                        )
                    )
                ).delete(synchronize_session=False)
                total_relationships += rel_count

            # Delete relationships for all activities
            for activity_id in activity_ids:
                rel_count = ProvRelationship.query.filter(
                    db.or_(
                        db.and_(
                            ProvRelationship.subject_type == 'activity',
                            ProvRelationship.subject_id == activity_id
                        ),
                        db.and_(
                            ProvRelationship.object_type == 'activity',
                            ProvRelationship.object_id == activity_id
                        )
                    )
                ).delete(synchronize_session=False)
                total_relationships += rel_count

            # Clear wasderivedfrom self-references BEFORE deleting entities
            # This handles the self-referential FK constraint on prov_entities
            for entity_id in entity_ids:
                ProvEntity.query.filter(
                    ProvEntity.wasderivedfrom == entity_id
                ).update({'wasderivedfrom': None}, synchronize_session=False)

            # Clear wasgeneratedby references to activities being deleted
            for activity_id in activity_ids:
                ProvEntity.query.filter(
                    ProvEntity.wasgeneratedby == activity_id
                ).update({'wasgeneratedby': None}, synchronize_session=False)

            # Delete all entities
            for entity in all_entities:
                db.session.delete(entity)

            # Delete all activities
            for activity in all_activities:
                db.session.delete(activity)

            total_entities = len(all_entities)
            total_activities = len(all_activities)
            db.session.commit()

            logger.info(
                f"Purged {total_entities} provenance entities, {total_activities} activities, "
                f"and {total_relationships} relationships for experiment {experiment_id}"
            )
            return {
                'success': True,
                'action': 'purged',
                'entities_deleted': total_entities,
                'activities_deleted': total_activities,
                'relationships_deleted': total_relationships
            }
        else:
            # Invalidate all entities
            for entity in all_entities:
                entity.invalidatedattime = datetime.utcnow()

            # Note: Activities don't have invalidatedattime in PROV-O model
            # They are only "purged" or left intact

            total_entities = len(all_entities)
            db.session.commit()

            logger.info(f"Invalidated {total_entities} provenance entities for experiment {experiment_id}")
            return {
                'success': True,
                'action': 'invalidated',
                'entities_invalidated': total_entities
            }
