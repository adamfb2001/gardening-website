"""Tests for the API contract (spec §6) and the note schema (spec §4.4)."""

from datetime import datetime, timedelta, timezone
from uuid import uuid4

from clipnotes.models import Category, Note

SHORT_URL = "https://www.youtube.com/shorts/dQw4w9WgXcQ?si=SHARE123"


def test_healthz(client):
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_create_job_matches_contract_shape(submit):
    body = submit(SHORT_URL)
    assert set(body) == {"job_id", "status", "dedup_of"}
    assert body["status"] == "queued"
    assert body["dedup_of"] is None


def test_job_completes_with_schema_valid_note(submit, wait_terminal):
    job = submit(SHORT_URL)
    body = wait_terminal(job["job_id"])

    assert body["status"] == "complete"
    assert body["progress"] == 1.0
    assert body["error"] is None

    note = Note.model_validate(body["note"])
    assert isinstance(note.category, Category)
    assert len(note.title) <= 70
    assert 0.0 <= note.confidence.overall <= 1.0
    # Stub notes must be honest about being stubs (never-fabricate rule).
    assert any("stub" in caveat.lower() for caveat in note.caveats)


def test_invalid_urls_rejected_with_422(client, auth_headers):
    for bad_url in ("not-a-url", "ftp://example.com/video", ""):
        response = client.post(
            "/v1/jobs",
            json={"client_id": str(uuid4()), "url": bad_url},
            headers=auth_headers,
        )
        assert response.status_code == 422, bad_url


def test_missing_job_returns_404(client, auth_headers):
    assert client.get("/v1/jobs/doesnotexist", headers=auth_headers).status_code == 404


def test_jobs_are_scoped_to_their_device(client, auth_headers, submit, wait_terminal):
    job = submit(SHORT_URL)
    wait_terminal(job["job_id"])

    other = client.post("/v1/devices").json()
    other_headers = {"Authorization": f"Bearer {other['token']}"}
    response = client.get(f"/v1/jobs/{job['job_id']}", headers=other_headers)
    assert response.status_code == 404


def test_list_jobs_with_since_filter(client, auth_headers, submit, wait_terminal):
    job = submit(SHORT_URL)
    wait_terminal(job["job_id"])

    everything = client.get("/v1/jobs", headers=auth_headers).json()
    assert [item["job_id"] for item in everything["jobs"]] == [job["job_id"]]

    past = "2000-01-01T00:00:00Z"
    response = client.get("/v1/jobs", params={"since": past}, headers=auth_headers)
    assert len(response.json()["jobs"]) == 1

    future = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
    response = client.get("/v1/jobs", params={"since": future}, headers=auth_headers)
    assert response.json()["jobs"] == []

    response = client.get("/v1/jobs", params={"since": "not-a-date"}, headers=auth_headers)
    assert response.status_code == 422


def test_delete_job(client, auth_headers, submit, wait_terminal):
    job = submit(SHORT_URL)
    wait_terminal(job["job_id"])

    assert client.delete(f"/v1/jobs/{job['job_id']}", headers=auth_headers).status_code == 204
    assert client.get(f"/v1/jobs/{job['job_id']}", headers=auth_headers).status_code == 404
    assert client.delete(f"/v1/jobs/{job['job_id']}", headers=auth_headers).status_code == 404


def test_retry_failed_job(client, auth_headers, submit, wait_terminal):
    job = submit("https://www.youtube.com/shorts/stub-unavailable")
    body = wait_terminal(job["job_id"])
    assert body["status"] == "failed"
    assert body["error"]["retryable"] is True

    response = client.post(f"/v1/jobs/{job['job_id']}/retry", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["error"] is None

    # The stub is deterministic, so the retry fails the same way.
    body = wait_terminal(job["job_id"])
    assert body["status"] == "failed"
    assert body["error"]["code"] == "media_unavailable"


def test_retry_of_completed_job_conflicts(client, auth_headers, submit, wait_terminal):
    job = submit(SHORT_URL)
    wait_terminal(job["job_id"])
    response = client.post(f"/v1/jobs/{job['job_id']}/retry", headers=auth_headers)
    assert response.status_code == 409


def test_client_id_replay_is_idempotent(client, auth_headers, wait_terminal):
    """The share extension may submit the same client_id twice (fast enqueue +
    background re-submission); the second call must not create a second job."""
    client_id = str(uuid4())
    payload = {"client_id": client_id, "url": SHORT_URL}

    first = client.post("/v1/jobs", json=payload, headers=auth_headers)
    assert first.status_code == 201
    second = client.post("/v1/jobs", json=payload, headers=auth_headers)
    assert second.status_code == 200
    assert second.json()["job_id"] == first.json()["job_id"]

    wait_terminal(first.json()["job_id"])
    listing = client.get("/v1/jobs", headers=auth_headers).json()
    assert len(listing["jobs"]) == 1


def test_reshared_url_sets_dedup_of(submit):
    first = submit(SHORT_URL)
    # Same clip, different share-tracking params → same canonical URL.
    second = submit("https://youtube.com/shorts/dQw4w9WgXcQ?si=OTHER&utm_source=share")
    assert second["job_id"] != first["job_id"]
    assert second["dedup_of"] == first["job_id"]
