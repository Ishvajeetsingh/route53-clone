"""UTC timestamp semantics: API output must carry an explicit UTC offset.

SQLite stores CURRENT_TIMESTAMP (UTC) but returns naive datetimes. The API
must serialize them as unambiguous UTC ISO-8601 so browsers render the
correct local time instead of misreading UTC as local time.
"""

from datetime import datetime, timezone

from app.schemas.dns import ensure_utc


def _parse_utc(value: str) -> datetime:
    parsed = datetime.fromisoformat(value)
    assert parsed.tzinfo is not None, f"timestamp missing offset: {value!r}"
    return parsed.astimezone(timezone.utc)


def test_zone_timestamps_are_utc_with_offset(client, auth_headers):
    res = client.post("/api/hosted-zones", json={"name": "time.test"}, headers=auth_headers)
    assert res.status_code == 201
    created = _parse_utc(res.json()["created_at"])
    # SQLite CURRENT_TIMESTAMP has second precision, so allow truncation skew.
    assert abs((datetime.now(timezone.utc) - created).total_seconds()) < 300


def test_zone_timestamps_survive_read_and_update(client, auth_headers, zone):
    zid = zone["id"]
    fetched = client.get(f"/api/hosted-zones/{zid}", headers=auth_headers).json()
    _parse_utc(fetched["created_at"])

    updated = client.patch(
        f"/api/hosted-zones/{zid}", json={"description": "bump"}, headers=auth_headers
    ).json()
    stamp = _parse_utc(updated["updated_at"])
    assert stamp >= _parse_utc(fetched["created_at"])


def test_record_timestamps_are_utc_with_offset(client, auth_headers, zone):
    res = client.post(
        f"/api/hosted-zones/{zone['id']}/records",
        json={"name": "www.example.com.", "type": "A", "values": ["192.0.2.1"], "ttl": 300, "routing_policy": "Simple"},
        headers=auth_headers,
    )
    assert res.status_code == 201
    created = _parse_utc(res.json()["created_at"])
    assert abs((datetime.now(timezone.utc) - created).total_seconds()) < 300

    listed = client.get(f"/api/hosted-zones/{zone['id']}/records", headers=auth_headers).json()
    for rec in listed["items"]:
        _parse_utc(rec["created_at"])
        _parse_utc(rec["updated_at"])


def test_ensure_utc_treats_naive_as_utc_without_shifting():
    naive = datetime(2026, 9, 25, 15, 18, 15)  # how SQLite returns CURRENT_TIMESTAMP
    assert ensure_utc(naive) == datetime(2026, 9, 25, 15, 18, 15, tzinfo=timezone.utc)

    aware = datetime(2026, 9, 25, 20, 48, 15, tzinfo=timezone.utc)
    assert ensure_utc(aware) == aware
