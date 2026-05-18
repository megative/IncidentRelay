from app.services.matchers import get_nested_value, match_alert, match_value


ALERT = {
    "status": "firing",
    "severity": "critical",
    "labels": {
        "alertname": "DiskFull",
        "instance": "host1",
        "team": "infra",
    },
    "annotations": {
        "summary": "Disk is full",
        "description": "/var is 95% full",
    },
}


def test_get_nested_value_reads_dotted_paths():
    assert get_nested_value(ALERT, "labels.alertname") == "DiskFull"
    assert get_nested_value(ALERT, "annotations.summary") == "Disk is full"
    assert get_nested_value(ALERT, "missing.key") is None


def test_match_value_supports_exact_list_regex_contains_and_not():
    assert match_value("critical", "critical")
    assert match_value("critical", ["warning", "critical"])
    assert match_value("DiskFull", {"regex": "^Disk"})
    assert match_value("/var is 95% full", {"contains": "95%"})
    assert match_value("critical", {"not": "warning"})

    assert not match_value("critical", "warning")
    assert not match_value("DiskFull", {"regex": "^CPU"})
    assert not match_value("/var is 95% full", {"contains": "CPU"})
    assert not match_value("critical", {"not": "critical"})


def test_match_alert_supports_labels_and_fields():
    assert match_alert(ALERT, {"labels": {"team": "infra"}})
    assert match_alert(ALERT, {"severity": "critical"})
    assert match_alert(ALERT, {"labels.alertname": {"regex": "^Disk"}})

    assert not match_alert(ALERT, {"labels": {"team": "backend"}})
    assert not match_alert(ALERT, {"severity": "warning"})
