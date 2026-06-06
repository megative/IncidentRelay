import os
import sys


# Preferred env var name. The old, mis-spelled name is kept as a fallback so
# existing self-hosted installations (Docker, systemd, RPM) keep working until
# operators migrate. A one-time warning is printed on startup if only the
# legacy name is set.
_CONFIG_ENV = "INCIDENTRELAY_CONFIG_FILE"
_LEGACY_CONFIG_ENV = "INCEDENTRELAY_CONFIG_FILE"
_DEFAULT_CONFIG_PATH = "/etc/incidentrelay/incidentrelay.conf"


def _resolve_config_path():
    """Return the configured config file path, preferring the non-typo env var."""
    value = os.getenv(_CONFIG_ENV)
    if value:
        return value

    legacy = os.getenv(_LEGACY_CONFIG_ENV)
    if legacy:
        print(
            f"WARNING: environment variable {_LEGACY_CONFIG_ENV} is deprecated "
            f"(typo); please use {_CONFIG_ENV} instead.",
            file=sys.stderr,
        )
        return legacy

    return _DEFAULT_CONFIG_PATH


CONFIG_FILE = _resolve_config_path()
