from datetime import datetime, timezone

from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


def utcnow():
    return datetime.now(timezone.utc)


class Equipment(db.Model):
    __tablename__ = "equipment"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    location = db.Column(db.String(120))
    notes = db.Column(db.Text)

    # What to order and who to order it from when this goes down.
    part_name = db.Column(db.String(200))
    part_number = db.Column(db.String(100))
    vendor_name = db.Column(db.String(120))
    vendor_email = db.Column(db.String(200))

    status = db.Column(db.String(10), nullable=False, default="up")  # "up" | "down"
    down_since = db.Column(db.DateTime)

    created_at = db.Column(db.DateTime, default=utcnow, nullable=False)

    events = db.relationship(
        "DowntimeEvent", backref="equipment", lazy=True, order_by="DowntimeEvent.timestamp.desc()"
    )

    def mark_down(self, note=None, when=None):
        when = when or utcnow()
        self.status = "down"
        self.down_since = when
        event = DowntimeEvent(equipment=self, event_type="down", timestamp=when, note=note)
        db.session.add(event)
        return event

    def mark_up(self, note=None, when=None):
        when = when or utcnow()
        self.status = "up"
        self.down_since = None
        event = DowntimeEvent(equipment=self, event_type="up", timestamp=when, note=note)
        db.session.add(event)
        return event

    @property
    def is_down(self):
        return self.status == "down"

    @property
    def downtime_duration(self):
        if not self.is_down or not self.down_since:
            return None
        since = self.down_since
        if since.tzinfo is None:
            since = since.replace(tzinfo=timezone.utc)
        return utcnow() - since


class DowntimeEvent(db.Model):
    __tablename__ = "downtime_event"

    id = db.Column(db.Integer, primary_key=True)
    equipment_id = db.Column(db.Integer, db.ForeignKey("equipment.id"), nullable=False)
    event_type = db.Column(db.String(10), nullable=False)  # "down" | "up"
    timestamp = db.Column(db.DateTime, default=utcnow, nullable=False)
    note = db.Column(db.Text)
