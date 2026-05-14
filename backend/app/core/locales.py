"""i18n 20 lang 단일 소스.

**Mirror:**
- frontend/src/lib/i18n/config.ts (LOCALES_ORDERED, LOCALE_META, RTL_LOCALES)
- supabase/migrations/014_i18n_locales.sql (CHECK 제약)

**셀렉트 박스 노출 순서 = SUPPORTED_LANGS 순서** (alphabetical ❌, 사용자 지정 정렬).

추가/변경 시 함께 갱신:
- frontend/src/lib/i18n/config.ts
- supabase/migrations 신규 SQL (CHECK 제약 교체)
- frontend/messages/{lang}.json (translate_i18n.py 자동 생성)
- backend/app/templates/*/{lang}.html (translate_i18n.py 자동 생성, F-i18n-2)

F-i18n-1 청크 (2026-05-09).
"""
from __future__ import annotations

from typing import Final, Literal


# ─── 사용자 지정 정렬 순서 (셀렉트 박스 노출 순서) ───
SUPPORTED_LANGS: Final[tuple[str, ...]] = (
    "en",  # English
    "zh",  # 中文 (Mandarin)
    "ja",  # 日本語 (Japanese)
    "de",  # Deutsch (German)
    "fr",  # Français (French)
    "es",  # Español (Spanish)
    "ko",  # 한국어 (Korean)
    "pt",  # Português (Portuguese)
    "hi",  # हिन्दी (Hindi)
    "ru",  # Русский (Russian)
    "nl",  # Nederlands (Dutch)
    "it",  # Italiano (Italian)
    "ar",  # العربية (Arabic, RTL)
    "sv",  # Svenska (Swedish)
    "th",  # ไทย (Thai)
    "pl",  # Polski (Polish)
    "id",  # Bahasa Indonesia (Indonesian)
    "ms",  # Bahasa Melayu (Malay)
    "da",  # Dansk (Danish)
    "tr",  # Türkçe (Turkish)
)

SUPPORTED_LANG_SET: Final[frozenset[str]] = frozenset(SUPPORTED_LANGS)

DEFAULT_LANG: Final[str] = "en"

# ─── RTL (right-to-left) 언어 ───
RTL_LANGS: Final[frozenset[str]] = frozenset({"ar"})


# ─── 언어 메타데이터 (native name / english name) ───
class LocaleMeta:
    __slots__ = ("code", "native_name", "english_name", "rtl")

    def __init__(self, code: str, native_name: str, english_name: str, rtl: bool) -> None:
        self.code = code
        self.native_name = native_name
        self.english_name = english_name
        self.rtl = rtl


LOCALE_META: Final[dict[str, LocaleMeta]] = {
    "en": LocaleMeta("en", "English", "English", False),
    "zh": LocaleMeta("zh", "中文", "Mandarin", False),
    "ja": LocaleMeta("ja", "日本語", "Japanese", False),
    "de": LocaleMeta("de", "Deutsch", "German", False),
    "fr": LocaleMeta("fr", "Français", "French", False),
    "es": LocaleMeta("es", "Español", "Spanish", False),
    "ko": LocaleMeta("ko", "한국어", "Korean", False),
    "pt": LocaleMeta("pt", "Português", "Portuguese", False),
    "hi": LocaleMeta("hi", "हिन्दी", "Hindi", False),
    "ru": LocaleMeta("ru", "Русский", "Russian", False),
    "nl": LocaleMeta("nl", "Nederlands", "Dutch", False),
    "it": LocaleMeta("it", "Italiano", "Italian", False),
    "ar": LocaleMeta("ar", "العربية", "Arabic", True),
    "sv": LocaleMeta("sv", "Svenska", "Swedish", False),
    "th": LocaleMeta("th", "ไทย", "Thai", False),
    "pl": LocaleMeta("pl", "Polski", "Polish", False),
    "id": LocaleMeta("id", "Bahasa Indonesia", "Indonesian", False),
    "ms": LocaleMeta("ms", "Bahasa Melayu", "Malay", False),
    "da": LocaleMeta("da", "Dansk", "Danish", False),
    "tr": LocaleMeta("tr", "Türkçe", "Turkish", False),
}

# Pydantic Literal 호환 — schemas/workspace.py 등에서 임포트해서 사용.
LangLiteral = Literal[
    "en", "zh", "ja", "de", "fr", "es", "ko", "pt", "hi", "ru",
    "nl", "it", "ar", "sv", "th", "pl", "id", "ms", "da", "tr",
]


def normalize_lang(lang: str | None) -> str:
    """SUPPORTED_LANGS 외 → DEFAULT_LANG 폴백."""
    if lang and lang in SUPPORTED_LANG_SET:
        return lang
    return DEFAULT_LANG


def is_rtl(lang: str) -> bool:
    return lang in RTL_LANGS


def sql_check_clause(column: str) -> str:
    """SQL CHECK 제약 절 생성 (마이그레이션 작성 보조).

    예: ``sql_check_clause('preferred_language')`` →
    ``"preferred_language IN ('en','zh',...,'tr')"``.
    """
    quoted = ", ".join(f"'{lang}'" for lang in SUPPORTED_LANGS)
    return f"{column} IN ({quoted})"
