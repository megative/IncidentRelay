"""Reusable database query filter helpers."""

from __future__ import annotations


def normalize_filter_values(values, value_type=str):
    """Normalize scalar, list and comma-separated filter values."""
    if values is None:
        return []

    if isinstance(values, (list, tuple, set)):
        raw_values = values
    else:
        raw_values = [values]

    result = []
    seen = set()

    for raw_value in raw_values:
        if raw_value is None:
            continue

        if isinstance(raw_value, str):
            parts = raw_value.split(",")
        else:
            parts = [raw_value]

        for part in parts:
            if part is None:
                continue

            if value_type is str:
                value = str(part).strip()
                if not value:
                    continue
            else:
                try:
                    value = value_type(part)
                except (TypeError, ValueError):
                    continue

            if value in seen:
                continue

            seen.add(value)
            result.append(value)

    return result


def apply_field_values_filter(query, field, values, value_type=str):
    """Apply an IN filter when one or more values are provided."""
    values = normalize_filter_values(values, value_type=value_type)

    if not values:
        return query

    return query.where(field.in_(values))
