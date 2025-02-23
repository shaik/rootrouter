import json
import pytest
import requests
from app import app, apps_dict, session

class DummyResponse:
    def __init__(self, content, status_code, headers):
        self.content = content
        self.status_code = status_code
        self.headers = headers

@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client

def dummy_request(method, url, headers=None, data=None, cookies=None, allow_redirects=None, timeout=None, stream=None):
    # Simulate a 200 OK response for proxy tests
    return DummyResponse(b"dummy content", 200, {"Content-Type": "text/plain", "Custom-Header": "value"})

def test_index(client):
    """Verify the index page loads and displays app names."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.get_data(as_text=True)
    for app_conf in apps_dict.values():
        assert app_conf["name"] in data

def test_proxy_valid_route(monkeypatch, client):
    """Check that a valid route is forwarded with the correct content and headers."""
    monkeypatch.setattr(session, "request", dummy_request)
    response = client.get("/emoji/test-path?query=abc", headers={"X-Script-Name": "/emoji"})
    assert response.status_code == 200
    assert response.get_data() == b"dummy content"
    assert response.headers.get("Content-Type") == "text/plain"
    assert response.headers.get("Custom-Header") == "value"

def test_proxy_static_file_exists(client):
    """Check that an existing static file returns 200 OK."""
    response = client.get("/emoji/static/js/main.js", headers={"X-Script-Name": "/emoji"})
    # If the emoji app has main.js, we expect 200
    assert response.status_code == 200

def test_proxy_static_file_missing(client):
    """Check that a non-existent static file returns 404."""
    response = client.get("/emoji/static/js/doesnotexist.js", headers={"X-Script-Name": "/emoji"})
    assert response.status_code == 404

def test_proxy_invalid_route(client):
    """Verify that an invalid route returns 404."""
    response = client.get("/invalid-route")
    assert response.status_code == 404

def test_invalid_target_url(monkeypatch, client):
    """Check that an insecure (HTTP) target URL triggers a 400 error."""
    original_url = apps_dict["emoji"]["url"]
    apps_dict["emoji"]["url"] = "http://insecure-url.com"
    response = client.get("/emoji/test")
    assert response.status_code == 400
    apps_dict["emoji"]["url"] = original_url

def test_timeout(monkeypatch, client):
    """Check that a request timeout triggers a 502 error."""
    def timeout_request(*args, **kwargs):
        raise requests.exceptions.Timeout("Request timed out")
    monkeypatch.setattr(session, "request", timeout_request)
    response = client.get("/emoji/test")
    assert response.status_code == 502
    assert b"Request timed out" in response.data

def test_script_root_header(client):
    """Check that /emoji/ route is reachable with X-Script-Name set."""
    response = client.get("/emoji/", headers={"X-Script-Name": "/emoji"})
    # If the 'emoji' route is valid, we expect 200
    if "emoji" in apps_dict:
        assert response.status_code == 200
    else:
        assert response.status_code == 404
