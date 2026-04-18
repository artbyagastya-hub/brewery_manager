"""
Tests for Flask web routes
"""
import pytest
from web.app import app


@pytest.fixture
def client():
    """Create test client"""
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False
    with app.test_client() as client:
        yield client


@pytest.fixture
def authenticated_client(client):
    """Create authenticated test client"""
    with client.session_transaction() as sess:
        sess['user_id'] = 1
        sess['username'] = 'admin'
        sess['role'] = 'admin'
    return client


class TestPublicRoutes:
    """Test public routes that don't require authentication"""

    def test_login_page(self, client):
        """Test login page loads"""
        response = client.get('/login')
        assert response.status_code == 200

    def test_login_post_invalid(self, client):
        """Test login with invalid credentials"""
        response = client.post('/login', data={
            'username': 'invalid',
            'password': 'invalid'
        }, follow_redirects=True)
        # Should redirect back to login page after failed attempt
        assert response.status_code == 200


class TestAuthenticatedRoutes:
    """Test routes that require authentication"""

    def test_dashboard(self, authenticated_client):
        """Test dashboard loads"""
        response = authenticated_client.get('/')
        assert response.status_code == 200

    def test_products_page(self, authenticated_client):
        """Test products page loads"""
        response = authenticated_client.get('/products')
        assert response.status_code == 200

    def test_customers_page(self, authenticated_client):
        """Test customers page loads"""
        response = authenticated_client.get('/customers')
        assert response.status_code == 200

    def test_inventory_page(self, authenticated_client):
        """Test inventory page loads"""
        response = authenticated_client.get('/inventory')
        assert response.status_code == 200

    def test_production_page(self, authenticated_client):
        """Test production page loads"""
        response = authenticated_client.get('/production')
        assert response.status_code == 200

    def test_quality_page(self, authenticated_client):
        """Test quality page loads"""
        response = authenticated_client.get('/quality')
        assert response.status_code == 200

    def test_finance_page(self, authenticated_client):
        """Test finance page loads"""
        response = authenticated_client.get('/finance')
        assert response.status_code == 200

    def test_staff_page(self, authenticated_client):
        """Test staff page loads"""
        response = authenticated_client.get('/staff')
        assert response.status_code == 200

    def test_tanks_page(self, authenticated_client):
        """Test tanks page loads"""
        response = authenticated_client.get('/equipment/tanks')
        assert response.status_code == 200

    def test_equipment_page(self, authenticated_client):
        """Test equipment page loads"""
        response = authenticated_client.get('/equipment')
        assert response.status_code == 200

    def test_analytics_page(self, authenticated_client):
        """Test analytics page loads"""
        response = authenticated_client.get('/analytics')
        assert response.status_code == 200


class TestLanguageSwitching:
    """Test language switching functionality"""

    def test_set_language_english(self, authenticated_client):
        """Test setting language to English"""
        response = authenticated_client.get('/language/en')
        assert response.status_code == 302

    def test_set_language_vietnamese(self, authenticated_client):
        """Test setting language to Vietnamese"""
        response = authenticated_client.get('/language/vi')
        assert response.status_code == 302


class TestLogout:
    """Test logout functionality"""

    def test_logout(self, authenticated_client):
        """Test logout redirects to login"""
        response = authenticated_client.get('/logout')
        assert response.status_code == 302