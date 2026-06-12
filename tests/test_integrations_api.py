from app.services.integrations.auth import hash_token
from tests.factories import create_group, create_route, create_team


def alertmanager_payload():
    return {
        "status": "firing",
        "alerts": [
            {
                "status": "firing",
                "labels": {
                    "alertname": "DiskFull",
                    "severity": "critical",
                    "instance": "host1",
                },
                "annotations": {
                    "summary": "Disk is full",
                    "description": "/var is 95% full",
                },
                "fingerprint": "disk-full-host1-var",
                "startsAt": "2026-05-18T10:00:00Z",
            }
        ],
    }


def test_alertmanager_endpoint_requires_token(client):
    response = client.post("/api/integrations/alertmanager", json=alertmanager_payload())

    assert response.status_code == 401
    assert response.is_json


def test_alertmanager_endpoint_accepts_valid_route_token(client, monkeypatch, db):
    raw_token = "test-route-token"
    group = create_group(slug="infra")
    team = create_team(group, slug="sre")
    create_route(team, source="alertmanager", token_hash=hash_token(raw_token))

    calls = []

    def fake_process_incoming_alerts(alerts):
        calls.append(alerts)
        return {"ok": True, "count": len(alerts)}, 200

    monkeypatch.setattr(
        "app.views.integrations_view.process_incoming_alerts",
        fake_process_incoming_alerts,
    )

    response = client.post(
        "/api/integrations/alertmanager",
        headers={"Authorization": f"Bearer {raw_token}"},
        json=alertmanager_payload(),
    )

    assert response.status_code == 200
    assert response.get_json() == {"ok": True, "count": 1}
    assert calls[0][0]["source"] == "alertmanager"
    assert calls[0][0]["title"] == "Disk is full"


def test_webhook_endpoint_rejects_invalid_payload_with_valid_route_token(client, db):
    raw_token = "test-route-token"
    group = create_group(slug="infra")
    team = create_team(group, slug="sre")
    create_route(team, source="webhook", token_hash=hash_token(raw_token))

    response = client.post(
        "/api/integrations/webhook",
        headers={"Authorization": f"Bearer {raw_token}"},
        json={"message": "missing required title"},
    )

    assert response.status_code == 400
    assert response.is_json
    assert response.get_json()["error"] == "validation_error"
