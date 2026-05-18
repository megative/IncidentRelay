import re

NAME_MIN_LENGTH = 2
NAME_MAX_LENGTH = 40

TOKEN_NAME_MIN_LENGTH = 1
TOKEN_NAME_MAX_LENGTH = 40

USERNAME_MIN_LENGTH = 2
USERNAME_MAX_LENGTH = 40

SLUG_MIN_LENGTH = 1
SLUG_MAX_LENGTH = 24

DISPLAY_NAME_MAX_LENGTH = 40
DESCRIPTION_MAX_LENGTH = 120
CONTACT_ID_MAX_LENGTH = 40
ROLE_MAX_LENGTH = 32

PHONE_MIN_DIGITS = 5
PHONE_MAX_DIGITS = 20
PHONE_MAX_LENGTH = PHONE_MAX_DIGITS + 1
PHONE_PATTERN = rf"^\+?[0-9]{{{PHONE_MIN_DIGITS},{PHONE_MAX_DIGITS}}}$"
PHONE_RE = re.compile(PHONE_PATTERN)


def validate_phone(value):
    """Validate phone as digits with an optional leading plus."""
    if value is None:
        return None

    value = str(value).strip()
    if not value:
        return None

    if not PHONE_RE.fullmatch(value):
        raise ValueError(
            "phone must contain only digits and optionally one leading +; "
            f"use {PHONE_MIN_DIGITS}-{PHONE_MAX_DIGITS} digits"
        )
    return value
