"""Simple test voice provider for local callback testing."""

from app.notifiers.voice.base import (
    BaseVoiceProvider,
    VoiceCallCallbackEvent,
    VoiceCallRequest,
    VoiceCallResult,
    VoiceProviderCapabilities,
)


class Provider(BaseVoiceProvider):
    """Test provider that accepts simple callback payloads."""

    name = "stub_callback_test"

    capabilities = VoiceProviderCapabilities(
        tts=True,
        status_callback=True,
        dtmf_callback=True,
        status_polling=False,
    )

    def place_call(self, request: VoiceCallRequest) -> VoiceCallResult:
        """Return a fake call id without sending a real call."""

        return VoiceCallResult(
            call_id=f"test-{request.alert_id or 'alert'}-{request.event_type}",
            status="logged",
            raw={
                "provider": self.name,
                "callback_url": request.callback_url,
                "action_hints": request.action_hints,
            },
        )

    def parse_callback(
        self,
        payload,
        headers=None,
        raw_body=None,
        query_args=None,
    ):
        """Parse a simple test callback payload."""

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
