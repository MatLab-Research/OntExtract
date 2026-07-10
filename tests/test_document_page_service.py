"""Regression coverage for document family list and detail page read models."""

from datetime import datetime, timedelta


def _document(db_session, user, title, **kwargs):
    from app.models.document import Document

    document = Document(
        title=title,
        content=f'Content for {title}.',
        content_type='text',
        document_type=kwargs.pop('document_type', 'document'),
        status='completed',
        user_id=user.id,
        **kwargs,
    )
    db_session.add(document)
    db_session.commit()
    return document


def _experiment(db_session, user, suffix):
    from app.models.experiment import Experiment

    experiment = Experiment(
        name=f'Document Page Experiment {suffix}',
        experiment_type='temporal_evolution',
        user_id=user.id,
        status='draft',
    )
    db_session.add(experiment)
    db_session.commit()
    return experiment


def _association(db_session, experiment, document):
    from app.models.experiment_document import ExperimentDocument

    association = ExperimentDocument(
        experiment_id=experiment.id,
        document_id=document.id,
    )
    db_session.add(association)
    db_session.commit()
    return association


def _processing_index(
    db_session,
    association,
    document,
    processing_type,
    method,
):
    from app.models.experiment_processing import (
        DocumentProcessingIndex,
        ExperimentDocumentProcessing,
    )

    processing = ExperimentDocumentProcessing(
        experiment_document_id=association.id,
        processing_type=processing_type,
        processing_method=method,
        status='completed',
    )
    db_session.add(processing)
    db_session.flush()
    index = DocumentProcessingIndex(
        document_id=document.id,
        experiment_id=association.experiment_id,
        processing_id=processing.id,
        processing_type=processing_type,
        processing_method=method,
        status='completed',
    )
    db_session.add(index)
    db_session.commit()
    return index


def test_document_page_routes_remain_canonical(app):
    expected = 'app.routes.text_input.crud.pages'
    assert app.view_functions['text_input.document_list'].__module__ == expected
    assert app.view_functions['text_input.document_detail'].__module__ == expected


def test_list_groups_versions_and_selects_latest(
    db_session, test_user
):
    from app.services.document_page_service import DocumentPageService

    root = _document(
        db_session,
        test_user,
        'Root document',
        version_number=1,
        version_type='original',
        created_at=datetime(2026, 1, 1),
    )
    version_two = _document(
        db_session,
        test_user,
        'Processed v2',
        source_document_id=root.id,
        version_number=2,
        version_type='processed',
        created_at=datetime(2026, 1, 2),
    )
    version_three = _document(
        db_session,
        test_user,
        'Cleaned v3',
        source_document_id=root.id,
        version_number=3,
        version_type='cleaned',
        created_at=datetime(2026, 1, 3),
    )

    context = DocumentPageService.get_list_context()
    group = next(
        item for item in context['documents'].items
        if item.base_document.id == root.id
    )
    assert group.latest_version is version_three
    assert group.versions == [version_three, version_two, root]
    assert group.latest_created == datetime(2026, 1, 3)


def test_list_filters_source_type_and_normalizes_invalid_filter(
    db_session, test_user
):
    from app.services.document_page_service import DocumentPageService

    document = _document(db_session, test_user, 'Document source')
    reference = _document(
        db_session,
        test_user,
        'Reference source',
        document_type='reference',
    )

    documents = DocumentPageService.get_list_context(source_type='document')
    references = DocumentPageService.get_list_context(source_type='reference')
    invalid = DocumentPageService.get_list_context(
        page=-4,
        source_type='invalid',
    )

    assert all(
        group.latest_version.document_type == 'document'
        for group in documents['documents'].items
    )
    assert any(
        group.base_document.id == document.id
        for group in documents['documents'].items
    )
    assert all(
        group.latest_version.document_type == 'reference'
        for group in references['documents'].items
    )
    assert any(
        group.base_document.id == reference.id
        for group in references['documents'].items
    )
    assert invalid['source_type'] == 'all'
    assert invalid['documents'].page == 1


def test_list_paginates_document_families_not_versions(
    db_session, test_user
):
    from app.services.document_page_service import DocumentPageService

    roots = []
    base_time = datetime(2026, 1, 1)
    for index in range(11):
        root = _document(
            db_session,
            test_user,
            f'Pagination root {index}',
            created_at=base_time + timedelta(days=index),
        )
        roots.append(root)
    _document(
        db_session,
        test_user,
        'Version of newest root',
        source_document_id=roots[-1].id,
        version_number=2,
        version_type='processed',
        created_at=base_time + timedelta(days=20),
    )

    first = DocumentPageService.get_list_context(page=1, per_page=10)
    second = DocumentPageService.get_list_context(page=2, per_page=10)

    assert first['documents'].total >= 11
    assert len(first['documents'].items) == 10
    assert first['documents'].has_next is True
    assert second['documents'].has_prev is True
    assert first['documents'].items[0].base_document.id == roots[-1].id
    assert len(first['documents'].items[0].versions) == 2


def test_detail_context_scopes_current_and_family_processing(
    db_session, test_user
):
    from app.models.processing_artifact_group import ProcessingArtifactGroup
    from app.services.document_page_service import DocumentPageService

    root = _document(
        db_session,
        test_user,
        'Detail root',
        version_number=1,
        version_type='original',
    )
    derived = _document(
        db_session,
        test_user,
        'Detail derived',
        source_document_id=root.id,
        version_number=2,
        version_type='processed',
    )
    root_experiment = _experiment(db_session, test_user, 'root')
    derived_experiment = _experiment(db_session, test_user, 'derived')
    root_link = _association(db_session, root_experiment, root)
    derived_link = _association(db_session, derived_experiment, derived)
    _processing_index(
        db_session,
        root_link,
        root,
        'segmentation',
        'paragraph',
    )
    _processing_index(
        db_session,
        derived_link,
        derived,
        'entities',
        'spacy',
    )
    db_session.add(ProcessingArtifactGroup(
        document_id=derived.id,
        artifact_type='embeddings',
        method_key='local-mini-lm',
        status='completed',
    ))
    db_session.commit()

    context = DocumentPageService.get_detail_context(derived.uuid)

    assert context['document'] is derived
    assert context['version_family'] == [root, derived]
    assert context['is_latest_version'] is True
    assert len(context['this_version_experiments']) == 1
    assert context['this_version_experiments'][0]['experiment'] is derived_experiment
    assert context['this_version_experiments'][0]['processing_results'] == [{
        'processing_type': 'entities',
        'processing_method': 'spacy',
        'status': 'completed',
    }]
    assert len(context['all_version_experiments']) == 2
    assert context['total_processing_count'] == 2


def test_detail_uses_latest_temporal_metadata(
    db_session, test_user
):
    from app.models.temporal_experiment import DocumentTemporalMetadata
    from app.services.document_page_service import DocumentPageService

    document = _document(db_session, test_user, 'Temporal metadata')
    first_experiment = _experiment(db_session, test_user, 'metadata-first')
    second_experiment = _experiment(db_session, test_user, 'metadata-second')
    older = DocumentTemporalMetadata(
        document_id=document.id,
        experiment_id=first_experiment.id,
        publication_year=1990,
        created_at=datetime(2026, 1, 1),
    )
    newer = DocumentTemporalMetadata(
        document_id=document.id,
        experiment_id=second_experiment.id,
        publication_year=2000,
        created_at=datetime(2026, 1, 2),
    )
    db_session.add_all([older, newer])
    db_session.commit()

    context = DocumentPageService.get_detail_context(document.uuid)
    assert context['temporal_metadata'] is newer


def test_document_pages_are_public_and_preserve_filters(
    client, db_session, test_user
):
    document = _document(db_session, test_user, 'Public detail')

    listing = client.get('/input/documents?type=document')
    detail = client.get(f'/input/document/{document.uuid}')
    invalid = client.get('/input/document/00000000-0000-0000-0000-000000000001')

    assert listing.status_code == 200
    assert b'Public detail' in listing.data
    assert detail.status_code == 200
    assert b'Public detail' in detail.data
    assert invalid.status_code == 404
