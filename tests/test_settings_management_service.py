"""Regression coverage for administrator-only settings management."""

import pytest


def _template(db_session, suffix='test'):
    from app.models.prompt_template import PromptTemplate

    template = PromptTemplate(
        template_key=f'settings-template-{suffix}',
        template_text='Hello {{ name }}',
        category='test',
        variables={'name': 'string'},
        supports_llm_enhancement=True,
        is_active=True,
    )
    db_session.add(template)
    db_session.commit()
    return template


def test_settings_routes_remain_canonical(app):
    expected = 'app.routes.settings'
    for endpoint in (
        'settings.index',
        'settings.update_setting',
        'settings.get_template',
        'settings.update_template',
        'settings.test_template',
        'settings.reset_category',
        'settings.test_llm_connection',
    ):
        assert app.view_functions[endpoint].__module__ == expected


def test_dashboard_context_merges_user_settings_and_templates(
    db_session, admin_user, monkeypatch
):
    from app.models.app_settings import AppSetting
    from app.services.settings_management_service import SettingsManagementService

    AppSetting.set_setting('llm_model', 'system-model', 'llm', user_id=None)
    AppSetting.set_setting(
        'llm_model',
        'user-model',
        'llm',
        user_id=admin_user.id,
    )
    template = _template(db_session, 'dashboard')
    monkeypatch.setenv('ANTHROPIC_API_KEY', 'test-key')

    context = SettingsManagementService.dashboard_context(
        admin_user.id,
        'prompts',
    )

    assert context['settings']['llm']['llm_model'] == 'user-model'
    assert template in context['templates']
    assert context['active_tab'] == 'prompts'
    assert context['api_key_available'] is True


@pytest.mark.parametrize(
    ('data_type', 'value', 'expected'),
    [
        ('integer', '200', 200),
        ('integer', 0.7, 0.7),
        ('float', '0.75', 0.75),
        ('boolean', 'false', False),
        ('boolean', 'true', True),
        ('json', '{"enabled": true}', {'enabled': True}),
        ('string', 'local', 'local'),
    ],
)
def test_update_setting_converts_values(
    db_session, admin_user, data_type, value, expected
):
    from app.models.app_settings import AppSetting
    from app.services.settings_management_service import SettingsManagementService

    key = f'conversion-{data_type}-{str(value)}'
    result = SettingsManagementService.update_setting(
        {
            'setting_key': key,
            'setting_value': value,
            'category': 'test',
            'data_type': data_type,
            'user_specific': True,
        },
        admin_user.id,
    )

    setting = AppSetting.query.filter_by(
        setting_key=key,
        user_id=admin_user.id,
    ).one()
    assert setting.setting_value == expected
    assert result['setting_value'] == expected


def test_update_setting_respects_user_and_system_scope(
    admin_user,
):
    from app.models.app_settings import AppSetting
    from app.services.settings_management_service import SettingsManagementService

    SettingsManagementService.update_setting(
        {
            'setting_key': 'scope-setting',
            'setting_value': 'system',
            'category': 'test',
            'user_specific': False,
        },
        admin_user.id,
    )
    SettingsManagementService.update_setting(
        {
            'setting_key': 'scope-setting',
            'setting_value': 'user',
            'category': 'test',
            'user_specific': True,
        },
        admin_user.id,
    )

    assert AppSetting.query.filter_by(
        setting_key='scope-setting', user_id=None
    ).one().setting_value == 'system'
    assert AppSetting.query.filter_by(
        setting_key='scope-setting', user_id=admin_user.id
    ).one().setting_value == 'user'


@pytest.mark.parametrize(
    ('payload', 'message'),
    [
        (None, 'Setting key and value required'),
        ({'setting_key': 'missing-value'}, 'Setting key and value required'),
        (
            {
                'setting_key': 'bad-bool',
                'setting_value': 'perhaps',
                'category': 'test',
                'data_type': 'boolean',
            },
            'Invalid boolean value',
        ),
    ],
)
def test_setting_validation(admin_user, payload, message):
    from app.services.base_service import ValidationError
    from app.services.settings_management_service import SettingsManagementService

    with pytest.raises(ValidationError, match=message):
        SettingsManagementService.update_setting(payload, admin_user.id)


def test_template_update_and_get(db_session):
    from app.services.settings_management_service import SettingsManagementService

    template = _template(db_session, 'update')
    result = SettingsManagementService.update_template(template.id, {
        'template_text': 'Welcome {{ name }}',
        'supports_llm_enhancement': 'false',
        'llm_enhancement_prompt': 'Enhance {{ template_output }}',
    })
    details = SettingsManagementService.get_template(template.id)

    assert result['success'] is True
    assert details['template_text'] == 'Welcome {{ name }}'
    assert details['supports_llm_enhancement'] is False
    assert details['llm_enhancement_prompt'] == 'Enhance {{ template_output }}'


def test_invalid_template_syntax_does_not_mutate_template(db_session):
    from app.services.base_service import ValidationError
    from app.services.settings_management_service import SettingsManagementService

    template = _template(db_session, 'invalid')
    original = template.template_text

    with pytest.raises(ValidationError, match='Invalid template syntax'):
        SettingsManagementService.update_template(
            template.id,
            {'template_text': 'Broken {{ name'},
        )

    assert template.template_text == original


def test_template_test_maps_missing_variables(db_session):
    from app.services.base_service import ValidationError
    from app.services.settings_management_service import SettingsManagementService

    template = _template(db_session, 'render')
    assert SettingsManagementService.test_template(
        template.id,
        {'context': {'name': 'OntExtract'}},
    )['result'] == 'Hello OntExtract'

    with pytest.raises(ValidationError, match='Missing variables'):
        SettingsManagementService.test_template(template.id, {'context': {}})


def test_reset_category_deletes_only_current_user_settings(
    db_session, admin_user, test_user
):
    from app.models.app_settings import AppSetting
    from app.services.settings_management_service import SettingsManagementService

    for user_id, value in (
        (None, 'system'),
        (admin_user.id, 'admin'),
        (test_user.id, 'other'),
    ):
        AppSetting.set_setting(
            'reset-scope', value, 'reset-test', user_id=user_id
        )

    SettingsManagementService.reset_category('reset-test', admin_user.id)

    assert AppSetting.query.filter_by(
        category='reset-test', user_id=admin_user.id
    ).count() == 0
    assert AppSetting.query.filter_by(
        category='reset-test', user_id=None
    ).count() == 1
    assert AppSetting.query.filter_by(
        category='reset-test', user_id=test_user.id
    ).count() == 1


def test_llm_connection_uses_selected_provider(admin_user):
    from app.services.settings_management_service import SettingsManagementService

    class FakePromptService:
        calls = []

        @staticmethod
        def _get_api_key(provider, user):
            return f'{provider}-key'

        @classmethod
        def _call_anthropic(cls, prompt, model, key):
            cls.calls.append(('anthropic', model, key))
            return 'anthropic response'

        @classmethod
        def _call_openai(cls, prompt, model, key):
            cls.calls.append(('openai', model, key))
            return 'openai response'

    service = SettingsManagementService(FakePromptService)
    anthropic = service.test_llm_connection('anthropic', admin_user)
    openai = service.test_llm_connection('openai', admin_user)

    assert anthropic['response'] == 'anthropic response'
    assert openai['response'] == 'openai response'
    assert FakePromptService.calls == [
        ('anthropic', 'claude-sonnet-4-5-20250929', 'anthropic-key'),
        ('openai', 'gpt-4', 'openai-key'),
    ]


def test_settings_routes_require_admin_for_reads_and_writes(
    auth_client,
):
    responses = [
        auth_client.get('/settings/'),
        auth_client.post('/settings/update', json={}),
        auth_client.get('/settings/template/1'),
        auth_client.put('/settings/template/1', json={}),
        auth_client.post('/settings/template/1/test', json={}),
        auth_client.post('/settings/reset/llm'),
        auth_client.post('/settings/test-llm-connection', json={}),
    ]

    assert all(response.status_code == 403 for response in responses)


def test_settings_routes_return_expected_json_contracts(
    admin_client, db_session
):
    template = _template(db_session, 'routes')
    update = admin_client.post('/settings/update', json={
        'setting_key': 'route-setting',
        'setting_value': 'false',
        'category': 'test',
        'data_type': 'boolean',
        'user_specific': True,
    })
    details = admin_client.get(f'/settings/template/{template.id}')
    tested = admin_client.post(
        f'/settings/template/{template.id}/test',
        json={'context': {'name': 'Route'}},
    )
    missing = admin_client.get('/settings/template/999999')

    assert update.status_code == 200
    assert update.get_json()['setting_value'] is False
    assert details.status_code == 200
    assert details.get_json()['template_key'] == template.template_key
    assert tested.get_json()['result'] == 'Hello Route'
    assert missing.status_code == 404
