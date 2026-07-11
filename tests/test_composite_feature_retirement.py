"""Regression coverage for retiring obsolete composite-document workflows."""


def test_composite_routes_are_not_registered(app):
    endpoints = set(app.view_functions)
    assert 'text_input.create_composite' not in endpoints
    assert 'text_input.get_composite_sources' not in endpoints
    assert 'text_input.update_composite' not in endpoints
    assert not any('/composite/' in str(rule) for rule in app.url_map.iter_rules())


def test_active_text_input_routes_remain_registered(app):
    for endpoint in (
        'text_input.document_list',
        'text_input.document_detail',
        'text_input.submit_text',
        'text_input.upload_file',
        'text_input.apply_embeddings',
    ):
        assert endpoint in app.view_functions


def test_legacy_composite_columns_and_read_helpers_remain_available(
    db_session, test_user, sample_document
):
    from app.models.document import Document

    historical = Document(
        title='Historical composite',
        content='Historical combined content.',
        content_type='text',
        document_type='document',
        status='completed',
        user_id=test_user.id,
        source_document_id=sample_document.id,
        version_number=2,
        version_type='composite',
        composite_sources=[sample_document.id],
        composite_metadata={'creation_method': 'legacy'},
    )
    db_session.add(historical)
    db_session.commit()

    assert historical.is_composite() is True
    assert historical.get_composite_sources() == [sample_document]
    assert historical.get_version_display_name().endswith('(composite)')


def test_inheritance_versioning_remains_canonical(app):
    assert 'processing.segment_document' in app.view_functions
    assert 'text_input.document_detail' in app.view_functions