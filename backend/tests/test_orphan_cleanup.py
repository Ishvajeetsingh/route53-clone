"""Startup orphan cleanup: rows whose zone is gone must not linger."""

from app.models.dns import DNSRecord
from app.services.seed import delete_orphaned_records


def test_startup_cleanup_removes_only_orphans(client, auth_headers, zone, db_session):
    zid = zone["id"]
    before = client.get("/api/stats/summary", headers=auth_headers).json()

    # Insert an orphan directly (bypasses the API, like pre-fix leftovers).
    db_session.add(
        DNSRecord(
            zone_id="ZDOESNOTEXIST",
            name="ghost.example.",
            type="A",
            values=["192.0.2.99"],
            ttl=300,
            routing_policy="Simple",
            description="",
        )
    )
    db_session.commit()

    removed = delete_orphaned_records(db_session)
    assert removed == 1
    assert db_session.query(DNSRecord).filter(DNSRecord.zone_id == "ZDOESNOTEXIST").count() == 0

    # Second run is a no-op and the zone's own records are untouched.
    assert delete_orphaned_records(db_session) == 0
    after = client.get("/api/stats/summary", headers=auth_headers).json()
    assert after["hosted_zones"] == before["hosted_zones"]
    assert after["records"] == before["records"]
    zone_detail = client.get(f"/api/hosted-zones/{zid}", headers=auth_headers).json()
    assert zone_detail["record_count"] == 2
