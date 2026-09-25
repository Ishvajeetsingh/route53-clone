"""Health + mocked auth behavior."""


def test_health_ok(client):
    res = client.get("/api/health")
    assert res.status_code == 200
    assert res.json()["ok"] is True


def test_login_me_logout_flow(client):
    login = client.post("/api/auth/login", json={"username": "alice", "password": "whatever"})
    assert login.status_code == 200
    token = login.json()["token"]
    headers = {"Authorization": f"Bearer {token}"}

    me = client.get("/api/auth/me", headers=headers)
    assert me.status_code == 200
    assert me.json()["user"]["username"] == "alice"

    logout = client.post("/api/auth/logout", headers=headers)
    assert logout.status_code == 200

    # Token is invalid after logout.
    assert client.get("/api/auth/me", headers=headers).status_code == 401


def test_protected_routes_require_auth(client):
    assert client.get("/api/hosted-zones").status_code == 401
    assert client.get("/api/stats/summary").status_code == 401
    assert client.get("/api/hosted-zones/Z123/records").status_code == 401


def test_invalid_token_rejected(client):
    assert client.get("/api/auth/me", headers={"Authorization": "Bearer bogus"}).status_code == 401
    assert client.get("/api/hosted-zones", headers={"Authorization": "Bearer bogus"}).status_code == 401


def test_stats_summary_requires_data_shape(client, auth_headers, zone):
    res = client.get("/api/stats/summary", headers=auth_headers)
    assert res.status_code == 200
    body = res.json()
    assert body["hosted_zones"] >= 1
    assert body["records"] >= 2  # auto-created NS + SOA
