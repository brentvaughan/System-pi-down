import logging
import smtplib
from email.message import EmailMessage

logger = logging.getLogger("downtime_tracker.email")


def send_email(app, to_addrs, subject, body):
    """Send a plain-text email using the app's configured SMTP server.

    If SMTP_HOST isn't set, the email is logged instead of sent so the
    app is usable before mail credentials are configured.
    """
    to_addrs = [addr for addr in (to_addrs or []) if addr]
    if not to_addrs:
        logger.info("No recipients for email %r, skipping send.", subject)
        return False

    host = app.config.get("SMTP_HOST")
    if not host:
        logger.info("SMTP not configured; would have sent email:\nTo: %s\nSubject: %s\n\n%s",
                     ", ".join(to_addrs), subject, body)
        return False

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = app.config["SMTP_FROM"]
    msg["To"] = ", ".join(to_addrs)
    msg.set_content(body)

    port = app.config.get("SMTP_PORT", 587)
    use_tls = app.config.get("SMTP_USE_TLS", True)
    username = app.config.get("SMTP_USERNAME")
    password = app.config.get("SMTP_PASSWORD")

    try:
        with smtplib.SMTP(host, port, timeout=10) as server:
            if use_tls:
                server.starttls()
            if username:
                server.login(username, password)
            server.send_message(msg)
        logger.info("Sent email %r to %s", subject, ", ".join(to_addrs))
        return True
    except Exception:
        logger.exception("Failed to send email %r to %s", subject, ", ".join(to_addrs))
        return False


def send_part_order_email(app, equipment, note=None):
    recipients = []
    if equipment.vendor_email:
        recipients.append(equipment.vendor_email)
    recipients.extend(app.config.get("REMINDER_EMAIL", []))

    subject = f"Part order needed: {equipment.name} is down"
    lines = [
        f"{equipment.name} is currently marked DOWN and needs a part ordered.",
        "",
        f"Part needed: {equipment.part_name or '(not specified)'}",
        f"Part number: {equipment.part_number or '(not specified)'}",
        f"Vendor: {equipment.vendor_name or '(not specified)'}",
    ]
    if equipment.location:
        lines.append(f"Location: {equipment.location}")
    if note:
        lines.append("")
        lines.append(f"Note: {note}")

    return send_email(app, recipients, subject, "\n".join(lines))


def send_equipment_restored_email(app, equipment, downtime_str, note=None):
    recipients = app.config.get("REMINDER_EMAIL", [])
    subject = f"Back up: {equipment.name} is working again"
    lines = [f"{equipment.name} was marked UP after being down for {downtime_str}."]
    if note:
        lines.append("")
        lines.append(f"Note: {note}")
    return send_email(app, recipients, subject, "\n".join(lines))


def send_reminder_email(app, down_equipment):
    """down_equipment: list of (Equipment, duration_str) tuples."""
    recipients = app.config.get("REMINDER_EMAIL", [])
    if not down_equipment:
        return False

    subject = f"Reminder: {len(down_equipment)} piece(s) of equipment still down"
    lines = ["Still down:", ""]
    for equipment, duration_str in down_equipment:
        part = equipment.part_name or "no part specified"
        lines.append(f"- {equipment.name} (down {duration_str}) — part: {part}")
    return send_email(app, recipients, subject, "\n".join(lines))
