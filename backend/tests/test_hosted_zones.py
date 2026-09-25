"""Hosted zone CRUD, search, pagination, cascade."""


def test_create_zone_returns_ns_soa(client, auth_headers):
    res = client.post(
        "/api/hosted-zones",
        json={"name": "shop.example", "description": "storefront", "type": "Public"},
        headers=auth_headers,
    )
    assert res.status_code == 201
    body = res.json()
    assert body["name"] == "shop.example."
    assert body["record_count"] == 2

    records = client.get(f"/api/hosted-zones/{body['id']}/records", headers=auth_headers).json()
    assert {r["type"] for r in records["items"]} >= {"NS", "SOA"}


def test_get_update_zone(client, auth_headers, zone):
    zid = zone["id"]
    assert client.get(f"/api/hosted-zones/{zid}", headers=auth_headers).status_code == 200

    upd = client.patch(
        f"/api/hosted-zones/{zid}",
        json={"description": "updated", "type": "Private"},
        headers=auth_headers,
    )
    assert upd.status_code == 200
    assert upd.json()["description"] == "updated"
    assert upd.json()["type"] == "Private"


def test_duplicate_zone_conflict_case_insensitive(client, auth_headers, zone):
    res = client.post(
        "/api/hosted-zones",
        json={"name": "EXAMPLE.com"},
        headers=auth_headers,
    )
    assert res.status_code == 409


def test_invalid_zone_name_rejected(client, auth_headers):
    for bad in ["not a domain!!!", "", "a" * 300]:
        res = client.post("/api/hosted-zones", json={"name": bad}, headers=auth_headers)
        assert res.status_code == 422, bad


def test_search_zones(client, auth_headers):
    for name in ["alpha-search.test", "beta-search.test"]:
        client.post("/api/hosted-zones", json={"name": name}, headers=auth_headers)
    res = client.get("/api/hosted-zones?q=alpha-search", headers=auth_headers)
    assert res.status_code == 200
    assert res.json()["total"] == 1
    assert res.json()["items"][0]["name"] == "alpha-search.test."


def test_pagination(client, auth_headers):
    for i in range(5):
        client.post("/api/hosted-zones", json={"name": f"page{i}.test"}, headers=auth_headers)
    first = client.get("/api/hosted-zones?page=1&page_size=2", headers=auth_headers).json()
    second = client.get("/api/hosted-zones?page=2&page_size=2", headers=auth_headers).json()
    assert first["total"] >= 5
    assert len(first["items"]) == 2
    assert len(second["items"]) == 2
    assert {z["id"] for z in first["items"]}.isdisjoint({z["id"] for z in second["items"]})


def test_delete_zone_cascades_records(client, auth_headers, zone):
    zid = zone["id"]
    rec = client.post(
        f"/api/hosted-zones/{zid}/records",
        json={"name": "www.example.com.", "type": "A", "values": ["192.0.2.9"], "ttl": 300, "routing_policy": "Simple"},
        headers=auth_headers,
    )
    assert rec.status_code == 201

    assert client.delete(f"/api/hosted-zones/{zid}", headers=auth_headers).status_code == 204
    assert client.get(f"/api/hosted-zones/{zid}", headers=auth_headers).status_code == 404
    # Records of a deleted zone are gone with it (zone lookup itself 404s).
    assert client.get(f"/api/hosted-zones/{zid}/records", headers=auth_headers).status_code == 404


def test_missing_zone_404(client, auth_headers):
    assert client.get("/api/hosted-zones/NOPE", headers=auth_headers).status_code == 404
    assert client.patch("/api/hosted-zones/NOPE", json={"description": "x"}, headers=auth_headers).status_code == 404
    assert client.delete("/api/hosted-zones/NOPE", headers=auth_headers).status_code == 404


def test_out_of_range_page_returns_empty_with_correct_total(client, auth_headers):
    for i in range(3):
        client.post("/api/hosted-zones", json={"name": f"rangetest{i}.test"}, headers=auth_headers)
    res = client.get("/api/hosted-zones?page=99&page_size=20", headers=auth_headers).json()
    assert res["items"] == []
    assert res["total"] >= 3
    assert res["page"] == 99


def test_deleting_last_item_on_page_leaves_previous_page_intact(client, auth_headers):
    ids = []
    for i in range(3):
        res = client.post("/api/hosted-zones", json={"name": f"shrink{i}.test"}, headers=auth_headers)
        ids.append(res.json()["id"])
    page2 = client.get("/api/hosted-zones?page=2&page_size=2", headers=auth_headers).json()
    assert len(page2["items"]) >= 1
    for item in page2["items"]:
        assert client.delete(f"/api/hosted-zones/{item['id']}", headers=auth_headers).status_code == 204
    # Page 2 is now empty, but page 1 still serves the remaining zones.
    assert client.get("/api/hosted-zones?page=2&page_size=2", headers=auth_headers).json()["items"] == []
    page1 = client.get("/api/hosted-zones?page=1&page_size=2", headers=auth_headers).json()
    assert len(page1["items"]) > 0
