"""Device registration and token verification."""

from uuid import uuid4

import jwt

from conftest import TEST_SECRET


def test_register_device_issues_token(client):
    response = client.post("/v1/devices")
    assert response.status_code == 201
    body = response.json()
    assert set(body) == {"device_id", "token", "expires_at"}
    assert jwt.decode(body["token"], TEST_SECRET, algorithms=["HS256"])["sub"] == body["device_id"]


def test_job_endpoints_require_auth(client):
    payload = {"client_id": str(uuid4()), "url": "https://youtube.com/shorts/abc"}
    assert client.post("/v1/jobs", json=payload).status_code == 401
    assert client.get("/v1/jobs").status_code == 401
    assert client.get("/v1/jobs/some-id").status_code == 401
    assert client.post("/v1/jobs/some-id/retry").status_code == 401
    assert client.delete("/v1/jobs/some-id").status_code == 401


def test_garbage_token_rejected(client):
    response = client.get("/v1/jobs", headers={"Authorization": "Bearer garbage"})
    assert response.status_code == 401


def test_non_bearer_scheme_rejected(client):
    response = client.get("/v1/jobs", headers={"Authorization": "Basic dXNlcjpwYXNz"})
    assert response.status_code == 401


def test_token_signed_with_wrong_secret_rejected(client):
    forged = jwt.encode(
        {"sub": "attacker", "exp": 4102444800},
        "wrong-secret-0123456789abcdef-0123456789abcdef",
        algorithm="HS256",
    )
    response = client.get("/v1/jobs", headers={"Authorization": f"Bearer {forged}"})
    assert response.status_code == 401
