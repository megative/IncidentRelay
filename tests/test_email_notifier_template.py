from types import SimpleNamespace

from app.notifiers.plugins import EmailNotifier
from app.settings import Config


class DummySMTP:
    instances = []

    def __init__(self, host, port, timeout=10):
        self.host = host
        self.port = port
        self.timeout = timeout
        self.started_tls = False
        self.login_args = None
        self.messages = []
        DummySMTP.instances.append(self)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def starttls(self):
        self.started_tls = True

    def login(self, username, password):
        self.login_args = (username, password)

    def send_message(self, message):
        self.messages.append(message)


def test_email_notifier_uses_global_smtp_and_sends_html(monkeypatch):
    DummySMTP.instances.clear()
    monkeypatch.setattr("app.notifiers.plugins.smtplib.SMTP", DummySMTP)
    monkeypatch.setattr("app.services.links.build_alert_web_url", lambda alert: "https://example.test/alerts/7")

    Config.SMTP_HOST = "smtp.global.test"
    Config.SMTP_PORT = 2525
    Config.SMTP_USE_TLS = True
    Config.SMTP_USER = "smtp-user"
    Config.SMTP_PASSWORD = "smtp-pass"
    Config.SMTP_FROM = "incidentrelay@example.test"

    channel = SimpleNamespace(
        id=1,
        name="email",
        channel_type="email",
        config={
            "recipients": ["sre@example.test"],
            "html_template": "<h1>{title}</h1><p>{message}</p>",
            "smtp_host": "ignored.local",
            "smtp_port": 1025,
        },
    )
    alert = SimpleNamespace(
        id=7,
        title="Disk <Full>",
        message="/var > 95%",
        severity="critical",
        status="firing",
        source="alertmanager",
        team=SimpleNamespace(slug="infra"),
        assignee=None,
    )

    result = EmailNotifier().send(channel, alert, "plain text", event_type="notification")

    assert result == {"provider": "email"}
    smtp = DummySMTP.instances[0]
    assert smtp.host == "smtp.global.test"
    assert smtp.port == 2525
    assert smtp.started_tls is True
    assert smtp.login_args == ("smtp-user", "smtp-pass")
    message = smtp.messages[0]
    assert message["From"] == "incidentrelay@example.test"
    assert message["To"] == "sre@example.test"
    assert message.is_multipart()
    html_part = message.get_body(preferencelist=("html",)).get_content()
    assert "Disk &lt;Full&gt;" in html_part
    assert "/var &gt; 95%" in html_part
