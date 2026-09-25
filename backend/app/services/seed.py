"""Seed a small demo dataset on first run (only when DB is empty)."""

from sqlalchemy.orm import Session

from app.models.dns import DNSRecord, HostedZone


def seed_if_empty(db: Session) -> None:
    if db.query(HostedZone).count() > 0:
        return
    zone = HostedZone(id="Z1A2B3C4D5E6F7", name="example.com.", description="Demo hosted zone", type="Public")
    db.add(zone)
    db.flush()
    db.add_all(
        [
            DNSRecord(zone_id=zone.id, name="example.com.", type="NS",
                      values=["ns-1.awsdns-1.com.", "ns-2.awsdns-2.net.", "ns-3.awsdns-3.org.", "ns-4.awsdns-4.co.uk."],
                      ttl=172800, routing_policy="Simple", description="Default name servers"),
            DNSRecord(zone_id=zone.id, name="example.com.", type="SOA",
                      values=["ns-1.awsdns-1.com. awsdns-hostmaster.amazon.com. 1 7200 900 1209600 86400"],
                      ttl=900, routing_policy="Simple", description="Start of authority"),
            DNSRecord(zone_id=zone.id, name="example.com.", type="A", values=["192.0.2.1"],
                      ttl=300, routing_policy="Simple", description="Apex site"),
            DNSRecord(zone_id=zone.id, name="www.example.com.", type="CNAME", values=["example.com."],
                      ttl=300, routing_policy="Simple", description="WWW alias"),
            DNSRecord(zone_id=zone.id, name="example.com.", type="MX", values=["10 mail.example.com."],
                      ttl=300, routing_policy="Simple", description="Mail"),
        ]
    )
    db.commit()
