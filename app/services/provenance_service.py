"""
Centralized PROV-O Provenance Tracking Service

Provides easy-to-use methods for tracking all actions in OntExtract:
- Term creation/updates
- Document uploads
- Experiment creation
- Tool executions
- Orchestration runs

Builds on the existing PROV-O database models (prov_agents, prov_activities, prov_entities).
"""

from datetime import datetime
from typing import Optional, Dict, Any, List
import uuid
import logging

from app import db
from app.models.prov_o_models import ProvAgent, ProvActivity, ProvEntity, ProvRelationship

logger = logging.getLogger(__name__)


def _serialize_value(value: Any) -> Any:
    """
    Convert values to JSON-serializable format.
    Handles UUIDs, datetime objects, and nested structures.
    """
    if isinstance(value, uuid.UUID):
        return str(value)
    elif isinstance(value, datetime):
        return value.isoformat()
    elif isinstance(value, dict):
        return {k: _serialize_value(v) for k, v in value.items()}
    elif isinstance(value, (list, tuple)):
        return [_serialize_value(v) for v in value]
    else:
        return value


class ProvenanceService:
    """
    Centralized service for PROV-O provenance tracking.

    Makes it easy to track any action with proper PROV-O semantics:
    - Agent: Who did it (user, LLM, system)
    - Activity: What happened (term_creation, tool_execution, etc.)
    - Entity: What was created/modified (term, document, result)
    """

    # ========================================================================
    # AGENT MANAGEMENT
    # ========================================================================

    @staticmethod
    def get_or_create_user_agent(user_id: int, username: str = None) -> ProvAgent:
        """Get or create agent for a user."""
        return ProvAgent.get_or_create_user_agent(
            user_id=user_id,
            user_metadata={'username': username} if username else None
        )

    @staticmethod
    def get_or_create_system_agent() -> ProvAgent:
        """Get or create system agent for automated actions."""
        agent = ProvAgent.query.filter_by(foaf_name='system').first()
        if not agent:
            agent = ProvAgent(
                agent_type='SoftwareAgent',
                foaf_name='system',
                agent_metadata={
                    'tool_type': 'system',
                    'description': 'OntExtract system agent'
                }
            )
            db.session.add(agent)
            db.session.commit()
        return agent

    @staticmethod
    def get_or_create_llm_agent(provider: str = 'anthropic', model_id: str = None) -> ProvAgent:
        """Get or create LLM agent."""
        return ProvAgent.get_or_create_orchestrator_agent(model_provider=provider)

    @staticmethod
    def get_or_create_tool_agent(tool_name: str, tool_metadata: Dict[str, Any] = None) -> ProvAgent:
        """
        Get or create SoftwareAgent for a processing tool.

        Args:
            tool_name: Name of the tool (e.g., 'nltk', 'spacy', 'pypdf')
            tool_metadata: Optional metadata about the tool

        Returns:
            ProvAgent instance
        """
        agent = ProvAgent.query.filter_by(foaf_name=tool_name).first()
        if not agent:
            metadata = tool_metadata or {}
            metadata['tool_type'] = 'processing_library'

            agent = ProvAgent(
                agent_type='SoftwareAgent',
                foaf_name=tool_name,
                agent_metadata=metadata
            )
            db.session.add(agent)
            db.session.commit()
        return agent

    @staticmethod
    def get_or_create_nltk_agent() -> ProvAgent:
        """Get or create NLTK SoftwareAgent."""
        return ProvenanceService.get_or_create_tool_agent(
            tool_name='nltk',
            tool_metadata={
                'description': 'Natural Language Toolkit',
                'url': 'https://www.nltk.org/',
                'tool_category': 'nlp_library'
            }
        )

    @staticmethod
    def get_or_create_spacy_agent(model_name: str = 'en_core_web_sm') -> ProvAgent:
        """Get or create spaCy SoftwareAgent."""
        agent_name = f'spacy_{model_name}'
        return ProvenanceService.get_or_create_tool_agent(
            tool_name=agent_name,
            tool_metadata={
                'description': f'spaCy NLP model: {model_name}',
                'url': 'https://spacy.io/',
                'model': model_name,
                'tool_category': 'nlp_library'
            }
        )

    @staticmethod
    def get_or_create_sentence_transformer_agent(model_name: str = 'all-MiniLM-L6-v2') -> ProvAgent:
        """Get or create Sentence Transformers SoftwareAgent."""
        agent_name = f'sentence_transformers_{model_name}'
        return ProvenanceService.get_or_create_tool_agent(
            tool_name=agent_name,
            tool_metadata={
                'description': f'Sentence Transformers model: {model_name}',
                'url': 'https://www.sbert.net/',
                'model': model_name,
                'tool_category': 'embedding_model'
            }
        )

    @staticmethod
    def get_or_create_pypdf_agent() -> ProvAgent:
        """Get or create pypdf SoftwareAgent."""
        return ProvenanceService.get_or_create_tool_agent(
            tool_name='pypdf',
            tool_metadata={
                'description': 'PDF text extraction library',
                'url': 'https://github.com/py-pdf/pypdf',
                'tool_category': 'text_extraction'
            }
        )

    @staticmethod
    def get_or_create_python_docx_agent() -> ProvAgent:
        """Get or create python-docx SoftwareAgent."""
        return ProvenanceService.get_or_create_tool_agent(
            tool_name='python-docx',
            tool_metadata={
                'description': 'DOCX text extraction library',
                'url': 'https://python-docx.readthedocs.io/',
                'tool_category': 'text_extraction'
            }
        )

    @staticmethod
    def get_or_create_beautifulsoup_agent() -> ProvAgent:
        """Get or create BeautifulSoup SoftwareAgent."""
        return ProvenanceService.get_or_create_tool_agent(
            tool_name='beautifulsoup4',
            tool_metadata={
                'description': 'HTML text extraction library',
                'url': 'https://www.crummy.com/software/BeautifulSoup/',
                'tool_category': 'text_extraction'
            }
        )

    @staticmethod
    def get_or_create_source_entity(source_name: str) -> ProvEntity:
        """
        Get or create a PROV-O entity for an external knowledge source.

        Args:
            source_name: Name of the source (e.g., "OED 2024", "Merriam-Webster", "WordNet")

        Returns:
            ProvEntity representing the external source
        """
        # Check if entity for this source already exists
        existing = ProvEntity.query.filter_by(
            entity_type='external_source'
        ).filter(
            ProvEntity.entity_value['source_name'].astext == source_name
        ).first()

        if existing:
            return existing

        # Get system agent (external sources are attributed to system)
        system_agent = ProvenanceService.get_or_create_system_agent()

        # Create activity for registering this external source
        registration_activity = ProvActivity(
            activity_type='source_registration',
            startedattime=datetime.utcnow(),
            endedattime=datetime.utcnow(),
            wasassociatedwith=system_agent.agent_id,
            activity_parameters={'source_name': source_name},
            activity_status='completed'
        )
        db.session.add(registration_activity)
        db.session.flush()

        # Create new source entity
        source_entity = ProvEntity(
            entity_type='external_source',
            generatedattime=datetime.utcnow(),
            wasgeneratedby=registration_activity.activity_id,  # Generated by registration
            wasattributedto=system_agent.agent_id,  # Attributed to system
            entity_value=_serialize_value({
                'source_name': source_name,
                'source_type': 'dictionary' if any(kw in source_name.lower() for kw in ['oed', 'dictionary', 'webster', 'wordnet']) else 'corpus'
            }),
            entity_metadata={'persistent': True}  # These are long-lived entities
        )
        db.session.add(source_entity)
        db.session.flush()

        return source_entity

    # ========================================================================
    # TERM MANAGEMENT TRACKING
    # ========================================================================

    @classmethod
    def track_term_creation(cls, term, user) -> tuple[ProvActivity, ProvEntity]:
        """
        Track term creation with PROV-O.

        Args:
            term: Term model instance
            user: User model instance

        Returns:
            (activity, entity) tuple
        """
        # Get/create user agent
        agent = cls.get_or_create_user_agent(user.id, user.username)

        # Create activity
        activity = ProvActivity(
            activity_type='term_creation',
            startedattime=term.created_at or datetime.utcnow(),
            endedattime=term.created_at or datetime.utcnow(),
            wasassociatedwith=agent.agent_id,
            activity_parameters={
                'term_text': term.term_text,
                'research_domain': term.research_domain,
                'term_id': str(term.id)
            },
            activity_status='completed'
        )
        db.session.add(activity)
        db.session.flush()  # Get activity_id

        # Check if term has a source (from first version's corpus_source)
        first_version = term.get_current_version()
        source_entity_id = None

        if first_version and first_version.corpus_source:
            # Create/get entity for the external source (OED, dictionary, etc.)
            source_entity = cls.get_or_create_source_entity(first_version.corpus_source)
            source_entity_id = source_entity.entity_id

        # Create entity representing the term
        entity = ProvEntity(
            entity_type='term',
            generatedattime=term.created_at or datetime.utcnow(),
            wasgeneratedby=activity.activity_id,
            wasattributedto=agent.agent_id,
            wasderivedfrom=source_entity_id,  # Link to source if available
            entity_value=_serialize_value({
                'term_id': str(term.id),
                'term_text': term.term_text,
                'research_domain': term.research_domain,
                'status': term.status
            }),
            entity_metadata={'created_via': 'ui'}
        )
        db.session.add(entity)
        db.session.commit()

        return activity, entity

    @classmethod
    def track_term_update(cls, term, user, changes: Dict[str, Any]) -> tuple[ProvActivity, ProvEntity]:
        """Track term updates."""
        agent = cls.get_or_create_user_agent(user.id, user.username)

        activity = ProvActivity(
            activity_type='term_update',
            startedattime=datetime.utcnow(),
            endedattime=datetime.utcnow(),
            wasassociatedwith=agent.agent_id,
            activity_parameters=_serialize_value({
                'term_id': str(term.id),
                'term_text': term.term_text,
                'fields_changed': list(changes.keys()),
                'num_changes': len(changes)
            }),
            activity_status='completed'
        )
        db.session.add(activity)
        db.session.flush()

        # Find previous entity for this term
        previous_entity = ProvEntity.query.filter_by(
            entity_type='term',
            entity_value=db.func.jsonb_build_object('term_id', term.id)
        ).order_by(ProvEntity.created_at.desc()).first()

        entity = ProvEntity(
            entity_type='term',
            generatedattime=datetime.utcnow(),
            wasgeneratedby=activity.activity_id,
            wasattributedto=agent.agent_id,
            wasderivedfrom=previous_entity.entity_id if previous_entity else None,
            entity_value=_serialize_value({
                'term_id': str(term.id),
                'term_text': term.term_text,
                'research_domain': term.research_domain,
                'status': term.status
            }),
            entity_metadata=_serialize_value({
                'changes': changes,  # Full change details stored here
                'updated_via': 'ui'
            })
        )
        db.session.add(entity)
        db.session.commit()

        return activity, entity

    # ========================================================================
    # DOCUMENT MANAGEMENT TRACKING
    # ========================================================================

    @classmethod
    def track_document_upload(cls, document, user, experiment=None) -> tuple[ProvActivity, ProvEntity]:
        """Track document upload."""
        agent = cls.get_or_create_user_agent(user.id, user.username)

        activity = ProvActivity(
            activity_type='document_upload',
            startedattime=document.created_at or datetime.utcnow(),
            endedattime=document.created_at or datetime.utcnow(),
            wasassociatedwith=agent.agent_id,
            activity_parameters=_serialize_value({
                'document_id': document.id,
                'document_uuid': document.uuid,
                'filename': document.original_filename,
                'file_type': document.file_type,
                'content_type': document.content_type,
                'document_type': document.document_type,
                'experiment_id': experiment.id if experiment else None
            }),
            activity_status='completed'
        )
        db.session.add(activity)
        db.session.flush()

        entity = ProvEntity(
            entity_type='document',
            generatedattime=document.created_at or datetime.utcnow(),
            wasgeneratedby=activity.activity_id,
            wasattributedto=agent.agent_id,
            entity_value=_serialize_value({
                'document_id': document.id,
                'document_uuid': document.uuid,
                'filename': document.original_filename,
                'title': document.title,
                'content_type': document.content_type,
                'document_type': document.document_type,
                'word_count': document.word_count,
                'character_count': document.character_count
            })
        )
        db.session.add(entity)
        db.session.commit()

        return activity, entity

    @classmethod
    def track_metadata_extraction(
        cls,
        document,
        user,
        extraction_source: str,
        extracted_fields: Dict[str, Any],
        confidence: float = 0.9
    ) -> tuple[ProvActivity, ProvEntity]:
        """
        Track automated metadata extraction (CrossRef, Zotero, PDF analysis).

        Args:
            document: Document instance
            user: User who initiated the upload (attribution)
            extraction_source: 'crossref', 'zotero', 'pdf_analysis'
            extracted_fields: Dictionary of extracted metadata fields
            confidence: Confidence score of extraction
        """
        # Get appropriate agent (system/API agent for automated extraction)
        if extraction_source == 'crossref':
            agent = ProvAgent.query.filter_by(foaf_name='crossref_api').first()
            if not agent:
                agent = ProvAgent(
                    agent_type='SoftwareAgent',
                    foaf_name='crossref_api',
                    agent_metadata={
                        'tool_type': 'metadata_api',
                        'description': 'CrossRef API metadata extraction',
                        'url': 'https://api.crossref.org'
                    }
                )
                db.session.add(agent)
                db.session.flush()
        elif extraction_source == 'zotero':
            agent = ProvAgent.query.filter_by(foaf_name='zotero_api').first()
            if not agent:
                agent = ProvAgent(
                    agent_type='SoftwareAgent',
                    foaf_name='zotero_api',
                    agent_metadata={
                        'tool_type': 'metadata_api',
                        'description': 'Zotero API metadata extraction',
                        'url': 'https://www.zotero.org'
                    }
                )
                db.session.add(agent)
                db.session.flush()
        elif extraction_source == 'semanticscholar':
            agent = ProvAgent.query.filter_by(foaf_name='semanticscholar_api').first()
            if not agent:
                agent = ProvAgent(
                    agent_type='SoftwareAgent',
                    foaf_name='semanticscholar_api',
                    agent_metadata={
                        'tool_type': 'metadata_api',
                        'description': 'Semantic Scholar API metadata extraction',
                        'url': 'https://api.semanticscholar.org'
                    }
                )
                db.session.add(agent)
                db.session.flush()
        elif extraction_source == 'pdf_analysis':
            agent = ProvAgent.query.filter_by(foaf_name='pdf_analyzer').first()
            if not agent:
                agent = ProvAgent(
                    agent_type='SoftwareAgent',
                    foaf_name='pdf_analyzer',
                    agent_metadata={
                        'tool_type': 'text_extraction',
                        'description': 'PDF metadata extraction from embedded fields',
                        'methods': ['embedded_metadata', 'text_analysis']
                    }
                )
                db.session.add(agent)
                db.session.flush()
        elif extraction_source in ['user', 'manual']:
            # User-provided data - use person agent
            agent = cls.get_or_create_user_agent(
                user_id=getattr(user, 'id', 0),
                username=getattr(user, 'username', 'unknown')
            )
        else:
            agent = cls.get_or_create_system_agent()

        activity = ProvActivity(
            activity_type='metadata_extraction',
            startedattime=datetime.utcnow(),
            endedattime=datetime.utcnow(),
            wasassociatedwith=agent.agent_id,
            activity_parameters=_serialize_value({
                'document_id': document.id,
                'extraction_source': extraction_source,
                'fields_extracted': list(extracted_fields.keys()),
                'confidence': confidence
            }),
            activity_status='completed'
        )
        db.session.add(activity)
        db.session.flush()

        # Find document entity to link derivation
        doc_entity = ProvEntity.query.filter(
            ProvEntity.entity_type == 'document',
            ProvEntity.entity_value['document_id'].astext == str(document.id)
        ).order_by(ProvEntity.created_at.desc()).first()

        entity = ProvEntity(
            entity_type='metadata',
            generatedattime=datetime.utcnow(),
            wasgeneratedby=activity.activity_id,
            wasattributedto=agent.agent_id,
            wasderivedfrom=doc_entity.entity_id if doc_entity else None,
            entity_value=_serialize_value({
                'document_id': document.id,
                'document_uuid': document.uuid,
                'extraction_source': extraction_source,
                'extracted_metadata': extracted_fields,
                'confidence': confidence
            })
        )
        db.session.add(entity)

        # Create "used" relationship (activity used document)
        if doc_entity:
            used_rel = ProvRelationship(
                relationship_type='used',
                subject_type='activity',
                subject_id=activity.activity_id,
                object_type='entity',
                object_id=doc_entity.entity_id
            )
            db.session.add(used_rel)

        db.session.commit()
        return activity, entity

    @classmethod
    def track_text_extraction(
        cls,
        document,
        user,
        source_format: str,
        extraction_method: str = 'auto',
        start_time: datetime = None,
        end_time: datetime = None
    ) -> tuple[ProvActivity, ProvEntity]:
        """
        Track text extraction from PDF/DOCX files.

        Args:
            document: Document instance
            user: User who initiated the upload
            source_format: 'pdf', 'docx', 'txt', etc.
            extraction_method: 'pypdf', 'python-docx', 'plain', etc.
            start_time: When extraction started
            end_time: When extraction completed
        """
        system_agent = cls.get_or_create_system_agent()

        activity = ProvActivity(
            activity_type='text_extraction',
            startedattime=start_time or datetime.utcnow(),
            endedattime=end_time or datetime.utcnow(),
            wasassociatedwith=system_agent.agent_id,
            activity_parameters=_serialize_value({
                'document_id': document.id,
                'document_uuid': document.uuid,
                'source_format': source_format,
                'extraction_method': extraction_method,
                'text_length': len(document.content) if document.content else 0
            }),
            activity_status='completed'
        )
        db.session.add(activity)
        db.session.flush()

        # Find the document entity created by document_upload
        doc_entity = ProvEntity.query.filter(
            ProvEntity.entity_type == 'document',
            ProvEntity.entity_value['document_id'].astext == str(document.id)
        ).order_by(ProvEntity.created_at.desc()).first()

        # Create TextSegment entity for the extracted content
        entity = ProvEntity(
            entity_type='text_content',
            generatedattime=end_time or datetime.utcnow(),
            wasgeneratedby=activity.activity_id,
            wasattributedto=system_agent.agent_id,
            wasderivedfrom=doc_entity.entity_id if doc_entity else None,
            entity_value=_serialize_value({
                'document_id': document.id,
                'document_uuid': document.uuid,
                'text_length': len(document.content) if document.content else 0,
                'word_count': len(document.content.split()) if document.content else 0
            })
        )
        db.session.add(entity)

        # Create "used" relationship (activity used uploaded document)
        if doc_entity:
            used_rel = ProvRelationship(
                relationship_type='used',
                subject_type='activity',
                subject_id=activity.activity_id,
                object_type='entity',
                object_id=doc_entity.entity_id
            )
            db.session.add(used_rel)

        db.session.commit()
        return activity, entity

    @classmethod
    def track_document_save(
        cls,
        document,
        user
    ) -> tuple[ProvActivity, ProvEntity]:
        """
        Track document persistence to database.

        Args:
            document: Document instance (after commit)
            user: User who initiated the upload
        """
        user_agent = cls.get_or_create_user_agent(user.id, user.username)

        activity = ProvActivity(
            activity_type='document_save',
            startedattime=document.created_at or datetime.utcnow(),
            endedattime=document.created_at or datetime.utcnow(),
            wasassociatedwith=user_agent.agent_id,
            activity_parameters=_serialize_value({
                'document_id': document.id,
                'document_uuid': document.uuid,
                'database': 'ontextract_db'
            }),
            activity_status='completed'
        )
        db.session.add(activity)
        db.session.flush()

        # Find text content entity
        text_entity = ProvEntity.query.filter(
            ProvEntity.entity_type == 'text_content',
            ProvEntity.entity_value['document_id'].astext == str(document.id)
        ).order_by(ProvEntity.created_at.desc()).first()

        # Create persisted document version entity
        entity = ProvEntity(
            entity_type='document_version',
            generatedattime=document.created_at or datetime.utcnow(),
            wasgeneratedby=activity.activity_id,
            wasattributedto=user_agent.agent_id,
            wasderivedfrom=text_entity.entity_id if text_entity else None,
            entity_value=_serialize_value({
                'document_id': document.id,
                'document_uuid': document.uuid,
                'version': 1,
                'status': document.status
            })
        )
        db.session.add(entity)

        # Create "used" relationship (save used text content)
        if text_entity:
            used_rel = ProvRelationship(
                relationship_type='used',
                subject_type='activity',
                subject_id=activity.activity_id,
                object_type='entity',
                object_id=text_entity.entity_id
            )
            db.session.add(used_rel)

        db.session.commit()
        return activity, entity

    @classmethod
    def track_metadata_extraction_pdf(
        cls,
        document,
        user,
        extracted_identifiers: Dict[str, str],
        extraction_patterns: list = None
    ) -> tuple[ProvActivity, ProvEntity]:
        """
        Track DOI/identifier extraction from PDF.

        Args:
            document: Document instance
            user: User who initiated upload
            extracted_identifiers: Dict of identifiers found (doi, arxiv_id, etc.)
            extraction_patterns: List of regex patterns used
        """
        system_agent = cls.get_or_create_system_agent()

        activity = ProvActivity(
            activity_type='metadata_extraction_pdf',
            startedattime=datetime.utcnow(),
            endedattime=datetime.utcnow(),
            wasassociatedwith=system_agent.agent_id,
            activity_parameters=_serialize_value({
                'document_id': document.id,
                'document_uuid': document.uuid,
                'extraction_patterns': extraction_patterns or ['doi_regex', 'arxiv_regex'],
                'identifiers_found': list(extracted_identifiers.keys())
            }),
            activity_status='completed'
        )
        db.session.add(activity)
        db.session.flush()

        # Find text content entity
        text_entity = ProvEntity.query.filter(
            ProvEntity.entity_type == 'text_content',
            ProvEntity.entity_value['document_id'].astext == str(document.id)
        ).order_by(ProvEntity.created_at.desc()).first()

        # Create metadata entity for extracted identifiers
        entity = ProvEntity(
            entity_type='metadata',
            generatedattime=datetime.utcnow(),
            wasgeneratedby=activity.activity_id,
            wasattributedto=system_agent.agent_id,
            wasderivedfrom=text_entity.entity_id if text_entity else None,
            entity_value=_serialize_value({
                'document_id': document.id,
                'document_uuid': document.uuid,
                'source': 'pdf_analysis',
                'identifiers': extracted_identifiers
            })
        )
        db.session.add(entity)

        # Create "used" relationship
        if text_entity:
            used_rel = ProvRelationship(
                relationship_type='used',
                subject_type='activity',
                subject_id=activity.activity_id,
                object_type='entity',
                object_id=text_entity.entity_id
            )
            db.session.add(used_rel)

        db.session.commit()
        return activity, entity

    @classmethod
    def track_metadata_update(
        cls,
        document,
        user,
        changes: Dict[str, Dict[str, Any]]
    ) -> tuple[ProvActivity, ProvEntity]:
        """
        Track manual metadata updates by users.

        Args:
            document: Document instance
            user: User making the update
            changes: Dict with 'old' and 'new' values for each field
                    e.g., {'title': {'old': 'Old Title', 'new': 'New Title'}}
        """
        agent = cls.get_or_create_user_agent(user.id, user.username)

        activity = ProvActivity(
            activity_type='metadata_update',
            startedattime=datetime.utcnow(),
            endedattime=datetime.utcnow(),
            wasassociatedwith=agent.agent_id,
            activity_parameters=_serialize_value({
                'document_id': document.id,
                'document_uuid': document.uuid,
                'fields_modified': list(changes.keys())
            }),
            activity_status='completed'
        )
        db.session.add(activity)
        db.session.flush()

        # Find previous metadata entity
        previous_entity = ProvEntity.query.filter(
            ProvEntity.entity_type == 'metadata',
            ProvEntity.entity_value['document_id'].astext == str(document.id)
        ).order_by(ProvEntity.created_at.desc()).first()

        entity = ProvEntity(
            entity_type='metadata',
            generatedattime=datetime.utcnow(),
            wasgeneratedby=activity.activity_id,
            wasattributedto=agent.agent_id,
            wasderivedfrom=previous_entity.entity_id if previous_entity else None,
            entity_value=_serialize_value({
                'document_id': document.id,
                'document_uuid': document.uuid,
                'source': 'manual_edit',
                'changes': changes,
                'updated_metadata': document.source_metadata
            })
        )
        db.session.add(entity)
        db.session.commit()

        return activity, entity

    @classmethod
    def track_metadata_field_update(
        cls,
        document,
        user,
        field_name: str,
        old_value: Any,
        new_value: Any
    ) -> tuple[ProvActivity, ProvEntity]:
        """
        Track individual metadata field update.

        Args:
            document: Document instance
            user: User making the update
            field_name: Name of the field being updated
            old_value: Previous value
            new_value: New value
        """
        agent = cls.get_or_create_user_agent(user.id, user.username)

        activity = ProvActivity(
            activity_type='metadata_field_update',
            startedattime=datetime.utcnow(),
            endedattime=datetime.utcnow(),
            wasassociatedwith=agent.agent_id,
            activity_parameters=_serialize_value({
                'document_id': document.id,
                'document_uuid': document.uuid,
                'field_name': field_name,
                'old_value': old_value,
                'new_value': new_value
            }),
            activity_status='completed'
        )
        db.session.add(activity)
        db.session.flush()

        # Find previous metadata field entity (if exists)
        previous_field_entity = ProvEntity.query.filter(
            ProvEntity.entity_type == 'metadata_field',
            ProvEntity.entity_value['document_id'].astext == str(document.id),
            ProvEntity.entity_value['field_name'].astext == field_name
        ).order_by(ProvEntity.created_at.desc()).first()

        # Create metadata field entity
        entity = ProvEntity(
            entity_type='metadata_field',
            generatedattime=datetime.utcnow(),
            wasgeneratedby=activity.activity_id,
            wasattributedto=agent.agent_id,
            wasderivedfrom=previous_field_entity.entity_id if previous_field_entity else None,
            entity_value=_serialize_value({
                'document_id': document.id,
                'document_uuid': document.uuid,
                'field_name': field_name,
                'field_value': new_value,
                'previous_value': old_value
            })
        )
        db.session.add(entity)

        # Create "used" relationship (activity used document)
        doc_entity = ProvEntity.query.filter(
            ProvEntity.entity_type == 'document',
            ProvEntity.entity_value['document_id'].astext == str(document.id)
        ).order_by(ProvEntity.created_at.desc()).first()

        if doc_entity:
            used_rel = ProvRelationship(
                relationship_type='used',
                subject_type='activity',
                subject_id=activity.activity_id,
                object_type='entity',
                object_id=doc_entity.entity_id
            )
            db.session.add(used_rel)

        db.session.commit()
        return activity, entity

    # ========================================================================
    # DOCUMENT PROCESSING TRACKING
    # ========================================================================

    @classmethod
    def track_document_segmentation(
        cls,
        document,
        user,
        method: str,
        segment_count: int,
        segments: List[Any] = None,
        tool_name: str = None,
        start_time: datetime = None,
        end_time: datetime = None
    ) -> tuple[ProvActivity, List[ProvEntity]]:
        """
        Track document segmentation into text segments.

        Args:
            document: Document instance being segmented
            user: User performing the segmentation
            method: Segmentation method (paragraph, sentence, semantic, langextract, etc.)
            segment_count: Number of segments created
            segments: Optional list of segment objects
            tool_name: Optional tool name (nltk, spacy, langextract)
            start_time: Optional start time
            end_time: Optional end time

        Returns:
            (activity, list of segment entities)
        """
        user_agent = cls.get_or_create_user_agent(user.id, user.username)

        # Get tool agent if tool_name provided
        tool_agent = None
        if tool_name:
            if tool_name == 'nltk':
                tool_agent = cls.get_or_create_nltk_agent()
            elif tool_name.startswith('spacy'):
                model = tool_name.split('_')[1] if '_' in tool_name else 'en_core_web_sm'
                tool_agent = cls.get_or_create_spacy_agent(model)
            else:
                tool_agent = cls.get_or_create_tool_agent(tool_name)

        activity = ProvActivity(
            activity_type='document_segmentation',
            startedattime=start_time or datetime.utcnow(),
            endedattime=end_time or datetime.utcnow(),
            wasassociatedwith=user_agent.agent_id,
            activity_parameters=_serialize_value({
                'document_id': document.id,
                'document_uuid': document.uuid,
                'method': method,
                'segment_count': segment_count,
                'tool_name': tool_name,
                'tool_agent_id': str(tool_agent.agent_id) if tool_agent else None
            }),
            activity_status='completed'
        )
        db.session.add(activity)
        db.session.flush()

        # Create TextSegment entities
        segment_entities = []
        if segments:
            for i, segment in enumerate(segments):
                entity = ProvEntity(
                    entity_type='text_segment',
                    generatedattime=datetime.utcnow(),
                    wasgeneratedby=activity.activity_id,
                    wasattributedto=tool_agent.agent_id if tool_agent else user_agent.agent_id,
                    entity_value=_serialize_value({
                        'document_id': document.id,
                        'document_uuid': document.uuid,
                        'segment_id': segment.id if hasattr(segment, 'id') else None,
                        'segment_number': i + 1,
                        'start_position': segment.start_position if hasattr(segment, 'start_position') else None,
                        'end_position': segment.end_position if hasattr(segment, 'end_position') else None,
                        'content_preview': segment.content[:100] if hasattr(segment, 'content') else None,
                        'method': method
                    })
                )
                db.session.add(entity)
                segment_entities.append(entity)

        # Create "used" relationship (activity used document)
        doc_entity = ProvEntity.query.filter(
            ProvEntity.entity_type == 'document',
            ProvEntity.entity_value['document_id'].astext == str(document.id)
        ).order_by(ProvEntity.created_at.desc()).first()

        if doc_entity:
            used_rel = ProvRelationship(
                relationship_type='used',
                subject_type='activity',
                subject_id=activity.activity_id,
                object_type='entity',
                object_id=doc_entity.entity_id
            )
            db.session.add(used_rel)

        db.session.commit()
        return activity, segment_entities

    @classmethod
    def track_embedding_generation(
        cls,
        document,
        user,
        model_name: str,
        segments: List[Any],
        embedding_method: str = 'local',
        dimension: int = None,
        start_time: datetime = None,
        end_time: datetime = None
    ) -> tuple[ProvActivity, List[ProvEntity]]:
        """
        Track embedding generation for document segments.

        Args:
            document: Document instance
            user: User performing the embedding
            model_name: Name of the embedding model
            segments: List of segments that were embedded
            embedding_method: Method used (local, openai, claude, period_aware)
            dimension: Embedding dimension
            start_time: Optional start time
            end_time: Optional end time

        Returns:
            (activity, list of embedding entities)
        """
        user_agent = cls.get_or_create_user_agent(user.id, user.username)

        # Get or create embedding model agent
        if 'sentence' in model_name.lower() or 'transformer' in model_name.lower():
            model_agent = cls.get_or_create_sentence_transformer_agent(model_name)
        else:
            model_agent = cls.get_or_create_tool_agent(
                model_name,
                {'tool_category': 'embedding_model', 'method': embedding_method}
            )

        activity = ProvActivity(
            activity_type='embedding_generation',
            startedattime=start_time or datetime.utcnow(),
            endedattime=end_time or datetime.utcnow(),
            wasassociatedwith=user_agent.agent_id,
            activity_parameters=_serialize_value({
                'document_id': document.id,
                'document_uuid': document.uuid,
                'model_name': model_name,
                'embedding_method': embedding_method,
                'dimension': dimension,
                'segment_count': len(segments),
                'model_agent_id': str(model_agent.agent_id)
            }),
            activity_status='completed'
        )
        db.session.add(activity)
        db.session.flush()

        # Create Embedding entities
        embedding_entities = []
        for i, segment in enumerate(segments):
            entity = ProvEntity(
                entity_type='embedding',
                generatedattime=datetime.utcnow(),
                wasgeneratedby=activity.activity_id,
                wasattributedto=model_agent.agent_id,
                entity_value=_serialize_value({
                    'document_id': document.id,
                    'document_uuid': document.uuid,
                    'segment_id': segment.id if hasattr(segment, 'id') else None,
                    'model_name': model_name,
                    'dimension': dimension,
                    'embedding_method': embedding_method
                })
            )
            db.session.add(entity)
            embedding_entities.append(entity)

            # Create derivation relationship (embedding derived from segment)
            # Find corresponding segment entity
            segment_entity = ProvEntity.query.filter(
                ProvEntity.entity_type == 'text_segment',
                ProvEntity.entity_value['segment_id'].astext == str(segment.id if hasattr(segment, 'id') else None)
            ).first()

            if segment_entity:
                entity.wasderivedfrom = segment_entity.entity_id

        db.session.commit()
        return activity, embedding_entities

    # ========================================================================
    # EXPERIMENT TRACKING
    # ========================================================================

    @classmethod
    def track_experiment_creation(cls, experiment, user) -> tuple[ProvActivity, ProvEntity]:
        """Track experiment creation."""
        agent = cls.get_or_create_user_agent(user.id, user.username)

        activity = ProvActivity(
            activity_type='experiment_creation',
            startedattime=experiment.created_at or datetime.utcnow(),
            endedattime=experiment.created_at or datetime.utcnow(),
            wasassociatedwith=agent.agent_id,
            activity_parameters=_serialize_value({
                'experiment_name': experiment.name,
                'description': experiment.description,
                'term_id': experiment.term_id
            }),
            activity_status='completed'
        )
        db.session.add(activity)
        db.session.flush()

        entity = ProvEntity(
            entity_type='experiment',
            generatedattime=experiment.created_at or datetime.utcnow(),
            wasgeneratedby=activity.activity_id,
            wasattributedto=agent.agent_id,
            entity_value=_serialize_value({
                'experiment_id': experiment.id,
                'name': experiment.name,
                'description': experiment.description,
                'term_id': experiment.term_id,
                'status': experiment.status
            })
        )
        db.session.add(entity)
        db.session.commit()

        return activity, entity

    @classmethod
    def track_processing_operation(
        cls,
        processing_type: str,
        processing_method: str,
        document,
        experiment_id: int,
        user_id: int,
        results: Dict[str, Any] = None
    ) -> tuple[ProvActivity, ProvEntity]:
        """
        Track a processing operation on a document.

        Args:
            processing_type: Type of processing (segmentation, embeddings, entities, temporal, definitions)
            processing_method: Method used (spacy, local, paragraph, sentence)
            document: Document being processed
            experiment_id: Experiment ID
            user_id: User who initiated the processing
            results: Processing results summary

        Returns:
            tuple: (activity, entity) provenance records
        """
        agent = cls.get_or_create_user_agent(user_id)
        current_time = datetime.utcnow()

        # Format activity type for display
        activity_type_name = f"{processing_type}_extraction" if processing_type in ['entities', 'temporal', 'definitions'] else processing_type

        # Build parameters
        params = {
            'processing_method': processing_method,
            'experiment_id': experiment_id,
            'document_id': document.id,
            'document_version': document.version_number if hasattr(document, 'version_number') else None
        }

        # Add results if provided
        if results:
            params.update(results)

        # Create activity
        activity = ProvActivity(
            activity_type=activity_type_name,
            startedattime=current_time,
            endedattime=current_time,
            wasassociatedwith=agent.agent_id,
            activity_parameters=_serialize_value(params),
            activity_status='completed'
        )
        db.session.add(activity)
        db.session.flush()

        # Create entity for the processed document
        entity = ProvEntity(
            entity_type='document',
            generatedattime=current_time,
            wasgeneratedby=activity.activity_id,
            wasattributedto=agent.agent_id,
            entity_value=_serialize_value({
                'document_id': document.id,
                'document_uuid': str(document.uuid) if hasattr(document, 'uuid') else None,
                'title': document.title if hasattr(document, 'title') else None,
                'version': document.version_number if hasattr(document, 'version_number') else None
            })
        )
        db.session.add(entity)
        db.session.commit()

        return activity, entity

    @classmethod
    def track_experiment_version_creation(
        cls,
        experiment_version_document,
        source_document,
        experiment,
        user
    ) -> tuple[ProvActivity, ProvEntity]:
        """
        Track creation of an experiment-specific document version.

        This implements PROV-O tracking for the one-version-per-experiment pattern.
        Creates provenance records showing:
        - Activity: create_experiment_version
        - Entity: experiment version document
        - Relationships: wasDerivedFrom (source), wasGeneratedBy (activity), wasAttributedTo (user)

        Args:
            experiment_version_document: The newly created experimental version
            source_document: The original document this derives from
            experiment: The experiment this version belongs to
            user: The user who triggered version creation

        Returns:
            tuple: (activity, entity) provenance records
        """
        agent = cls.get_or_create_user_agent(user.id, user.username)
        creation_time = datetime.utcnow()

        # Create activity for experiment version creation
        activity = ProvActivity(
            activity_type='create_experiment_version',
            startedattime=creation_time,
            endedattime=creation_time,
            wasassociatedwith=agent.agent_id,
            activity_parameters=_serialize_value({
                'document_id': experiment_version_document.id,
                'source_document_id': source_document.id,
                'source_document_uuid': str(source_document.uuid),
                'experiment_id': experiment.id,
                'experiment_name': experiment.name,
                'version_number': experiment_version_document.version_number,
                'version_type': 'experimental'
            }),
            activity_status='completed'
        )
        db.session.add(activity)
        db.session.flush()

        # Create entity for the experiment version document
        # This entity shows derivation from source document
        entity = ProvEntity(
            entity_type='document',
            generatedattime=creation_time,
            wasgeneratedby=activity.activity_id,
            wasattributedto=agent.agent_id,
            entity_value=_serialize_value({
                'document_id': experiment_version_document.id,
                'document_uuid': str(experiment_version_document.uuid),
                'title': experiment_version_document.title,
                'version_number': experiment_version_document.version_number,
                'version_type': 'experimental',
                'experiment_id': experiment.id,
                'experiment_name': experiment.name,
                'source_document_id': source_document.id,
                'source_document_uuid': str(source_document.uuid),
                'derivation': 'wasDerivedFrom'
            })
        )
        db.session.add(entity)

        # Link: experiment version wasDerivedFrom source document
        # This is recorded in entity_value as 'derivation' relationship
        # The PROV-O standard relationship is captured via source_document_id

        db.session.commit()

        logger.info(f"Tracked experiment version creation: document {experiment_version_document.id} "
                   f"v{experiment_version_document.version_number} for experiment {experiment.id}")

        return activity, entity

    # ========================================================================
    # TOOL EXECUTION TRACKING
    # ========================================================================

    @classmethod
    def track_tool_execution(
        cls,
        tool_name: str,
        document,
        user,
        experiment,
        result_data: Dict[str, Any],
        started_at: datetime = None,
        ended_at: datetime = None
    ) -> tuple[ProvActivity, ProvEntity]:
        """
        Track tool execution (segment_paragraph, extract_entities, etc.).

        Args:
            tool_name: Name of tool executed
            document: Document model instance
            user: User model instance
            experiment: Experiment model instance
            result_data: Tool execution results
            started_at: Activity start time
            ended_at: Activity end time

        Returns:
            (activity, entity) tuple
        """
        agent = cls.get_or_create_user_agent(user.id, user.username)

        activity = ProvActivity(
            activity_type='tool_execution',
            startedattime=started_at or datetime.utcnow(),
            endedattime=ended_at or datetime.utcnow(),
            wasassociatedwith=agent.agent_id,
            activity_parameters=_serialize_value({
                'tool_name': tool_name,
                'document_id': document.id,
                'experiment_id': experiment.id
            }),
            activity_status='completed'
        )
        db.session.add(activity)
        db.session.flush()

        # Find document entity
        doc_entity = ProvEntity.query.filter(
            ProvEntity.entity_type == 'document',
            ProvEntity.entity_value['document_id'].astext == str(document.id)
        ).order_by(ProvEntity.created_at.desc()).first()

        entity = ProvEntity(
            entity_type='tool_result',
            generatedattime=ended_at or datetime.utcnow(),
            wasgeneratedby=activity.activity_id,
            wasattributedto=agent.agent_id,
            wasderivedfrom=doc_entity.entity_id if doc_entity else None,
            entity_value=_serialize_value({
                'tool_name': tool_name,
                'document_id': document.id,
                'experiment_id': experiment.id,
                'status': result_data.get('status'),
                'metadata': result_data.get('metadata', {})
            })
        )
        db.session.add(entity)

        # Create "used" relationship (activity used document)
        if doc_entity:
            used_rel = ProvRelationship(
                relationship_type='used',
                subject_type='activity',
                subject_id=activity.activity_id,
                object_type='entity',
                object_id=doc_entity.entity_id
            )
            db.session.add(used_rel)

        db.session.commit()

        return activity, entity

    # ========================================================================
    # ORCHESTRATION TRACKING
    # ========================================================================

    @classmethod
    def track_orchestration_start(
        cls,
        run_id: str,
        experiment,
        user,
        parameters: Dict[str, Any] = None
    ) -> ProvActivity:
        """Track start of orchestration run."""
        agent = cls.get_or_create_user_agent(user.id, user.username)
        llm_agent = cls.get_or_create_llm_agent()

        activity = ProvActivity(
            activity_id=uuid.UUID(run_id),
            activity_type='orchestration_run',
            startedattime=datetime.utcnow(),
            wasassociatedwith=llm_agent.agent_id,
            activity_parameters=_serialize_value({
                'experiment_id': experiment.id,
                'initiated_by_user': user.id,
                'parameters': parameters or {}
            }),
            activity_status='active'
        )
        db.session.add(activity)
        db.session.commit()

        return activity

    @classmethod
    def track_orchestration_complete(
        cls,
        run_id: str,
        strategy: Dict[str, Any],
        results: Dict[str, Any] = None
    ) -> ProvEntity:
        """Track completion of orchestration run."""
        activity = ProvActivity.query.get(uuid.UUID(run_id))
        if not activity:
            raise ValueError(f"Orchestration activity {run_id} not found")

        activity.endedattime = datetime.utcnow()
        activity.activity_status = 'completed'
        activity.activity_metadata = _serialize_value(results or {})

        entity = ProvEntity(
            entity_type='processing_strategy',
            generatedattime=datetime.utcnow(),
            wasgeneratedby=activity.activity_id,
            wasattributedto=activity.wasassociatedwith,
            entity_value=_serialize_value({
                'strategy': strategy,
                'confidence': strategy.get('confidence', 0.0),
                'reasoning': strategy.get('reasoning', '')
            })
        )
        db.session.add(entity)
        db.session.commit()

        return entity

    # ========================================================================
    # SEMANTIC EVENT TRACKING
    # ========================================================================

    @classmethod
    def track_semantic_event(
        cls,
        event_type: str,
        experiment,
        user,
        event_metadata: Dict[str, Any],
        related_documents: List[Dict[str, Any]] = None,
        is_update: bool = False,
        is_deletion: bool = False
    ) -> tuple[ProvActivity, ProvEntity]:
        """
        Track semantic event creation, update, or deletion.

        Args:
            event_type: Type of semantic change event
            experiment: Experiment model instance
            user: User model instance
            event_metadata: Event metadata (type_uri, type_label, periods, etc.)
            related_documents: List of documents used as evidence
            is_update: True if updating existing event
            is_deletion: True if deleting event

        Returns:
            (activity, entity) tuple
        """
        agent = cls.get_or_create_user_agent(user.id, user.username)

        if is_deletion:
            activity_type = 'semantic_event_deletion'
        elif is_update:
            activity_type = 'semantic_event_update'
        else:
            activity_type = 'semantic_event_creation'

        activity = ProvActivity(
            activity_type=activity_type,
            startedattime=datetime.utcnow(),
            endedattime=datetime.utcnow(),
            wasassociatedwith=agent.agent_id,
            activity_parameters=_serialize_value({
                'experiment_id': experiment.id,
                'event_id': event_metadata.get('id'),
                'event_type': event_type,
                'type_uri': event_metadata.get('type_uri'),
                'type_label': event_metadata.get('type_label'),
                'from_period': event_metadata.get('from_period'),
                'to_period': event_metadata.get('to_period')
            }),
            activity_status='completed'
        )
        db.session.add(activity)
        db.session.flush()

        # Create entity for the semantic event
        entity = ProvEntity(
            entity_type='semantic_event',
            generatedattime=datetime.utcnow(),
            wasgeneratedby=activity.activity_id,
            wasattributedto=agent.agent_id,
            entity_value=_serialize_value({
                'event_id': event_metadata.get('id'),
                'event_type': event_type,
                'type_uri': event_metadata.get('type_uri'),
                'type_label': event_metadata.get('type_label'),
                'experiment_id': experiment.id
            })
        )
        db.session.add(entity)
        db.session.flush()

        # Create "used" relationships for related documents
        if related_documents and not is_deletion:
            for doc in related_documents:
                doc_uuid = doc.get('uuid')
                if doc_uuid:
                    # Find document entity
                    doc_entity = ProvEntity.query.filter(
                        ProvEntity.entity_type == 'document',
                        ProvEntity.entity_value['document_uuid'].astext == str(doc_uuid)
                    ).order_by(ProvEntity.created_at.desc()).first()

                    if doc_entity:
                        used_rel = ProvRelationship(
                            relationship_type='used',
                            subject_type='activity',
                            subject_id=activity.activity_id,
                            object_type='entity',
                            object_id=doc_entity.entity_id
                        )
                        db.session.add(used_rel)

        db.session.commit()

        return activity, entity

    # ========================================================================
    # QUERY HELPERS FOR TIMELINE UI
    # ========================================================================

    @staticmethod
    def get_timeline(
        experiment_id: int = None,
        user_id: int = None,
        activity_type: str = None,
        term_id: int = None,
        document_id: int = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Get chronological timeline of activities with entities and agents.

        Args:
            experiment_id: Filter by experiment (optional)
            user_id: Filter by user (optional)
            activity_type: Filter by activity type (optional)
            term_id: Filter by term (optional)
            document_id: Filter by document (optional)
            limit: Maximum number of activities to return

        Returns:
            List of timeline entries with full PROV-O context
        """
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
            query = query.filter(
                ProvActivity.activity_parameters['term_id'].astext == str(term_id)
            )

        if document_id:
            query = query.filter(
                ProvActivity.activity_parameters['document_id'].astext == str(document_id)
            )

        if user_id:
            # Join with agents to filter by user
            user_agent = ProvAgent.get_or_create_user_agent(user_id)
            query = query.filter(ProvActivity.wasassociatedwith == user_agent.agent_id)

        activities = query.limit(limit).all()

        # Enrich with entities and agents
        timeline = []
        for activity in activities:
            # Get generated entities
            generated = ProvEntity.query.filter_by(wasgeneratedby=activity.activity_id).all()

            # Get used entities (via relationships)
            used_rels = ProvRelationship.query.filter_by(
                relationship_type='used',
                subject_id=activity.activity_id
            ).all()
            used = [
                ProvEntity.query.get(rel.object_id)
                for rel in used_rels
            ] if used_rels else []

            # Get agent
            agent = ProvAgent.query.get(activity.wasassociatedwith)

            # Get derived-from entities for generated entities
            derived_from = []
            for entity in generated:
                if entity.wasderivedfrom:
                    source_entity = ProvEntity.query.get(entity.wasderivedfrom)
                    if source_entity:
                        derived_from.append({
                            'id': str(source_entity.entity_id),
                            'type': source_entity.entity_type,
                            'value': source_entity.entity_value,
                            'for_entity_id': str(entity.entity_id)
                        })

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
                'generated': [
                    {
                        'id': str(e.entity_id),
                        'type': e.entity_type,
                        'value': e.entity_value
                    }
                    for e in generated
                ],
                'used': [
                    {
                        'id': str(e.entity_id),
                        'type': e.entity_type,
                        'value': e.entity_value
                    }
                    for e in used if e
                ],
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


# Singleton instance
provenance_service = ProvenanceService()
