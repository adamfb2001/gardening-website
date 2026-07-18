"""Per-device rate limiting (spec §6: 30/hour, 200/day; tested with low limits)."""

from uuid import uuid4

from fastapi.testclient import TestClient

from clipnotes.main import create_app
from clipnotes.ratelimit import RateLimiter
from conftest import make_settings

URL = "https://www.youtube.com/shorts/ratelimit-test"


def _register(client: TestClient) -> dict:
    return {"Authorization": f"Bearer {client.post('/v1/devices').json()['token']}"}


def _submit(client: TestClient, headers: dict):
    return client.post(
        "/v1/jobs", json={"client_id": str(uuid4()), "url": URL}, headers=headers
    )


def test_hourly_limit_enforced_per_device():
    app = create_app(make_settings(rate_limit_per_hour=3, rate_limit_per_day=100))
    with TestClient(app) as client:
        headers = _register(client)
        for _ in range(3):
            assert _submit(client, headers).status_code == 201

        blocked = _submit(client, headers)
        assert blocked.status_code == 429
        detail = blocked.json()["detail"]
        assert detail["code"] == "rate_limited"
        assert detail["retryable"] is True
        assert int(blocked.headers["Retry-After"]) > 0

        # Another device is unaffected.
        assert _submit(client, _register(client)).status_code == 201


def test_idempotent_replay_not_charged_against_limit():
    app = create_app(make_settings(rate_limit_per_hour=1, rate_limit_per_day=100))
    with TestClient(app) as client:
        headers = _register(client)
        payload = {"client_id": str(uuid4()), "url": URL}
        assert client.post("/v1/jobs", json=payload, headers=headers).status_code == 201
        # Replaying the same client_id after the limit is reached still works.
        assert client.post("/v1/jobs", json=payload, headers=headers).status_code == 200


def test_sliding_windows():
    clock = {"now": 1_000_000.0}
    limiter = RateLimiter(per_hour=2, per_day=3, clock=lambda: clock["now"])

    assert limiter.try_acquire("device") is None
    assert limiter.try_acquire("device") is None
    retry_after = limiter.try_acquire("device")
    assert retry_after is not None and 0 < retry_after <= 3600

    # The hourly window frees up...
    clock["now"] += 3601
    assert limiter.try_acquire("device") is None

    # ...but the daily cap still holds and reports a day-scale wait.
    retry_after = limiter.try_acquire("device")
    assert retry_after is not None and retry_after > 3600
