from datetime import timedelta

from app.models import Equipment, db, utcnow


def test_mark_down_then_up_tracks_events(app_ctx):
    item = Equipment(name="Table Saw")
    db.session.add(item)
    db.session.commit()

    assert item.status == "up"
    assert item.downtime_duration is None

    item.mark_down(note="blade snapped")
    db.session.commit()

    assert item.is_down
    assert item.down_since is not None
    assert item.downtime_duration is not None
    assert item.events[0].event_type == "down"
    assert item.events[0].note == "blade snapped"

    item.mark_up(note="replaced blade")
    db.session.commit()

    assert item.status == "up"
    assert item.down_since is None
    assert item.downtime_duration is None
    assert item.events[0].event_type == "up"


def test_downtime_duration_reflects_elapsed_time(app_ctx):
    item = Equipment(name="Forklift")
    db.session.add(item)
    db.session.commit()

    item.mark_down(when=utcnow() - timedelta(hours=2))
    db.session.commit()

    duration = item.downtime_duration
    assert duration >= timedelta(hours=1, minutes=59)
