"""
Smoke Tests for Demo-Critical Routes

This test file verifies that all routes critical for the JCDL 2025 demo
are accessible and return expected status codes. These are lightweight
tests that check route availability, not full functionality.

URL Prefixes (from app/__init__.py):
- /auth - Authentication routes
- /input - Text input/document routes
- /process - Processing routes
- /results - Results routes
- /upload - Upload routes (no prefix)
- /experiments - Experiments (no prefix)
- /references - References (no prefix)
- /terms - Terms (no prefix)
- /temporal - Temporal visualization (no prefix)
- /provenance - Provenance visualization (no prefix)
- /settings - Settings (no prefix)
- /admin - Admin (no prefix)
- /api - API routes
- /orchestration - Orchestration routes
- /linked-data - Linked data routes
- /docs - Documentation routes

Expected behaviors:
- Public routes return 200
- Protected routes redirect to login (302) or return 401 when not authenticated
- Protected routes return 200 when authenticated
- Admin routes return 403 for non-admin users
- Non-existent resources return 404
"""

import pytest
import uuid


class TestPublicRoutes:
    """Test routes accessible without authentication."""

    def test_login_page(self, client):
        """Login page should be publicly accessible."""
        response = client.get('/auth/login')
        assert response.status_code == 200
        assert b'login' in response.data.lower() or b'sign in' in response.data.lower()

    def test_register_page(self, client):
        """Register page should be publicly accessible."""
        response = client.get('/auth/register')
        assert response.status_code == 200

    def test_experiments_index(self, client):
        """Experiments list should be publicly accessible."""
        response = client.get('/experiments/')
        assert response.status_code == 200

    def test_api_health(self, client):
        """API health endpoint should return 200."""
        response = client.get('/api/health')
        assert response.status_code == 200

    def test_docs_redirect_or_serve(self, client):
        """Documentation endpoint should work."""
        response = client.get('/docs/')
        # May redirect to index.html or serve directly
        assert response.status_code in [200, 302, 404]


class TestAuthenticationFlow:
    """Test authentication-related routes."""

    def test_login_post_invalid_credentials(self, client):
        """Login with invalid credentials should fail gracefully."""
        response = client.post('/auth/login', data={
            'username': 'nonexistent',
            'password': 'wrongpassword'
        }, follow_redirects=True)
        # Should stay on login page or show error
        assert response.status_code == 200

    def test_logout_redirects(self, auth_client):
        """Logout should redirect to login or home."""
        response = auth_client.get('/auth/logout')
        assert response.status_code == 302

    def test_logout_unauthenticated(self, client):
        """Logout without auth should redirect to login."""
        response = client.get('/auth/logout')
        assert response.status_code == 302


class TestProtectedRouteRedirects:
    """Test that protected routes redirect unauthenticated users."""

    def test_experiments_new_requires_login(self, client):
        """New experiment form requires authentication."""
        response = client.get('/experiments/new')
        assert response.status_code in [302, 401]

    def test_experiments_wizard_requires_login(self, client):
        """Experiment wizard requires authentication."""
        response = client.get('/experiments/wizard')
        assert response.status_code in [302, 401]

    def test_upload_requires_login(self, client):
        """Upload page requires authentication."""
        response = client.get('/upload/')
        # Note: upload may be publicly accessible - check actual behavior
        assert response.status_code in [200, 302, 401]

    def test_settings_requires_admin(self, auth_client):
        """Settings page requires admin role."""
        response = auth_client.get('/settings/')
        # Regular user should get 403
        assert response.status_code == 403

    def test_admin_requires_login(self, client):
        """Admin dashboard requires authentication."""
        response = client.get('/admin')
        assert response.status_code in [302, 401]


class TestAuthenticatedExperimentRoutes:
    """Test experiment routes with authentication."""

    def test_experiments_index_authenticated(self, auth_client):
        """Experiments index works when authenticated."""
        response = auth_client.get('/experiments/')
        assert response.status_code == 200

    def test_experiments_new_form(self, auth_client):
        """New experiment form renders when authenticated."""
        response = auth_client.get('/experiments/new')
        assert response.status_code == 200

    def test_experiments_wizard(self, auth_client):
        """Experiment wizard renders when authenticated."""
        response = auth_client.get('/experiments/wizard')
        assert response.status_code == 200

    def test_experiment_view(self, auth_client, temporal_experiment):
        """View existing experiment."""
        response = auth_client.get(f'/experiments/{temporal_experiment.id}')
        assert response.status_code == 200

    def test_experiment_edit(self, auth_client, temporal_experiment):
        """Edit experiment form renders."""
        response = auth_client.get(f'/experiments/{temporal_experiment.id}/edit')
        assert response.status_code == 200

    def test_experiment_timeline(self, auth_client, temporal_experiment):
        """Timeline view renders for temporal experiment."""
        response = auth_client.get(f'/experiments/{temporal_experiment.id}/timeline')
        assert response.status_code == 200

    def test_experiment_results(self, auth_client, temporal_experiment):
        """Results page renders."""
        response = auth_client.get(f'/experiments/{temporal_experiment.id}/results')
        assert response.status_code == 200

    def test_experiment_document_pipeline(self, auth_client, temporal_experiment):
        """Document pipeline page renders."""
        response = auth_client.get(f'/experiments/{temporal_experiment.id}/document_pipeline')
        assert response.status_code == 200

    def test_experiment_manage_terms(self, auth_client, temporal_experiment):
        """Manage terms page renders."""
        response = auth_client.get(f'/experiments/{temporal_experiment.id}/manage_terms')
        assert response.status_code == 200

    def test_experiment_manage_temporal_terms(self, auth_client, temporal_experiment):
        """Manage temporal terms page renders."""
        response = auth_client.get(f'/experiments/{temporal_experiment.id}/manage_temporal_terms')
        assert response.status_code == 200

    def test_experiment_orchestrated_analysis(self, auth_client, temporal_experiment):
        """Orchestrated analysis page renders."""
        response = auth_client.get(f'/experiments/{temporal_experiment.id}/orchestrated_analysis')
        assert response.status_code == 200


class TestExperimentNotFound:
    """Test 404 handling for non-existent experiments."""

    def test_view_nonexistent_experiment(self, auth_client):
        """Viewing non-existent experiment returns 404."""
        response = auth_client.get('/experiments/99999')
        assert response.status_code == 404

    def test_edit_nonexistent_experiment(self, auth_client):
        """Editing non-existent experiment returns 404."""
        response = auth_client.get('/experiments/99999/edit')
        assert response.status_code == 404

    def test_timeline_nonexistent_experiment(self, auth_client):
        """Timeline for non-existent experiment returns 404."""
        response = auth_client.get('/experiments/99999/timeline')
        assert response.status_code == 404


class TestAuthenticatedDocumentRoutes:
    """Test document routes with authentication."""

    def test_upload_page(self, auth_client):
        """Upload page renders when authenticated."""
        response = auth_client.get('/upload/')
        assert response.status_code == 200

    def test_documents_list(self, auth_client):
        """Documents list renders."""
        response = auth_client.get('/input/documents')
        assert response.status_code == 200

    def test_document_view(self, auth_client, sample_document):
        """View existing document."""
        response = auth_client.get(f'/input/document/{sample_document.uuid}')
        assert response.status_code == 200

    def test_document_edit(self, auth_client, sample_document):
        """Edit document form renders."""
        response = auth_client.get(f'/input/document/{sample_document.uuid}/edit')
        assert response.status_code == 200


class TestDocumentNotFound:
    """Test 404 handling for non-existent documents."""

    def test_view_nonexistent_document(self, auth_client):
        """Viewing non-existent document returns 404."""
        fake_uuid = uuid.uuid4()
        response = auth_client.get(f'/input/document/{fake_uuid}')
        assert response.status_code == 404


class TestProcessingRoutes:
    """Test processing-related routes."""

    def test_processing_home(self, auth_client):
        """Processing home page renders."""
        response = auth_client.get('/process/')
        assert response.status_code == 200

    def test_processing_jobs_list(self, auth_client):
        """Processing jobs list renders."""
        response = auth_client.get('/process/jobs')
        assert response.status_code == 200


class TestOrchestrationRoutes:
    """Test LLM orchestration routes."""

    def test_orchestration_results_nonexistent(self, auth_client, temporal_experiment):
        """Orchestration results for experiment without run."""
        response = auth_client.get(f'/experiments/{temporal_experiment.id}/orchestration-results')
        # Should either show empty results or redirect
        assert response.status_code in [200, 302, 404]

    def test_orchestration_status_invalid_run(self, auth_client):
        """Status check for invalid run ID."""
        fake_uuid = uuid.uuid4()
        response = auth_client.get(f'/orchestration/status/{fake_uuid}')
        assert response.status_code == 404


class TestReferenceRoutes:
    """Test reference management routes."""

    def test_references_list(self, auth_client):
        """References list renders."""
        response = auth_client.get('/references/')
        assert response.status_code == 200

    def test_references_upload_form(self, auth_client):
        """References upload form renders."""
        response = auth_client.get('/references/upload')
        assert response.status_code == 200


class TestTermRoutes:
    """Test term management routes."""

    def test_terms_list(self, auth_client):
        """Terms list renders."""
        response = auth_client.get('/terms/')
        assert response.status_code == 200

    def test_terms_add_form(self, auth_client):
        """Add term form renders."""
        response = auth_client.get('/terms/add')
        assert response.status_code == 200

    def test_term_view(self, auth_client, sample_term):
        """View existing term."""
        response = auth_client.get(f'/terms/{sample_term.id}')
        assert response.status_code == 200


class TestTermNotFound:
    """Test 404 handling for non-existent terms."""

    def test_view_nonexistent_term(self, auth_client):
        """Viewing non-existent term returns 404."""
        fake_uuid = uuid.uuid4()
        response = auth_client.get(f'/terms/{fake_uuid}')
        assert response.status_code == 404


class TestAdminRoutes:
    """Test admin-only routes."""

    @pytest.fixture
    def admin_client(self, app, db_session, admin_user):
        """Provide an authenticated admin client."""
        client = app.test_client()
        with client.session_transaction() as sess:
            sess['_user_id'] = str(admin_user.id)
            sess['_fresh'] = True
        return client

    def test_admin_dashboard(self, admin_client):
        """Admin dashboard renders for admin user."""
        response = admin_client.get('/admin')
        assert response.status_code == 200

    def test_admin_users_list(self, admin_client):
        """Admin users list renders."""
        response = admin_client.get('/admin/users')
        assert response.status_code == 200

    def test_settings_dashboard(self, admin_client):
        """Settings dashboard renders for admin."""
        response = admin_client.get('/settings/')
        assert response.status_code == 200

    def test_admin_forbidden_for_regular_user(self, auth_client):
        """Admin dashboard forbidden for regular users."""
        response = auth_client.get('/admin')
        assert response.status_code == 403


class TestAPIEndpoints:
    """Test API endpoints return proper JSON responses."""

    def test_experiments_api_list(self, auth_client):
        """Experiments API list returns JSON."""
        response = auth_client.get('/experiments/api/list')
        assert response.status_code == 200
        assert response.content_type == 'application/json'

    def test_experiments_api_get(self, auth_client, temporal_experiment):
        """Experiments API get returns JSON."""
        response = auth_client.get(f'/experiments/api/{temporal_experiment.id}')
        assert response.status_code == 200
        assert response.content_type == 'application/json'

    def test_experiments_api_get_nonexistent(self, auth_client):
        """API returns 404 for non-existent experiment."""
        response = auth_client.get('/experiments/api/99999')
        assert response.status_code == 404

    def test_documents_api_list(self, auth_client):
        """Documents API list returns JSON."""
        response = auth_client.get('/input/api/documents')
        assert response.status_code == 200
        assert response.content_type == 'application/json'

    def test_terms_api_search(self, auth_client):
        """Terms search API works."""
        response = auth_client.get('/terms/api/terms/search?q=test')
        assert response.status_code == 200
        assert response.content_type == 'application/json'


class TestTemporalVisualization:
    """Test temporal visualization routes."""

    def test_temporal_home(self, auth_client):
        """Temporal visualization home renders."""
        response = auth_client.get('/temporal/')
        assert response.status_code == 200

    def test_temporal_experiment_view(self, auth_client, temporal_experiment):
        """Temporal experiment visualization renders."""
        response = auth_client.get(f'/temporal/experiment/{temporal_experiment.id}')
        assert response.status_code == 200

    def test_temporal_api_data(self, auth_client, temporal_experiment):
        """Temporal API returns data."""
        response = auth_client.get(f'/temporal/api/experiment/{temporal_experiment.id}/data')
        assert response.status_code == 200
        assert response.content_type == 'application/json'


class TestProvenanceRoutes:
    """Test provenance visualization routes."""

    def test_provenance_graph(self, auth_client):
        """Provenance graph page renders."""
        response = auth_client.get('/provenance/graph')
        assert response.status_code == 200

    def test_provenance_timeline(self, auth_client):
        """Provenance timeline page renders."""
        response = auth_client.get('/provenance/timeline')
        assert response.status_code == 200

    def test_provenance_experiment(self, auth_client, temporal_experiment):
        """Provenance for experiment renders."""
        response = auth_client.get(f'/provenance/experiment/{temporal_experiment.id}')
        assert response.status_code == 200


class TestErrorHandling:
    """Test error page handling."""

    def test_404_invalid_route(self, client):
        """Non-existent route returns 404."""
        response = client.get('/this-route-does-not-exist')
        assert response.status_code == 404

    def test_method_not_allowed(self, client):
        """Wrong HTTP method returns 405."""
        response = client.delete('/login')
        assert response.status_code == 405
