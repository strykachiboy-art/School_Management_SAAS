# test/test_logout_route.py
import time

import pytest

from school_app.extensions import redis_client


@pytest.fixture(autouse=True)
def clear_redis_blocklist():
    """Ensure no leftover blocklist keys interfere between tests."""
    yield
    for key in redis_client.keys("blocklist:*"):
        redis_client.delete(key)


class TestLogout:
    def test_logout_success(self, client, user_with_password):
        headers = user_with_password["headers"]

        resp = client.post("/auth/logout", headers=headers)
        assert resp.status_code == 200
        assert resp.get_json()["message"] == "Successfully logged out"

    def test_logout_requires_auth(self, client):
        resp = client.post("/auth/logout")
        assert resp.status_code == 401

    def test_logout_adds_token_to_blocklist(self, client, user_with_password):
        headers = user_with_password["headers"]

        client.post("/auth/logout", headers=headers)

        keys = redis_client.keys("blocklist:*")
        assert len(keys) == 1

    def test_revoked_token_rejected_on_next_request(self, client, user_with_password):
        headers = user_with_password["headers"]

        # First logout succeeds
        first = client.post("/auth/logout", headers=headers)
        assert first.status_code == 200

        # Same token, reused on a second request — should now be rejected
        second = client.post("/auth/logout", headers=headers)
        assert second.status_code == 401

    def test_blocklist_ttl_matches_remaining_token_life(self, client, user_with_password):
        headers = user_with_password["headers"]

        client.post("/auth/logout", headers=headers)

        keys = redis_client.keys("blocklist:*")
        assert len(keys) == 1

        ttl = redis_client.ttl(keys[0])
        assert ttl > 0