import logging

from app.notifiers.voice.base import (
    BaseVoiceProvider,
    VoiceCallCallbackEvent,
    VoiceCallRequest,
    VoiceCallResult,
    VoiceProviderCapabilities,
)

logger = logging.getLogger("oncall.voice")


def _mask_phone(phone: str | None) -> str | None:
    """Mask phone before writing it to logs."""

    if not phone:
        return None

    value = str(phone)

    if len(value) <= 4:
        return "****"

    return f"***{value[-4:]}"


class Provider(BaseVoiceProvider):
    """Stub provider for development and dry-run setups."""

    name = "stub"

    capabilities = VoiceProviderCapabilities(
        tts=True,
        status_callback=True,
        dtmf_callback=True,
        status_polling=False,
    )

    def place_call(self, request: VoiceCallRequest) -> VoiceCallResult:
        """Log a voice call instead of sending it."""

        logger.warning(
            "VOICE CALL STUB: should place a voice call",
            extra={
                "extra": {
                    "phone": _mask_phone(request.phone),
                    "alert_id": request.alert_id,
                    "event_type": request.event_type,
                    "severity": request.severity,
                    "team": request.team,
                    "assignee": request.assignee,
                    "callback_url": request.callback_url,
                    "action_hints": request.action_hints,
                }
            },
        )

        return VoiceCallResult(
            call_id=f"stub-{request.alert_id or 'test'}-{request.event_type}",
            status="logged",
            raw={"provider": self.name},
        )

    def parse_callback(
        self,
        payload,
        headers=None,
        raw_body=None,
        query_args=None,
    ):
        """Parse test callbacks.

        Example:
        {
          "call_id": "stub-1-notification",
          "event_type": "dtmf",
          "digit": "1"
        }
        """

        return [
            VoiceCallCallbackEvent(
                call_id=str(payload.get("call_id") or ""),
                event_type=str(payload.get("event_type") or "status"),
                status=payload.get("status"),
                digit=payload.get("digit"),
                action=payload.get("action"),
                alert_id=payload.get("alert_id"),
                message=payload.get("message"),
                raw=payload,
            )
        ]
