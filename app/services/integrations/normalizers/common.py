import hashlib


def normalize_event_link(value):
    """Return a clean event/source link value."""
    if value is None:
        return None

    value = str(value).strip()

    if not value:
        return None

    return value


def first_event_link(*values):
    """Return first non-empty event/source link."""
    for value in values:
        value = normalize_event_link(value)

        if value:
            return value

    return None


def add_event_link_label(labels, event_link):
    """Store external event link in alert labels."""
    event_link = normalize_event_link(event_link)

    if event_link:
        labels.setdefault("event_link", event_link)

    return labels


def make_hash(value):
    """
    Build a stable hash from a Python value.
    """

    return hashlib.sha256(repr(value).encode("utf-8")).hexdigest()


def make_dedup_key(source, external_id=None, title=None, labels=None):
    """
    Create a stable deduplication key.
    """

    return make_hash({"source": source, "external_id": external_id, "title": title, "labels": labels or {}})


def first_non_empty(*values):
    """Return first non-empty string-like value."""
    for value in values:
        if value is None:
            continue

        if isinstance(value, str):
            value = value.strip()

        if value:
            return value

    return None
