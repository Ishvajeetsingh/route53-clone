"""Apex NS/SOA protection + persistence across sessions."""


def _apex_records(client, auth_headers, zone_id):
    res = client.get(f"/api/hosted-zones/{zone_id}/records?page_size=200", headers=auth_headers).json()
    zone_name = client.get(f"/api/hosted-zones/{zone_id}", headers=auth_headers).json()["name"]
    apex = [r for r in res["items"] if r["name"] == zone_name and r["type"] in ("NS", "SOA")]
    assert len(apex) == 2
    return apex


def test_apex_ns_soa_cannot_be_deleted(client, auth_headers, zone):
    for rec in _apex_records(client, auth_headers, zone["id"]):
        res = client.delete(f"/api/hosted-zones/{zone['id']}/records/{rec['id']}", headers=auth_headers)
        assert res.status_code == 400


def test_apex_ns_soa_stay_editable(client, auth_headers, zone):
    apex = _apex_records(client, auth_headers, zone["id"])
    soa = next(r for r in apex if r["type"] == "SOA")
    res = client.patch(
        f"/api/hosted-zones/{zone['id']}/records/{soa['id']}",
        json={"ttl": 1200},
        headers=auth_headers,
    )
    assert res.status_code == 200
    assert res.json()["ttl"] == 1200


def test_non_apex_ns_is_deletable(client, auth_headers, zone):
    created = client.post(
        f"/api/hosted-zones/{zone['id']}/records",
        json={"name": "delegated.example.com.", "type": "NS", "values": ["ns1.example.net."], "ttl": 300, "routing_policy": "Simple"},
        headers=auth_headers,
    )
    assert created.status_code == 201
    assert client.delete(
        f"/api/hosted-zones/{zone['id']}/records/{created.json()['id']}", headers=auth_headers
    ).status_code == 204


def test_data_visible_from_new_session(tmp_path):
    """File-backed SQLite: rows written by one connection are visible to another."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    from app.database import Base
    from app.models.dns import DNSRecord, HostedZone
    import app.models.dns  # noqa: F401

    db_path = tmp_path / "persist.db"
    engine = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)

    with Session() as s:
        s.add(HostedZone(id="ZTEST123", name="persist.test.", description="", type="Public"))
        s.commit()

    with Session() as s2:  # brand-new connection, like a backend restart
        row = s2.get(HostedZone, "ZTEST123")
        assert row is not None
        assert row.name == "persist.test."
        s2.add(DNSRecord(zone_id="ZTEST123", name="persist.test.", type="A", values=["192.0.2.1"], ttl=300,
                         routing_policy="Simple", description=""))
        s2.commit()

    with Session() as s3:
        assert s3.query(DNSRecord).filter(DNSRecord.zone_id == "ZTEST123").count() == 1
