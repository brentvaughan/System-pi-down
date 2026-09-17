import logging
from datetime import datetime, timezone

from apscheduler.schedulers.background import BackgroundScheduler

from .emailer import send_reminder_email
from .models import Equipment

logger = logging.getLogger("downtime_tracker.scheduler")

_scheduler = None


def _format_duration(delta):
    total_minutes = int(delta.total_seconds() // 60)
    hours, minutes = divmod(total_minutes, 60)
    days, hours = divmod(hours, 24)
    parts = []
    if days:
        parts.append(f"{days}d")
    if hours:
        parts.append(f"{hours}h")
    parts.append(f"{minutes}m")
    return " ".join(parts)


def send_due_reminders(app):
    """Send a reminder email listing all currently-down equipment.

    Only runs during the configured active hours, and only sends when
    something is actually down (no news, no email).
    """
    with app.app_context():
        now = datetime.now()
        start = app.config["REMINDER_ACTIVE_START_HOUR"]
        end = app.config["REMINDER_ACTIVE_END_HOUR"]
        if not (start <= now.hour < end):
            return

        down_items = Equipment.query.filter_by(status="down").all()
        if not down_items:
            return

        payload = [(item, _format_duration(item.downtime_duration)) for item in down_items]
        send_reminder_email(app, payload)


def init_scheduler(app):
    global _scheduler
    if not app.config.get("SCHEDULER_ENABLED", True):
        return None
    if _scheduler is not None:
        return _scheduler

    scheduler = BackgroundScheduler(daemon=True, timezone=str(datetime.now(timezone.utc).astimezone().tzinfo))
    interval = app.config["REMINDER_INTERVAL_MINUTES"]
    scheduler.add_job(
        send_due_reminders,
        "interval",
        minutes=interval,
        args=[app],
        id="downtime_reminder",
        replace_existing=True,
    )
    scheduler.start()
    logger.info("Scheduler started: reminder every %s minutes", interval)
    _scheduler = scheduler
    return scheduler
