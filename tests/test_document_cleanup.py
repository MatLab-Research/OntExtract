"""
Tests for LLM Text Cleanup and Versioning Workflow

These tests verify:
- Cleaned version creation with correct version_type
- Multiple cleaned versions increment version numbers
- Experiment versions prefer cleaned versions when available
- Processing metadata tracks derivation source correctly
"""

import pytest
from app import db
from app.models.document import Document
from app.models.experiment import Experiment
from app.models.experiment_document import ExperimentDocument
from app.services.inheritance_versioning_service import InheritanceVersioningService


class TestCleanedVersionCreation:
    """Tests for creating cleaned document versions."""

    def test_create_cleaned_version_has_correct_type(self, db_session, sample_document):
        """Cleaned version should have version_type='cleaned' and link to root."""
        # Create a cleaned version using the versioning service
        cleaned = InheritanceVersioningService.create_new_version(
            original_document=sample_document,
            processing_type='text_cleanup',
            processing_metadata={'cleanup_method': 'llm_claude'}
        )
        # Manually set version_type as the route does
        cleaned.version_type = 'cleaned'
        cleaned.content = "This is cleaned content."
        db_session.commit()

        assert cleaned.version_type == 'cleaned'
        assert cleaned.source_document_id == sample_document.id
        assert cleaned.version_number == 2

    def test_cleaned_version_content_differs(self, db_session, sample_document):
        """Cleaned version content should be the cleaned text, not original."""
        original_content = sample_document.content
        cleaned_content = "This is the cleaned version of the content."

        cleaned = InheritanceVersioningService.create_new_version(
            original_document=sample_document,
            processing_type='text_cleanup',
            processing_metadata={'cleanup_method': 'llm_claude'}
        )
        cleaned.version_type = 'cleaned'
        cleaned.content = cleaned_content
        db_session.commit()

        assert cleaned.content == cleaned_content
        assert cleaned.content != original_content

    def test_multiple_cleaned_versions_increment(self, db_session, sample_document):
        """Re-cleaning should create v3, v4, etc., not replace."""
        # Create first cleaned version (v2)
        cleaned1 = InheritanceVersioningService.create_new_version(
            original_document=sample_document,
            processing_type='text_cleanup',
            processing_metadata={'cleanup_method': 'llm_claude'}
        )
        cleaned1.version_type = 'cleaned'
        cleaned1.content = "First cleanup result."
        db_session.commit()

        # Create second cleaned version (v3)
        cleaned2 = InheritanceVersioningService.create_new_version(
            original_document=sample_document,
            processing_type='text_cleanup',
            processing_metadata={'cleanup_method': 'llm_claude'}
        )
        cleaned2.version_type = 'cleaned'
        cleaned2.content = "Second cleanup result."
        db_session.commit()

        assert cleaned1.version_number == 2
        assert cleaned2.version_number == 3
        assert cleaned1.id != cleaned2.id

    def test_cleaned_version_preserves_metadata(self, db_session, sample_document):
        """Bibliographic metadata should copy from source."""
        # Set some metadata on original
        sample_document.source_metadata = {
            'title': 'Test Title',
            'authors': 'Test Author'
        }
        db_session.commit()

        cleaned = InheritanceVersioningService.create_new_version(
            original_document=sample_document,
            processing_type='text_cleanup',
            processing_metadata={'cleanup_method': 'llm_claude'}
        )
        cleaned.version_type = 'cleaned'
        db_session.commit()

        assert cleaned.source_metadata == sample_document.source_metadata


class TestExperimentVersionSource:
    """Tests for experiment version creation with cleaned version preference."""

    def test_experiment_uses_cleaned_version_content(self, db_session, sample_document,
                                                      temporal_experiment, test_user):
        """When cleaned version exists, experimental version should use its content."""
        original_content = sample_document.content
        cleaned_content = "This is the cleaned version."

        # Create cleaned version
        cleaned = InheritanceVersioningService.create_new_version(
            original_document=sample_document,
            processing_type='text_cleanup',
            processing_metadata={'cleanup_method': 'llm_claude'}
        )
        cleaned.version_type = 'cleaned'
        cleaned.content = cleaned_content
        db_session.commit()

        # Create experimental version (should use cleaned content)
        exp_version, created = InheritanceVersioningService.get_or_create_experiment_version(
            sample_document, temporal_experiment.id, test_user
        )

        assert created is True
        assert exp_version.content == cleaned_content
        assert exp_version.content != original_content

    def test_experiment_falls_back_to_original(self, db_session, sample_document,
                                               temporal_experiment, test_user):
        """When no cleaned version, experimental version uses original content."""
        original_content = sample_document.content

        # No cleaned version exists
        exp_version, created = InheritanceVersioningService.get_or_create_experiment_version(
            sample_document, temporal_experiment.id, test_user
        )

        assert created is True
        assert exp_version.content == original_content

    def test_experiment_tracks_derivation_source_cleaned(self, db_session, sample_document,
                                                         temporal_experiment, test_user):
        """processing_metadata should record derived_from when using cleaned version."""
        # Create cleaned version
        cleaned = InheritanceVersioningService.create_new_version(
            original_document=sample_document,
            processing_type='text_cleanup',
            processing_metadata={'cleanup_method': 'llm_claude'}
        )
        cleaned.version_type = 'cleaned'
        cleaned.content = "Cleaned content."
        db_session.commit()

        # Create experimental version
        exp_version, _ = InheritanceVersioningService.get_or_create_experiment_version(
            sample_document, temporal_experiment.id, test_user
        )

        assert exp_version.processing_metadata is not None
        assert 'derived_from' in exp_version.processing_metadata
        derived = exp_version.processing_metadata['derived_from']
        assert derived['source_version_type'] == 'cleaned'
        assert derived['source_version_id'] == cleaned.id
        assert derived['source_version_number'] == cleaned.version_number

    def test_experiment_tracks_derivation_source_original(self, db_session, sample_document,
                                                          temporal_experiment, test_user):
        """processing_metadata should record derived_from when using original."""
        # No cleaned version, create experimental directly
        exp_version, _ = InheritanceVersioningService.get_or_create_experiment_version(
            sample_document, temporal_experiment.id, test_user
        )

        assert exp_version.processing_metadata is not None
        assert 'derived_from' in exp_version.processing_metadata
        derived = exp_version.processing_metadata['derived_from']
        assert derived['source_version_type'] == 'original'
        assert derived['source_version_id'] == sample_document.id

    def test_existing_experiment_not_updated_after_cleanup(self, db_session, sample_document,
                                                           temporal_experiment, test_user):
        """Cleaning source after experiment created should not change experimental version."""
        original_content = sample_document.content

        # Create experimental version FIRST (before cleanup)
        exp_version, _ = InheritanceVersioningService.get_or_create_experiment_version(
            sample_document, temporal_experiment.id, test_user
        )
        exp_version_id = exp_version.id
        exp_content = exp_version.content

        # Now create cleaned version
        cleaned = InheritanceVersioningService.create_new_version(
            original_document=sample_document,
            processing_type='text_cleanup',
            processing_metadata={'cleanup_method': 'llm_claude'}
        )
        cleaned.version_type = 'cleaned'
        cleaned.content = "Late cleanup content."
        db_session.commit()

        # Re-fetch experimental version
        exp_version_after = Document.query.get(exp_version_id)

        # Should still have original content (not cleaned)
        assert exp_version_after.content == exp_content
        assert exp_version_after.content == original_content

    def test_new_experiment_uses_latest_cleaned(self, db_session, sample_document, test_user):
        """New experiment created AFTER cleanup should use cleaned version content."""
        # Create cleaned version first
        cleaned = InheritanceVersioningService.create_new_version(
            original_document=sample_document,
            processing_type='text_cleanup',
            processing_metadata={'cleanup_method': 'llm_claude'}
        )
        cleaned.version_type = 'cleaned'
        cleaned.content = "This is cleaned content for new experiments."
        db_session.commit()

        # Create a new experiment
        new_experiment = Experiment(
            name='New Experiment After Cleanup',
            description='Test experiment created after cleanup',
            experiment_type='entity_extraction',
            user_id=test_user.id,
            status='draft'
        )
        db_session.add(new_experiment)
        db_session.commit()

        # Add document to new experiment
        exp_version, created = InheritanceVersioningService.get_or_create_experiment_version(
            sample_document, new_experiment.id, test_user
        )

        assert created is True
        assert exp_version.content == cleaned.content

    def test_experiment_uses_latest_of_multiple_cleaned(self, db_session, sample_document,
                                                        temporal_experiment, test_user):
        """When multiple cleaned versions exist, use the most recent one."""
        # Create first cleaned version
        cleaned1 = InheritanceVersioningService.create_new_version(
            original_document=sample_document,
            processing_type='text_cleanup',
            processing_metadata={'cleanup_method': 'llm_claude'}
        )
        cleaned1.version_type = 'cleaned'
        cleaned1.content = "First cleanup."
        db_session.commit()

        # Create second cleaned version
        cleaned2 = InheritanceVersioningService.create_new_version(
            original_document=sample_document,
            processing_type='text_cleanup',
            processing_metadata={'cleanup_method': 'llm_claude'}
        )
        cleaned2.version_type = 'cleaned'
        cleaned2.content = "Second cleanup - latest."
        db_session.commit()

        # Create experimental version (should use latest cleaned)
        exp_version, _ = InheritanceVersioningService.get_or_create_experiment_version(
            sample_document, temporal_experiment.id, test_user
        )

        assert exp_version.content == cleaned2.content


class TestVersionFamily:
    """Tests for version family relationships with cleaned versions."""

    def test_cleaned_version_in_family(self, db_session, sample_document):
        """Cleaned versions should appear in get_all_versions()."""
        cleaned = InheritanceVersioningService.create_new_version(
            original_document=sample_document,
            processing_type='text_cleanup',
            processing_metadata={'cleanup_method': 'llm_claude'}
        )
        cleaned.version_type = 'cleaned'
        db_session.commit()

        all_versions = sample_document.get_all_versions()
        version_types = [v.version_type for v in all_versions]

        assert 'cleaned' in version_types
        assert len(all_versions) == 2

    def test_get_root_from_cleaned_version(self, db_session, sample_document):
        """get_root_document() from cleaned version should return original."""
        cleaned = InheritanceVersioningService.create_new_version(
            original_document=sample_document,
            processing_type='text_cleanup',
            processing_metadata={'cleanup_method': 'llm_claude'}
        )
        cleaned.version_type = 'cleaned'
        db_session.commit()

        root = cleaned.get_root_document()
        assert root.id == sample_document.id
