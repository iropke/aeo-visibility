"""IP 기반 rate limiter — in-memory sliding window.

Phase 1 단일 uvicorn worker 가정. 멀티 인스턴스 도입 시점에 Redis sorted set
구현으로 교체 (인터페이스 동일 — ``check_and_record(key, *, max_requests, window_s)``).

사용처: ``app.routers.contact`` (POST /api/contact) — bot/abuse 방지.
도메인 무관 ``X-Forwarded-For`` 또는 client.host 를 키로 사용.

설계:
    - 키별 sliding window 의 timestamp deque (`collections.deque`).
    - lock=asyncio.Lock — async 라우터 환경에서 atomic check+record.
    - window_s 보다 오래된 timestamp 자동 evict (메모리 보호).
    - 키 자체는 어뷰저 추적 hash (sha256(salt+ip)) 와 동일 사용 가능.

PII 정책: 평문 IP 저장 ❌ — caller 가 hash 후 전달.
"""
from __future__ import annotations

import asyncio
import hashlib
import time
from collections import deque
from collections.abc import Iterable

# 키 → 최근 요청 timestamp deque. 모듈 전역 (단일 worker).
_buckets: dict[str, deque[float]] = {}
_lock = asyncio.Lock()

# Phase 1 Contact 폼 기본 한도 — 1분 3회. caller 가 override 가능.
DEFAULT_MAX_REQUESTS: int = 3
DEFAULT_WINDOW_SECONDS: int = 60


async def check_and_record(
    key: str,
    *,
    max_requests: int = DEFAULT_MAX_REQUESTS,
    window_s: int = DEFAULT_WINDOW_SECONDS,
) -> bool:
    """``key`` 의 요청을 기록하고, ``max_requests/window_s`` 한도 내인지 반환.

    True  = 한도 내 (요청 통과)
    False = 한도 초과 (라우터에서 429 반환)

    한도 초과 시에도 timestamp 는 기록 ❌ — 추가 요청이 한도 자동 회복 막지 않게.
    """
    now = time.monotonic()
    async with _lock:
        bucket = _buckets.get(key)
        if bucket is None:
            bucket = deque()
            _buckets[key] = bucket

        # window 밖 timestamp evict.
        cutoff = now - window_s
        while bucket and bucket[0] < cutoff:
            bucket.popleft()

        if len(bucket) >= max_requests:
            return False

        bucket.append(now)
        return True


def hash_ip(ip: str, salt: str = "") -> str:
    """평문 IP → sha256(salt + ip). 어뷰저 추적/rate limit 키 생성용.

    salt 는 호출자가 환경변수로 주입 (예: ``CONTACT_IP_HASH_SALT``).
    빈 salt 도 허용 — 단일 인스턴스 환경에서는 충돌 가능성 무시할 수준.
    """
    h = hashlib.sha256()
    h.update(salt.encode("utf-8"))
    h.update(b":")
    h.update(ip.encode("utf-8"))
    return h.hexdigest()


def reset_buckets(keys: Iterable[str] | None = None) -> None:
    """테스트 / 디버깅용 — 특정 키들만 또는 전체 reset."""
    if keys is None:
        _buckets.clear()
        return
    for k in keys:
        _buckets.pop(k, None)
