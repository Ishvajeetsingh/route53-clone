"""DNS record CRUD across every required type, plus filtering and errors."""

import pytest

VALID = [
    ("A", "www.example.com.", ["192.0.2.1"]),
    ("A", "multi.example.com.", ["192.0.2.1", "192.0.2.2"]),
    ("AAAA", "ipv6.example.com.", ["2001:db8::1"]),
    ("CNAME", "alias.example.com.", ["example.com."]),
    ("TXT", "txt.example.com.", ['"v=spf1 include:_spf.example.com ~all"']),
    ("MX", "example.com.", ["10 mail.example.com."]),
    ("MX", "nullmx.example.com.", ["0 ."]),
    ("NS", "sub.example.com.", ["ns1.example.net."]),
    ("PTR", "1.2.0.192.in-addr.arpa.", ["host.example.com."]),
    ("SRV", "_sip._tcp.example.com.", ["10 5 443 sip.example.com."]),
    ("CAA", "example.com.", ['0 issue "letsencrypt.org"']),
    ("SOA", "other.example.com.", ["ns.example.com. hostmaster.example.com. 1 7200 900 1209600 86400"]),
]

INVALID = [
    ("A", ["999.1.1.1"]),
    ("A", ["example.com."]),
    ("AAAA", ["not-an-ipv6"]),
    ("AAAA", ["192.0.2.1"]),
    ("CNAME", ["not a hostname!!!"]),
    ("CNAME", ["a.example.com.", "b.example.com."]),  # exactly one value
    ("TXT", ["x" * 5000]),
    ("MX", ["no-priority-here"]),
    ("MX", ["10"]),
    ("NS", ["bad host name"]),
    ("PTR", [""]),
    ("SRV", ["10 5"]),
    ("SRV", ["10 5 99999 target.example.com."]),  # port out of range
    ("CAA", ["0 badtag value"]),
    ("CAA", ["999 issue value"]),  # flag out of range
    ("SOA", ["single-token"]),
]


@pytest.mark.parametrize("rtype,name,values", VALID)
def test_create_valid_record_per_type(client, auth_headers, zone, rtype, name, values):
    res = client.post(
        f"/api/hosted-zones/{zone['id']}/records",
        json={"name": name, "type": rtype, "values": values, "ttl": 300, "routing_policy": "Simple"},
        headers=auth_headers,
    )
    assert res.status_code == 201, (rtype, res.json())
    body = res.json()
    assert body["type"] == rtype
    assert body["values"] == values


@pytest.mark.parametrize("rtype,values", INVALID)
def test_create_invalid_record_rejected(client, auth_headers, zone, rtype, values):
    res = client.post(
        f"/api/hosted-zones/{zone['id']}/records",
        json={"name": "t.example.com.", "type": rtype, "values": values, "ttl": 300, "routing_policy": "Simple"},
        headers=auth_headers,
    )
    assert res.status_code == 422, (rtype, values)


def test_invalid_name_and_ttl_rejected(client, auth_headers, zone):
    bad_name = client.post(
        f"/api/hosted-zones/{zone['id']}/records",
        json={"name": "!!!", "type": "A", "values": ["192.0.2.1"], "ttl": 300, "routing_policy": "Simple"},
        headers=auth_headers,
    )
    assert bad_name.status_code == 422

    bad_ttl = client.post(
        f"/api/hosted-zones/{zone['id']}/records",
        json={"name": "t.example.com.", "type": "A", "values": ["192.0.2.1"], "ttl": 0, "routing_policy": "Simple"},
        headers=auth_headers,
    )
    assert bad_ttl.status_code == 422


def test_read_update_delete_record(client, auth_headers, zone):
    zid = zone["id"]
    created = client.post(
        f"/api/hosted-zones/{zid}/records",
        json={"name": "www.example.com.", "type": "A", "values": ["192.0.2.1"], "ttl": 300, "routing_policy": "Simple"},
        headers=auth_headers,
    ).json()

    fetched = client.get(f"/api/hosted-zones/{zid}/records/{created['id']}", headers=auth_headers)
    assert fetched.status_code == 200

    updated = client.patch(
        f"/api/hosted-zones/{zid}/records/{created['id']}",
        json={"values": ["203.0.113.7"], "ttl": 60, "routing_policy": "Weighted"},
        headers=auth_headers,
    )
    assert updated.status_code == 200
    assert updated.json()["values"] == ["203.0.113.7"]
    assert updated.json()["ttl"] == 60

    bad_update = client.patch(
        f"/api/hosted-zones/{zid}/records/{created['id']}",
        json={"values": ["not-an-ip"]},
        headers=auth_headers,
    )
    assert bad_update.status_code == 422

    assert client.delete(f"/api/hosted-zones/{zid}/records/{created['id']}", headers=auth_headers).status_code == 204
    assert client.get(f"/api/hosted-zones/{zid}/records/{created['id']}", headers=auth_headers).status_code == 404


def test_filter_search_pagination(client, auth_headers, zone):
    zid = zone["id"]
    client.post(
        f"/api/hosted-zones/{zid}/records",
        json={"name": "a1.example.com.", "type": "A", "values": ["192.0.2.1"], "ttl": 300, "routing_policy": "Simple"},
        headers=auth_headers,
    )
    client.post(
        f"/api/hosted-zones/{zid}/records",
        json={"name": "mail.example.com.", "type": "MX", "values": ["10 mail.example.com."], "ttl": 300, "routing_policy": "Simple"},
        headers=auth_headers,
    )

    only_a = client.get(f"/api/hosted-zones/{zid}/records?record_type=A", headers=auth_headers).json()
    assert only_a["total"] >= 1
    assert all(r["type"] == "A" for r in only_a["items"])

    search = client.get(f"/api/hosted-zones/{zid}/records?q=mail.example", headers=auth_headers).json()
    assert search["total"] >= 1

    paged = client.get(f"/api/hosted-zones/{zid}/records?page=1&page_size=1", headers=auth_headers).json()
    assert len(paged["items"]) == 1
    assert paged["total"] >= 3

    bad_filter = client.get(f"/api/hosted-zones/{zid}/records?record_type=BOGUS", headers=auth_headers)
    assert bad_filter.status_code == 422


def test_missing_zone_or_record_404(client, auth_headers, zone):
    assert client.get("/api/hosted-zones/NOPE/records", headers=auth_headers).status_code == 404
    assert client.get(f"/api/hosted-zones/{zone['id']}/records/999999", headers=auth_headers).status_code == 404
    assert client.patch(f"/api/hosted-zones/{zone['id']}/records/999999", json={"ttl": 60}, headers=auth_headers).status_code == 404
    assert client.delete(f"/api/hosted-zones/{zone['id']}/records/999999", headers=auth_headers).status_code == 404


def test_deleting_last_item_on_page_leaves_previous_page_intact(client, auth_headers, zone):
    zid = zone["id"]
    for i in range(4):
        res = client.post(
            f"/api/hosted-zones/{zid}/records",
            json={"name": f"h{i}.example.com.", "type": "A", "values": [f"192.0.2.{10 + i}"], "ttl": 300, "routing_policy": "Simple"},
            headers=auth_headers,
        )
        assert res.status_code == 201
    # Filter to A records so the last page holds a deletable item (apex NS/SOA sort last).
    last_page = client.get(
        f"/api/hosted-zones/{zid}/records?record_type=A&page=2&page_size=3", headers=auth_headers
    ).json()
    assert len(last_page["items"]) == 1
    assert client.delete(
        f"/api/hosted-zones/{zid}/records/{last_page['items'][0]['id']}", headers=auth_headers
    ).status_code == 204
    empty = client.get(
        f"/api/hosted-zones/{zid}/records?record_type=A&page=2&page_size=3", headers=auth_headers
    ).json()
    assert empty["items"] == []
    assert empty["total"] == 3
    prev = client.get(
        f"/api/hosted-zones/{zid}/records?record_type=A&page=1&page_size=3", headers=auth_headers
    ).json()
    assert len(prev["items"]) == 3
