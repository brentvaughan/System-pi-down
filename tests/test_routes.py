from unittest.mock import patch

from app.models import Equipment, db


def _add_equipment(app, **kwargs):
    with app.app_context():
        item = Equipment(name=kwargs.pop("name", "Table Saw"), **kwargs)
        db.session.add(item)
        db.session.commit()
        return item.id


def test_index_lists_equipment(client, app):
    _add_equipment(app)
    resp = client.get("/")
    assert resp.status_code == 200
    assert b"Table Saw" in resp.data


def test_mark_down_sends_part_order_email(client, app):
    eid = _add_equipment(app, vendor_email="parts@example.com", part_name="Blade")

    with patch("app.routes.send_part_order_email") as mock_send:
        mock_send.return_value = True
        resp = client.post(f"/equipment/{eid}/down", data={"note": "snapped"}, follow_redirects=True)

    assert resp.status_code == 200
    mock_send.assert_called_once()
    with app.app_context():
        item = db.session.get(Equipment, eid)
        assert item.is_down


def test_mark_up_sends_restored_email(client, app):
    eid = _add_equipment(app)
    with app.app_context():
        item = db.session.get(Equipment, eid)
        item.mark_down()
        db.session.commit()

    with patch("app.routes.send_equipment_restored_email") as mock_send:
        mock_send.return_value = True
        resp = client.post(f"/equipment/{eid}/up", follow_redirects=True)

    assert resp.status_code == 200
    mock_send.assert_called_once()
    with app.app_context():
        item = db.session.get(Equipment, eid)
        assert not item.is_down


def test_api_set_status_down_and_up(client, app):
    eid = _add_equipment(app, vendor_email="parts@example.com")

    with patch("app.routes.send_part_order_email", return_value=True):
        resp = client.post(f"/api/equipment/{eid}/status", json={"status": "down", "note": "x"})
    assert resp.status_code == 200
    assert resp.get_json()["status"] == "down"

    with patch("app.routes.send_equipment_restored_email", return_value=True):
        resp = client.post(f"/api/equipment/{eid}/status", json={"status": "up"})
    assert resp.status_code == 200
    assert resp.get_json()["status"] == "up"


def test_api_set_status_rejects_bad_value(client, app):
    eid = _add_equipment(app)
    resp = client.post(f"/api/equipment/{eid}/status", json={"status": "sideways"})
    assert resp.status_code == 400
