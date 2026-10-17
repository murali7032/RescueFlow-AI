from __future__ import annotations

from datetime import datetime, timedelta, timezone


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"
    r2 = client.get("/api/v1/health")
    assert r2.status_code == 200


def test_create_donation_and_matches(client, auth_headers, seed_recipients, future_deadline):
    # seed_recipients uses db_session; need same DB as client.
    # Re-seed via API demo endpoint instead.
    pass


def test_demo_seed_and_donation_flow(client, auth_headers, future_deadline):
    seed = client.post("/api/v1/demo/seed", headers=auth_headers("admin"))
    assert seed.status_code == 200
    assert seed.json()["count"] == 4

    create = client.post(
        "/api/v1/donations",
        headers=auth_headers("donor"),
        json={
            "donor_name": "Harbor Bistro",
            "category": "vegetarian",
            "food_name": "Veg thali",
            "total_portions": 120,
            "pickup_deadline": future_deadline,
            "pickup_address": "12 Market St",
            "is_demo": True,
        },
    )
    assert create.status_code == 201, create.text
    body = create.json()
    assert body["remaining_portions"] == 120
    assert body["invitations_created"] >= 1
    donation_id = body["id"]

    matches = client.get(
        f"/api/v1/donations/{donation_id}/matches",
        headers=auth_headers("donor"),
    )
    assert matches.status_code == 200
    pending = [m for m in matches.json() if m["status"] == "pending"]
    assert sum(m["suggested_portions"] for m in pending) <= 120
    # Kitchen D excluded
    recipients = client.get("/api/v1/recipients", headers=auth_headers("admin")).json()
    d = next(r for r in recipients if r["name"] == "Community Kitchen D")
    assert all(m["recipient_id"] != d["id"] for m in pending)


def test_reject_invalid_quantity(client, auth_headers, future_deadline):
    client.post("/api/v1/demo/seed", headers=auth_headers("admin"))
    r = client.post(
        "/api/v1/donations",
        headers=auth_headers("donor"),
        json={
            "donor_name": "X",
            "category": "vegetarian",
            "total_portions": 0,
            "pickup_deadline": future_deadline,
        },
    )
    assert r.status_code == 422


def test_reject_past_deadline(client, auth_headers):
    client.post("/api/v1/demo/seed", headers=auth_headers("admin"))
    past = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat().replace(
        "+00:00", "Z"
    )
    r = client.post(
        "/api/v1/donations",
        headers=auth_headers("donor"),
        json={
            "donor_name": "X",
            "category": "vegetarian",
            "total_portions": 10,
            "pickup_deadline": past,
        },
    )
    assert r.status_code == 422


def test_accept_decline_via_api(client, auth_headers, future_deadline):
    client.post("/api/v1/demo/seed", headers=auth_headers("admin"))
    created = client.post(
        "/api/v1/donations",
        headers=auth_headers("donor"),
        json={
            "donor_name": "Harbor Bistro",
            "category": "vegetarian",
            "total_portions": 120,
            "pickup_deadline": future_deadline,
            "is_demo": True,
        },
    ).json()
    donation_id = created["id"]
    matches = client.get(
        f"/api/v1/donations/{donation_id}/matches",
        headers=auth_headers("admin"),
    ).json()
    pending = [m for m in matches if m["status"] == "pending"]
    # Decline the smallest offer if multiple, else first
    to_decline = sorted(pending, key=lambda m: m["suggested_portions"])[0]
    rid = to_decline["recipient_id"]
    dec = client.post(
        f"/api/v1/invitations/{to_decline['invitation_id']}/decline",
        headers=auth_headers("recipient", recipient_id=rid),
    )
    assert dec.status_code == 200, dec.text
    assert dec.json()["status"] == "declined"

    donation = client.get(
        f"/api/v1/donations/{donation_id}", headers=auth_headers("admin")
    ).json()
    assert donation["remaining_portions"] == 120

    matches2 = client.get(
        f"/api/v1/donations/{donation_id}/matches",
        headers=auth_headers("admin"),
    ).json()
    pending2 = [m for m in matches2 if m["status"] == "pending"]
    assert pending2
    accept_target = pending2[0]
    acc = client.post(
        f"/api/v1/invitations/{accept_target['invitation_id']}/accept",
        headers=auth_headers(
            "recipient", recipient_id=accept_target["recipient_id"]
        ),
    )
    assert acc.status_code == 200, acc.text
    assert acc.json()["pickup_status"] == "pending"
    assert acc.json()["portions"] > 0

    donation2 = client.get(
        f"/api/v1/donations/{donation_id}", headers=auth_headers("admin")
    ).json()
    assert donation2["remaining_portions"] == 120 - acc.json()["portions"]


def test_unauthorized_without_auth(client):
    # Demo mode still allows default admin via missing headers? get_current_user
    # with demo_mode uses default admin when headers missing.
    # Production would 401 — here we force by using a protected role check with bad role
    r = client.get(
        "/api/v1/admin/dashboard",
        headers={"X-Demo-Role": "donor"},
    )
    assert r.status_code == 403


def test_admin_dashboard(client, auth_headers, future_deadline):
    client.post("/api/v1/demo/seed", headers=auth_headers("admin"))
    client.post(
        "/api/v1/donations",
        headers=auth_headers("donor"),
        json={
            "donor_name": "Harbor Bistro",
            "category": "vegetarian",
            "total_portions": 120,
            "pickup_deadline": future_deadline,
            "is_demo": True,
        },
    )
    dash = client.get("/api/v1/admin/dashboard", headers=auth_headers("admin"))
    assert dash.status_code == 200
    body = dash.json()
    assert body["total_donations"] >= 1
    assert body["total_portions_donated"] >= 120
    assert "portions_allocated" in body
    assert "portions_pickup_completed" in body


def test_ai_explain_fallback(client, auth_headers, future_deadline):
    client.post("/api/v1/demo/seed", headers=auth_headers("admin"))
    created = client.post(
        "/api/v1/donations",
        headers=auth_headers("donor"),
        json={
            "donor_name": "Harbor Bistro",
            "category": "vegetarian",
            "total_portions": 120,
            "pickup_deadline": future_deadline,
            "is_demo": True,
        },
    ).json()
    r = client.post(
        "/api/v1/ai/explain-match",
        headers=auth_headers("admin"),
        json={"donation_id": created["id"]},
    )
    assert r.status_code == 200
    assert r.json()["source"] == "fallback"
    assert r.json()["summary"]


def test_timezone_naive_rejected(client, auth_headers):
    client.post("/api/v1/demo/seed", headers=auth_headers("admin"))
    # pydantic may accept naive datetime — our handler checks tzinfo
    naive = (datetime.now(timezone.utc) + timedelta(hours=2)).strftime(
        "%Y-%m-%dT%H:%M:%S"
    )
    r = client.post(
        "/api/v1/donations",
        headers=auth_headers("donor"),
        json={
            "donor_name": "X",
            "category": "vegetarian",
            "total_portions": 10,
            "pickup_deadline": naive,
        },
    )
    assert r.status_code == 422
