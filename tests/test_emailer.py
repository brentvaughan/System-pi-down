from unittest.mock import MagicMock, patch

from app.emailer import send_email


def test_send_email_no_recipients_does_not_call_smtp(app):
    with patch("smtplib.SMTP") as mock_smtp:
        result = send_email(app, [], "subject", "body")
    assert result is False
    mock_smtp.assert_not_called()


def test_send_email_without_smtp_host_configured_logs_instead_of_sending(app):
    app.config["SMTP_HOST"] = ""
    with patch("smtplib.SMTP") as mock_smtp:
        result = send_email(app, ["a@example.com"], "subject", "body")
    assert result is False
    mock_smtp.assert_not_called()


def test_send_email_with_smtp_host_sends_via_smtp(app):
    app.config["SMTP_HOST"] = "smtp.example.com"
    app.config["SMTP_USERNAME"] = "user"
    app.config["SMTP_PASSWORD"] = "pass"

    mock_server = MagicMock()
    with patch("smtplib.SMTP") as mock_smtp:
        mock_smtp.return_value.__enter__.return_value = mock_server
        result = send_email(app, ["a@example.com"], "subject", "body")

    assert result is True
    mock_server.starttls.assert_called_once()
    mock_server.login.assert_called_once_with("user", "pass")
    mock_server.send_message.assert_called_once()
