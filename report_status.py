"""Quick command-line helper to report equipment status without opening a browser.

Usage:
    python report_status.py list
    python report_status.py down "Table Saw" [--note "blade snapped"]
    python report_status.py up "Table Saw" [--note "replaced blade"]
"""
import argparse
import sys

from app import create_app
from app.emailer import send_equipment_restored_email, send_part_order_email
from app.models import Equipment, db
from app.scheduler import _format_duration


def find_equipment(name):
    match = Equipment.query.filter(Equipment.name.ilike(f"%{name}%")).all()
    if not match:
        print(f"No equipment matching {name!r}.")
        sys.exit(1)
    if len(match) > 1:
        print(f"Multiple matches for {name!r}:")
        for item in match:
            print(f"  - {item.name}")
        sys.exit(1)
    return match[0]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("list")

    for cmd in ("down", "up"):
        p = sub.add_parser(cmd)
        p.add_argument("name")
        p.add_argument("--note")

    args = parser.parse_args()
    app = create_app()

    with app.app_context():
        if args.command == "list":
            for item in Equipment.query.order_by(Equipment.name).all():
                status = item.status.upper()
                extra = f" (down {_format_duration(item.downtime_duration)})" if item.is_down else ""
                print(f"{item.name}: {status}{extra}")
            return

        item = find_equipment(args.name)

        if args.command == "down":
            if item.is_down:
                print(f"{item.name} is already down.")
                return
            item.mark_down(note=args.note)
            db.session.commit()
            send_part_order_email(app, item, note=args.note)
            print(f"Marked {item.name} down and sent part-order email.")
        else:
            if not item.is_down:
                print(f"{item.name} is already up.")
                return
            duration_str = _format_duration(item.downtime_duration)
            item.mark_up(note=args.note)
            db.session.commit()
            send_equipment_restored_email(app, item, duration_str, note=args.note)
            print(f"Marked {item.name} up (was down {duration_str}).")


if __name__ == "__main__":
    main()
