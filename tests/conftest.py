import pytest
from app import app as flask_app

@pytest.fixture
def app():
    """Create and configure a new app instance for each test."""
    # Here you could add test-specific configuration
    # For example, using an in-memory SQLite database
    # flask_app.config.update({"TESTING": True, "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:"})
    
    yield flask_app

@pytest.fixture
def client(app):
    """A test client for the app."""
    return app.test_client()
