import hashlib
import hmac


SENTRY_SIGNATURE_HEADER = "Sentry-Hook-Signature"


def get_sentry_route_config(route):
    config = route.integration_config or {}
    return config.get("sentry") or {}


def get_sentry_webhook_secret(route):
    return get_sentry_route_config(route).get("webhook_secret")


def verify_sentry_signature(secret, raw_body, signature):
    """Verify Sentry-Hook-Signature.

    Sentry signs the raw request body with HMAC-SHA256 using Client Secret.
    """
    if not secret or not signature:
        return False

    expected = hmac.new(
        secret.encode("utf-8"),
        raw_body or b"",
        hashlib.sha256,
    ).hexdigest()

    return hmac.compare_digest(expected, str(signature))


def validate_sentry_route_signature(route, raw_body, headers):
    secret = get_sentry_webhook_secret(route)

    if not secret:
        return {
            "error": "sentry_secret_not_configured",
            "message": "Sentry webhook secret is not configured for this route",
        }, 409

    signature = (
        headers.get(SENTRY_SIGNATURE_HEADER)
        or headers.get(SENTRY_SIGNATURE_HEADER.lower())
    )

    if not signature:
        return {
            "error": "sentry_signature_missing",
            "message": "Sentry-Hook-Signature header is required",
        }, 403

    if not verify_sentry_signature(secret, raw_body, signature):
        return {
            "error": "sentry_signature_invalid",
            "message": "Sentry webhook signature is invalid",
        }, 403

    return None, None