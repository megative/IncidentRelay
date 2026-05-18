from app.services.severity import normalize_priority, normalize_severity, severity_rank


def test_normalize_severity_known_aliases():
    assert normalize_severity("disaster") == "critical"
    assert normalize_severity("warn") == "warning"
    assert normalize_severity("average") == "warning"
    assert normalize_severity("not_classified") == "info"


def test_normalize_severity_unknown_value_falls_back_to_info():
    assert normalize_severity("unexpected") == "info"
    assert normalize_severity(None) == "info"


def test_normalize_priority_maps_severity_to_priority():
    assert normalize_priority("critical") == 1
    assert normalize_priority("warning") == 3
    assert normalize_priority("info") == 5


def test_severity_rank_orders_critical_before_warning():
    assert severity_rank("critical") < severity_rank("warning")
    assert severity_rank("warning") < severity_rank("info")
