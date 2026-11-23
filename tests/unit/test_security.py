from datetime import UTC, datetime, timedelta
from uuid import uuid4

import jwt
import pytest

from task_api.infrastructure.security import ArgonPasswords, JwtTokens


def test_password_is_argon2_and_verifies():
    passwords = ArgonPasswords()
    hashed = passwords.hash("A very long password")
    assert hashed.startswith("$argon2id$")
    assert passwords.verify("A very long password", hashed)
    assert not passwords.verify("incorrect password", hashed)


def test_token_requires_all_claims_and_fixed_algorithm():
    secret = "test-secret-at-least-thirty-two-bytes-long"
    tokens = JwtTokens(secret, "issuer", "audience")
    now = datetime.now(UTC)
    user_id, jti = uuid4(), uuid4()
    token = tokens.encode(user_id, jti, now, now + timedelta(minutes=30))
    assert tokens.decode(token) == (user_id, jti)
    forged = jwt.encode(
        {"sub": str(user_id), "exp": now + timedelta(minutes=30)}, secret, algorithm="HS256"
    )
    with pytest.raises(ValueError):
        tokens.decode(forged)
    prefix, signature = token.rsplit(".", 1)
    altered = prefix + "." + ("A" if signature[0] != "A" else "B") + signature[1:]
    with pytest.raises(ValueError):
        tokens.decode(altered)


@pytest.mark.parametrize("change", ["issuer", "audience", "expired", "future", "algorithm"])
def test_token_rejects_invalid_claims_and_algorithm(change):
    secret = "test-secret-at-least-thirty-two-bytes-long" + "x" * 32
    tokens = JwtTokens(secret, "issuer", "audience")
    now = datetime.now(UTC)
    payload = {
        "sub": str(uuid4()),
        "jti": str(uuid4()),
        "iat": now,
        "nbf": now,
        "exp": now + timedelta(minutes=30),
        "iss": "issuer",
        "aud": "audience",
    }
    if change == "issuer":
        payload["iss"] = "other"
    elif change == "audience":
        payload["aud"] = "other"
    elif change == "expired":
        payload["exp"] = now - timedelta(seconds=1)
    elif change == "future":
        payload["nbf"] = now + timedelta(minutes=5)
    algorithm = "HS384" if change == "algorithm" else "HS256"
    forged = jwt.encode(payload, secret, algorithm=algorithm)
    with pytest.raises(ValueError):
        tokens.decode(forged)
