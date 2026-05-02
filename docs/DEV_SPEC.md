# AEO Visibility — 개발 스펙 (DEV_SPEC)

> 본 문서는 `docs/SPEC.md`의 구현 가이드입니다.
> SPEC이 "무엇을 만드는가"라면, DEV_SPEC은 "어떻게 만드는가"를 다룹니다.

---

## 1. 문서 개요

### 1-1. 범위
- ✅ 라이브러리 목록 + 버전 권고
- ✅ 디렉토리 구조 (변경분)
- ✅ 환경변수 정의
- ✅ DB 마이그레이션 단계별 계획
- ✅ 시드 데이터
- ✅ API 설계 원칙 (OpenAPI)
- ✅ 코드 컨벤션
- ✅ 테스트 전략
- ✅ CI/CD 파이프라인
- ✅ 로컬 개발 워크플로우
- ✅ 보안 / 관측성 / 성능 가이드
- ✅ Git 브랜치 / PR 가이드
- ✅ Phase별 개발 체크리스트

### 1-2. 대상 독자
- 이 프로젝트의 백엔드 / 프론트엔드 구현 담당자
- DevOps / 인프라 담당자
- 신규 합류 개발자

---

## 2. 개발 환경 / 도구

### 2-1. 필수 설치
| 도구 | 버전 | 용도 |
|---|---|---|
| Node.js | 20.x LTS | Frontend 빌드/런타임 |
| pnpm | 9.x | Frontend 패키지 매니저 (npm 대체) |
| Python | 3.12.x | Backend 런타임 |
| Poetry 또는 uv | 최신 | Python 패키지 매니저 (pip 대체 권장) |
| Docker Desktop | 최신 | 로컬 Postgres / Redis 실행 |
| Git | 2.40+ | 버전 관리 |
| GitHub CLI (`gh`) | 최신 | PR 자동화 |
| Stripe CLI | 최신 | Webhook 로컬 테스트 |
| Supabase CLI | 1.200+ | 로컬 Supabase, 마이그레이션 |

### 2-2. 권장 IDE 설정
- **VS Code** + 다음 확장:
  - ESLint, Prettier
  - Tailwind CSS IntelliSense
  - Python (Microsoft)
  - Ruff
  - Pylance
  - GitLens
  - Stripe (선택)
- 또는 Cursor / Windsurf (AI 페어 프로그래밍)

### 2-3. 환경 격리
- Frontend: `pnpm install` (lockfile 동기화)
- Backend: `python -m venv .venv` 또는 `uv venv` → 가상환경에 의존성 설치
- 절대 글로벌 설치 ❌

---

## 3. 디렉토리 구조 (변경분)

### 3-1. 전체 트리

```
aeo-visibility/
├── .github/
│   └── workflows/
│       ├── frontend-ci.yml          # Vercel preview, lint, test
│       ├── backend-ci.yml           # Railway, lint, test, migration check
│       └── e2e.yml                  # Playwright E2E
├── docs/
│   ├── reboot-service-concept.md    # 의사결정 정리
│   ├── SPEC.md                      # 종합 스펙
│   └── DEV_SPEC.md                  # 본 문서
├── frontend/
│   ├── src/
│   │   ├── app/
│   │   │   ├── [lang]/              # i18n 라우팅
│   │   │   │   ├── (public)/        # 비로그인 (랜딩, 가격, 위키)
│   │   │   │   │   ├── page.tsx
│   │   │   │   │   ├── pricing/
│   │   │   │   │   ├── wiki/
│   │   │   │   │   │   ├── page.tsx
│   │   │   │   │   │   ├── category/[category]/page.tsx
│   │   │   │   │   │   └── [slug]/page.tsx
│   │   │   │   │   ├── legal/
│   │   │   │   │   │   ├── terms/page.tsx
│   │   │   │   │   │   ├── privacy/page.tsx
│   │   │   │   │   │   ├── cookies/page.tsx
│   │   │   │   │   │   └── refund/page.tsx
│   │   │   │   │   └── layout.tsx
│   │   │   │   ├── (auth)/          # 인증 흐름
│   │   │   │   │   ├── signup/page.tsx
│   │   │   │   │   ├── login/page.tsx
│   │   │   │   │   ├── verify/page.tsx
│   │   │   │   │   └── onboarding/page.tsx
│   │   │   │   ├── (app)/           # 로그인 후 대시보드
│   │   │   │   │   ├── dashboard/page.tsx
│   │   │   │   │   ├── sites/
│   │   │   │   │   │   ├── page.tsx
│   │   │   │   │   │   └── [site_id]/
│   │   │   │   │   │       ├── page.tsx
│   │   │   │   │   │       └── results/[result_id]/page.tsx
│   │   │   │   │   ├── reports/page.tsx
│   │   │   │   │   ├── qa/page.tsx
│   │   │   │   │   ├── settings/
│   │   │   │   │   │   ├── workspace/page.tsx
│   │   │   │   │   │   ├── members/page.tsx
│   │   │   │   │   │   ├── billing/page.tsx
│   │   │   │   │   │   ├── profile/page.tsx
│   │   │   │   │   │   └── danger/page.tsx
│   │   │   │   │   └── layout.tsx
│   │   │   │   ├── (admin)/         # super_admin only
│   │   │   │   │   ├── admin/
│   │   │   │   │   │   ├── page.tsx
│   │   │   │   │   │   ├── users/page.tsx
│   │   │   │   │   │   ├── workspaces/page.tsx
│   │   │   │   │   │   ├── subscriptions/page.tsx
│   │   │   │   │   │   ├── coupons/page.tsx
│   │   │   │   │   │   ├── wiki/
│   │   │   │   │   │   │   ├── page.tsx
│   │   │   │   │   │   │   └── [id]/edit/page.tsx
│   │   │   │   │   │   ├── stats/page.tsx
│   │   │   │   │   │   ├── audit-logs/page.tsx
│   │   │   │   │   │   └── health/page.tsx
│   │   │   │   │   └── layout.tsx
│   │   │   │   └── layout.tsx
│   │   │   ├── api/
│   │   │   │   ├── reports/[id]/pdf/route.ts   # PDF on-demand 생성
│   │   │   │   ├── reports/[id]/csv/route.ts
│   │   │   │   └── og/route.ts                 # Open Graph 이미지 생성
│   │   │   ├── sitemap.ts
│   │   │   ├── robots.ts
│   │   │   ├── layout.tsx
│   │   │   └── globals.css
│   │   ├── components/
│   │   │   ├── ui/                  # shadcn 스타일 primitives
│   │   │   │   ├── button.tsx
│   │   │   │   ├── input.tsx
│   │   │   │   ├── modal.tsx
│   │   │   │   └── ...
│   │   │   ├── charts/
│   │   │   │   ├── radar-chart.tsx
│   │   │   │   ├── time-series.tsx
│   │   │   │   └── score-card.tsx
│   │   │   ├── pdf/
│   │   │   │   ├── report-document.tsx
│   │   │   │   ├── pages/
│   │   │   │   │   ├── cover.tsx
│   │   │   │   │   ├── summary.tsx
│   │   │   │   │   ├── category-detail.tsx
│   │   │   │   │   └── ...
│   │   │   │   └── styles.ts
│   │   │   ├── analysis/
│   │   │   │   ├── category-card.tsx
│   │   │   │   ├── metric-row.tsx
│   │   │   │   ├── improvement-list.tsx
│   │   │   │   └── custom-analysis-modal.tsx
│   │   │   ├── qa/
│   │   │   │   ├── qa-widget.tsx
│   │   │   │   ├── qa-thread.tsx
│   │   │   │   └── source-card.tsx
│   │   │   └── layout/
│   │   │       ├── header.tsx
│   │   │       ├── sidebar.tsx
│   │   │       └── footer.tsx
│   │   ├── lib/
│   │   │   ├── supabase/
│   │   │   │   ├── client.ts        # 브라우저용 (anon key)
│   │   │   │   ├── server.ts        # SSR용
│   │   │   │   └── admin.ts         # service_role (백엔드 쪽 사용 ❌)
│   │   │   ├── api/                 # Backend API 호출 래퍼
│   │   │   │   ├── client.ts
│   │   │   │   ├── workspaces.ts
│   │   │   │   ├── analyses.ts
│   │   │   │   └── ...
│   │   │   ├── stripe/
│   │   │   │   └── client.ts
│   │   │   ├── pdf/
│   │   │   │   └── generator.ts
│   │   │   ├── i18n/
│   │   │   │   ├── config.ts
│   │   │   │   └── request.ts
│   │   │   └── utils/
│   │   │       ├── format.ts
│   │   │       └── validation.ts
│   │   ├── hooks/                   # 기존 + 신규
│   │   │   ├── use-workspace.ts
│   │   │   ├── use-analysis-status.ts
│   │   │   └── ...
│   │   ├── types/
│   │   │   ├── database.ts          # Supabase 자동 생성 타입
│   │   │   ├── api.ts               # API 응답 타입
│   │   │   └── analysis.ts          # 분석 결과 표준 스키마
│   │   ├── messages/                # next-intl
│   │   │   ├── en.json
│   │   │   ├── ko.json
│   │   │   └── es.json
│   │   ├── styles/
│   │   ├── middleware.ts            # 언어 감지, 인증 가드, /admin 가드
│   │   └── env.ts                   # 환경변수 검증 (zod)
│   ├── public/
│   ├── tests/
│   │   ├── unit/
│   │   ├── integration/
│   │   └── e2e/                     # Playwright
│   ├── next.config.mjs
│   ├── tailwind.config.ts
│   ├── tsconfig.json
│   ├── package.json
│   └── playwright.config.ts
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── config.py                # Pydantic Settings
│   │   ├── deps.py                  # FastAPI 의존성 (auth, db, redis)
│   │   ├── models/                  # SQLAlchemy 모델
│   │   │   ├── __init__.py
│   │   │   ├── base.py
│   │   │   ├── profile.py
│   │   │   ├── workspace.py
│   │   │   ├── subscription.py
│   │   │   ├── site.py
│   │   │   ├── analysis.py
│   │   │   ├── wiki.py
│   │   │   ├── qa.py
│   │   │   ├── coupon.py
│   │   │   └── audit.py
│   │   ├── schemas/                 # Pydantic 스키마 (API I/O)
│   │   │   ├── workspace.py
│   │   │   ├── analysis.py
│   │   │   └── ...
│   │   ├── routers/                 # FastAPI 라우터
│   │   │   ├── __init__.py
│   │   │   ├── workspaces.py
│   │   │   ├── members.py
│   │   │   ├── sites.py
│   │   │   ├── analyses.py
│   │   │   ├── reports.py
│   │   │   ├── billing.py           # Stripe Checkout, Portal
│   │   │   ├── webhooks.py          # Stripe webhook
│   │   │   ├── qa.py
│   │   │   ├── wiki.py              # 공개 읽기
│   │   │   ├── admin/
│   │   │   │   ├── users.py
│   │   │   │   ├── workspaces.py
│   │   │   │   ├── coupons.py
│   │   │   │   ├── wiki.py
│   │   │   │   └── stats.py
│   │   │   └── internal.py          # cron HMAC 엔드포인트
│   │   ├── services/                # 비즈니스 로직
│   │   │   ├── analysis_runner.py   # 분석 오케스트레이션
│   │   │   ├── llm_synthesizer.py   # Claude 통합 호출 (insights/improvements)
│   │   │   ├── translator.py        # on-demand 번역 + 캐시
│   │   │   ├── stripe_service.py
│   │   │   ├── coupon_service.py
│   │   │   ├── email_service.py
│   │   │   ├── pdf_service.py
│   │   │   ├── qa_service.py
│   │   │   ├── embedding_service.py # Voyage AI 래핑
│   │   │   ├── usage_service.py     # monthly_usage 카운터
│   │   │   └── grace_processor.py
│   │   ├── scoring/                 # 분석 엔진 (재작성)
│   │   │   ├── __init__.py
│   │   │   ├── orchestrator.py      # 5개 카테고리 병렬 실행
│   │   │   ├── schema.py            # 표준 결과 스키마 (Pydantic)
│   │   │   ├── weights.py           # 가중치 외부 설정
│   │   │   ├── technical.py
│   │   │   ├── structured.py
│   │   │   ├── content.py
│   │   │   ├── authority.py
│   │   │   └── visibility.py
│   │   ├── auth/
│   │   │   ├── jwt.py               # Supabase JWT 검증
│   │   │   └── permissions.py       # 역할 검증 헬퍼
│   │   ├── db/
│   │   │   ├── session.py
│   │   │   └── migrations/          # Alembic
│   │   ├── cache/
│   │   │   └── redis_client.py
│   │   ├── tasks/                   # BackgroundTasks 핸들러
│   │   │   ├── analysis_task.py
│   │   │   ├── pdf_task.py
│   │   │   └── embedding_task.py
│   │   ├── utils/
│   │   │   ├── hmac_verify.py
│   │   │   ├── url_normalize.py
│   │   │   └── domain_extract.py
│   │   └── templates/               # 이메일 (Jinja2)
│   │       ├── auth_magic_link/
│   │       │   ├── en.html
│   │       │   ├── ko.html
│   │       │   └── es.html
│   │       └── ...
│   ├── alembic/
│   │   ├── env.py
│   │   ├── script.py.mako
│   │   └── versions/
│   ├── tests/
│   │   ├── conftest.py
│   │   ├── unit/
│   │   ├── integration/
│   │   └── fixtures/
│   ├── alembic.ini
│   ├── Dockerfile
│   ├── Procfile
│   ├── railway.json
│   ├── pyproject.toml               # Poetry 또는 uv
│   ├── pytest.ini
│   └── ruff.toml
├── supabase/
│   ├── migrations/                  # 순서 보장 SQL 파일
│   │   ├── 001_initial_schema.sql   # (기존)
│   │   ├── 002_v2_baseline_drop.sql # MVP 테이블 정리 (선택)
│   │   ├── 003_profiles.sql
│   │   ├── 004_plans.sql
│   │   ├── 005_workspaces.sql
│   │   ├── 006_workspace_members.sql
│   │   ├── 007_subscriptions.sql
│   │   ├── 008_sites.sql
│   │   ├── 009_analysis_results.sql
│   │   ├── 010_monthly_usage.sql
│   │   ├── 011_reports.sql
│   │   ├── 012_audit_logs.sql
│   │   ├── 013_deletion_grace.sql
│   │   ├── 014_rls_policies.sql
│   │   ├── 015_pg_cron_setup.sql
│   │   ├── 016_pgvector_setup.sql
│   │   ├── 017_wiki.sql
│   │   ├── 018_qa.sql
│   │   ├── 019_coupons.sql
│   │   └── seeds/
│   │       └── plans_seed.sql
│   ├── functions/                   # Supabase Edge Functions (선택)
│   └── config.toml
├── DEPLOY.md
├── README.md
└── .gitignore
```

> `(public)`, `(auth)`, `(app)`, `(admin)`은 Next.js Route Group (URL에 영향 없음, 레이아웃 분리용).

### 3-2. v2 신규 디렉토리 / 파일

| 신규 | 목적 |
|---|---|
| `frontend/src/messages/` | next-intl 메시지 번들 |
| `frontend/src/components/pdf/` | @react-pdf/renderer 컴포넌트 |
| `frontend/src/lib/i18n/` | next-intl 설정 |
| `frontend/src/lib/stripe/` | Stripe 클라이언트 |
| `frontend/src/lib/supabase/` | Supabase SSR/Client 분리 |
| `frontend/src/types/database.ts` | Supabase 자동 생성 타입 |
| `backend/app/services/` | 비즈니스 로직 분리 |
| `backend/app/scoring/orchestrator.py` | 5 카테고리 병렬 실행 |
| `backend/app/scoring/schema.py` | 표준 결과 스키마 |
| `backend/app/auth/` | JWT 검증, 권한 헬퍼 |
| `backend/app/tasks/` | BackgroundTasks 핸들러 |
| `supabase/migrations/` | Supabase 관리 schema (RLS/cron/vector) |

### 3-3. 모노레포 도구

선택지:
- **단순 다중 디렉토리** (현재 구조 유지) ← **권장**
  - frontend/, backend/, supabase/ 각각 독립
  - GitHub Actions에서 path filter로 분리 빌드
- Turbo 또는 Nx 도입은 향후 고려 (1년차 이후)

---

## 4. Frontend 라이브러리

### 4-1. 핵심 의존성 (package.json `dependencies`)

```json
{
  "next": "^14.2.0",
  "react": "^18.3.0",
  "react-dom": "^18.3.0",

  "next-intl": "^3.20.0",

  "@supabase/ssr": "^0.5.0",
  "@supabase/supabase-js": "^2.45.0",

  "@stripe/stripe-js": "^4.7.0",
  "stripe": "^17.0.0",

  "@react-pdf/renderer": "^4.0.0",
  "recharts": "^2.15.0",

  "@tanstack/react-query": "^5.59.0",
  "zustand": "^4.5.0",

  "react-hook-form": "^7.53.0",
  "zod": "^3.23.0",
  "@hookform/resolvers": "^3.9.0",

  "react-markdown": "^9.0.0",
  "remark-gfm": "^4.0.0",
  "rehype-sanitize": "^6.0.0",

  "@radix-ui/react-dialog": "^1.1.0",
  "@radix-ui/react-dropdown-menu": "^2.1.0",
  "@radix-ui/react-tabs": "^1.1.0",
  "@radix-ui/react-toast": "^1.2.0",
  "@radix-ui/react-select": "^2.1.0",
  "@radix-ui/react-checkbox": "^1.1.0",
  "@radix-ui/react-popover": "^1.1.0",
  "@radix-ui/react-tooltip": "^1.1.0",

  "class-variance-authority": "^0.7.0",
  "clsx": "^2.1.0",
  "tailwind-merge": "^2.5.0",
  "lucide-react": "^0.450.0",
  "date-fns": "^4.1.0",

  "langdetect": "^1.0.0"
}
```

### 4-2. 개발 의존성 (devDependencies)

```json
{
  "typescript": "^5.4.0",
  "@types/node": "^20.0.0",
  "@types/react": "^18.3.0",
  "@types/react-dom": "^18.3.0",

  "tailwindcss": "^3.4.0",
  "autoprefixer": "^10.4.0",
  "postcss": "^8.4.0",
  "@tailwindcss/typography": "^0.5.0",

  "eslint": "^8.57.0",
  "eslint-config-next": "^14.2.0",
  "@typescript-eslint/eslint-plugin": "^7.0.0",
  "prettier": "^3.3.0",
  "prettier-plugin-tailwindcss": "^0.6.0",

  "vitest": "^2.1.0",
  "@vitejs/plugin-react": "^4.3.0",
  "@testing-library/react": "^16.0.0",
  "@testing-library/user-event": "^14.5.0",
  "jsdom": "^25.0.0",

  "@playwright/test": "^1.48.0",

  "husky": "^9.1.0",
  "lint-staged": "^15.2.0"
}
```

> 버전은 권장값. v2 개발 시작 시점에 `pnpm outdated`로 업데이트 검토.

### 4-3. 라이브러리 선택 근거

| 라이브러리 | 선택 근거 |
|---|---|
| next-intl | App Router 친화, Server Component 지원, 타입 안전 |
| @supabase/ssr | App Router에서 쿠키 기반 세션 관리 |
| @react-pdf/renderer | 클라이언트/서버 양쪽 렌더, React 컴포넌트 기반 |
| recharts | 가벼움, 반응형, SVG 출력 (PDF 임베드 가능) |
| TanStack Query | 서버 상태 관리, 캐싱, 낙관적 업데이트 |
| zustand | 간단한 클라이언트 상태만 (Redux 과함) |
| react-hook-form + zod | 폼 검증 + 스키마 일관성 |
| Radix UI | 접근성 보장된 unstyled primitives |
| lucide-react | 트리쉐이킹 가능한 아이콘 |
| Vitest | Jest 대체, Vite 기반 빠름 |
| Playwright | 멀티 브라우저 E2E |

---

## 5. Backend 라이브러리

### 5-1. 핵심 의존성 (pyproject.toml 또는 requirements.txt)

```toml
[tool.poetry.dependencies]
python = "^3.12"

# Core
fastapi = "^0.115.6"
uvicorn = {extras = ["standard"], version = "^0.34.0"}
pydantic-settings = "^2.7.1"

# DB
sqlalchemy = {extras = ["asyncio"], version = "^2.0.36"}
asyncpg = "^0.30.0"
alembic = "^1.14.1"
pgvector = "^0.3.6"

# Cache
redis = "^5.2.1"

# HTTP / crawling
httpx = "^0.28.1"
beautifulsoup4 = "^4.12.3"
lxml = "^5.3.0"

# Scoring
python-whois = "^0.9.5"
textstat = "^0.7.4"

# AI
anthropic = "^0.43.0"
voyageai = "^0.3.0"

# Payment
stripe = "^11.0.0"

# Email
resend = "^2.5.1"
jinja2 = "^3.1.5"

# Auth
python-jose = {extras = ["cryptography"], version = "^3.3.0"}

# Utils
python-multipart = "^0.0.20"
python-dateutil = "^2.9.0"
tenacity = "^9.0.0"
langdetect = "^1.0.9"

[tool.poetry.group.dev.dependencies]
pytest = "^8.3.0"
pytest-asyncio = "^0.24.0"
pytest-cov = "^5.0.0"
pytest-mock = "^3.14.0"
httpx = "^0.28.1"  # for TestClient
faker = "^30.0.0"

ruff = "^0.7.0"
mypy = "^1.13.0"
pre-commit = "^4.0.0"
```

### 5-2. 라이브러리 선택 근거

| 라이브러리 | 선택 근거 |
|---|---|
| pgvector (Python) | SQLAlchemy 통합, 벡터 컬럼 모델 정의 |
| voyageai | Anthropic 권장, voyage-3 임베딩 |
| python-jose | Supabase JWT 검증 (HS256/RS256) |
| tenacity | 외부 API 호출 재시도 (Claude, Voyage, Stripe) |
| langdetect | Q&A 사용자 언어 감지 (가벼움) |
| faker | 테스트 픽스처 생성 |
| ruff | flake8 + black + isort 통합, 매우 빠름 |

---

## 6. 환경변수

### 6-1. Frontend (`.env.local`, Vercel)

```bash
# Public (브라우저 노출 OK)
NEXT_PUBLIC_SUPABASE_URL=https://[project].supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=eyJ...
NEXT_PUBLIC_BACKEND_URL=https://aeo-visibility-production.up.railway.app
NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY=pk_test_...
NEXT_PUBLIC_SITE_URL=https://aeo-visibility.vercel.app

# Private (Server Actions, API Routes에서만)
SUPABASE_SERVICE_ROLE_KEY=eyJ...        # ⚠️ 절대 클라이언트 노출 ❌
STRIPE_SECRET_KEY=sk_test_...           # PDF on-demand 생성용
STRIPE_WEBHOOK_SECRET=whsec_...         # webhook 검증
RESEND_API_KEY=re_...                   # 직접 발송이 필요한 경우만 (보통 백엔드)
INTERNAL_API_TOKEN=...                  # 백엔드와 공유 비밀
```

### 6-2. Backend (Railway)

```bash
# Database
DATABASE_URL=postgresql+asyncpg://...
DIRECT_URL=postgresql://...             # Alembic 마이그레이션 (asyncpg가 아닌 동기)

# Supabase
SUPABASE_URL=https://[project].supabase.co
SUPABASE_ANON_KEY=eyJ...
SUPABASE_SERVICE_ROLE_KEY=eyJ...
SUPABASE_JWT_SECRET=...                  # JWT 검증

# Cache
REDIS_URL=rediss://...                   # Upstash

# AI
ANTHROPIC_API_KEY=sk-ant-...
VOYAGE_API_KEY=pa-...

# Payment
STRIPE_SECRET_KEY=sk_test_...
STRIPE_WEBHOOK_SECRET=whsec_...

# Email
RESEND_API_KEY=re_...
EMAIL_FROM_NOREPLY=no-reply@[domain]
EMAIL_FROM_HELLO=hello@[domain]
EMAIL_FROM_SUPPORT=support@[domain]

# Internal
INTERNAL_API_TOKEN=...                   # Frontend ↔ Backend 공유
CRON_HMAC_SECRET=...                     # pg_cron HMAC 검증

# CORS
CORS_ORIGINS=https://aeo-visibility.vercel.app,http://localhost:3000

# Misc
APP_ENV=production                       # development | staging | production
LOG_LEVEL=INFO
```

### 6-3. 환경변수 검증

**Frontend (`src/env.ts`)**:
```typescript
import { z } from 'zod';

const schema = z.object({
  NEXT_PUBLIC_SUPABASE_URL: z.string().url(),
  NEXT_PUBLIC_SUPABASE_ANON_KEY: z.string().min(1),
  NEXT_PUBLIC_BACKEND_URL: z.string().url(),
  NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY: z.string().startsWith('pk_'),
  NEXT_PUBLIC_SITE_URL: z.string().url(),
  // ...
});

export const env = schema.parse(process.env);
```

**Backend (`app/config.py`)**:
```python
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    
    database_url: str
    supabase_url: str
    supabase_jwt_secret: str
    anthropic_api_key: str
    voyage_api_key: str
    stripe_secret_key: str
    stripe_webhook_secret: str
    redis_url: str
    cron_hmac_secret: str
    app_env: str = "development"
    log_level: str = "INFO"

settings = Settings()
```

### 6-4. `.env.template`

> 모든 키는 **빈 값**으로. 실제 값은 README에 가이드 + 1Password / Doppler 활용 권장.

```bash
# .env.template
DATABASE_URL=
SUPABASE_URL=
# ... (값 없음)
```

---

## 7. DB 마이그레이션 전략

### 7-1. 도구 분담

| 도구 | 담당 |
|---|---|
| **Supabase 마이그레이션 (`supabase/migrations/*.sql`)** | 스키마 정의, RLS 정책, pg_cron, pgvector, ENUM 타입 |
| **Alembic (`backend/alembic/versions/*`)** | Backend SQLAlchemy 모델과의 동기화. 보조 인덱스/트리거. 백엔드 전용 테이블 |

> 기본 원칙: **Supabase 마이그레이션을 정본**으로. Alembic은 SQLAlchemy 모델 관점에서 보조.
>
> **단일 도구 운영도 가능**: Supabase 마이그레이션만으로 통일하고 Alembic 제거. 단, SQLAlchemy 모델과의 동기화는 수동으로 검증 필요.

### 7-2. 마이그레이션 적용 순서

> 실제 적용 번호는 작업 진행 중 청크 분할에 따라 일부 갱신됨. 아래는 현재 시점(2026-05-02)의 정합 순서.

```
1. 기존 MVP 마이그레이션 (001_initial_schema.sql) 그대로 유지
   → v2에서 사용하지 않는 테이블은 002에서 DROP

2. Phase 1 마이그레이션 (003 ~ 016)
   ── 청크 A (적용 완료) ──
   - 002_drop_mvp_tables.sql
   - 003_profiles.sql                + handle_new_user / set_updated_at
   - 004_plans.sql                   (구 시드 — 008에서 가격/한도 갱신됨)
   - 005_workspaces.sql
   - 006_workspace_members.sql       + ENUM workspace_role + add_owner_to_workspace_members
   - 007_rls_phase1_workspace.sql    (profiles/plans/workspaces/workspace_members RLS)
   ── 청크 D0 (가격 정책 확정 반영) ──
   - 008_plans_repricing.sql         컬럼 7개 ADD + 5-tier → 4-tier+trial+enterprise 시드 갱신
   ── 청크 D 이후 ──
   - 009_subscriptions.sql           + ENUM subscription_status (trial 자동 시작 포함)
   - 010_sites.sql                   + ENUM site_type (own/competitor) + 30일 cooldown
   - 011_analysis_results.sql        + ENUM analysis_trigger_type
   - 012_monthly_usage.sql           (Custom 카운터: base/basic_pack/pro_pack/payg 분리)
   - 013_reports.sql
   - 014_audit_logs.sql
   - 015_deletion_grace_queue.sql
   - 016_pg_cron_setup.sql           매월 분석 + 트라이얼 만료 시퀀스

3. Phase 2 마이그레이션 (017 ~ 019) — 결제 + 쿠폰
   - 017_subscription_addons.sql     + ENUM addon_type (13종, SPEC §5-2)
   - 018_workspace_invitations.sql
   - 019_coupons.sql + coupon_redemptions.sql  (Phase 4 → Phase 2 당김)
                                     + auto_apply 모드 (시즌 프로모션)

4. Phase 3 마이그레이션
   - 020_pdf_csv_storage_buckets.sql  ← Supabase Storage 정책

5. Phase 4 마이그레이션 (Wiki + Q&A 중심, 쿠폰은 Phase 2로 이미 이동됨)
   - 021_pgvector_extension.sql       ← CREATE EXTENSION vector
   - 022_wiki_articles.sql
   - 023_wiki_embeddings.sql
   - 024_qa_sessions.sql
   - 025_qa_messages.sql
```

### 7-3. 마이그레이션 작성 규칙

1. 파일명: `NNN_description.sql` (3자리 zero-pad)
2. 모든 마이그레이션은 **idempotent하지 않아도 됨** (한 번만 실행)
3. 각 파일은 단일 트랜잭션 (`BEGIN; ... COMMIT;`)
4. RLS 정책은 테이블 생성과 분리 (디버깅 용이)
5. ENUM 타입은 첫 사용처에서 생성, `IF NOT EXISTS` 사용
6. 인덱스는 테이블 생성 직후 같은 파일에
7. 외래키 제약은 명시 (`ON DELETE CASCADE` / `SET NULL` 등)
8. 주석으로 변경 의도 기록

### 7-4. 시드 데이터

#### plans_seed.sql

```sql
-- 2026-05-02 시장조사 결과로 확정. SPEC §4 / reboot-service-concept §1 정합.
-- -1 = 무제한 표기.
-- 정가만 보관 — 시즌 프로모션은 §14 coupons 테이블의 auto_apply 모드로 별도 관리.
INSERT INTO plans (
    id, name, price_monthly_usd, price_annual_usd,
    max_sites, max_competitors, max_members_default, max_members_hardcap,
    custom_analyses_per_month, timeseries_months,
    csv_export, competitor_comparison, competitor_trend_graph,
    default_ai_engines, competitors_per_site, industry_benchmark,
    audit_log_days, data_retention_years, support_tier, is_enterprise,
    is_active
) VALUES
-- 7-day trial 한도 (보수적): 자사 1 / 경쟁사 0 / 멤버 1 / Custom 0
('free',       'Free Trial',    0.00,    NULL,
    1, 0, 1, 1,  0, 0,
    false, false, false,
    3, 0, false,
    0, 5, 'self', false,
    true),
('basic',      'Basic',        19.99,   203.88,    -- $16.99 × 12
    1, 0, 1, 5,  5, 6,
    false, false, false,
    3, 0, false,
    0, 5, 'email', false,
    true),
('pro',        'Pro',          79.99,   815.88,    -- $67.99 × 12
    3, 0, 3, 30,  30, 12,
    true, true, false,
    3, 1, false,
    30, 5, 'email_chat', false,
    true),
('business',   'Business',    299.99,  3059.88,    -- $254.99 × 12
    5, 0, 5, 100,  100, 24,
    true, true, true,
    3, 3, true,
    90, 5, 'email_chat_sla4h', false,
    true),
('enterprise', 'Enterprise', 1499.99, 15299.88,    -- $1,274.99 × 12 (annual commit 필수)
    -1, -1, 20, -1,  -1, -1,
    true, true, true,
    -1, 5, true,
    -1, 7, 'dedicated', true,
    true);
-- 연간가 = 월 환산가 × 12 (15% 할인 후 단가). reboot-service-concept §1-1 표기 일치.
-- Stripe 상품 생성 후 stripe_price_id_monthly / _annual 컬럼에 Price ID UPDATE.
```

### 7-5. 로컬 마이그레이션 워크플로우

```bash
# 로컬 Supabase 시작
supabase start

# 마이그레이션 작성
touch supabase/migrations/$(date +%Y%m%d%H%M%S)_add_feature.sql

# 로컬 적용
supabase migration up

# 모델 변경 시 SQLAlchemy 모델 동기화
# (자동화 도구 X, 수동으로 backend/app/models/*.py 작성)

# 타입 자동 생성 (Frontend)
supabase gen types typescript --local > frontend/src/types/database.ts

# 원격 적용 (production)
supabase db push --linked
```

---

## 8. RLS 정책 적용 순서

### 8-1. 적용 단계

1. 모든 테이블 생성 완료 후 RLS 활성화
2. 정책은 별도 마이그레이션 파일 (`014_rls_policies.sql`)
3. SELECT 정책 먼저 → INSERT/UPDATE/DELETE 순서
4. service_role은 RLS 우회 (백엔드용)

### 8-2. 표준 패턴

```sql
-- 1. RLS 활성화
ALTER TABLE workspaces ENABLE ROW LEVEL SECURITY;

-- 2. SELECT 정책 (멤버만)
CREATE POLICY workspaces_select ON workspaces FOR SELECT
  TO authenticated
  USING (id IN (
    SELECT workspace_id FROM workspace_members WHERE user_id = auth.uid()
  ));

-- 3. UPDATE 정책 (owner/admin)
CREATE POLICY workspaces_update ON workspaces FOR UPDATE
  TO authenticated
  USING (id IN (
    SELECT workspace_id FROM workspace_members 
    WHERE user_id = auth.uid() AND role IN ('owner', 'admin')
  ))
  WITH CHECK (id IN (
    SELECT workspace_id FROM workspace_members 
    WHERE user_id = auth.uid() AND role IN ('owner', 'admin')
  ));

-- 4. DELETE 정책 (owner만)
CREATE POLICY workspaces_delete ON workspaces FOR DELETE
  TO authenticated
  USING (id IN (
    SELECT workspace_id FROM workspace_members 
    WHERE user_id = auth.uid() AND role = 'owner'
  ));

-- 5. INSERT는 백엔드(service_role)에서만 → 정책 생성 ❌, 그러면 anon/authenticated INSERT 차단
```

### 8-3. 검증

각 정책 작성 후 `supabase test db` 또는 직접 SQL로 검증:

```sql
-- 다른 워크스페이스 데이터 접근 시도 → 0 row 반환되어야 함
SET request.jwt.claim.sub = '<other-user-uuid>';
SELECT * FROM workspaces WHERE id = '<my-workspace-uuid>';
```

---

## 9. API 설계 원칙 (OpenAPI)

### 9-1. FastAPI 자동 OpenAPI 활용

- FastAPI는 Pydantic 스키마 기반 OpenAPI 자동 생성
- `/openapi.json`, `/docs` (Swagger UI), `/redoc` 자동 제공
- Frontend는 OpenAPI에서 타입 생성 (선택): `openapi-typescript` 도구 사용

### 9-2. 명명 규칙

- URL: kebab-case (`/api/audit-logs`)
- JSON 키: snake_case (`workspace_id`, `created_at`)
- Pydantic 필드: snake_case → 자동으로 JSON snake_case
- TypeScript 인터페이스: camelCase ↔ JSON snake_case 변환은 axios interceptor 또는 zod transform

### 9-3. 응답 표준

**성공**:
```json
{
  "data": { ... },
  "meta": { "page": 1, "total": 100 }   // 페이지네이션 시
}
```

**오류**:
```json
{
  "error": {
    "code": "WORKSPACE_QUOTA_EXCEEDED",
    "message": "Custom analysis quota exceeded for this month",
    "details": { "limit": 10, "used": 10 }
  }
}
```

오류 코드는 `app/errors.py`에 enum으로 관리.

### 9-4. 페이지네이션

- 기본: cursor 기반 (`?cursor=...&limit=20`)
- 페이지 기반은 admin 등 특수 케이스만

### 9-5. 멱등성 (Idempotency)

- 결제, 분석 트리거 등 중요 mutation은 `Idempotency-Key` 헤더 지원
- Redis에 24h 캐시

### 9-6. 인증 헤더

- 모든 보호된 엔드포인트: `Authorization: Bearer <supabase-jwt>`
- Internal cron: `X-Cron-Signature: <hmac-sha256>` + `X-Cron-Timestamp: <unix>`
- Stripe Webhook: `Stripe-Signature` (Stripe SDK 검증)

---

## 10. 코드 컨벤션

### 10-1. Frontend (TypeScript)

**ESLint + Prettier**:
- `eslint-config-next` 기반
- 추가 규칙: no-unused-vars, no-console (warn), prefer-const
- Prettier 옵션: 100자 줄, single quote, semi-colon, trailing comma

**파일명**:
- 컴포넌트: PascalCase 디렉토리 + `index.tsx` 또는 kebab-case 파일 (`button.tsx`)
- 일관성을 위해 **kebab-case** 권장 (`button.tsx`, `score-card.tsx`)
- 페이지: `page.tsx`, `layout.tsx` (Next.js 규약)

**컴포넌트 작성**:
```typescript
'use client';  // 클라이언트 컴포넌트 명시

import { type FC } from 'react';

interface Props {
  // ...
}

export const Button: FC<Props> = ({ ... }) => {
  // ...
};
```

**서버 컴포넌트 우선**: 가능하면 Server Component로, 인터랙션 필요 시에만 Client Component.

**i18n 사용**:
```typescript
import { useTranslations } from 'next-intl';

export default function Page() {
  const t = useTranslations('dashboard');
  return <h1>{t('title')}</h1>;
}
```

### 10-2. Backend (Python)

**Ruff + MyPy**:
- Ruff: lint + format 통합 (black 호환)
- MyPy: strict mode (`disallow_untyped_defs`, `no_implicit_optional`)

**`ruff.toml`**:
```toml
line-length = 100
target-version = "py312"

[lint]
select = ["E", "F", "W", "I", "N", "UP", "B", "ASYNC", "S"]
ignore = ["S101"]  # assert in tests OK
```

**파일명/네이밍**:
- 모듈: snake_case
- 클래스: PascalCase
- 함수/변수: snake_case
- 상수: UPPER_SNAKE_CASE

**FastAPI 라우터 패턴**:
```python
from fastapi import APIRouter, Depends
from app.deps import get_current_user, require_workspace_role
from app.schemas.workspace import WorkspaceCreate, WorkspaceResponse

router = APIRouter(prefix="/api/workspaces", tags=["workspaces"])

@router.post("", response_model=WorkspaceResponse, status_code=201)
async def create_workspace(
    payload: WorkspaceCreate,
    current_user = Depends(get_current_user),
):
    # ...
```

**비동기 우선**: 모든 IO는 async/await. 동기 IO 호출은 `run_in_threadpool` 사용.

### 10-3. SQL

- 키워드 대문자, 식별자 소문자
- 한 줄에 여러 컬럼 ❌
- JOIN 시 ON 조건 명시
- 명시적 `INNER JOIN`, `LEFT JOIN`

---

## 11. 테스트 전략

### 11-1. Frontend 테스트

**단위 (Vitest)**:
- 유틸 함수, 커스텀 훅, 작은 컴포넌트
- 커버리지 목표: 70%+

**컴포넌트 (Testing Library)**:
```typescript
import { render, screen } from '@testing-library/react';
import { Button } from './button';

test('renders with label', () => {
  render(<Button>Click me</Button>);
  expect(screen.getByText('Click me')).toBeInTheDocument();
});
```

**E2E (Playwright)**:
- 핵심 유저 저니: 가입 → 분석 → 결제 → 해지
- 멀티 브라우저: Chromium, Firefox, WebKit
- CI에서 매 PR 실행 (Vercel Preview URL 대상)

### 11-2. Backend 테스트

**단위 (pytest)**:
- 비즈니스 로직 (services/), 스코어링 (scoring/)
- 외부 API mocking (`pytest-mock`, `respx` for httpx)

**통합 (pytest + 테스트 DB)**:
- 라우터 → DB → 응답 전체 흐름
- 픽스처: 테스트 DB 트랜잭션 롤백 패턴

**`conftest.py` 예시**:
```python
import pytest
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from app.db.session import Base

@pytest.fixture
async def db_session():
    engine = create_async_engine(TEST_DATABASE_URL)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    async with AsyncSession(engine) as session:
        yield session
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

@pytest.fixture
async def authenticated_client(db_session):
    # ...
```

**커버리지 목표**: 80%+ (서비스 레이어 / 라우터 / 스코어링)

### 11-3. 분석 엔진 테스트

스냅샷 테스트:
- 알려진 사이트 (예: example.com)에 대한 분석 결과를 fixture로 저장
- 코드 변경 시 결과 비교

LLM 호출 mocking:
- `services/llm_synthesizer.py`는 추상화 → 테스트에서 fake response 주입

### 11-4. Stripe 테스트

- Stripe CLI로 webhook 로컬 forwarding
- 테스트 카드: `4242 4242 4242 4242` (성공), `4000 0000 0000 0002` (실패)
- `stripe trigger checkout.session.completed` 등으로 시나리오 시뮬레이션

---

## 12. CI/CD 파이프라인

### 12-1. GitHub Actions 구성

**`.github/workflows/frontend-ci.yml`**:
```yaml
name: Frontend CI
on:
  pull_request:
    paths: ['frontend/**']
  push:
    branches: [main, v2]
    paths: ['frontend/**']

jobs:
  lint-test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: pnpm/action-setup@v4
        with: { version: 9 }
      - uses: actions/setup-node@v4
        with: { node-version: 20, cache: 'pnpm' }
      - run: pnpm install --frozen-lockfile
        working-directory: frontend
      - run: pnpm lint
        working-directory: frontend
      - run: pnpm typecheck
        working-directory: frontend
      - run: pnpm test
        working-directory: frontend
      - run: pnpm build
        working-directory: frontend
```

**`.github/workflows/backend-ci.yml`**:
```yaml
name: Backend CI
on:
  pull_request:
    paths: ['backend/**', 'supabase/**']
  push:
    branches: [main, v2]
    paths: ['backend/**', 'supabase/**']

jobs:
  lint-test:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: pgvector/pgvector:pg16
        env:
          POSTGRES_PASSWORD: postgres
        ports: ['5432:5432']
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
      redis:
        image: redis:7-alpine
        ports: ['6379:6379']
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: '3.12' }
      - run: pip install poetry
      - run: poetry install
        working-directory: backend
      - run: poetry run ruff check .
        working-directory: backend
      - run: poetry run mypy app
        working-directory: backend
      - run: poetry run pytest --cov=app
        working-directory: backend
        env:
          DATABASE_URL: postgresql+asyncpg://postgres:postgres@localhost/postgres
          REDIS_URL: redis://localhost:6379
```

**`.github/workflows/e2e.yml`**:
```yaml
name: E2E
on:
  pull_request:
  workflow_dispatch:

jobs:
  playwright:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      # ... wait for Vercel preview URL
      - run: pnpm playwright install --with-deps
      - run: pnpm playwright test
        env:
          BASE_URL: ${{ env.PREVIEW_URL }}
```

### 12-2. 배포 트리거

| 브랜치 | 액션 | 환경 |
|---|---|---|
| `feature/*`, `fix/*` | PR 생성 → preview deploy | Vercel preview, Railway PR (선택) |
| `v2` | merge → staging deploy | staging.aeo-visibility.com (선택) |
| `main` | merge → production deploy | aeo-visibility.com |

### 12-3. 시크릿 관리

GitHub Repository Secrets에 등록:
- `VERCEL_TOKEN`, `VERCEL_PROJECT_ID`, `VERCEL_ORG_ID`
- `RAILWAY_TOKEN`
- `SUPABASE_ACCESS_TOKEN`
- `STRIPE_SECRET_KEY` (테스트 모드용)

> 운영 시크릿은 Vercel/Railway 대시보드에 직접 등록.

---

## 13. 로컬 개발 워크플로우

### 13-1. 초기 설정

```bash
# 클론
git clone https://github.com/[org]/aeo-visibility.git
cd aeo-visibility

# Frontend
cd frontend
pnpm install
cp .env.template .env.local
# .env.local 편집 (가이드는 README)
pnpm dev   # http://localhost:3000

# Backend (별도 터미널)
cd backend
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
poetry install
cp .env.template .env
# .env 편집
uvicorn app.main:app --reload --port 8000

# Supabase 로컬 (선택)
supabase start
# Studio: http://localhost:54323
# DB: postgresql://postgres:postgres@localhost:54322/postgres

# Stripe Webhook 로컬 forwarding (별도 터미널)
stripe login
stripe listen --forward-to localhost:8000/api/webhooks/stripe
# whsec_... 출력 → backend .env STRIPE_WEBHOOK_SECRET에 입력
```

### 13-2. 일상 워크플로우

```bash
# 새 기능 시작
git checkout v2
git pull
git checkout -b feature/wiki-search

# 작업, 커밋
git add .
git commit -m "feat(wiki): add full-text search"

# PR 생성
gh pr create --base v2 --title "feat(wiki): full-text search"

# CI 통과 + 리뷰 후 머지 (squash merge 권장)
```

### 13-3. 마이그레이션 작업

```bash
# 1. 마이그레이션 작성
echo "-- New table" > supabase/migrations/$(date +%Y%m%d%H%M%S)_add_xyz.sql

# 2. 로컬 적용
supabase migration up

# 3. SQLAlchemy 모델 작성/갱신 (수동)
# backend/app/models/xyz.py

# 4. 타입 재생성
supabase gen types typescript --local > frontend/src/types/database.ts

# 5. 테스트 추가
pytest backend/tests/...

# 6. 커밋
git add supabase/migrations backend/app/models frontend/src/types
git commit -m "feat(db): add xyz table"
```

### 13-4. 환경 자료

`README.md`에 명시:
- 필수 외부 서비스 가입 가이드 (Supabase, Stripe, Resend, Voyage, Anthropic)
- 환경변수 입수 경로
- 로컬 실행 troubleshooting

---

## 14. 모니터링 / 관측성

### 14-1. 로깅

**Backend**:
- Python `logging` 모듈, JSON 포맷터
- 레벨: DEBUG (개발), INFO (운영 기본), WARNING/ERROR
- 구조화 필드: `request_id`, `user_id`, `workspace_id`, `action`

**Frontend**:
- 콘솔은 dev only
- 운영: Vercel 로그 + 클라이언트 에러는 Sentry (Phase 4)

**Logflare 연동** (Supabase 통합):
- Supabase Pro에서 무료
- 구조화 로그 검색 가능

### 14-2. 에러 추적 (Phase 4)

- **Sentry** (Frontend + Backend)
- DSN을 환경변수로
- PII 필터링 정책 명시 (이메일, 토큰 자동 제거)

### 14-3. 메트릭

**Backend**:
- 분석 실행 메트릭: duration_ms, status, category, plan
- DB에 `analysis_results` 자체가 메트릭 소스
- Stripe webhook 처리 시간/실패율 (audit_logs)

**Frontend**:
- Vercel Web Analytics (무료)
- Speed Insights

### 14-4. 헬스체크

```python
# backend/app/main.py
@app.get("/api/health")
async def health(db: Session = Depends(get_db), redis = Depends(get_redis)):
    return {
        "status": "ok",
        "db": await check_db(db),
        "redis": await check_redis(redis),
        "version": settings.app_version,
    }
```

Railway가 5분마다 헬스체크 호출.

### 14-5. 알람 (Phase 4)

- Stripe Webhook 실패율 > 5% → Slack 알림
- 분석 실패율 > 10% → Slack 알림
- DB 연결 풀 고갈 → Slack 알림
- 일일 비용 한도 초과 → Slack 알림

---

## 15. 보안 체크리스트

### 15-1. 항상 지켜야 할 것

- [ ] `SUPABASE_SERVICE_ROLE_KEY`는 백엔드만, Frontend ❌
- [ ] `.env*` 파일은 절대 커밋 ❌ (.gitignore 확인)
- [ ] Stripe Webhook 서명 검증 100%
- [ ] 모든 API 엔드포인트에 인증 검사 (public 라우트 제외)
- [ ] RLS 정책 모든 테이블에 적용
- [ ] CORS는 명시적 허용 도메인만
- [ ] HTTPS 강제 (Vercel/Railway 기본)
- [ ] SQL Injection 방지 (SQLAlchemy ORM 사용, raw SQL 금지)
- [ ] XSS 방지: React 자동 escape + Wiki Markdown은 `rehype-sanitize`
- [ ] CSRF: Supabase JWT가 헤더 기반이라 자동 방지
- [ ] Rate limit: Q&A, 로그인 시도, 분석 트리거
- [ ] 비밀번호 정책 N/A (Magic Link만)

### 15-2. 정기 점검 (분기별)

- [ ] 의존성 보안 업데이트 (`npm audit`, `pip-audit`)
- [ ] 노출된 시크릿 검사 (gitleaks)
- [ ] 권한 정책 리뷰 (super_admin 명단)
- [ ] 백업 복원 훈련 (Supabase)

### 15-3. 사고 대응

- 침해 의심 시 즉시:
  1. 영향받은 시크릿 회전
  2. 영향받은 사용자 통보 (GDPR 72시간 의무)
  3. audit_logs에서 영향 범위 파악
  4. 사후 분석 보고서 작성

---

## 16. 성능 최적화 가이드

### 16-1. Frontend

- **React Server Components** 우선 (대부분 페이지)
- 이미지는 `next/image` (자동 최적화)
- 폰트는 `next/font` (CSP 안전, FOUC 방지)
- 동적 import로 무거운 컴포넌트 lazy load (PDF 생성기 등)
- `prefetch` 자동 (Link 컴포넌트)
- TanStack Query로 중복 호출 제거 + stale-while-revalidate
- 번들 분석: `@next/bundle-analyzer`

### 16-2. Backend

- DB 쿼리:
  - N+1 방지 (`selectinload`, `joinedload`)
  - 인덱스: WHERE/ORDER BY 컬럼 + JSON 키 (GIN)
  - 페이지네이션은 cursor 기반
- Redis 캐싱:
  - 분석 결과 status (TTL 1h)
  - Q&A 답변 (TTL 7d)
  - Wiki 인덱스 (TTL 1d)
- 외부 API:
  - Claude/Voyage 호출은 `tenacity` 재시도 (백오프)
  - HTTP connection pool (httpx 기본 사용)

### 16-3. DB

- pgvector HNSW 인덱스 (코사인 유사도)
- 큰 JSONB는 별도 테이블로 분리 검토 (analysis_results.raw_metrics가 비대해질 경우)
- Vacuum 자동 (Supabase 관리)

### 16-4. CDN / 캐시

- Vercel Edge Network 자동
- Wiki 글: ISR (`revalidate: 3600`) → CDN 캐시 1시간
- 정적 자산: immutable + long max-age

---

## 17. Git 브랜치 전략

### 17-1. 브랜치 모델

```
main             ← production (현재 MVP 라이브)
v2               ← v2 개발 통합 브랜치 (Phase 1~4 누적)
feature/...      ← 기능 단위 브랜치 (v2에서 분기)
fix/...          ← 버그 수정
hotfix/...       ← main에 직접 머지하는 긴급 수정
```

### 17-2. 머지 전략

- `feature/*` → `v2`: **Squash merge** (커밋 깔끔하게)
- `v2` → `main`: **Merge commit** (이력 보존)
- `hotfix/*` → `main`: **Squash merge**, 후 `v2`에 cherry-pick

### 17-3. 브랜치 보호

GitHub Branch Protection (main, v2):
- Require PR before merge
- Require status checks (frontend-ci, backend-ci)
- Require 1 approval (팀 운영 시)
- Dismiss stale reviews on push
- Require linear history (선택)

### 17-4. 커밋 메시지 (Conventional Commits)

```
<type>(<scope>): <subject>

[optional body]

[optional footer]
```

**Type**:
- `feat`: 신규 기능
- `fix`: 버그 수정
- `refactor`: 동작 변경 ❌
- `chore`: 빌드, 의존성
- `docs`: 문서
- `test`: 테스트
- `perf`: 성능
- `style`: 포매팅
- `ci`: CI/CD

**예시**:
```
feat(analysis): add custom category selection UI

- Modal with 5 checkboxes
- Quota validation before queueing
- Time series visual distinction (full vs partial)

Closes #123
```

---

## 18. PR 가이드

### 18-1. PR 크기

- 권장: **변경 라인 < 400줄** (리뷰 가능 범위)
- 큰 기능은 작은 PR로 분할 (인터페이스 → 구현 → UI 등)

### 18-2. PR 템플릿

```markdown
## What
[변경 사항 1-2줄]

## Why
[배경, 의도]

## How
[구현 접근, 트레이드오프]

## Screenshots
[UI 변경 시]

## Test plan
- [ ] Unit tests added
- [ ] E2E updated
- [ ] Manual: [scenario]

## Migration impact
- [ ] DB migration: [yes/no]
- [ ] Env vars: [list]
- [ ] Breaking change: [yes/no]
```

### 18-3. 리뷰 체크리스트

- [ ] SPEC과 일치하는가?
- [ ] 테스트 추가됐는가?
- [ ] RLS / 권한 검증 빠지지 않았는가?
- [ ] 환경변수 추가 시 .env.template 업데이트?
- [ ] 마이그레이션 idempotent하지 않아도 됨, 단 일관성 OK?
- [ ] 보안 체크리스트 통과?
- [ ] PII 로깅 없음?

---

## 19. 트러블슈팅 (자주 발생하는 문제)

### 19-1. Supabase

**문제**: RLS로 데이터가 안 보임
- 해결: SQL Editor에서 `SET request.jwt.claim.sub = '<uuid>'` 후 쿼리 실행 → 정책 디버깅
- 백엔드는 service_role 키 사용 중인지 확인

**문제**: pgvector 차원 불일치
- 해결: `vector(1024)`는 voyage-3 차원. Voyage 모델 변경 시 마이그레이션 필요

**문제**: pg_cron이 외부 API 호출 못함
- 해결: Supabase에서 `http` extension 활성화 + `net.http_post()` 사용

### 19-2. Stripe

**문제**: Webhook 서명 검증 실패
- 해결: STRIPE_WEBHOOK_SECRET이 현재 endpoint의 시크릿과 일치하는지 확인. 로컬은 `stripe listen` 출력값.

**문제**: 구독 상태 동기화 누락
- 해결: webhook idempotency 키 검증, 재처리 로직 확인

### 19-3. Frontend

**문제**: 빌드 시 환경변수 누락
- 해결: Vercel 환경변수 확인 + `next.config.mjs`의 `env` 노출 누락 여부

**문제**: i18n 라우트가 404
- 해결: `middleware.ts`에서 lang 매처 확인 + `[lang]/` 폴더 구조

**문제**: PDF 렌더 시 폰트 깨짐
- 해결: @react-pdf/renderer는 폰트를 별도 등록 필요. `Font.register({...})`로 Pretendard 등록

### 19-4. Backend

**문제**: BackgroundTasks가 응답 후 실행 안 됨
- 해결: ASGI 서버가 응답 종료 전에 task를 완료시켜야 함. 큰 작업은 Redis 큐로

**문제**: Claude API rate limit
- 해결: tenacity 재시도 + 동시 호출 제한 (semaphore)

---

## 20. Phase별 개발 체크리스트

### 20-1. Phase 1: 코어 (~6-8주)

**Backend**:
- [ ] Supabase Auth JWT 검증 미들웨어
- [ ] 모델 (profiles, workspaces, members, sites, analysis_results, monthly_usage, audit_logs)
- [ ] 라우터 (workspaces, members, sites, analyses, qa[mock])
- [ ] 분석 엔진 표준 스키마 정의 (`scoring/schema.py`)
- [ ] 5개 카테고리 모듈 재작성
- [ ] LLM 통합 호출 (`services/llm_synthesizer.py`)
- [ ] BackgroundTasks 통합
- [ ] pg_cron 자동 분석 스케줄러
- [ ] Resend 트랜잭셔널 이메일 (Magic Link, 분석 완료, 초대)

**Frontend**:
- [ ] Supabase Auth 통합 (Magic Link)
- [ ] 워크스페이스 CRUD UI
- [ ] 사이트 CRUD UI (변경 1회/월 표시)
- [ ] 분석 진행/결과 대시보드
- [ ] Custom 재분석 모달
- [ ] 시계열 그래프 (recharts, 전체/부분 시각 구분)
- [ ] 멤버 초대 UI

**DB / Infra**:
- [ ] 마이그레이션 003-015
- [ ] RLS 정책 적용
- [ ] 시드 데이터 (plans)
- [ ] Frontend ↔ Backend 인증 검증

### 20-2. Phase 2: 결제 (~4-6주)

**Backend**:
- [ ] Stripe Checkout / Customer Portal 통합
- [ ] Stripe Webhook 핸들러 (모든 시나리오)
- [ ] 구독 상태 동기화 + audit_logs
- [ ] add-on 13종 처리 (seat / viewer_seat / own_site / competitor_site / ai_engine /
      custom_pack_basic·pro / payg_custom / looker_studio / api_access /
      extra_workspace / data_retention_extension / pdf_branding) — SPEC §5-2 `addon_type` ENUM
- [ ] 트라이얼 → 유료 전환 로직 (카드 등록은 첫 결제 시점)
- [ ] 트라이얼 만료 후 자동 이메일 시퀀스 (Day 7 / Day 30 / Day 90, SPEC §4-3)
- [ ] 워크스페이스 7일 grace + grace_processor 작업
- [ ] 데이터 보관 1년 grace 처리
- [ ] 강제 소유권 이양 로직
- [ ] **쿠폰 시스템 (Phase 4 → Phase 2 당김)**: SPEC §14 전체 — 코드형/블라인드/auto_apply 3모드.
      Phase 2 출시 시 시즌 프로모션(Cyber Monday 등) 가능 필수.
- [ ] Stripe Coupon / PromotionCode 동기화
- [ ] Pricing 페이지 active auto_apply 쿠폰 조회 API
- [ ] Admin 라우터 기본 (users, workspaces, subscriptions, coupons, stats)
- [ ] 결제 관련 이메일 템플릿

**Frontend**:
- [ ] Pricing 페이지 (월간/연간 토글, 4-tier 카드 + Free Trial CTA + Enterprise "Contact Sales")
- [ ] Pricing 페이지 active auto_apply 프로모션 노출 (`~~정가~~ 할인가` + 만료 카운트다운)
- [ ] Stripe Checkout 리디렉션 (auto_apply 쿠폰 자동 attach, 사용자 코드 입력 옵션)
- [ ] Customer Portal 링크
- [ ] 사용량 표시 (잔여 Custom 횟수 — base / basic_pack / pro_pack / payg 분리, 멤버 수)
- [ ] 티어 한도 도달 시 업그레이드 / add-on 구매 프롬프트
- [ ] 워크스페이스 삭제 흐름 (Danger Zone)
- [ ] Admin 패널 기본 + 쿠폰 빌더 (코드형 / 블라인드 / auto_apply 3모드 토글)

**DB**:
- [ ] 마이그레이션 016 — subscriptions / subscription_addons (addon_type 13종)
- [ ] 마이그레이션 017 — workspace_invitations
- [ ] 마이그레이션 018 — coupons / coupon_redemptions (Phase 4 → Phase 2 당김)

### 20-3. Phase 3: PDF + 경쟁사 + i18n (~5-7주)

**Backend**:
- [ ] PDF 생성 백엔드 트리거 (자동 분석 시)
- [ ] CSV export 엔드포인트
- [ ] 경쟁사 분석 로직 (사이트 type='competitor')
- [ ] LLM 출력 다국어 (workspace primary_language 저장)
- [ ] on-demand 번역 + Redis 캐시
- [ ] 이메일 템플릿 다국어

**Frontend**:
- [ ] @react-pdf/renderer 컴포넌트 (12p 구성)
- [ ] CSV 다운로드 버튼 (Pro+)
- [ ] 경쟁사 비교 UI (Pro/Business)
- [ ] 경쟁사 추이 그래프 (Pro 12개월 / Business 24개월)
- [ ] 산업 벤치마크 페이지 (Business 이상)
- [ ] **next-intl 도입** (한/영/스페인어)
- [ ] 메시지 번들 작성 (전체 UI 텍스트)
- [ ] 메트릭 i18n 키 매핑
- [ ] PDF 다국어 폰트 등록 (Pretendard, Noto)

**DB**:
- [ ] 마이그레이션 018 (Storage 정책)

### 20-4. Phase 4: Wiki + Q&A + Admin 고도화 (~5-7주)

> 쿠폰 시스템은 Phase 2로 당겨졌음 (§20-2 참조). Phase 4는 Wiki + Q&A 중심.

**Backend**:
- [ ] pgvector 확장 활성화
- [ ] Voyage AI 임베딩 서비스
- [ ] Wiki 임베딩 자동 생성 작업
- [ ] Q&A RAG 파이프라인 (`services/qa_service.py`)
- [ ] Q&A 응답 캐싱 (Redis)
- [ ] 마케팅 이메일 발송 (rate limit, 동의 검증)
- [ ] Admin Wiki 라우터

**Frontend**:
- [ ] Wiki 공개 페이지 (다국어 라우트)
- [ ] Wiki 카테고리/검색 UI
- [ ] sitemap.ts, robots.ts (Wiki 포함)
- [ ] JSON-LD 구조화 데이터
- [ ] hreflang 자동 처리
- [ ] Q&A 전체 페이지 + floating widget
- [ ] Q&A 출처 카드
- [ ] Admin Wiki 에디터 (다국어 탭)
- [ ] Audit logs 뷰어

**DB**:
- [ ] 마이그레이션 — pgvector / wiki / qa 관련 (쿠폰 제외, Phase 2에 이미 적용됨)

---

## 21. 외부 서비스 가입 / 설정

| 서비스 | 가입 후 작업 |
|---|---|
| **Anthropic** | API 키 발급, 결제 카드 등록, monthly limit 설정 |
| **Voyage AI** | 가입, API 키 발급 → 사용자 공유 예정 |
| **Stripe** | 한국 법인 활성화, 약관 동의, 상품(Plans) 생성 → price_id 시드 데이터 입력 |
| **Resend** | 도메인 인증 (SPF/DKIM/DMARC), API 키 발급, alias 설정 (no-reply, hello, support) |
| **Supabase** | Pro 플랜 (운영), pg_cron / pgvector 활성화 |
| **Upstash** | Redis 인스턴스 생성 (Free → Pay-as-you-go) |
| **Vercel** | 도메인 연결, 환경변수 등록 |
| **Railway** | Backend 배포, 환경변수 등록 |
| **GitHub** | Branch protection, Repository Secrets, Actions 활성화 |

---

## 22. 추후 확장 (참고)

### 22-1. 1만명 이상 도달 시
- BackgroundTasks → Celery + Redis Queue (또는 Inngest)
- Backend 다중 인스턴스 (Railway Pro)
- DB read replica (Supabase Team)
- Sentry / Datadog 도입
- AWS / GCP 마이그레이션 검토 (multi-region)

### 22-2. Enterprise 기능
- SSO (SAML, OAuth)
- DPA, SOC 2 준비
- Custom SLA
- 화이트라벨

### 22-3. 모바일
- React Native 또는 Expo
- 현재 반응형 웹으로 시작

---

*최종 업데이트: 2026-05-02*
*관련 문서:*
- *`docs/SPEC.md` (종합 스펙, 무엇을)*
- *`docs/reboot-service-concept.md` (의사결정 정리)*
- *`DEPLOY.md` (현재 배포 가이드)*
