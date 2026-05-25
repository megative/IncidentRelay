from pydantic import BaseModel, ConfigDict, Field

from app.modules.sso.sso_login import SsoLoginError


class SamlSecurityConfig(BaseModel):
    """Validated python3-saml security configuration."""

    model_config = ConfigDict(extra="ignore")

    nameIdEncrypted: bool = False
    authnRequestsSigned: bool = False
    logoutRequestSigned: bool = False
    logoutResponseSigned: bool = False
    signMetadata: bool = False

    wantMessagesSigned: bool = False
    wantAssertionsSigned: bool = False
    wantNameId: bool = True
    wantNameIdEncrypted: bool = False
    wantAssertionsEncrypted: bool = False
    wantAttributeStatement: bool = False
    requestedAuthnContext: bool = False

    signatureAlgorithm: str = Field(
        default="http://www.w3.org/2001/04/xmldsig-more#rsa-sha256",
        max_length=512,
    )
    digestAlgorithm: str = Field(
        default="http://www.w3.org/2001/04/xmlenc#sha256",
        max_length=512,
    )


class SsoExtraConfig(BaseModel):
    """Validated SSO provider extra config."""

    model_config = ConfigDict(extra="allow")

    saml_security: SamlSecurityConfig = Field(default_factory=SamlSecurityConfig)


def normalize_sso_extra_config(extra_config):
    """Normalize provider extra_config before saving or using it."""
    if not extra_config:
        return SsoExtraConfig().model_dump()

    if isinstance(extra_config, SsoExtraConfig):
        return extra_config.model_dump()

    return SsoExtraConfig.model_validate(extra_config).model_dump()


def get_saml_security(extra_config):
    """Return effective SAML security config as dict."""
    normalized = normalize_sso_extra_config(extra_config)
    return normalized["saml_security"]


def validate_saml_crypto_config(provider, security, sp_private_key):
    """Validate SP certificate/private key requirements for selected SAML security mode."""
    signing_required = any(
        security.get(key)
        for key in (
            "authnRequestsSigned",
            "logoutRequestSigned",
            "logoutResponseSigned",
            "signMetadata",
        )
    )

    if signing_required and (not provider.saml_sp_x509_cert or not sp_private_key):
        raise SsoLoginError(
            "sso_saml_sp_signing_not_configured",
            "SAML SP certificate and private key are required when request, logout or metadata signing is enabled",
            400,
        )

    decryption_required = (
        security.get("wantNameIdEncrypted")
        or security.get("wantAssertionsEncrypted")
    )

    if decryption_required and not sp_private_key:
        raise SsoLoginError(
            "sso_saml_sp_decryption_not_configured",
            "SAML SP private key is required when encrypted NameID or encrypted assertions are required",
            400,
        )
