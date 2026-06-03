from typing import Any, Dict

from pydantic import Field, model_validator

from app.api.schemas.base import ApiModel
from app.notifiers.types import CHANNEL_TYPE_PATTERN, WEBHOOK_STYLE_CHANNELS
from app.notifiers.email.email_templates import normalize_email_html_template
from app.services.severity import normalize_severity_list


class ChannelBaseSchema(ApiModel):
    """Base schema for notification channel input."""

    team_id: int | None = Field(default=None, ge=1)
    name: str = Field(min_length=2, max_length=120)
    channel_type: str = Field(pattern=CHANNEL_TYPE_PATTERN)
    config: Dict[str, Any] = Field(default_factory=dict)
    enabled: bool = True

    @model_validator(mode="after")
    def validate_config(self):
        """Validate channel-specific config fields."""
        config = dict(self.config or {})

        try:
            notify_on_severities = normalize_severity_list(
                config.get("notify_on_severities")
            )
        except ValueError as exc:
            raise ValueError(f"channel notify_on_severities {exc}") from exc

        if notify_on_severities:
            config["notify_on_severities"] = notify_on_severities
        else:
            config.pop("notify_on_severities", None)

        if self.channel_type == "telegram":
            bot_token = str(config.get("bot_token") or "").strip()
            chat_id = str(config.get("chat_id") or "").strip()

            if not bot_token or not chat_id:
                raise ValueError("telegram channel requires bot_token and chat_id")

            if ":" not in bot_token:
                raise ValueError("telegram bot_token must contain ':'")

            config["bot_token"] = bot_token
            config["chat_id"] = chat_id

        if self.channel_type in WEBHOOK_STYLE_CHANNELS and not config.get("webhook_url"):
            raise ValueError(f"{self.channel_type} channel requires webhook_url")

        if self.channel_type == "mattermost":
            mode = config.get("mode") or ("bot_api" if config.get("api_url") else "webhook")
            if mode == "bot_api":
                missing = [
                    name
                    for name in ["api_url", "bot_token", "channel_id"]
                    if not config.get(name)
                ]
                if missing:
                    raise ValueError(
                        f"mattermost Bot API mode requires: {', '.join(missing)}"
                    )
            if mode == "webhook" and not config.get("webhook_url"):
                raise ValueError("mattermost webhook mode requires webhook_url")

        if self.channel_type == "email":
            html_template = normalize_email_html_template(config.get("html_template"))
            if html_template:
                config["html_template"] = html_template
            else:
                config.pop("html_template", None)

        self.config = config
        return self


class ChannelCreateSchema(ChannelBaseSchema):
    """Validate notification channel creation input."""


class ChannelUpdateSchema(ChannelBaseSchema):
    """Validate notification channel update input."""
