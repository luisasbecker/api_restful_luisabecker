from datetime import datetime
from uuid import UUID

import jwt
from pwdlib import PasswordHash


class ArgonPasswords:
    def __init__(self):
        self.hasher = PasswordHash.recommended()

    def hash(self, password: str) -> str:
        return self.hasher.hash(password)

    def verify(self, password: str, password_hash: str) -> bool:
        return self.hasher.verify(password, password_hash)


class JwtTokens:
    def __init__(self, secret: str, issuer: str, audience: str):
        self.secret = secret
        self.issuer = issuer
        self.audience = audience

    def encode(self, user_id: UUID, jti: UUID, now: datetime, expires_at: datetime) -> str:
        return jwt.encode(
            {
                "sub": str(user_id),
                "jti": str(jti),
                "iat": now,
                "nbf": now,
                "exp": expires_at,
                "iss": self.issuer,
                "aud": self.audience,
            },
            self.secret,
            algorithm="HS256",
        )

    def decode(self, token: str) -> tuple[UUID, UUID]:
        try:
            claims = jwt.decode(
                token,
                self.secret,
                algorithms=["HS256"],
                issuer=self.issuer,
                audience=self.audience,
                options={"require": ["sub", "jti", "iat", "nbf", "exp", "iss", "aud"]},
            )
            return UUID(claims["sub"]), UUID(claims["jti"])
        except (jwt.PyJWTError, ValueError, KeyError, TypeError) as exc:
            raise ValueError("Token inválido") from exc
