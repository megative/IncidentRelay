from app.services.normalizers import (
    make_dedup_key,
    make_hash,
    normalize_alertmanager,
    normalize_webhook,
    normalize_zabbix,
)


def test_make_hash_is_stable():
    assert make_hash("abc") == make_hash("abc")
    assert make_hash("abc") != make_hash("abcd")


def test_make_dedup_key_is_stable_for_equal_payloads():
    labels = {"alertname": "DiskFull", "instance": "host1"}

    assert make_dedup_key("alertmanager", "fp1", "DiskFull", labels) == make_dedup_key(
        "alertmanager",
        "fp1",
        "DiskFull",
        labels,
    )


def test_normalize_alertmanager_payload():
    payload = {
        "status": "firing",
        "alerts": [
            {
                "status": "firing",
                "labels": {
                    "alertname": "DiskFull",
                    "severity": "critical",
                    "instance": "host1",
                    "team": "infra",
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

    alerts = normalize_alertmanager(payload)

    assert len(alerts) == 1
    assert alerts[0]["source"] == "alertmanager"
    assert alerts[0]["team_slug"] == "infra"
    assert alerts[0]["status"] == "firing"
    assert alerts[0]["severity"] == "critical"
    assert alerts[0]["title"] == "Disk is full"
    assert alerts[0]["message"] == "/var is 95% full"
    assert alerts[0]["dedup_key"] == "disk-full-host1-var"
    assert alerts[0]["labels"]["instance"] == "host1"


def test_normalize_zabbix_payload():
    payload = {
        "event_id": "123",
        "title": "CPU load is high",
        "message": "Load average is high",
        "severity": "High",
        "status": "firing",
        "labels": {"team": "infra"},
    }

    alerts = normalize_zabbix(payload)

    assert len(alerts) == 1
    assert alerts[0]["source"] == "zabbix"
    assert alerts[0]["team_slug"] == "infra"
    assert alerts[0]["status"] == "firing"
    assert alerts[0]["severity"] == "High"
    assert alerts[0]["title"] == "CPU load is high"
    assert alerts[0]["message"] == "Load average is high"


def test_normalize_webhook_payload():
    payload = {
        "status": "resolved",
        "title": "DiskFull",
        "message": "Disk is ok",
        "severity": "info",
        "fingerprint": "fp-1",
        "labels": {"team": "infra"},
        "external_id": "external-1",
    }

    alerts = normalize_webhook(payload)

    assert len(alerts) == 1
    assert alerts[0]["source"] == "webhook"
    assert alerts[0]["team_slug"] == "infra"
    assert alerts[0]["status"] == "resolved"
    assert alerts[0]["dedup_key"] == "fp-1"
    assert alerts[0]["title"] == "DiskFull"
    assert alerts[0]["labels"]["team"] == "infra"
