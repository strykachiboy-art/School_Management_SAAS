import pytest
from school_app.auth.services.login import issue_tokens
from school_app.extensions import limiter 


def test_refresh_token_success(client, app, base_user):
    """Test successful token refresh when whitelisted in Redis."""
    with app.app_context():
        tokens = issue_tokens(base_user)
        refresh_token = tokens["refresh_token"]

    headers = {
        "Authorization": f"Bearer {refresh_token}",
        "Accept": "application/json"
    }

    response = client.post("/auth/refresh", headers=headers)

    if response.status_code != 200:
        print("FAIL REASON:", response.get_json())

    assert response.status_code == 200
    data = response.get_json()
    assert data.get("status") == "success"
    assert "access_token" in data



def test_refresh_token_rate_limit(client, app, base_user):
    """Test Flask-Limiter enforcing 10 requests per minute on POST /auth/refresh."""
    # Force Flask-Limiter extension to active state for this test
    limiter.enabled = True
    app.config["RATELIMIT_ENABLED"] = True

    remote_ip = {"REMOTE_ADDR": "127.0.0.1"}

    # First 10 requests succeed
    for _ in range(10):
        with app.app_context():
            tokens = issue_tokens(base_user)
            refresh_token = tokens["refresh_token"]

        headers = {
            "Authorization": f"Bearer {refresh_token}",
            "Accept": "application/json"
        }

        res = client.post("/auth/refresh", headers=headers, environ_base=remote_ip)
        assert res.status_code == 200

    # 11th request MUST be blocked
    with app.app_context():
        tokens = issue_tokens(base_user)
        refresh_token = tokens["refresh_token"]

    headers = {
        "Authorization": f"Bearer {refresh_token}",
        "Accept": "application/json"
    }

    res = client.post("/auth/refresh", headers=headers, environ_base=remote_ip)
    assert res.status_code == 429