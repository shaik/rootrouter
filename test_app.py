import json
import pytest
import requests
from app import app, apps_dict, session

# DummyResponse to simulate external HTTP responses
class DummyResponse:
    def __init__(self, content, status_code, headers):
        self.content = content
        self.status_code = status_code
        self.headers = headers

# Dummy request function to simulate a successful external HTTP call
def dummy_request(method, url, headers=None, data=None, cookies=None, allow_redirects=None, timeout=None, stream=None):
    return DummyResponse(b"dummy content", 200, {"Content-Type": "text/plain", "Custom-Header": "value"})

# Pytest fixture for the Flask test client
@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client

def test_index(client):
    """Test that the index page loads and lists all available apps."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.get_data(as_text=True)
    for app_conf in apps_dict.values():
        assert app_conf["name"] in data

def test_proxy_valid_route(monkeypatch, client):
    """Test that a valid proxy route forwards the request correctly."""
    # Override the session.request with our dummy_request function
    monkeypatch.setattr(session, "request", dummy_request)
    response = client.get("/anagram/test-path?query=abc")
    assert response.status_code == 200
    # Check that the response data matches dummy content
    assert response.get_data() == b"dummy content"
    # Check that the custom headers are preserved
    assert response.headers.get("Content-Type") == "text/plain"
    assert response.headers.get("Custom-Header") == "value"

def test_proxy_invalid_route(client):
    """Test that accessing an invalid route returns a 404 error after following redirects."""
    response = client.get("/nonexistent", follow_redirects=True)
    assert response.status_code == 404

def test_invalid_target_url(monkeypatch, client):
    """Test that a non-HTTPS target URL results in a 400 error."""
    # Backup the original URL
    original_url = apps_dict["anagram"]["url"]
    # Temporarily set an insecure URL (non-HTTPS)
    apps_dict["anagram"]["url"] = "http://insecure-url.com"
    response = client.get("/anagram/test")
    assert response.status_code == 400
    # Restore the original URL after the test
    apps_dict["anagram"]["url"] = original_url

def test_timeout(monkeypatch, client):
    """Test that a request timeout results in a 502 error."""
    def timeout_request(method, url, headers=None, data=None, cookies=None, allow_redirects=None, timeout=None, stream=None):
        raise requests.exceptions.Timeout("Request timed out")
    # Override session.request to simulate a timeout
    monkeypatch.setattr(session, "request", timeout_request)
    response = client.get("/anagram/test")
    assert response.status_code == 502  # Bad Gateway
    assert "Request timed out" in response.get_data(as_text=True)
