"""i18n 번역 스크립트 (Claude Haiku) — F-i18n-1 청크.

영어 마스터 JSON/HTML → 19 target lang 자동 생성.
빌드 시점 정적 생성 (런타임 LLM 호출 ❌). 결과 파일은 git commit.

사용법:
    # frontend/messages/en.json → 19 lang 생성
    python -m scripts.translate_i18n messages

    # 특정 lang 만 (디버그)
    python -m scripts.translate_i18n messages --lang ko

    # 강제 재생성 (캐싱 무시)
    python -m scripts.translate_i18n messages --force

    # 메일 템플릿 (F-i18n-2 청크에서 사용)
    python -m scripts.translate_i18n emails

전략:
    - **캐싱:** target 파일이 이미 존재하고 동일 키 + 동일 영어 원문이면 skip.
      변경된/새로운 leaf 만 LLM 호출.
    - **ICU placeholder 보호:** ``{var}`` / ``{count, plural, ...}`` 는 시스템 프롬프트로
      "do not translate" 명시.
    - **HTML 태그 보호:** 메일 템플릿은 HTML 구조 보존 — 시스템 프롬프트 명시.
    - **배치:** lang 별 1회 호출에 모든 변경 leaf 를 dict 로 전달 → API 호출 최소화.
    - **모델:** Claude Haiku 4.5 (저비용, 충분한 품질).

비용 추정: 영어 마스터 ~5KB, 19 lang × ~1500 tokens output ≈ $0.05/run.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

import anthropic


# ─── 경로 ─────────────────────────────────────────────────────────────────

ROOT: Path = Path(__file__).parent.parent.parent  # repo root
FRONTEND_MESSAGES: Path = ROOT / "frontend" / "src" / "messages"
BACKEND_TEMPLATES: Path = ROOT / "backend" / "app" / "templates"


# ─── 20 lang 메타 (core.locales 미러, 본 스크립트가 단독 실행 가능하도록 inline) ───

# (code, native name, english name, rtl)
LOCALES: list[tuple[str, str, str, bool]] = [
    ("en", "English", "English", False),
    ("zh", "中文", "Mandarin", False),
    ("ja", "日本語", "Japanese", False),
    ("de", "Deutsch", "German", False),
    ("fr", "Français", "French", False),
    ("es", "Español", "Spanish", False),
    ("ko", "한국어", "Korean", False),
    ("pt", "Português", "Portuguese", False),
    ("hi", "हिन्दी", "Hindi", False),
    ("ru", "Русский", "Russian", False),
    ("nl", "Nederlands", "Dutch", False),
    ("it", "Italiano", "Italian", False),
    ("ar", "العربية", "Arabic", True),
    ("sv", "Svenska", "Swedish", False),
    ("th", "ไทย", "Thai", False),
    ("pl", "Polski", "Polish", False),
    ("id", "Bahasa Indonesia", "Indonesian", False),
    ("ms", "Bahasa Melayu", "Malay", False),
    ("da", "Dansk", "Danish", False),
    ("tr", "Türkçe", "Turkish", False),
]

SOURCE_LANG: str = "en"
TARGET_LANGS: list[tuple[str, str, str]] = [
    (code, native, eng) for code, native, eng, _ in LOCALES if code != SOURCE_LANG
]


# ─── 모델 ─────────────────────────────────────────────────────────────────

MODEL: str = "claude-haiku-4-5-20251001"
MAX_TOKENS: int = 8192


# ─── JSON leaf walker ─────────────────────────────────────────────────────

def _flatten(obj: Any, prefix: str = "") -> dict[str, str]:
    """nested dict 를 dot-delimited flat dict 로. 값은 string 만 (다른 타입 무시)."""
    out: dict[str, str] = {}
    if isinstance(obj, dict):
        for k, v in obj.items():
            sub = f"{prefix}.{k}" if prefix else k
            out.update(_flatten(v, sub))
    elif isinstance(obj, str):
        out[prefix] = obj
    # number/bool/null/list 은 번역 대상 ❌
    return out


def _unflatten(flat: dict[str, str]) -> dict[str, Any]:
    """dot-delimited flat dict → nested dict."""
    out: dict[str, Any] = {}
    for key, val in flat.items():
        parts = key.split(".")
        cursor: dict[str, Any] = out
        for p in parts[:-1]:
            cursor = cursor.setdefault(p, {})
        cursor[parts[-1]] = val
    return out


# ─── LLM 호출 ─────────────────────────────────────────────────────────────

def _system_prompt(target_lang_native: str, target_lang_english: str) -> str:
    intro = (
        "You are a professional UI string translator. "
        f"Translate the given JSON dict of strings from English into {target_lang_english} ({target_lang_native})."
    )
    rules = (
        "Critical rules:\n"
        "1. Output ONLY a JSON object with the same keys, values translated. No markdown, no commentary.\n"
        "2. Preserve placeholder syntax exactly: `{var}`, `{count, plural, one {x} other {y}}`, `{name, select, ...}`. "
        "Do NOT translate placeholder names or ICU keywords (one/other/plural/select).\n"
        "3. Preserve HTML tags if present (e.g., `<strong>`, `<a href=\"...\">`). Translate text content inside tags.\n"
        "4. Preserve URLs, email addresses, brand names (e.g., \"AEO Visibility\", \"Stripe\").\n"
        "5. Match the target language's formal/business register (UI of a B2B SaaS product).\n"
        "6. For Korean, use 존댓말 (formal). For Japanese, use です/ます調. "
        "For German/French/Spanish/etc, use the formal \"you\" form.\n"
        "7. Empty strings and pure-numeric strings should be returned unchanged.\n"
    )
    return f"{intro}\n\n{rules}"


def _translate_batch(
    client: anthropic.Anthropic,
    flat_en: dict[str, str],
    target_native: str,
    target_english: str,
) -> dict[str, str]:
    """flat_en 의 모든 string 을 target lang 으로 번역해 같은 키 반환."""
    if not flat_en:
        return {}

    user_msg = json.dumps(flat_en, ensure_ascii=False, indent=2)

    response = client.messages.create(
        model=MODEL,
        max_tokens=MAX_TOKENS,
        system=_system_prompt(target_native, target_english),
        messages=[{"role": "user", "content": user_msg}],
    )

    text_blocks = [b.text for b in response.content if hasattr(b, "text")]
    raw = "".join(text_blocks).strip()

    # Strip markdown code fence (LLM 가 잘못 감싸도 복구).
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1] if "\n" in raw else raw
        if raw.endswith("```"):
            raw = raw.rsplit("```", 1)[0]
        raw = raw.strip()
        if raw.startswith("json"):
            raw = raw[4:].strip()

    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as e:
        print(f"  ⚠ JSON parse failed for {target_english}: {e}", file=sys.stderr)
        print(f"  raw: {raw[:200]}...", file=sys.stderr)
        return {}

    # Validate: 모든 영어 키가 응답에 있는지.
    missing = set(flat_en.keys()) - set(parsed.keys())
    if missing:
        print(f"  ⚠ {target_english}: {len(missing)} keys missing, falling back to en for those", file=sys.stderr)
        for k in missing:
            parsed[k] = flat_en[k]

    return parsed


# ─── 메인 워크플로 ────────────────────────────────────────────────────────

def translate_messages_json(
    client: anthropic.Anthropic,
    *,
    target_filter: str | None = None,
    force: bool = False,
) -> None:
    """frontend/messages/en.json → 19 lang JSON.

    캐싱: target/{lang}.json 의 키 + 영어 원문 비교, 변경된 것만 호출.
    cache 형식: 같은 디렉토리에 ``.{lang}.cache.json`` (영어 원문 스냅샷).
    """
    src_path = FRONTEND_MESSAGES / "en.json"
    if not src_path.exists():
        print(f"❌ source not found: {src_path}", file=sys.stderr)
        sys.exit(1)

    src_obj = json.loads(src_path.read_text(encoding="utf-8"))
    flat_en = _flatten(src_obj)
    print(f"📖 {src_path}: {len(flat_en)} string leaves")

    targets = TARGET_LANGS if target_filter is None else [
        t for t in TARGET_LANGS if t[0] == target_filter
    ]
    if not targets:
        print(f"❌ no target matched filter: {target_filter}", file=sys.stderr)
        sys.exit(1)

    for code, native, english in targets:
        out_path = FRONTEND_MESSAGES / f"{code}.json"
        cache_path = FRONTEND_MESSAGES / f".{code}.cache.json"

        # 캐시 로드.
        cached_en: dict[str, str] = {}
        existing_target: dict[str, str] = {}
        if not force and cache_path.exists() and out_path.exists():
            try:
                cached_en = json.loads(cache_path.read_text(encoding="utf-8"))
                existing_target = _flatten(json.loads(out_path.read_text(encoding="utf-8")))
            except Exception:
                cached_en, existing_target = {}, {}

        # 변경 검출: 새 키 OR 영어 원문이 바뀐 키.
        to_translate: dict[str, str] = {}
        for k, v in flat_en.items():
            if cached_en.get(k) != v or k not in existing_target:
                to_translate[k] = v

        if not to_translate:
            print(f"  ✅ {code} ({english}) — up to date, skipped")
            continue

        print(f"  🌐 {code} ({english}) — translating {len(to_translate)} keys...")
        translated = _translate_batch(client, to_translate, native, english)

        # 병합: 기존 target + 신규 번역. 영어에서 제거된 키도 정리.
        merged: dict[str, str] = {}
        for k in flat_en.keys():
            if k in translated:
                merged[k] = translated[k]
            elif k in existing_target:
                merged[k] = existing_target[k]
            else:
                merged[k] = flat_en[k]  # fallback

        # 저장.
        out_obj = _unflatten(merged)
        out_path.write_text(
            json.dumps(out_obj, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        cache_path.write_text(
            json.dumps(flat_en, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        print(f"     wrote {out_path}")


def translate_email_templates(
    client: anthropic.Anthropic,
    *,
    target_filter: str | None = None,
    force: bool = False,
) -> None:
    """backend/app/templates/{trigger}/en.html → 17 lang HTML.

    F-i18n-2 청크 본 진입점. F-i18n-1 에서는 placeholder (호출 ❌).
    """
    print("⏸  email templates 번역은 F-i18n-2 청크에서 활성화", file=sys.stderr)
    print(f"   대상 디렉토리: {BACKEND_TEMPLATES}", file=sys.stderr)
    print(f"   _ = ({target_filter}, force={force})", file=sys.stderr)


# ─── CLI ──────────────────────────────────────────────────────────────────

def _make_client() -> anthropic.Anthropic:
    api_key = os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("CLAUDE_API_KEY")
    if not api_key:
        print("❌ ANTHROPIC_API_KEY (or CLAUDE_API_KEY) not set in env", file=sys.stderr)
        sys.exit(1)
    return anthropic.Anthropic(api_key=api_key)


def main() -> None:
    parser = argparse.ArgumentParser(description="i18n 번역 스크립트 (Claude Haiku)")
    parser.add_argument(
        "mode",
        choices=["messages", "emails"],
        help="messages = frontend/messages/*.json, emails = backend/app/templates/*/{lang}.html",
    )
    parser.add_argument(
        "--lang", default=None,
        help="특정 lang 만 (예: ko). 미지정 시 19 lang 모두.",
    )
    parser.add_argument(
        "--force", action="store_true",
        help="캐시 무시하고 모두 재번역.",
    )
    args = parser.parse_args()

    client = _make_client()
    if args.mode == "messages":
        translate_messages_json(client, target_filter=args.lang, force=args.force)
    elif args.mode == "emails":
        translate_email_templates(client, target_filter=args.lang, force=args.force)


if __name__ == "__main__":
    main()
