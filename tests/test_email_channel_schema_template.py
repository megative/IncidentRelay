import pytest
from pydantic import ValidationError

from app.api.schemas.channels import ChannelCreateSchema


def test_email_channel_accepts_html_template_and_strips_smtp_transport_fields():
    payload = ChannelCreateSchema.model_validate(
        {
            "team_id": 1,
            "name": "email",
            "channel_type": "email",
            "config": {
                "recipients": ["sre@example.com"],
                "html_template": "<h1>{title}</h1>",
                "smtp_host": "smtp.example.com",
                "smtp_port": 2525,
                "smtp_user": "legacy-user",
                "smtp_password": "legacy-password",
                "smtp_use_tls": False,
                "from": "legacy@example.com",
            },
            "enabled": True,
        }
    )

    assert payload.config["recipients"] == ["sre@example.com"]
    assert payload.config["html_template"] == "<h1>{title}</h1>"
    assert "smtp_host" not in payload.config
    assert "smtp_port" not in payload.config
    assert "smtp_user" not in payload.config
    assert "smtp_password" not in payload.config
    assert "smtp_use_tls" not in payload.config
    assert "from" not in payload.config


def test_email_channel_rejects_invalid_html_template():
    with pytest.raises(ValidationError):
        ChannelCreateSchema.model_validate(
            {
                "team_id": 1,
                "name": "email",
                "channel_type": "email",
                "config": {
                    "recipients": ["sre@example.com"],
                    "html_template": "<h1>{title</h1>",
                },
                "enabled": True,
            }
        )
