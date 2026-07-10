"""Regression coverage for modular text-input CRUD routes."""


def test_text_input_crud_routes_are_grouped_by_responsibility(app):
    expected_modules = {
        "text_input.document_list": "app.routes.text_input.crud.pages",
        "text_input.document_detail": "app.routes.text_input.crud.pages",
        "text_input.document_edit": "app.routes.text_input.crud.editing",
        "text_input.delete_document": "app.routes.text_input.crud.deletion",
        "text_input.delete_document_by_uuid": "app.routes.text_input.crud.deletion",
        "text_input.delete_all_versions": "app.routes.text_input.crud.deletion",
        "text_input.delete_all_documents": "app.routes.text_input.crud.deletion",
    }

    actual_modules = {
        endpoint: app.view_functions[endpoint].__module__
        for endpoint in expected_modules
    }

    assert actual_modules == expected_modules