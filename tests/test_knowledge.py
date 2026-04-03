"""Tests for the User Knowledge API endpoints (add / list / delete)."""

from __future__ import annotations

import uuid


# ── POST /knowledge/add ───────────────────────────────────────────────────────

def test_add_single_paragraph(client):
    resp = client.post(
        "/api/v1/ai/knowledge/add",
        json={
            "user_id": "u_test_add",
            "text": "I am a backend engineer with 5 years of Python experience.",
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    assert body["chunks_added"] >= 1
    assert isinstance(body["contexts"], list) and body["contexts"]  # auto-detected
    assert isinstance(body["chunks"], list)
    assert len(body["chunks"]) == body["chunks_added"]


def test_add_multi_paragraph_splits_correctly(client):
    resp = client.post(
        "/api/v1/ai/knowledge/add",
        json={
            "user_id": "u_test_split",
            "text": (
                "I specialise in cloud architecture and AWS services.\n\n"
                "My favourite databases are PostgreSQL and Redis.\n\n"
                "I have led teams of up to 10 engineers."
            ),
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["chunks_added"] == 3
    texts = [c["text"] for c in body["chunks"]]
    assert any("cloud" in t.lower() for t in texts)
    assert any("redis" in t.lower() for t in texts)


def test_add_with_explicit_context(client):
    resp = client.post(
        "/api/v1/ai/knowledge/add",
        json={
            "user_id": "u_test_ctx",
            "text": "Built a React Native app for iOS and Android.",
            "context": "projects",
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["contexts"] == ["projects"]


def test_add_chunk_has_id_and_category(client):
    resp = client.post(
        "/api/v1/ai/knowledge/add",
        json={
            "user_id": "u_test_fields",
            "text": "Expert in Kubernetes and container orchestration.",
        },
    )
    assert resp.status_code == 200
    chunk = resp.json()["chunks"][0]
    assert "id" in chunk
    assert "category" in chunk
    assert len(chunk["category"]) > 0


def test_add_empty_text_rejected(client):
    resp = client.post(
        "/api/v1/ai/knowledge/add",
        json={"user_id": "u_test_empty", "text": ""},
    )
    assert resp.status_code == 422


def test_add_too_short_text_returns_422(client):
    resp = client.post(
        "/api/v1/ai/knowledge/add",
        json={"user_id": "u_test_short", "text": "Hi"},
    )
    assert resp.status_code == 422


def test_add_without_user_id_stores_as_global(client):
    """Omitting user_id should succeed — stored as global knowledge (user_id=NULL)."""
    resp = client.post(
        "/api/v1/ai/knowledge/add",
        json={"text": "Some meaningful knowledge text here."},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert data["chunks_added"] >= 1


# ── GET /knowledge/{user_id} ──────────────────────────────────────────────────

def test_list_returns_chunks_for_user(client):
    user_id = f"u_list_{uuid.uuid4().hex[:8]}"

    # First add something
    client.post(
        "/api/v1/ai/knowledge/add",
        json={"user_id": user_id, "text": "Unique knowledge for listing test."},
    )

    resp = client.get(f"/api/v1/ai/knowledge/{user_id}")
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    assert body["user_id"] == user_id
    assert body["total"] >= 1
    assert len(body["chunks"]) == body["total"]


def test_list_unknown_user_returns_empty(client):
    resp = client.get("/api/v1/ai/knowledge/no_such_user_xyz_999")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 0
    assert body["chunks"] == []


def test_list_context_filter(client):
    user_id = f"u_filter_{uuid.uuid4().hex[:8]}"

    client.post(
        "/api/v1/ai/knowledge/add",
        json={"user_id": user_id, "text": "My portfolio includes e-commerce apps.", "context": "portfolio"},
    )
    client.post(
        "/api/v1/ai/knowledge/add",
        json={"user_id": user_id, "text": "I graduated from a Computer Science program.", "context": "profile"},
    )

    resp = client.get(f"/api/v1/ai/knowledge/{user_id}?context=portfolio")
    assert resp.status_code == 200
    body = resp.json()
    assert all(c["context"] == "portfolio" for c in body["chunks"])


def test_list_chunk_has_required_fields(client):
    user_id = f"u_fields_{uuid.uuid4().hex[:8]}"
    client.post(
        "/api/v1/ai/knowledge/add",
        json={"user_id": user_id, "text": "Certified AWS Solutions Architect.", "context": "profile"},
    )
    resp = client.get(f"/api/v1/ai/knowledge/{user_id}")
    assert resp.status_code == 200
    chunk = resp.json()["chunks"][0]
    for field in ("id", "context", "category", "text"):
        assert field in chunk, f"Field '{field}' missing from chunk"


# ── DELETE /knowledge/{user_id}/{chunk_id} ────────────────────────────────────

def test_delete_existing_chunk(client):
    user_id = f"u_del_{uuid.uuid4().hex[:8]}"

    # Add a chunk to delete
    add_resp = client.post(
        "/api/v1/ai/knowledge/add",
        json={"user_id": user_id, "text": "This chunk will be deleted.", "context": "general"},
    )
    chunk_id = add_resp.json()["chunks"][0]["id"]

    del_resp = client.delete(f"/api/v1/ai/knowledge/{user_id}/{chunk_id}")
    assert del_resp.status_code == 200
    body = del_resp.json()
    assert body["success"] is True
    assert body["deleted"] is True
    assert body["chunk_id"] == chunk_id


def test_delete_nonexistent_chunk_returns_deleted_false(client):
    resp = client.delete("/api/v1/ai/knowledge/any_user/00000000-0000-0000-0000-000000000000")
    assert resp.status_code == 200
    assert resp.json()["deleted"] is False


def test_delete_wrong_user_cannot_delete(client):
    owner_id = f"owner_{uuid.uuid4().hex[:8]}"
    attacker_id = f"attacker_{uuid.uuid4().hex[:8]}"

    # Owner adds a chunk
    add_resp = client.post(
        "/api/v1/ai/knowledge/add",
        json={"user_id": owner_id, "text": "Owner-only knowledge content here.", "context": "profile"},
    )
    chunk_id = add_resp.json()["chunks"][0]["id"]

    # Attacker tries to delete it
    del_resp = client.delete(f"/api/v1/ai/knowledge/{attacker_id}/{chunk_id}")
    assert del_resp.status_code == 200
    assert del_resp.json()["deleted"] is False

    # Owner can still see their chunk
    list_resp = client.get(f"/api/v1/ai/knowledge/{owner_id}")
    ids = [c["id"] for c in list_resp.json()["chunks"]]
    assert chunk_id in ids


def test_delete_then_list_reflects_removal(client):
    user_id = f"u_dellist_{uuid.uuid4().hex[:8]}"

    add_resp = client.post(
        "/api/v1/ai/knowledge/add",
        json={"user_id": user_id, "text": "Temporary knowledge entry for delete test.", "context": "general"},
    )
    chunk_id = add_resp.json()["chunks"][0]["id"]

    client.delete(f"/api/v1/ai/knowledge/{user_id}/{chunk_id}")

    list_resp = client.get(f"/api/v1/ai/knowledge/{user_id}")
    ids = [c["id"] for c in list_resp.json()["chunks"]]
    assert chunk_id not in ids
