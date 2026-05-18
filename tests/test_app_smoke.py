from app.version import get_service_version


def test_service_version_is_set():
    assert isinstance(get_service_version(), str)
    assert get_service_version()


def test_version_api_is_public(client):
    response = client.get("/api/version", follow_redirects=True)

    assert response.status_code == 200
    payload = response.get_json()

    assert payload["service_version"] == get_service_version()
    assert "migrations" in payload


def test_login_page_renders(client):
    response = client.get("/login")

    assert response.status_code == 200


def test_protected_api_requires_auth(client):
    response = client.get("/api/groups", follow_redirects=True)

    assert response.status_code == 401
    assert response.is_json
    assert response.get_json()["error"] == "JWT or API token authentication is required"
