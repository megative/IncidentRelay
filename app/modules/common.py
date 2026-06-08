from datetime import datetime, timezone as dt_timezone


class SafeFormatDict(dict):
    """Keep unknown template placeholders unchanged."""

    def __missing__(self, key):
        return "{" + key + "}"


def as_naive_datetime(value):
    """Return aware UTC datetime from datetime or ISO string."""
    if value is None:
        return None

    if isinstance(value, str):
        text = value.strip()

        if not text:
            return None

        if text.endswith("Z"):
            text = f"{text[:-1]}+00:00"

        try:
            value = datetime.fromisoformat(text)
        except ValueError as exc:
            raise ValueError("datetime must be ISO datetime") from exc

    if not isinstance(value, datetime):
        raise ValueError("datetime must be ISO datetime")

    if value.tzinfo is None:
        return value.replace(tzinfo=dt_timezone.utc)

    return value.astimezone(dt_timezone.utc)
