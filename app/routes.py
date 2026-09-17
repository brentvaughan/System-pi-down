from flask import Blueprint, current_app, flash, jsonify, redirect, render_template, request, url_for

from .emailer import send_equipment_restored_email, send_part_order_email
from .models import Equipment, db
from .scheduler import _format_duration

bp = Blueprint("main", __name__)
api = Blueprint("api", __name__, url_prefix="/api")


@bp.route("/")
def index():
    equipment = Equipment.query.order_by(Equipment.status.desc(), Equipment.name).all()
    down_count = sum(1 for item in equipment if item.is_down)
    durations = {
        item.id: _format_duration(item.downtime_duration) for item in equipment if item.is_down
    }
    return render_template(
        "index.html", equipment=equipment, down_count=down_count, durations=durations
    )


@bp.route("/equipment/new", methods=["GET", "POST"])
def new_equipment():
    if request.method == "POST":
        item = Equipment(
            name=request.form["name"].strip(),
            location=request.form.get("location", "").strip() or None,
            part_name=request.form.get("part_name", "").strip() or None,
            part_number=request.form.get("part_number", "").strip() or None,
            vendor_name=request.form.get("vendor_name", "").strip() or None,
            vendor_email=request.form.get("vendor_email", "").strip() or None,
            notes=request.form.get("notes", "").strip() or None,
        )
        db.session.add(item)
        db.session.commit()
        flash(f"Added {item.name}.", "success")
        return redirect(url_for("main.index"))
    return render_template("equipment_form.html", equipment=None)


@bp.route("/equipment/<int:equipment_id>/edit", methods=["GET", "POST"])
def edit_equipment(equipment_id):
    item = Equipment.query.get_or_404(equipment_id)
    if request.method == "POST":
        item.name = request.form["name"].strip()
        item.location = request.form.get("location", "").strip() or None
        item.part_name = request.form.get("part_name", "").strip() or None
        item.part_number = request.form.get("part_number", "").strip() or None
        item.vendor_name = request.form.get("vendor_name", "").strip() or None
        item.vendor_email = request.form.get("vendor_email", "").strip() or None
        item.notes = request.form.get("notes", "").strip() or None
        db.session.commit()
        flash(f"Updated {item.name}.", "success")
        return redirect(url_for("main.index"))
    return render_template("equipment_form.html", equipment=item)


@bp.route("/equipment/<int:equipment_id>/delete", methods=["POST"])
def delete_equipment(equipment_id):
    item = Equipment.query.get_or_404(equipment_id)
    db.session.delete(item)
    db.session.commit()
    flash(f"Deleted {item.name}.", "success")
    return redirect(url_for("main.index"))


@bp.route("/equipment/<int:equipment_id>/down", methods=["POST"])
def mark_down(equipment_id):
    item = Equipment.query.get_or_404(equipment_id)
    note = request.form.get("note", "").strip() or None
    if item.is_down:
        flash(f"{item.name} is already marked down.", "warning")
        return redirect(url_for("main.index"))

    item.mark_down(note=note)
    db.session.commit()

    sent = send_part_order_email(current_app._get_current_object(), item, note=note)
    if sent:
        flash(f"{item.name} marked down. Part-order email sent.", "success")
    else:
        flash(f"{item.name} marked down. (No email sent — check SMTP/vendor email config.)", "warning")
    return redirect(url_for("main.index"))


@bp.route("/equipment/<int:equipment_id>/up", methods=["POST"])
def mark_up(equipment_id):
    item = Equipment.query.get_or_404(equipment_id)
    note = request.form.get("note", "").strip() or None
    if not item.is_down:
        flash(f"{item.name} is already marked up.", "warning")
        return redirect(url_for("main.index"))

    duration_str = _format_duration(item.downtime_duration)
    item.mark_up(note=note)
    db.session.commit()

    send_equipment_restored_email(current_app._get_current_object(), item, duration_str, note=note)
    flash(f"{item.name} marked up. Was down for {duration_str}.", "success")
    return redirect(url_for("main.index"))


# --- JSON API, for scripts / CLI / voice-assistant style integrations ---

def _equipment_to_dict(item):
    return {
        "id": item.id,
        "name": item.name,
        "status": item.status,
        "down_since": item.down_since.isoformat() if item.down_since else None,
        "part_name": item.part_name,
        "part_number": item.part_number,
        "vendor_name": item.vendor_name,
        "vendor_email": item.vendor_email,
    }


@api.route("/equipment", methods=["GET"])
def api_list_equipment():
    return jsonify([_equipment_to_dict(item) for item in Equipment.query.order_by(Equipment.name).all()])


@api.route("/equipment/<int:equipment_id>/status", methods=["POST"])
def api_set_status(equipment_id):
    item = Equipment.query.get_or_404(equipment_id)
    data = request.get_json(silent=True) or request.form
    status = (data.get("status") or "").strip().lower()
    note = (data.get("note") or "").strip() or None

    if status not in ("up", "down"):
        return jsonify({"error": "status must be 'up' or 'down'"}), 400

    app_obj = current_app._get_current_object()
    if status == "down":
        if item.is_down:
            return jsonify(_equipment_to_dict(item)), 200
        item.mark_down(note=note)
        db.session.commit()
        send_part_order_email(app_obj, item, note=note)
    else:
        if not item.is_down:
            return jsonify(_equipment_to_dict(item)), 200
        duration_str = _format_duration(item.downtime_duration)
        item.mark_up(note=note)
        db.session.commit()
        send_equipment_restored_email(app_obj, item, duration_str, note=note)

    return jsonify(_equipment_to_dict(item)), 200
