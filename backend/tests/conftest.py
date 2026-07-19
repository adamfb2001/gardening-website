import time
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from clipnotes.config import Settings
from clipnotes.main import create_app

TEST_SECRET = "test-secret-0123456789abcdef-0123456789abcdef"


def make_settings(**overrides) -> Settings:
    defaults = dict(
        secret_key=TEST_SECRET,
        stage_delay_seconds=0.0,
        worker_concurrency=2,
        pipeline_mode="stub",
    )
    defaults.update(overrides)
    return Settings(**defaults)


@pytest.fixture
def client():
    app = create_app(make_settings())
    # The context manager runs the lifespan, which starts the worker pool.
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def auth_headers(client):
    response = client.post("/v1/devices")
    assert response.status_code == 201, response.text
    return {"Authorization": f"Bearer {response.json()['token']}"}


@pytest.fixture
def submit(client, auth_headers):
    """POST a job and return the response body."""

    def _submit(url: str, client_id=None, expect: int = 201) -> dict:
        payload = {"client_id": str(client_id or uuid4()), "url": url}
        response = client.post("/v1/jobs", json=payload, headers=auth_headers)
        assert response.status_code == expect, response.text
        return response.json()

    return _submit


@pytest.fixture
def wait_terminal(client, auth_headers):
    """Poll a job until it reaches complete/failed and return the body."""

    def _wait(job_id: str, timeout: float = 5.0) -> dict:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            response = client.get(f"/v1/jobs/{job_id}", headers=auth_headers)
            assert response.status_code == 200, response.text
            body = response.json()
            if body["status"] in ("complete", "failed"):
                return body
            time.sleep(0.01)
        pytest.fail(f"job {job_id} did not reach a terminal state within {timeout}s")

    return _wait
