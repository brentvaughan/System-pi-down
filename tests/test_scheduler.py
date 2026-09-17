from datetime import datetime, timedelta
from unittest.mock import patch

from app.models import Equipment, db
from app.scheduler import _format_duration, send_due_reminders


def test_format_duration():
    assert _format_duration(timedelta(minutes=5)) == "5m"
    assert _format_duration(timedelta(hours=2, minutes=5)) == "2h 5m"
    assert _format_duration(timedelta(days=1, hours=1, minutes=5)) == "1d 1h 5m"


def test_send_due_reminders_skips_outside_active_hours(app):
    with app.app_context():
        item = Equipment(name="Table Saw")
        item.mark_down()
        db.session.add(item)
        db.session.commit()

    app.config["REMINDER_ACTIVE_START_HOUR"] = 7
    app.config["REMINDER_ACTIVE_END_HOUR"] = 19

    fake_now = datetime(2024, 1, 1, 22, 0)
    with patch("app.scheduler.datetime") as mock_datetime, \
            patch("app.scheduler.send_reminder_email") as mock_send:
        mock_datetime.now.return_value = fake_now
        send_due_reminders(app)

    mock_send.assert_not_called()


def test_send_due_reminders_skips_when_nothing_down(app):
    fake_now = datetime(2024, 1, 1, 12, 0)
    with patch("app.scheduler.datetime") as mock_datetime, \
            patch("app.scheduler.send_reminder_email") as mock_send:
        mock_datetime.now.return_value = fake_now
        send_due_reminders(app)

    mock_send.assert_not_called()


def test_send_due_reminders_sends_when_down_and_in_hours(app):
    with app.app_context():
        item = Equipment(name="Table Saw")
        item.mark_down()
        db.session.add(item)
        db.session.commit()

    fake_now = datetime(2024, 1, 1, 12, 0)
    with patch("app.scheduler.datetime") as mock_datetime, \
            patch("app.scheduler.send_reminder_email") as mock_send:
        mock_datetime.now.return_value = fake_now
        send_due_reminders(app)

    mock_send.assert_called_once()
    down_items = mock_send.call_args[0][1]
    assert len(down_items) == 1
    assert down_items[0][0].name == "Table Saw"
