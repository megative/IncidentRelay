from app import create_app
from app.version import get_service_version


def test_service_version_is_set():
    assert isinstance(get_service_version(), str)
    assert get_service_version()


def test_version_api_is_public_and_returns_json():
    app = create_app()
    app.config.update(TESTING=True)

    with app.test_client() as client:
        response = client.get("/api/version")

    assert response.status_code == 200
    payload = response.get_json()

    assert payload["service_version"] == get_service_version()
    assert "migrations" in payload


def test_login_page_renders():
    app = create_app()
    app.config.update(TESTING=True)

    with app.test_client() as client:
        response = client.get("/login")

    assert response.status_code == 200
