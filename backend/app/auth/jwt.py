"""Supabase JWT 검증.

Supabase는 두 가지 서명 모드를 지원한다:

1. **Asymmetric (현행 권장)** — ES256/RS256으로 서명. 검증은 프로젝트의 JWKS
   엔드포인트(``{SUPABASE_URL}/auth/v1/.well-known/jwks.json``)에서 공개 키를
   조회해 수행. JWT 헤더의 ``kid``로 사용할 키를 식별.

2. **Symmetric (legacy)** — HS256으로 서명. 검증은 프로젝트의 ``JWT Secret``
   (Settings → API → JWT Settings)을 공유 비밀로 사용.

본 모듈은 두 모드를 모두 지원한다:
- JWT 헤더에 ``kid``가 있고 JWKS에서 일치하는 키를 찾으면 비대칭 검증.
- 그렇지 않으면 ``SUPABASE_JWT_SECRET``으로 HS256 fallback.

JWKS는 첫 호출 시 1회 fetch 후 메모리에 캐시. 미스매치 ``kid``를 만나면
1회 갱신 시도 후 재검증. 키 회전(key rotation)에 대응.
"""
from __future__ import annotations

from dataclasses import dataclass
from threading import Lock
from typing import Any
from uuid import UUID

import httpx
from jose import JWTError, jwt

from app.config import get_settings


class InvalidJWTError(Exception):
    """JWT 형식/서명/만료 등 검증 실패."""


class JWTSecretMissingError(Exception):
    """비대칭 키와 ``SUPABASE_JWT_SECRET`` 모두 미설정."""


@dataclass(frozen=True)
class AuthenticatedUser:
    """JWT에서 추출한 인증 사용자.

    DB의 profiles row 자체는 아님 — 후속 조회는 ``deps.get_current_user``에서.
    """
    id: UUID
    email: str | None
    role: str  # 보통 'authenticated'
    raw_claims: dict


# ---------------- JWKS 캐시 ----------------

_JWKS_CACHE: dict[str, dict[str, Any]] = {}  # kid -> JWK (dict)
_JWKS_LOCK = Lock()
_ASYMMETRIC_ALGS = ("ES256", "RS256", "ES384", "RS384", "ES512", "RS512")


def _jwks_url() -> str:
    return f"{get_settings().supabase_url.rstrip('/')}/auth/v1/.well-known/jwks.json"


def _refresh_jwks() -> None:
    """JWKS를 동기 fetch 해 ``_JWKS_CACHE``를 갱신.

    실패 시 캐시는 그대로 두고 예외 전파.
    """
    url = _jwks_url()
    with httpx.Client(timeout=5.0) as client:
        resp = client.get(url)
    resp.raise_for_status()
    keys = resp.json().get("keys", [])
    with _JWKS_LOCK:
        _JWKS_CACHE.clear()
        for key in keys:
            kid = key.get("kid")
            if kid:
                _JWKS_CACHE[kid] = key


def _get_jwk(kid: str, allow_refresh: bool = True) -> dict[str, Any] | None:
    """캐시에서 ``kid``로 JWK 조회. 미스 시 1회 refresh."""
    with _JWKS_LOCK:
        key = _JWKS_CACHE.get(kid)
    if key is not None:
        return key
    if not allow_refresh:
        return None
    try:
        _refresh_jwks()
    except (httpx.HTTPError, ValueError):
        return None
    with _JWKS_LOCK:
        return _JWKS_CACHE.get(kid)


# ---------------- 메인 검증 ----------------


def decode_supabase_jwt(token: str) -> AuthenticatedUser:
    """Supabase JWT를 검증하고 사용자 정보를 반환.

    Raises:
        JWTSecretMissingError: 비대칭 검증 실패 + ``SUPABASE_JWT_SECRET`` 미설정.
        InvalidJWTError: 토큰이 잘못됨 (서명/만료/audience 등).
    """
    try:
        header = jwt.get_unverified_header(token)
    except JWTError as exc:
        raise InvalidJWTError(f"Invalid JWT header: {exc}") from exc

    alg = header.get("alg", "")
    kid = header.get("kid")
    settings = get_settings()

    claims: dict[str, Any] | None = None

    # 1) 비대칭 — kid + asymmetric alg.
    if kid and alg in _ASYMMETRIC_ALGS:
        jwk = _get_jwk(kid)
        if jwk is not None:
            try:
                claims = jwt.decode(
                    token,
                    jwk,
                    algorithms=[alg],
                    audience="authenticated",
                    options={"verify_iss": False},
                )
            except JWTError as exc:
                raise InvalidJWTError(f"Invalid JWT: {exc}") from exc

    # 2) HS256 fallback (legacy / 비대칭 키 미발견).
    if claims is None:
        secret = settings.supabase_jwt_secret
        if not secret:
            raise JWTSecretMissingError(
                "Cannot verify JWT: no asymmetric key found for kid "
                f"{kid!r} and SUPABASE_JWT_SECRET is empty."
            )
        try:
            claims = jwt.decode(
                token,
                secret,
                algorithms=["HS256"],
                audience="authenticated",
                options={"verify_iss": False},
            )
        except JWTError as exc:
            raise InvalidJWTError(f"Invalid JWT: {exc}") from exc

    sub = claims.get("sub")
    if not sub:
        raise InvalidJWTError("JWT missing 'sub' claim")

    try:
        user_id = UUID(sub)
    except ValueError as exc:
        raise InvalidJWTError(f"JWT 'sub' is not a valid UUID: {sub}") from exc

    return AuthenticatedUser(
        id=user_id,
        email=claims.get("email"),
        role=claims.get("role", "authenticated"),
        raw_claims=claims,
    )
