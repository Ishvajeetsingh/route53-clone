"""HostedZone.updated_at = latest meaningful mutation to the zone or its records."""

from datetime import datetime, timezone

from app.models.dns import HostedZone

OLD = datetime(2020, 1, 1, tzinfo=timezone.utc)


def _backdate(db_session, zone_id: str) -> None:
    """Pin updated_at to a fixed past instant to defeat second-level precision."""
    zone = db_session.get(HostedZone, zone_id)
    assert zone is not None
    zone.updated_at = OLD
    db_session.commit()


def _fetch(client, auth_headers, zone_id: str) -> dict:
    res = client.get(f"/api/hosted-zones/{zone_id}", headers=auth_headers)
    assert res.status_code == 200
    return res.json()


def _instant(value: str) -> datetime:
    parsed = datetime.fromisoformat(value)
    assert parsed.tzinfo is not None, f"timestamp missing offset: {value!r}"
    return parsed.astimezone(timezone.utc)


def _create_a_record(client, auth_headers, zone_id: str) -> dict:
    res = client.post(
        f"/api/hosted-zones/{zone_id}/records",
        json={"name": "www.example.com.", "type": "A", "values": ["192.0.2.10"], "ttl": 300, "routing_policy": "Simple"},
        headers=auth_headers,
    )
    assert res.status_code == 201
    return res.json()


def test_record_create_advances_parent_zone(client, auth_headers, zone, db_session):
    created_before = _instant(zone["created_at"])
    _backdate(db_session, zone["id"])

    _create_a_record(client, auth_headers, zone["id"])

    after = _fetch(client, auth_headers, zone["id"])
    assert _instant(after["updated_at"]) > OLD
    assert _instant(after["created_at"]) == created_before


def test_record_update_advances_parent_zone(client, auth_headers, zone, db_session):
    rec = _create_a_record(client, auth_headers, zone["id"])
    created_before = _instant(_fetch(client, auth_headers, zone["id"])["created_at"])
    _backdate(db_session, zone["id"])

    res = client.patch(
        f"/api/hosted-zones/{zone['id']}/records/{rec['id']}",
        json={"values": ["192.0.2.20"]},
        headers=auth_headers,
    )
    assert res.status_code == 200

    after = _fetch(client, auth_headers, zone["id"])
    assert _instant(after["updated_at"]) > OLD
    assert _instant(after["created_at"]) == created_before


def test_record_delete_advances_parent_zone(client, auth_headers, zone, db_session):
    rec = _create_a_record(client, auth_headers, zone["id"])
    created_before = _instant(_fetch(client, auth_headers, zone["id"])["created_at"])
    _backdate(db_session, zone["id"])

    res = client.delete(f"/api/hosted-zones/{zone['id']}/records/{rec['id']}", headers=auth_headers)
    assert res.status_code == 204

    after = _fetch(client, auth_headers, zone["id"])
    assert _instant(after["updated_at"]) > OLD
    assert _instant(after["created_at"]) == created_before


def test_reads_do_not_advance_parent_zone(client, auth_headers, zone, db_session):
    _backdate(db_session, zone["id"])
    zid = zone["id"]

    assert client.get(f"/api/hosted-zones/{zid}", headers=auth_headers).status_code == 200
    assert client.get("/api/hosted-zones?q=example", headers=auth_headers).status_code == 200
    assert client.get("/api/hosted-zones?page=1&page_size=1", headers=auth_headers).status_code == 200
    assert client.get(f"/api/hosted-zones/{zid}/records", headers=auth_headers).status_code == 200
    assert client.get(f"/api/hosted-zones/{zid}/records?q=www&page=1&page_size=10", headers=auth_headers).status_code == 200
    assert client.get(f"/api/hosted-zones/{zid}/records?record_type=A", headers=auth_headers).status_code == 200

    after = _fetch(client, auth_headers, zid)
    assert _instant(after["updated_at"]) == OLD


def test_zone_edit_advances_updated_at_not_created_at(client, auth_headers, zone, db_session):
    created_before = _instant(zone["created_at"])
    _backdate(db_session, zone["id"])

    res = client.patch(
        f"/api/hosted-zones/{zone['id']}", json={"description": "touched"}, headers=auth_headers
    )
    assert res.status_code == 200
    assert _instant(res.json()["updated_at"]) > OLD
    assert _instant(res.json()["created_at"]) == created_before
