# AEO Visibility — 종합 스펙 (SPEC)

> 본 문서는 AEO Visibility 서비스의 종합 스펙입니다.
> 의사결정의 출처: `docs/reboot-service-concept.md`
> 개발 환경/라이브러리 디테일은: `docs/DEV_SPEC.md` (별도)

---

## 1. 문서 개요

### 1-1. 목적
AEO Visibility는 **AEO(Answer Engine Optimization)** 관점에서 웹사이트의 가시성을 측정·모니터링·개선 가이드를 제공하는 구독형 SaaS입니다.

### 1-2. 핵심 가치 제안
- **5축 분석**: Technical / Structured / Content / Authority / Visibility 카테고리별 점수
- **자동 모니터링**: 월 1회 자동 분석 + 사용자 트리거 Custom 재분석
- **경쟁사 비교**: Pro/Business 티어에서 경쟁사와 나란히 비교 (Business는 심층 분석 + 산업 벤치마크)
- **AI 가이드**: Wiki + RAG 기반 Q&A로 개선 방향 제시
- **다국어**: 한국어 / 영어 / 스페인어

### 1-3. 문서 범위
- ✅ 시스템 아키텍처, 데이터 모델, 권한, 결제, 스케줄링, 분석, 리포트, Wiki/Q&A, 쿠폰, Admin, i18n, 이메일, 유저 저니, API 엔드포인트, 비기능 요구사항, 개발 로드맵
- ❌ 구체적 라이브러리 버전, 디렉토리 구조, 환경변수, 마이그레이션 스크립트 (→ DEV_SPEC)
- ✅ 가격 정책 최종 확정 (2026-05-02, Section 4 참조)

---

## 2. 시스템 아키텍처

### 2-1. 전체 구성도

```
┌─────────────────────────────────────────────────────────────────────┐
│                            User / Browser                           │
└─────────────────────────────┬───────────────────────────────────────┘
                              │ HTTPS
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│  Frontend (Next.js 14 App Router) — Vercel                          │
│  - [lang]/ routing (ko/en/es)                                       │
│  - next-intl                                                        │
│  - Public: Landing, Pricing, Wiki                                   │
│  - App: Dashboard, Sites, Reports, Settings, Q&A                    │
│  - Admin: /admin/* (super_admin only)                               │
└─────────────────────────────┬───────────────────────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        │                     │                     │
        ▼                     ▼                     ▼
┌──────────────┐    ┌──────────────────┐    ┌────────────────────┐
│ Supabase     │    │ Backend API       │    │ Stripe             │
│ - Auth       │    │ FastAPI - Railway │    │ - Checkout         │
│ - Postgres   │    │ - REST endpoints  │    │ - Customer Portal  │
│ - pgvector   │    │ - BackgroundTasks │    │ - Webhooks         │
│ - Storage    │    │ - Stripe webhook  │    │                    │
│ - RLS        │    │ - Analysis engine │    │                    │
│ - pg_cron    │    └─────┬─────────────┘    └────────────────────┘
└──────┬───────┘          │
       │                  │
       └─────┬────────────┘
             │
   ┌─────────┴──────────┬──────────────┬──────────────┐
   ▼                    ▼              ▼              ▼
┌─────────┐    ┌──────────────┐  ┌──────────┐  ┌──────────┐
│ Upstash │    │ Anthropic    │  │ Voyage   │  │ Resend   │
│ Redis   │    │ Claude API   │  │ AI       │  │ Email    │
│ Cache   │    │ - Sonnet 4.6 │  │ voyage-3 │  │          │
│         │    │ - Haiku 4.5  │  │ Embedding│  │          │
└─────────┘    └──────────────┘  └──────────┘  └──────────┘
```

### 2-2. 컴포넌트 책임

| 컴포넌트 | 책임 |
|---|---|
| Frontend (Next.js) | UI 렌더링, 라우팅, 사용자 입력, Supabase 클라이언트 인증, Stripe Checkout 리디렉션 |
| Backend API (FastAPI) | 비즈니스 로직, 분석 실행, Stripe Webhook 처리, BackgroundTasks 큐 관리 |
| Supabase Postgres | 메인 DB. RLS로 워크스페이스 격리. pgvector로 RAG 임베딩 저장 |
| Supabase Auth | Magic Link 인증, JWT 발급 |
| Supabase Storage | PDF 리포트, Wiki 이미지 저장 |
| Supabase pg_cron | 월간 자동 분석, 데이터 grace 만료 처리 |
| Upstash Redis | 분석 진행 상태, Q&A 답변 캐시, rate limit |
| Anthropic Claude API | 분석 인사이트 생성 (Sonnet), Q&A 답변 (Haiku) |
| Voyage AI | Wiki 청크 임베딩 (voyage-3, 1024차원) |
| Resend | 트랜잭셔널/마케팅 이메일 |
| Stripe | 결제 처리, 구독 관리, 쿠폰 적용 |

### 2-3. 데이터 흐름 예시

**자동 월간 분석**:
```
pg_cron(매월 1일 00:00 UTC)
  → Backend /internal/cron/monthly-analysis (HMAC 서명 검증)
  → 활성 사이트 목록 조회 (workspace 활성, plan별 사이트 수 한도 내)
  → 각 사이트에 대해 BackgroundTask enqueue
  → 분석 엔진 (5 카테고리 병렬 실행) → Claude API
  → analysis_results INSERT → PDF 생성 → Supabase Storage 업로드
  → Resend 이메일 발송 (워크스페이스 owner+admin)
```

**Custom 재분석**:
```
User 클릭 → POST /api/workspaces/:id/sites/:site_id/analyze {categories: [...]}
  → 잔여 횟수/쿨다운/한도 검증
  → BackgroundTask enqueue → Redis에 진행 상태 기록
  → Frontend가 5초 polling
  → 완료 시 대시보드 갱신, 사용자가 PDF/CSV 다운로드 버튼 클릭
```

---

## 3. 기술 스택

### 3-1. Frontend
- **Framework**: Next.js 14 (App Router)
- **Language**: TypeScript 5
- **Styling**: Tailwind CSS 3
- **i18n**: next-intl
- **Auth Client**: @supabase/ssr
- **PDF Render**: @react-pdf/renderer
- **Charts**: recharts
- **Form**: react-hook-form + zod
- **State**: TanStack Query (server state) + zustand (client state, 최소)
- **Markdown (Wiki)**: @next/mdx 또는 react-markdown

### 3-2. Backend
- **Framework**: FastAPI 0.115
- **Language**: Python 3.12
- **DB ORM**: SQLAlchemy 2 (asyncio) + Alembic
- **DB Driver**: asyncpg
- **Cache**: redis-py
- **HTTP Client**: httpx
- **Crawling**: beautifulsoup4 + lxml
- **Anthropic SDK**: anthropic >=0.43
- **Voyage SDK**: voyageai
- **Stripe SDK**: stripe
- **Email**: resend
- **Background**: FastAPI BackgroundTasks (1만 명 미만 단계)

### 3-3. Infrastructure
- **Frontend Host**: Vercel (Next.js)
- **Backend Host**: Railway
- **DB**: Supabase Postgres + pgvector + RLS
- **Storage**: Supabase Storage
- **Cron**: Supabase pg_cron
- **Cache**: Upstash Redis
- **Email**: Resend (도메인 1개, alias 3개)
- **Payment**: Stripe (USD, 한국 법인)
- **CI/CD**: GitHub Actions → Vercel/Railway

> 라이브러리 정확한 버전은 DEV_SPEC.md 참조.

---

## 4. 티어별 기능 매트릭스 — **확정 (2026-05-02)**

> **출처**: `research/compare-price-policy.md` Section 7 (시장조사 + 사용자 결정 v3.1)
> **구조**: 5-tier (Basic/Medium/Pro/Premium) → **4-tier (Basic/Pro/Business)** + Free trial + Enterprise 단순화

### 4-1. 핵심 매트릭스

| 기능 | Free (Trial) | Basic | Pro | Business | Enterprise |
|---|---|---|---|---|---|
| **가격 (USD/월)** | $0 | **$19.99** | **$79.99** | **$299.99** | **$1,499.99** |
| **연간 (월 환산, 15% 할인)** | — | $16.99 | $67.99 | $254.99 | $1,274.99 (annual commit 필수) |
| **자사 사이트 수** | 1 (trial) | 1 | 3 | 5 | 무제한 |
| **경쟁사 사이트 옵션** | — | — | 사이트당 1건 옵션 | 사이트당 3건 옵션 | 자사 + 경쟁사 5 |
| **자사 사이트 추가 단가** | — | $9.99/site/월 | $9.99/site/월 | $9.99/site/월 | 협의 |
| **경쟁사 사이트 추가 단가** | — | — | **$39.99/site/월** | **$39.99/site/월** | 협의 |
| **기본 AI 엔진** | 3 | 3 (Google AI Overviews, Claude, ChatGPT) | 3 | 3 | **모든 엔진 (10+)** |
| **AI 엔진 추가 단가** | — | $19.99/engine/월 | $19.99/engine/월 | $19.99/engine/월 | 포함 |
| **자동 모니터링 빈도** | 1회 (총) | **월 1회** | **월 1회** | **월 1회** | **월 1회** |
| **Custom 재분석** | ❌ | ✅ | ✅ | ✅ | ✅ |
| **Custom 한도 (월 기본)** | — | **5회** | **30회** | **100회** | **무제한** |
| **Custom Pack 추가** | — | Basic Pack $4.99 (+5) | Basic/Pro Pack | Pro Pack $14.99 (+20) | 포함 |
| **PAYG (단건)** | — | $2.99/회 | $2.99/회 | $2.99/회 | 포함 |
| **5개 카테고리 분석** | ✅ | ✅ | ✅ | ✅ | ✅ |
| **시계열 그래프** | — | 6개월 | 12개월 | 24개월 | 무제한 |
| **PDF 리포트 다운로드** | ✅ (1회) | ✅ | ✅ | ✅ | ✅ + 브랜딩 무료 |
| **PDF 브랜딩 커스텀** | — | $19.99 (1회) | $19.99 (1회) | $19.99 (1회) | 무료 |
| **CSV 데이터 export** | ❌ | ❌ | ✅ | ✅ | ✅ |
| **경쟁사 비교 그래프** | ❌ | ❌ | ✅ (1건) | ✅ (심층, 3건) | ✅ (심층, 5건) |
| **산업 벤치마크** | ❌ | ❌ | ❌ | ✅ | ✅ |
| **워크스페이스 멤버 (기본)** | 1 | 1 | 3 | 5 | 20 |
| **시트 추가 단가** | — | $2.99/u/월 | $2.99/u/월 | $2.99/u/월 | 협의 |
| **외부 컨설턴트 (Viewer 시트)** | — | — | $1.99/u/월 | $1.99/u/월 | 포함 |
| **Looker Studio Connector** | — | ❌ | $19.99/월 | $19.99/월 | 포함 |
| **API 액세스** | — | — | Add-on $99/월 | Add-on $99/월 | 기본 포함 |
| **추가 워크스페이스** | — | — | $99/월/ws | $99/월/ws | 협의 |
| **데이터 보관 연장 (5→7년)** | — | — | — | $49/월 | 포함 |
| **이메일 알림** | ✅ | ✅ | ✅ | ✅ | ✅ |
| **Q&A 사용** | rate limit만 | **무제한** (rate limit 외) | **무제한** | **무제한** | **무제한** |
| **Wiki 열람 (공개)** | ✅ | ✅ | ✅ | ✅ | ✅ |
| **Wiki 워크스페이스 전용** | — | — | — | — | ✅ |
| **다국어 (한/영/스페인어)** | ✅ | ✅ | ✅ | ✅ | ✅ |
| **SSO (SAML/OIDC)** | — | — | — | — | ✅ |
| **감사 로그** | — | — | 30일 | 90일 | 무제한 |
| **온보딩** | — | 셀프 | 셀프 | 셀프 | **White-glove** (2회 콜) |
| **지원 채널** | 셀프 | Email | Email + Chat | Email + Chat + 4h SLA | **Dedicated Slack + 2h SLA + AM** |
| **GDPR DPA / HIPAA / SOC2 docs** | — | — | — | — | 무료 |

> 가격은 **확정** (2026-05-02). 변동 시 본 문서와 `research/compare-price-policy.md` Section 7 동시 갱신.

### 4-2. 가격 ladder 검증

| 단계 | Ratio | 평가 |
|---|---|---|
| Basic ($19.99) → Pro ($79.99) | 4.0x | ✅ 정상 |
| Pro ($79.99) → Business ($299.99) | 3.75x | ✅ 정상 |
| Business ($299.99) → Enterprise ($1,499.99) | 5.0x | ✅ 정상 |
| **평균** | **4.22x** | ✅ 75배 격차의 3제곱근과 일치 — **이론적 균형값** |

### 4-3. 트라이얼 정책 (확정)

| 항목 | 정책 |
|---|---|
| **트라이얼 형식** | **7-day free trial** (시간 기반) |
| **트라이얼 중 기능** | Pro 티어 수준 (자사 1, 경쟁사 1, Custom 재분석 일부 허용, 3 시트) |
| **카드 등록** | ❌ (첫 유료 결제 시점에 등록) |
| **트라이얼 만료 후 시퀀스** | 자동 이메일 시퀀스 ↓ |

#### 트라이얼 만료 후 이메일 시퀀스 (확정)

| 시점 | 액션 | 메시지 컨셉 |
|---|---|---|
| **Day 7 (만료 직후)** | 1차 이메일 | 즉시 전환 인센티브 — "지금 가입 시 첫 달 30% 할인 (3일 한정)" |
| **Day 30** | 2차 이메일 | 재참여 유도 — "잊으셨나요? 다시 시작하면 첫 달 50% 할인" |
| **Day 90** | 3차 이메일 (최종) | 최종 제안 — "마지막 기회: 첫 3개월 50% 할인 + 1:1 데모" |
| **Day 90+** | 시퀀스 종료 | 마케팅 동의자만 일반 뉴스레터로 전환 |

> 재트라이얼 ❌ (만료 후 추가 트라이얼 ❌, 단 위 시퀀스의 최종 제안에 한정)

### 4-4. 결제 / 할인 정책 (확정)

| 항목 | 정책 |
|---|---|
| **연간 할인** | 모든 티어 15% (시작 표준). 시즌별 적극적 할인은 쿠폰 시스템으로 운용 |
| **연간 약정 (Enterprise)** | 필수 — 중도 해지 시 잔여 12개월 정산 |
| **쿠폰 시스템** | Section 14의 일반/블라인드 쿠폰 + 시즌 캠페인. **연간 할인과 중복 적용 ❌** |
| **결제 통화** | USD 단일 (한국 사용자도 USD 결제) |
| **결제 수단** | Stripe (Visa, MC, Amex, UnionPay), Enterprise는 wire transfer 가능 |
| **환불 정책** | 월간: 7일 이내 미사용 시 가능 / 연간: 30일 이내 환불, 이후 prorated / Enterprise: 계약별 |

### 4-5. 사이트/멤버 운영 제약 (어뷰징 방지)

| 제약 | 적용 |
|---|---|
| 사이트 변경 (URL 교체) | 워크스페이스당 월 1회. 단, **첫 분석 전 변경은 횟수 미차감** |
| 사이트 삭제 cooldown | 삭제 후 30일간 동일 도메인 재등록 ❌ |
| 워크스페이스 삭제 | 7일 grace period (취소 가능) → 영구 삭제 |
| 분석 결과 보관 | 활성: 영구 / 만료 후: 1년 grace → 영구 삭제 / GDPR 즉시 삭제 요청 별도 |
| 동일 사이트 연속 분석 | 마지막 분석 후 1시간 cooldown |
| 워크스페이스당 동시 분석 | 1개 (큐잉) |
| Q&A rate limit | 시간당 10회 (abuse 방지) — Q&A는 횟수 무제한이지만 rate limit 적용 |

### 4-6. 자연스러운 업셀 메커니즘 (의도된 설계)

| 사용 패턴 | 청구액 | 결과 |
|---|---|---|
| Basic + AI 엔진 3개 추가 | $19.99 + $59.97 = **$79.96** | Pro($79.99)와 동가 → **Pro 전환 트리거** ✅ |
| Pro + 경쟁사 5건 추가 | $79.99 + $5.98(2 seats) + $199.95 = **$285.92** | Business($299.99)와 $14 차이 → **Business 업셀 명확** ⭐ |

---

## 5. 데이터 모델 (ERD + SQL)

### 5-1. 개념적 ERD

```
auth.users (Supabase Auth)
  └─ profiles                          # 사용자 프로필 확장
       ├─ marketing_consents            # 마케팅 동의
       └─ workspace_members → workspaces

workspaces
  ├─ workspace_members
  ├─ workspace_invitations
  ├─ subscriptions
  │    └─ subscription_addons
  ├─ sites
  │    ├─ analysis_results
  │    ├─ site_change_history
  │    └─ monitoring_schedule
  ├─ monthly_usage
  ├─ reports
  └─ deletion_grace_queue (워크스페이스 7일)

plans (master, seed data)
coupons
  └─ coupon_redemptions
wiki_articles
  └─ wiki_embeddings (pgvector)
qa_sessions
  └─ qa_messages
audit_logs
```

### 5-2. 주요 테이블 SQL

#### profiles
```sql
CREATE TABLE profiles (
    id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    display_name TEXT,
    preferred_language TEXT NOT NULL DEFAULT 'en' CHECK (preferred_language IN ('en', 'ko', 'es')),
    timezone TEXT NOT NULL DEFAULT 'UTC',
    marketing_consent BOOLEAN NOT NULL DEFAULT FALSE,
    marketing_consent_at TIMESTAMPTZ,
    age_verified BOOLEAN NOT NULL DEFAULT FALSE,
    last_login_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

#### plans (마스터 시드)
```sql
CREATE TABLE plans (
    id TEXT PRIMARY KEY,  -- 'free' | 'basic' | 'medium' | 'pro' | 'premium'
    name TEXT NOT NULL,
    price_monthly_usd NUMERIC(10,2) NOT NULL,
    price_annual_usd NUMERIC(10,2),
    max_sites INT NOT NULL,
    max_competitors INT NOT NULL DEFAULT 0,
    max_members_default INT NOT NULL DEFAULT 1,
    max_members_hardcap INT NOT NULL DEFAULT 1,
    custom_analyses_per_month INT NOT NULL DEFAULT 0,
    timeseries_months INT NOT NULL DEFAULT 0,  -- 0 = 무제한
    csv_export BOOLEAN NOT NULL DEFAULT FALSE,
    competitor_comparison BOOLEAN NOT NULL DEFAULT FALSE,
    competitor_trend_graph BOOLEAN NOT NULL DEFAULT FALSE,
    stripe_price_id_monthly TEXT,
    stripe_price_id_annual TEXT,
    is_active BOOLEAN NOT NULL DEFAULT TRUE
);
```

#### workspaces
```sql
CREATE TABLE workspaces (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    slug TEXT UNIQUE NOT NULL,
    primary_language TEXT NOT NULL DEFAULT 'en' CHECK (primary_language IN ('en', 'ko', 'es')),
    timezone TEXT NOT NULL DEFAULT 'UTC',
    owner_id UUID NOT NULL REFERENCES profiles(id),
    plan_id TEXT NOT NULL REFERENCES plans(id) DEFAULT 'free',
    stripe_customer_id TEXT,
    delete_requested_at TIMESTAMPTZ,
    delete_grace_until TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_workspaces_owner ON workspaces(owner_id);
CREATE INDEX idx_workspaces_delete_grace ON workspaces(delete_grace_until) WHERE delete_grace_until IS NOT NULL;
```

#### workspace_members
```sql
CREATE TYPE workspace_role AS ENUM ('owner', 'admin', 'member', 'viewer');

CREATE TABLE workspace_members (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    role workspace_role NOT NULL,
    invited_by UUID REFERENCES profiles(id),
    joined_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (workspace_id, user_id)
);

CREATE INDEX idx_workspace_members_user ON workspace_members(user_id);
```

#### workspace_invitations
```sql
CREATE TABLE workspace_invitations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    email TEXT NOT NULL,
    role workspace_role NOT NULL,
    token TEXT UNIQUE NOT NULL,
    invited_by UUID NOT NULL REFERENCES profiles(id),
    expires_at TIMESTAMPTZ NOT NULL,
    accepted_at TIMESTAMPTZ,
    accepted_by UUID REFERENCES profiles(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

#### subscriptions
```sql
CREATE TYPE subscription_status AS ENUM ('trial', 'active', 'past_due', 'canceled', 'paused');

CREATE TABLE subscriptions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    stripe_subscription_id TEXT UNIQUE,
    plan_id TEXT NOT NULL REFERENCES plans(id),
    status subscription_status NOT NULL DEFAULT 'trial',
    billing_cycle TEXT NOT NULL DEFAULT 'monthly' CHECK (billing_cycle IN ('monthly', 'annual')),
    current_period_start TIMESTAMPTZ,
    current_period_end TIMESTAMPTZ,
    cancel_at_period_end BOOLEAN NOT NULL DEFAULT FALSE,
    canceled_at TIMESTAMPTZ,
    trial_ends_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_subscriptions_workspace ON subscriptions(workspace_id);
CREATE INDEX idx_subscriptions_status ON subscriptions(status);
```

#### subscription_addons
```sql
CREATE TYPE addon_type AS ENUM ('extra_member', 'extra_site', 'extra_competitor');

CREATE TABLE subscription_addons (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    subscription_id UUID NOT NULL REFERENCES subscriptions(id) ON DELETE CASCADE,
    addon_type addon_type NOT NULL,
    quantity INT NOT NULL DEFAULT 1 CHECK (quantity > 0),
    unit_price_usd NUMERIC(10,2) NOT NULL,
    stripe_subscription_item_id TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

#### sites
```sql
CREATE TYPE site_type AS ENUM ('own', 'competitor');

CREATE TABLE sites (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    url TEXT NOT NULL,
    domain TEXT NOT NULL,  -- 정규화된 도메인 (cooldown 검사용)
    nickname TEXT,
    type site_type NOT NULL DEFAULT 'own',
    last_analyzed_at TIMESTAMPTZ,
    last_url_changed_at TIMESTAMPTZ,
    deleted_at TIMESTAMPTZ,
    delete_cooldown_until TIMESTAMPTZ,  -- 30일 cooldown
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_sites_workspace ON sites(workspace_id) WHERE deleted_at IS NULL;
CREATE INDEX idx_sites_domain_cooldown ON sites(workspace_id, domain) WHERE delete_cooldown_until IS NOT NULL;
```

#### site_change_history
```sql
CREATE TABLE site_change_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    site_id UUID NOT NULL REFERENCES sites(id),
    previous_url TEXT,
    new_url TEXT NOT NULL,
    changed_by UUID NOT NULL REFERENCES profiles(id),
    changed_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_site_change_workspace_time ON site_change_history(workspace_id, changed_at DESC);
```

#### monthly_usage
```sql
CREATE TABLE monthly_usage (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    year_month TEXT NOT NULL,  -- 'YYYY-MM'
    custom_analyses_used INT NOT NULL DEFAULT 0,
    sites_changed_count INT NOT NULL DEFAULT 0,
    qa_messages_count INT NOT NULL DEFAULT 0,
    UNIQUE (workspace_id, year_month)
);
```

#### analysis_results
```sql
CREATE TYPE analysis_trigger_type AS ENUM ('auto', 'manual');

CREATE TABLE analysis_results (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    site_id UUID NOT NULL REFERENCES sites(id) ON DELETE CASCADE,
    trigger_type analysis_trigger_type NOT NULL,
    triggered_by UUID REFERENCES profiles(id),  -- NULL for auto
    triggered_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMPTZ,
    duration_ms INT,
    categories TEXT[] NOT NULL,  -- ['technical', 'structured', 'content', 'authority', 'visibility']
    overall_score NUMERIC(5,2),
    category_scores JSONB,  -- {technical: 80.5, structured: 75.0, ...}
    raw_metrics JSONB,  -- 표준 스키마 (섹션 7-2)
    insights JSONB,  -- {language_code: "..."} 워크스페이스 primary_language 기준 저장
    improvements JSONB,  -- 우선순위별 개선 제안
    analysis_version TEXT NOT NULL,  -- 'v2.0', 'v2.1', ... 스키마 변경 시 증가
    status TEXT NOT NULL DEFAULT 'queued' CHECK (status IN ('queued', 'running', 'completed', 'failed')),
    error_message TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_analysis_results_site_time ON analysis_results(site_id, triggered_at DESC);
CREATE INDEX idx_analysis_results_workspace ON analysis_results(workspace_id);
```

#### reports (PDF)
```sql
CREATE TABLE reports (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    analysis_result_id UUID NOT NULL REFERENCES analysis_results(id) ON DELETE CASCADE,
    pdf_storage_path TEXT NOT NULL,
    csv_storage_path TEXT,
    language TEXT NOT NULL,
    generated_by UUID REFERENCES profiles(id),
    generated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    bytes INT
);
```

#### wiki_articles
```sql
CREATE TYPE wiki_visibility AS ENUM ('public', 'members');

CREATE TABLE wiki_articles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    slug TEXT UNIQUE NOT NULL,
    category TEXT NOT NULL,
    tags TEXT[] NOT NULL DEFAULT '{}',
    visibility wiki_visibility NOT NULL DEFAULT 'public',
    -- 다국어 콘텐츠 (i18n JSONB: {en: {...}, ko: {...}, es: {...}})
    titles JSONB NOT NULL,           -- {en: "Title", ko: "제목", es: "Título"}
    contents JSONB NOT NULL,         -- markdown source
    meta_titles JSONB NOT NULL,      -- SEO <title>
    meta_descriptions JSONB NOT NULL, -- SEO meta description
    og_image_url TEXT,
    author_id UUID NOT NULL REFERENCES profiles(id),
    published_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_wiki_visibility ON wiki_articles(visibility, published_at) WHERE published_at IS NOT NULL;
CREATE INDEX idx_wiki_category ON wiki_articles(category);
CREATE INDEX idx_wiki_tags ON wiki_articles USING GIN(tags);
```

#### wiki_embeddings (pgvector)
```sql
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE wiki_embeddings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    article_id UUID NOT NULL REFERENCES wiki_articles(id) ON DELETE CASCADE,
    chunk_index INT NOT NULL,
    chunk_lang TEXT NOT NULL CHECK (chunk_lang IN ('en', 'ko', 'es')),
    chunk_text TEXT NOT NULL,
    embedding vector(1024) NOT NULL,  -- Voyage voyage-3 차원
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_wiki_embeddings_vector ON wiki_embeddings 
    USING hnsw (embedding vector_cosine_ops);
CREATE INDEX idx_wiki_embeddings_article ON wiki_embeddings(article_id);
```

#### qa_sessions / qa_messages
```sql
CREATE TABLE qa_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    workspace_id UUID REFERENCES workspaces(id) ON DELETE SET NULL,
    title TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_message_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TYPE qa_role AS ENUM ('user', 'assistant');

CREATE TABLE qa_messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID NOT NULL REFERENCES qa_sessions(id) ON DELETE CASCADE,
    role qa_role NOT NULL,
    content TEXT NOT NULL,
    language TEXT NOT NULL,  -- 자동 감지된 언어
    referenced_article_ids UUID[],  -- assistant 메시지일 때 출처
    cache_hit BOOLEAN NOT NULL DEFAULT FALSE,
    tokens_used INT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

#### coupons
```sql
CREATE TYPE coupon_discount_type AS ENUM ('percent', 'fixed_amount');
CREATE TYPE coupon_applies_to AS ENUM ('first_payment', 'all_renewals', 'first_n_renewals');

CREATE TABLE coupons (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    code TEXT UNIQUE,  -- NULL for blind coupons
    is_blind BOOLEAN NOT NULL DEFAULT FALSE,
    target_plans TEXT[] NOT NULL,  -- ['basic', 'medium', ...] or ['all']
    discount_type coupon_discount_type NOT NULL,
    discount_value NUMERIC(10,2) NOT NULL,
    valid_from TIMESTAMPTZ NOT NULL,
    valid_until TIMESTAMPTZ NOT NULL,
    max_uses INT,  -- NULL = 무제한
    max_uses_per_user INT NOT NULL DEFAULT 1,
    applies_to coupon_applies_to NOT NULL DEFAULT 'first_payment',
    applies_for_n_renewals INT,  -- applies_to = 'first_n_renewals' 일 때
    -- 블라인드 쿠폰 전용
    segment_query TEXT,  -- e.g., "trial_only AND last_login < NOW() - INTERVAL '90 days'"
    delivery_channel TEXT,  -- 'email' | 'in_app' | 'both'
    unique_per_user BOOLEAN NOT NULL DEFAULT FALSE,
    -- Stripe 동기화
    stripe_coupon_id TEXT,
    stripe_promotion_code_id TEXT,
    -- 메타
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_by UUID NOT NULL REFERENCES profiles(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_coupons_code ON coupons(code) WHERE is_active;
CREATE INDEX idx_coupons_blind ON coupons(is_blind, is_active) WHERE is_blind;
```

#### coupon_redemptions
```sql
CREATE TABLE coupon_redemptions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    coupon_id UUID NOT NULL REFERENCES coupons(id),
    user_id UUID NOT NULL REFERENCES profiles(id),
    workspace_id UUID REFERENCES workspaces(id),
    blind_token TEXT,  -- 블라인드 쿠폰 고유 토큰
    redeemed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    stripe_invoice_id TEXT,
    UNIQUE (coupon_id, user_id, blind_token)
);
```

#### audit_logs
```sql
CREATE TABLE audit_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    actor_user_id UUID REFERENCES profiles(id),
    workspace_id UUID REFERENCES workspaces(id),
    action TEXT NOT NULL,  -- e.g., 'workspace.delete_requested', 'ownership.force_transferred'
    resource_type TEXT,
    resource_id UUID,
    metadata JSONB,
    ip_address INET,
    user_agent TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_audit_workspace_time ON audit_logs(workspace_id, created_at DESC);
CREATE INDEX idx_audit_actor_time ON audit_logs(actor_user_id, created_at DESC);
```

#### deletion_grace_queue
```sql
CREATE TYPE grace_resource_type AS ENUM ('workspace', 'analysis_result', 'user');

CREATE TABLE deletion_grace_queue (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    resource_type grace_resource_type NOT NULL,
    resource_id UUID NOT NULL,
    delete_at TIMESTAMPTZ NOT NULL,
    requested_by UUID REFERENCES profiles(id),
    canceled_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (resource_type, resource_id)
);

CREATE INDEX idx_grace_delete_at ON deletion_grace_queue(delete_at) WHERE canceled_at IS NULL;
```

> 정확한 마이그레이션 순서, 인덱스 튜닝, RLS 정책 SQL은 DEV_SPEC.md 참조.

---

## 6. 권한 정책 (RLS)

### 6-1. 역할 정의

| 역할 | 위치 | 권한 |
|---|---|---|
| `super_admin` | 시스템 (Profile flag 또는 별도 테이블) | 모든 데이터 접근, Admin 패널 |
| `workspace_owner` | `workspace_members.role` | 결제, 소유권 이양, 삭제, 멤버 관리, 모든 데이터 |
| `workspace_admin` | `workspace_members.role` | 멤버 초대/제거, 사이트 관리, 분석 실행, 모든 데이터 (결제/이양/삭제 ❌) |
| `member` | `workspace_members.role` | 분석 실행, 리포트 조회, Q&A 사용 |
| `viewer` | `workspace_members.role` | 읽기 전용 |

### 6-2. RLS 정책 원칙

**기본 원칙**:
1. 모든 워크스페이스 데이터는 `workspace_id` 기준 RLS로 격리
2. `auth.uid()` → `workspace_members` 테이블 lookup → 권한 검증
3. `super_admin`은 service_role 키 사용 (RLS 우회). 백엔드 Admin API에서만.
4. RLS는 **Read 정책과 Write 정책을 분리** 정의

### 6-3. 핵심 정책 예시

**workspaces 테이블**:
```sql
-- SELECT: 워크스페이스 멤버만
CREATE POLICY workspaces_select ON workspaces FOR SELECT
  USING (id IN (
    SELECT workspace_id FROM workspace_members WHERE user_id = auth.uid()
  ));

-- UPDATE: owner/admin만
CREATE POLICY workspaces_update ON workspaces FOR UPDATE
  USING (id IN (
    SELECT workspace_id FROM workspace_members 
    WHERE user_id = auth.uid() AND role IN ('owner', 'admin')
  ));

-- DELETE: owner만 (단, 실제 삭제는 grace queue 통해 7일 후)
CREATE POLICY workspaces_delete ON workspaces FOR DELETE
  USING (id IN (
    SELECT workspace_id FROM workspace_members 
    WHERE user_id = auth.uid() AND role = 'owner'
  ));
```

**sites 테이블**:
```sql
CREATE POLICY sites_select ON sites FOR SELECT
  USING (workspace_id IN (
    SELECT workspace_id FROM workspace_members WHERE user_id = auth.uid()
  ));

-- 사이트 추가/수정/삭제는 owner/admin만
CREATE POLICY sites_modify ON sites FOR ALL
  USING (workspace_id IN (
    SELECT workspace_id FROM workspace_members 
    WHERE user_id = auth.uid() AND role IN ('owner', 'admin')
  ));
```

**analysis_results 테이블**:
```sql
-- 멤버 모두 읽기 가능
CREATE POLICY analysis_select ON analysis_results FOR SELECT
  USING (workspace_id IN (
    SELECT workspace_id FROM workspace_members WHERE user_id = auth.uid()
  ));

-- INSERT는 백엔드 service_role만 (BackgroundTasks에서 처리)
-- viewer는 분석 트리거 ❌ (REST API 레벨 검증)
```

**wiki_articles 테이블** (공개 콘텐츠):
```sql
-- 누구나 읽기 가능 (anon role 포함)
CREATE POLICY wiki_select_public ON wiki_articles FOR SELECT
  USING (visibility = 'public' AND published_at IS NOT NULL)
  TO anon, authenticated;

-- 멤버 전용 콘텐츠
CREATE POLICY wiki_select_members ON wiki_articles FOR SELECT
  USING (visibility = 'members' AND auth.uid() IS NOT NULL)
  TO authenticated;

-- 작성/수정은 super_admin만 (service_role 통해)
```

### 6-4. 오너십 이양

**일반 이양** (Owner 직접):
1. Owner가 다른 멤버에게 이양 요청
2. 대상 사용자가 수락 → `workspace_members.role` 업데이트 (트랜잭션)
3. 기존 owner는 admin으로 강등
4. audit_logs 기록

**강제 이양** (super_admin):
조건:
- Owner의 `last_login_at` > 30일 이전
- Subscription `past_due` 상태
- 워크스페이스 활성 멤버 ≥ 1명

절차:
1. super_admin이 Admin 패널에서 강제 이양 요청
2. 잔여 admin 중 가장 오래된 멤버 → owner 승격 (가중치: 회사 도메인 일치 시 우선)
3. 7일 이내 이의 제기 가능 (이메일 통보)
4. 모든 단계 audit_logs 기록

---

## 7. 분석 엔진

### 7-1. 5축 카테고리

| 카테고리 | 측정 영역 |
|---|---|
| **Technical** | SSL, robots.txt, sitemap, 페이지 속도, mobile-friendly, HTTP 응답 |
| **Structured** | JSON-LD, schema.org, OpenGraph, Twitter Card, hreflang, canonical |
| **Content** | 콘텐츠 길이, 가독성, 키워드 분포, 헤딩 구조, 이미지 alt, 인용 가능성 |
| **Authority** | 도메인 신뢰도, whois 정보, 백링크 추정, HTTPS 평가, E-E-A-T 신호 |
| **Visibility** | LLM 인용 가능성 (Claude API에 query → 답변에 사이트 등장 여부), 검색 결과 노출 추정 |

### 7-2. 표준 결과 스키마

분석 결과는 다음 스키마로 표준화:

```typescript
interface AnalysisResult {
  workspace_id: string;
  site_id: string;
  trigger_type: 'auto' | 'manual';
  triggered_by: string | null;
  triggered_at: string;
  completed_at: string;
  categories: ('technical' | 'structured' | 'content' | 'authority' | 'visibility')[];
  overall_score: number;  // 0-100, 가중평균
  category_scores: {
    technical?: number;
    structured?: number;
    content?: number;
    authority?: number;
    visibility?: number;
  };
  raw_metrics: {
    [category: string]: CategoryMetrics;
  };
  insights: {
    [language: 'en' | 'ko' | 'es']: string;  // workspace primary_language 기준 저장
  };
  improvements: Improvement[];
  analysis_version: string;
}

interface CategoryMetrics {
  score: number;  // 0-100
  metrics: MetricResult[];
}

interface MetricResult {
  key: string;  // 안정 식별자 (e.g., "ssl_enabled", "json_ld_present")
  display_name_key: string;  // i18n 사전 키
  description_key: string;
  value: boolean | number | string;
  weight: number;  // 0-1
  passed: boolean;
  threshold?: number;
  evidence?: string;  // 디버깅용
}

interface Improvement {
  priority: 'high' | 'medium' | 'low';
  category: string;
  title_key: string;  // i18n 사전 키 (정적 케이스)
  description: { [lang: string]: string };  // LLM 동적 생성 시 직접 저장
  estimated_impact: number;  // 1-10
  estimated_effort: 'low' | 'medium' | 'high';
  related_metric_keys: string[];
}
```

### 7-3. 카테고리별 재작성 (Q3 옵션 B)

기존 `backend/app/scoring/{technical,structured,content,authority,visibility}.py`는 **참고용으로 유지**하고, v2에서 표준 스키마 기반으로 재작성.

**재작성 원칙**:
1. 각 카테고리 모듈은 `analyze(url, options) -> CategoryMetrics` 시그니처를 따름
2. 메트릭 키는 안정 식별자 (변경 ❌, 새 키 추가만)
3. 가중치는 모듈 외부에서 설정 가능 (`scoring/weights.py`)
4. LLM 호출이 필요한 부분(insights, improvements)은 **카테고리 내부에서 ❌**, 모든 카테고리 분석 후 한 번에 통합 호출 (비용 효율)
5. 모든 메트릭은 evidence 필드로 raw 데이터 보존 (디버깅 + 재현)
6. 카테고리는 병렬 실행 가능해야 함 (asyncio)

### 7-4. LLM 통합 호출

```
모든 카테고리 분석 완료
  → CategoryMetrics × 5개를 시스템 프롬프트에 포함
  → Claude Sonnet 4.6에 단일 호출
  → 응답: insights (서술형) + improvements (구조화 배열)
  → workspace.primary_language 기준으로 출력
  → analysis_results.insights, .improvements에 저장
```

**번역 처리**:
- 기본 저장: 워크스페이스 primary_language
- 다른 언어 사용자가 조회 시: on-demand Claude Haiku 번역 + Redis 캐시 (24h)

### 7-5. Custom 재분석 처리

```
사용자 트리거 → categories: ['technical', 'content'] 등 부분 선택
  → 선택된 카테고리만 실행 (병렬)
  → LLM 호출도 선택된 카테고리만 포함
  → analysis_results 신규 row INSERT (categories 컬럼에 분석된 카테고리 명시)
  → 시계열 그래프에서 부분 분석은 연한 색 마커로 표시
```

---

## 8. Stripe 결제 시스템

### 8-1. 가입/구독 플로우

```
1. 사용자가 Pricing 페이지에서 플랜 선택 (월간/연간)
2. POST /api/billing/checkout-session
   - workspace_id, plan_id, billing_cycle 전달
   - 백엔드: Stripe Checkout Session 생성 (성공/취소 URL 포함)
   - Customer가 없으면 생성 (workspace.stripe_customer_id에 저장)
3. 사용자를 Stripe Checkout으로 리디렉션
4. 결제 완료 → Stripe가 success_url로 리디렉션 + Webhook 발사
5. Webhook 처리:
   - checkout.session.completed → subscriptions 테이블 활성화
   - workspace.plan_id 업데이트
   - 환영 이메일 발송 (Resend)
```

### 8-2. Webhook 시나리오

| 이벤트 | 처리 |
|---|---|
| `checkout.session.completed` | 신규 subscription INSERT, status='active' |
| `customer.subscription.updated` | plan/status 동기화 (업그레이드/다운그레이드) |
| `customer.subscription.deleted` | status='canceled', `cancel_at_period_end` 또는 `canceled_at` |
| `invoice.payment_succeeded` | `current_period_*` 업데이트, 영수증 이메일 |
| `invoice.payment_failed` | status='past_due', 결제 실패 이메일 (1일/3일/7일 리트라이) |
| `customer.subscription.trial_will_end` | (사용 시) 트라이얼 종료 알림 |

**보안**:
- Webhook 서명 검증 (`stripe.Webhook.construct_event`) 필수
- 이벤트 ID 기반 idempotency (재처리 방지)
- 처리 실패 시 5xx 반환 → Stripe 재시도

### 8-3. 업그레이드/다운그레이드

- **업그레이드**: 즉시 적용, proration (일할 계산) → Stripe `subscription.update(proration_behavior='create_prorations')`
- **다운그레이드**: 다음 결제일에 적용 (`proration_behavior='none'` + 다음 cycle부터 새 plan)

### 8-4. 해지

- 사용자가 Stripe Customer Portal에서 해지 → `cancel_at_period_end=true`
- 현재 결제 주기 끝까지 사용 가능 → 만료 시 자동 `canceled` 전환
- 해지 후 분석 결과는 1년 grace, 신규 분석 ❌

### 8-5. 추가 과금 (Add-on)

- 시트 추가: Stripe `subscription.items` 추가 (price_id_seat_addon, quantity)
- 사이트 추가: 별도 add-on price ID
- subscription_addons 테이블에 매핑 저장

### 8-6. 쿠폰 적용

- 사용자가 Checkout 단계에서 쿠폰 코드 입력 또는 자동 적용 (블라인드)
- 백엔드가 coupon DB 검증 → 유효하면 Stripe `discounts` 필드에 promotion_code_id 전달
- 결제 후 coupon_redemptions에 이력 INSERT

---

## 9. 스케줄링 시스템

### 9-1. pg_cron 작업

| 작업 | 스케줄 | 동작 |
|---|---|---|
| `monthly_analysis_trigger` | `0 0 1 * *` (매월 1일 00:00 UTC) | 모든 활성 사이트 분석 enqueue |
| `grace_period_processor` | `0 */6 * * *` (6시간마다) | deletion_grace_queue 만료 처리 |
| `usage_counter_reset` | `0 0 1 * *` (매월 1일) | monthly_usage 신규 row 생성 |
| `wiki_embedding_refresh` | `0 3 * * *` (매일 03:00 UTC) | 갱신된 wiki_articles 임베딩 재생성 |

### 9-2. pg_cron → Backend API 호출

pg_cron은 SQL을 실행하므로, 백엔드 API를 직접 호출할 수 없음. 따라서:

**옵션 (선택)**:
- pg_cron이 `pg_notify` 발사 → 백엔드 listener가 처리
- 또는 pg_cron이 `http` extension(Supabase 지원)으로 직접 백엔드 webhook 호출 ← **권장**

**보안**:
- 백엔드 cron 엔드포인트(`/internal/cron/*`)는 HMAC 서명 검증 (공유 비밀)
- IP 제한 (Supabase 출구 IP)

### 9-3. BackgroundTasks 큐

- FastAPI BackgroundTasks 사용 (1만 명 미만 단계)
- 워크스페이스당 동시 1개 작업 제한 (Redis lock)
- 작업 상태는 Redis에 기록 (key: `analysis:status:{result_id}`, TTL 1h)
- 실패 시 재시도 3회 (지수 백오프), 모두 실패 시 `analysis_results.status='failed'`

### 9-4. 1만 명 이상 시 마이그레이션

향후 Celery 또는 Inngest로 마이그레이션 (DEV_SPEC에서 다룸).

---

## 10. PDF / CSV 리포트 파이프라인

### 10-1. PDF 리포트 (모든 티어)

**생성 트리거**:
- 자동 분석 완료 시 자동 생성 → Supabase Storage 업로드 → 이메일 알림 (다운로드 링크 포함)
- Custom 재분석은 사용자가 "PDF 다운로드" 클릭 시 on-demand 생성

**구성 (8-12p)**:
| 페이지 | 내용 |
|---|---|
| 1. Cover | 사이트 URL, 분석일, 워크스페이스명, 로고 |
| 2. Executive Summary | 5개 카테고리 점수 + 전월 대비 변화 (▲▼) |
| 3. Radar Chart | 5축 시각화 |
| 4-8. Category Deep Dive | 카테고리당 1p — 점수, 메트릭 표, 의미 해석, 개선 제안 3개 |
| 9. Time Series | 월간 추이 라인 차트 (전체 분석 = 진한 색 / 부분 분석 = 연한 색) |
| 10. Action Items | 우선순위 TOP 5 (impact × effort 매트릭스) |
| 11-12. (Pro/Business) Competitor Comparison | 나란히 비교 + 갭 분석 (Business는 심층, 사이트당 3건) |
| 13. (Business 이상) Industry Benchmark | 산업 벤치마크 — 동종 업계 평균 대비 위치 |

**기술**:
- @react-pdf/renderer (Frontend) — Custom 재분석은 클라이언트에서 즉시 생성
- Backend Python측은 자동 분석에서 사용. 옵션:
  - Frontend Next.js API Route로 위임 (가장 단순)
  - 또는 백엔드에서 WeasyPrint 사용 (Python)
- **권장**: Frontend Next.js API route(`/api/reports/[id]/pdf`)에서 React-PDF 렌더링 → Supabase Storage 업로드

### 10-2. CSV Export (Pro 이상)

**구성**:
- `summary.csv`: 분석 결과 요약 (날짜, 카테고리별 점수)
- `metrics.csv`: 모든 메트릭 raw 데이터 (key, value, weight, passed)
- `improvements.csv`: 개선 제안 목록
- 인코딩: UTF-8 BOM (Excel 한글 호환)
- 압축: 단일 분석 → CSV / 시계열 export → ZIP

**다운로드 엔드포인트**: `GET /api/results/:id/csv` (티어 검증)

### 10-3. 저장 정책

- Supabase Storage 버킷: `reports/{workspace_id}/{result_id}.pdf` 등
- RLS: 워크스페이스 멤버만 download URL 생성 가능
- 다운로드는 short-lived signed URL (1시간) 사용

---

## 11. Custom 재분석 UX

### 11-1. UI 흐름

```
사이트 상세 페이지 (/[lang]/dashboard/sites/[site_id])
  └─ "Re-analyze" 버튼 클릭
       └─ Modal 열림: "어떤 카테고리를 분석할까요?"
            ├─ ☑ Technical
            ├─ ☑ Structured
            ├─ ☐ Content
            ├─ ☐ Authority
            ├─ ☐ Visibility
            └─ [Cancel]  [Analyze (2 categories)]
                   ↓
            Backend: 잔여 횟수 검증 → 큐잉
                   ↓
            Modal 닫히고 인라인 progress bar 표시
                   ↓
            완료 → toast "Analysis complete"
                   ↓
            대시보드 즉시 갱신 + [Download PDF] / (Pro+) [Download CSV] 버튼 표시
```

### 11-2. 검증 규칙 (Backend)

```python
# POST /api/workspaces/:id/sites/:site_id/analyze
# Body: { categories: ['technical', 'content'] }

1. 사용자 권한 확인 (member 이상, viewer ❌)
2. 워크스페이스의 plan에서 custom_analyses_per_month 한도 확인
3. monthly_usage 테이블에서 잔여 횟수 확인
4. 사이트의 last_analyzed_at + 1h cooldown 확인
5. 워크스페이스에 진행 중 분석 없음 (Redis lock)
6. categories 배열이 비어있지 않음 (최소 1개)
7. 모두 통과 → 큐잉, monthly_usage.custom_analyses_used += 1
```

### 11-3. 진행 상태 polling

```
Frontend: GET /api/analyses/:result_id/status (5초 간격)
Backend: Redis에서 상태 조회 → { status: 'queued' | 'running' | 'completed' | 'failed', progress: 0-100 }
완료 시: 분석 결과 자동 갱신 (TanStack Query invalidate)
```

### 11-4. 시계열 그래프 시각 구분

```
recharts <LineChart> 데이터:
  - 전체 분석 포인트: stroke="#0011BB", strokeWidth={3}
  - 부분 분석 포인트: stroke="#0011BB", strokeOpacity={0.4}, strokeDasharray="5 5"
  - Tooltip에 "Full analysis" / "Partial analysis (Technical, Content)" 표시
  - Legend에서 두 종류 구분
```

---

## 12. Wiki 시스템

### 12-1. URL 구조 (SEO 친화적)

```
/[lang]/wiki                       # 카테고리 인덱스
/[lang]/wiki/category/[category]   # 카테고리 페이지
/[lang]/wiki/[slug]                # 개별 글
```

**예시**:
- `/en/wiki/getting-started/setup-first-site`
- `/ko/wiki/getting-started/setup-first-site`
- `/es/wiki/getting-started/setup-first-site`

### 12-2. SEO 메타 관리

각 wiki_articles 레코드에 다국어 메타 필드:

```json
{
  "titles": {
    "en": "How to set up your first site",
    "ko": "첫 사이트 설정하기",
    "es": "Cómo configurar tu primer sitio"
  },
  "meta_titles": {
    "en": "Setup Your First Site | AEO Visibility Wiki",
    "ko": "첫 사이트 설정하기 | AEO Visibility 위키",
    "es": "Configura tu primer sitio | Wiki AEO Visibility"
  },
  "meta_descriptions": {
    "en": "Step-by-step guide to register and analyze...",
    "ko": "사이트를 등록하고 분석하는 단계별 가이드...",
    "es": "Guía paso a paso para registrar y analizar..."
  },
  "og_image_url": "https://..."
}
```

### 12-3. 검색엔진 색인

- `app/sitemap.ts`: 모든 published wiki_articles 자동 포함, hreflang 처리
- `robots.txt`: `/wiki/*` 허용
- 구조화 데이터: 각 글에 schema.org `Article` JSON-LD 자동 삽입
- `<link rel="alternate" hreflang="...">` 자동 생성

### 12-4. 콘텐츠 관리 (Admin)

`/admin/wiki` 라우트 (super_admin 전용):
- 글 목록 (카테고리/태그/언어 필터)
- Markdown 에디터 (3개 언어 탭)
- Slug, 카테고리, 태그, 공개 범위 설정
- SEO 메타 (제목/디스크립션/OG 이미지)
- 게시/비공개 토글
- 변경 이력 (audit_logs)

### 12-5. 임베딩 자동 생성

```
wiki_articles UPDATE/INSERT
  → trigger or BackgroundTask
  → 청크 분할 (1000자 단위, 200자 overlap)
  → 언어별 분리 (en/ko/es)
  → Voyage AI 호출 → vector(1024) 생성
  → wiki_embeddings 테이블 갱신 (이전 청크 DELETE 후 INSERT)
```

---

## 13. Q&A 시스템 (RAG)

### 13-1. 사용 권한
- **로그인 사용자만** (Free 트라이얼 포함)
- 비로그인 사용자는 Wiki만 열람 가능
- 한도: **rate limit만** (사용자당 시간당 30회) — 어뷰징 방지 목적

### 13-2. RAG 파이프라인

```
1. 사용자 질문 입력 → POST /api/qa/sessions/:id/messages
2. 언어 자동 감지 (langdetect 또는 Claude Haiku 호출)
3. 캐시 조회: Redis에서 유사 질문 검색
   - 임베딩 코사인 유사도 ≥ 0.95 → 캐시 hit, 즉시 반환
4. Cache miss:
   a. Voyage AI로 질문 임베딩 (voyage-3, 1024차원)
   b. wiki_embeddings에서 코사인 유사도 top 5 검색
      - 사용자 언어 chunks 우선, 부족하면 다른 언어 fallback
   c. Claude Haiku에 다음 형식으로 호출:
      ```
      System: You answer based ONLY on provided wiki excerpts. 
              If the answer is not in the excerpts, say so.
              Respond in {detected_language}.
              Cite source articles by ID at end.
      User: [excerpts]
            [question]
      ```
   d. 답변 + 참조 article_ids 추출
5. qa_messages 저장 + Redis 캐시 (TTL 7일)
```

### 13-3. 응답 형식

```json
{
  "session_id": "uuid",
  "message_id": "uuid",
  "role": "assistant",
  "content": "답변 텍스트...",
  "language": "ko",
  "referenced_articles": [
    { "id": "uuid", "slug": "setup-first-site", "title": "첫 사이트 설정하기" }
  ],
  "cache_hit": false,
  "tokens_used": 850
}
```

### 13-4. UI

**위치**: `/[lang]/qa` (전체 페이지) + 모든 페이지 우하단 floating widget

**기능**:
- 세션 목록 (좌측 사이드바)
- 메시지 스트림 (대화형)
- 답변에 출처 wiki 링크 카드 표시
- 사용자가 출처 카드 클릭 → 위키 글로 이동
- "이 답변이 도움이 되었나요?" 피드백 (👍👎) — 향후 품질 개선에 활용

### 13-5. 가드레일

- system prompt에서 "출처 wiki에 없는 내용 답변 ❌" 명시
- 답변 후처리: "I don't know" 패턴 감지 시 "Wiki에서 관련 내용을 찾지 못했습니다. support@... 로 문의해주세요." 메시지로 변환
- 비속어/PII 필터링 (입력 단계)

---

## 14. 쿠폰 시스템

### 14-1. 일반 쿠폰 (코드형)

**Admin 패널 입력 필드**:
- code (대문자, 영숫자, e.g., "BLACKFRIDAY30")
- target_plans (체크박스 다중 선택 또는 'all')
- discount_type (percent / fixed_amount)
- discount_value
- valid_from / valid_until
- max_uses (총)
- max_uses_per_user (보통 1)
- applies_to (first_payment / all_renewals / first_n_renewals)
- (옵션) applies_for_n_renewals

**적용 흐름**:
1. 사용자가 Pricing 페이지/Checkout에서 쿠폰 코드 입력
2. POST /api/billing/validate-coupon → 검증 결과 반환
3. Stripe Checkout Session 생성 시 `discounts: [{coupon: stripe_coupon_id}]` 포함
4. 결제 완료 → coupon_redemptions INSERT

### 14-2. 블라인드 쿠폰 (타겟 세그먼트)

**Admin 패널 흐름**:
1. "Blind Coupon" 신규 생성
2. 쿠폰 조건 입력 (할인율, 기간 등) — 일반 쿠폰과 동일
3. **세그먼트 정의** (조건 빌더 UI):
   ```
   조건 추가:
   ├─ 사용자 상태: [트라이얼만 / 무료 / 기존 유료 / 해지 사용자]
   ├─ 마지막 로그인: [N일 이전]
   ├─ 가입 후 경과: [N일 이상]
   ├─ 사용 이력: [분석 N회 미만 / 등]
   └─ 마케팅 동의 여부: [동의자만]
   ```
4. "Preview" 클릭 → 일치 사용자 수 + 샘플 10명 표시
5. "Send" → 사용자별 고유 토큰 생성 → 이메일/in-app 발송
6. 사용자가 토큰 URL 클릭 → `/redeem?token=abc123` → 자동 로그인 → Checkout에 쿠폰 자동 적용

**중요한 가드**:
- `marketing_consent = false`인 사용자에게는 **이메일 발송 ❌** (in_app만 가능)
- 트랜잭셔널 이메일에 블라인드 쿠폰 임베드 ❌

### 14-3. Stripe 동기화

```
DB coupon INSERT/UPDATE
  → Stripe Coupon API 호출 (생성)
  → Stripe PromotionCode API 호출 (코드 발급)
  → coupons.stripe_coupon_id, .stripe_promotion_code_id 저장
DB coupon DELETE 또는 is_active=false
  → Stripe Coupon delete or PromotionCode active=false
```

---

## 15. Admin 패널

### 15-1. 라우트 구조

```
/admin                       # 대시보드 (KPI 요약)
/admin/users                 # 회원 관리
/admin/workspaces            # 워크스페이스 관리
/admin/subscriptions         # 결제 현황
/admin/coupons               # 쿠폰 관리
/admin/wiki                  # Wiki 작성/관리
/admin/stats                 # 분석 통계
/admin/audit-logs            # 감사 로그
/admin/health                # 시스템 헬스
```

### 15-2. 접근 통제

- `super_admin` 플래그 (별도 테이블 또는 profiles.is_super_admin BOOLEAN)
- middleware.ts에서 `/admin/*` 라우트 가드
- 백엔드 Admin API는 super_admin JWT 검증 + service_role 키로 RLS 우회

### 15-3. 주요 기능

**대시보드 (/admin)**:
- MRR (Monthly Recurring Revenue) 그래프
- 활성 워크스페이스 수 (전월 대비)
- 신규 가입 / 해지율
- 분석 실행 통계 (전체, 자동/수동 비율)
- Q&A 사용량 (Claude API 비용 추정)

**회원 관리 (/admin/users)**:
- 검색 (이메일, 이름)
- 사용자 상세: 워크스페이스 목록, 결제 이력, 활동 로그
- 액션: 정지 (suspend) / 강제 로그아웃 / 데이터 삭제 (GDPR)

**워크스페이스 관리 (/admin/workspaces)**:
- 검색, 필터 (plan, 상태)
- 상세: 멤버, 사이트, 분석 이력, 결제
- 액션: **소유권 강제 이양**, 정지, 삭제 grace 취소

**Wiki 관리 (/admin/wiki)**:
- 글 목록, 신규 작성
- Markdown 에디터 (다국어 탭)
- 게시/비공개, SEO 메타 편집
- 임베딩 재생성 트리거 (수동)

**쿠폰 관리 (/admin/coupons)**:
- 일반 쿠폰 / 블라인드 쿠폰 생성
- 사용 현황 (redemption 수, 매출 영향)
- 비활성화

---

## 16. i18n 전략

### 16-1. 라이브러리: next-intl

선정 이유:
- App Router 친화적 (Server Components 지원)
- 타입 안전 (TypeScript 통합)
- 메시지 번들 분리 가능

### 16-2. 메시지 구조

```
messages/
  ├─ en.json
  ├─ ko.json
  └─ es.json
```

**구조**:
```json
{
  "common": {
    "buttons": { "save": "Save", "cancel": "Cancel" }
  },
  "dashboard": { ... },
  "wiki": { ... },
  "errors": { ... },
  "metrics": {
    "ssl_enabled": {
      "name": "SSL Enabled",
      "description": "Site uses HTTPS"
    }
  }
}
```

### 16-3. 라우팅

- `/[lang]/...` 패턴 (lang ∈ {ko, en, es})
- middleware.ts에서 Accept-Language 감지 → 기본 redirect
- 사용자 로그인 후 `profiles.preferred_language` 우선

### 16-4. 동적 콘텐츠 다국어

| 콘텐츠 종류 | 처리 |
|---|---|
| UI 정적 텍스트 | next-intl 메시지 번들 |
| 메트릭 이름/설명 (분석 결과) | i18n 키 (`metrics.ssl_enabled.name`) |
| LLM 인사이트/개선제안 | workspace.primary_language 기준 저장, 다른 언어 조회 시 on-demand 번역 + 캐시 |
| Wiki 콘텐츠 | wiki_articles JSONB 다국어 필드 |
| 이메일 템플릿 | Resend 템플릿 또는 Jinja2 템플릿 (언어별 분리) |

### 16-5. 통화 표기

- 결제 UI: USD 고정 (언어 무관)
- 로컬화 표기: `Intl.NumberFormat` 사용
  - en: `$19.99`
  - ko: `US$19.99` 또는 `$19.99 USD`
  - es: `US$ 19,99` (소수점 콤마)

---

## 17. 이메일 시스템

### 17-1. 발송 도메인 / 계정

```
도메인: [TBD - 사용자 확정 후 공유]
실제 메일박스 (3개):
  - no-reply@   (자동 발송)
  - hello@      (일반 문의, 답장 가능)
  - support@    (고객지원)
메일링 그룹 (hello로 포워딩):
  - legal@, privacy@, security@
```

**도메인 인증**:
- SPF / DKIM / DMARC 레코드 설정 필수
- Resend 도메인 검증 통과

### 17-2. 트랜잭셔널 이메일 (마케팅 동의 무관)

| 트리거 | 템플릿 | 발송 시점 |
|---|---|---|
| Magic Link 요청 | `auth_magic_link` | 즉시 |
| 회원가입 환영 | `welcome` | 가입 직후 |
| 자동 분석 완료 | `analysis_auto_complete` | 분석 완료 |
| 수동 분석 완료 (옵션) | `analysis_manual_complete` | 분석 완료 |
| 정기 리포트 | `monthly_report` | 매월 1일 분석 후 |
| 결제 영수증 | `invoice_paid` | invoice.payment_succeeded |
| 결제 실패 | `payment_failed` | invoice.payment_failed |
| 구독 만료 임박 (7일 전) | `subscription_expiring` | 만료 7일 전 |
| 워크스페이스 멤버 초대 | `workspace_invitation` | 초대 발송 시 |
| 워크스페이스 삭제 grace | `workspace_deletion_warning` | 7/3/1일 전 |
| 데이터 보관 만료 임박 | `data_expiring` | 30일 전 |
| 강제 소유권 이양 통지 | `ownership_force_transfer` | 강제 이양 시 |

### 17-3. 마케팅 이메일 (옵트인 사용자만)

| 트리거 | 템플릿 |
|---|---|
| 신기능 출시 | `feature_announcement` |
| 프로모션 (일반 쿠폰) | `promotion_general` |
| 블라인드 쿠폰 | `promotion_targeted` (사용자별 고유 토큰) |
| 뉴스레터 (월간) | `newsletter` |

### 17-4. 다국어 템플릿

- Resend 템플릿 ID를 언어별로 분리: `auth_magic_link_en`, `_ko`, `_es`
- 또는 Jinja2 템플릿 + Resend HTML 직접 발송
- 사용자 `profiles.preferred_language` 기준

### 17-5. 발송 우선순위

- 트랜잭셔널: Resend 즉시 발송 (rate limit 없음)
- 마케팅 (대량): 큐잉 + rate limit (분당 100건) — 도메인 평판 보호

---

## 18. 유저 저니

### 18-1. 신규 가입 → 트라이얼

```
랜딩 페이지 방문
  → Wiki / Pricing 탐색
  → "Start Free Trial" 클릭
  → /signup
    ├─ 이메일 입력
    ├─ 동의 (이용약관/개인정보/16세이상 [필수], 마케팅 [선택])
    └─ Magic Link 발송
  → 이메일 클릭 → 자동 로그인 → /onboarding
    ├─ 표시 이름 입력
    ├─ 워크스페이스 이름 입력 (자동 slug)
    ├─ 분석할 사이트 URL 입력
    └─ "Start Analysis"
  → 분석 진행 화면 (5초 polling)
  → 완료 → 결과 대시보드 + PDF 다운로드 가능
```

### 18-2. 트라이얼 → 유료 전환

```
대시보드에서 "Upgrade" 클릭
  → /pricing (월간/연간 토글)
  → 플랜 선택 → "Subscribe"
  → (옵션) 쿠폰 코드 입력
  → Stripe Checkout (카드 등록 + 결제)
  → 성공 → 워크스페이스 plan 활성화 + 환영 이메일
```

### 18-3. 정기 모니터링 (자동)

```
매월 1일 00:00 UTC
  → pg_cron 트리거 → 워크스페이스의 사이트 분석
  → 완료 → "Analysis complete" 이메일 (다운로드 링크)
  → 사용자 클릭 → 대시보드로 이동 → 결과 확인
```

### 18-4. Custom 재분석

```
대시보드 → 사이트 상세
  → "Re-analyze" → 카테고리 선택 모달
  → 분석 시작 → progress 표시
  → 완료 → 결과 갱신 + PDF/CSV 다운로드 버튼
```

### 18-5. 멤버 초대 (Pro 이상 — Basic은 1명 고정)

```
Workspace Settings → Members
  → "Invite member" → 이메일 + 역할 선택
  → 초대 이메일 발송 (토큰 URL 포함)
  → 수신자 클릭 → 로그인/가입 → 자동 가입 + workspace_members INSERT
```

### 18-6. 해지

```
Settings → Billing → "Cancel subscription"
  → Stripe Customer Portal 리디렉션
  → 해지 → cancel_at_period_end=true
  → 만료일까지 사용 가능
  → 만료 후 readonly + 1년 grace
```

### 18-7. 워크스페이스 삭제

```
Settings → Danger Zone → "Delete workspace"
  → 확인 모달 (이름 입력 + 비밀번호 재확인)
  → delete_grace_until = NOW() + 7 days
  → 7일간 사용 ❌, "Cancel deletion" 버튼만 활성
  → 7일 후 pg_cron이 영구 삭제 (CASCADE)
```

---

## 19. API 엔드포인트 (요약)

> 상세 스키마는 OpenAPI YAML로 별도 관리 (DEV_SPEC).

### 19-1. Auth (Supabase 직접)
- `POST /auth/v1/magiclink`

### 19-2. Workspace
```
GET    /api/workspaces
POST   /api/workspaces
GET    /api/workspaces/:id
PATCH  /api/workspaces/:id
POST   /api/workspaces/:id/delete-request
POST   /api/workspaces/:id/cancel-deletion
POST   /api/workspaces/:id/transfer-ownership
```

### 19-3. Members & Invitations
```
GET    /api/workspaces/:id/members
POST   /api/workspaces/:id/invitations
DELETE /api/workspaces/:id/members/:user_id
PATCH  /api/workspaces/:id/members/:user_id
POST   /api/invitations/:token/accept
```

### 19-4. Sites
```
GET    /api/workspaces/:id/sites
POST   /api/workspaces/:id/sites
PATCH  /api/workspaces/:id/sites/:site_id
DELETE /api/workspaces/:id/sites/:site_id
```

### 19-5. Analysis
```
POST   /api/workspaces/:id/sites/:site_id/analyze    # Custom 재분석
GET    /api/workspaces/:id/sites/:site_id/results
GET    /api/results/:result_id
GET    /api/results/:result_id/status                # polling
GET    /api/results/:result_id/pdf
GET    /api/results/:result_id/csv                   # Pro+
```

### 19-6. Reports
```
GET    /api/workspaces/:id/reports
```

### 19-7. Billing
```
POST   /api/billing/checkout-session
POST   /api/billing/portal-session
POST   /api/billing/validate-coupon
POST   /api/billing/webhook                          # Stripe webhook
```

### 19-8. Q&A
```
GET    /api/qa/sessions
POST   /api/qa/sessions
POST   /api/qa/sessions/:id/messages
GET    /api/qa/sessions/:id
DELETE /api/qa/sessions/:id
```

### 19-9. Wiki (공개 읽기)
```
GET    /api/wiki                                      # 목록 (필터)
GET    /api/wiki/:slug
```

### 19-10. Admin (super_admin 전용)
```
GET    /api/admin/stats
GET    /api/admin/users
GET    /api/admin/users/:id
POST   /api/admin/users/:id/suspend
GET    /api/admin/workspaces
POST   /api/admin/workspaces/:id/force-transfer
GET    /api/admin/subscriptions
GET    /api/admin/coupons
POST   /api/admin/coupons
PATCH  /api/admin/coupons/:id
GET    /api/admin/coupons/:id/preview-recipients     # 블라인드 미리보기
POST   /api/admin/coupons/:id/send                   # 블라인드 발송
GET    /api/admin/wiki
POST   /api/admin/wiki
PATCH  /api/admin/wiki/:id
DELETE /api/admin/wiki/:id
GET    /api/admin/audit-logs
```

### 19-11. Internal (Cron)
```
POST   /internal/cron/monthly-analysis        # HMAC 서명 검증
POST   /internal/cron/grace-processor
POST   /internal/cron/wiki-embedding-refresh
```

---

## 20. 비기능 요구사항

### 20-1. 성능

| 항목 | 목표 |
|---|---|
| 페이지 First Contentful Paint | < 1.5s (3G 기준) |
| 대시보드 데이터 로드 (TTI) | < 2.5s |
| 분석 실행 완료 시간 | 단일 사이트 < 60s, 5 카테고리 전체 |
| Q&A 응답 시간 | 캐시 hit < 500ms / 캐시 miss < 5s |
| API 99p latency | < 1s (분석/PDF 제외) |

### 20-2. 보안

- 모든 통신 HTTPS
- Supabase RLS로 워크스페이스 데이터 격리
- service_role 키는 백엔드만, 절대 frontend 노출 ❌
- Stripe Webhook 서명 검증
- pg_cron → backend 호출은 HMAC 서명
- Rate limit (Redis 기반):
  - Q&A: 사용자당 시간당 30회
  - API 일반: IP당 분당 60회
  - 분석 트리거: 워크스페이스당 동시 1개
- PII는 audit_logs 외에 로그에 남기지 않음
- 비밀번호 ❌ (Magic Link만 사용 → 비밀번호 유출 위험 0)

### 20-3. 확장성

- Backend stateless (BackgroundTasks 상태는 Redis)
- 1만 명 미만 단일 Railway 인스턴스로 충분
- 1만 명 이상: Celery + Redis Queue 도입 (DEV_SPEC에서 다룸)
- DB는 Supabase Pro로 수직 확장, 추후 read replica

### 20-4. 가용성

- Vercel + Railway 모두 99.9% SLA
- Supabase Pro 99.9% SLA
- 장애 대응: status 페이지 (선택), 이메일 알림
- 백업: Supabase 자동 daily backup (7일 보관, Pro 30일)

### 20-5. 접근성 / SEO

- WCAG 2.1 AA 목표 (Wiki, 마케팅 페이지 우선)
- Wiki: 시맨틱 HTML, alt 텍스트, 키보드 네비게이션
- SEO 메타: 모든 공개 페이지 `<title>`, `<meta description>`, OG, Twitter Card
- Sitemap, robots.txt, hreflang
- Wiki 글에 `Article` JSON-LD

### 20-6. 관측성 (Observability)

- 로그: 구조화 (JSON), 레벨 (debug/info/warn/error)
- 메트릭: Railway 내장 + 백엔드 `/api/health`
- 분석 실행 메트릭: duration_ms, status, error 추적 (DB)
- Stripe Webhook 처리 메트릭 (성공/실패율)
- (Phase 4) Sentry / Logflare 등 외부 통합 검토

### 20-7. 컴플라이언스

- 약관 4종 명시: 이용약관, 개인정보처리방침, Cookie Policy, Refund Policy
- GDPR: 데이터 다운로드 / 삭제 요청 처리 (Settings → Privacy)
- 마케팅 동의 분리, 옵트아웃 링크 모든 마케팅 메일에 포함
- 한국 개인정보보호법 준수
- DPA: enterprise sales 단계에서 추가

---

## 21. 단계별 개발 로드맵 (Phase 1~4) — 옵션 B (코어 우선)

### Phase 1: 코어 인프라 + 분석 엔진 (베타, 무료)

**기간**: ~6-8주
**목표**: 인증/워크스페이스/표준화된 분석 엔진의 안정적 동작. 결제 없음 (무료 베타).

**범위**:
1. Supabase Auth (Magic Link) 통합
2. 데이터 모델 마이그레이션 (profiles, workspaces, workspace_members, sites, analysis_results, monthly_usage, audit_logs)
3. RLS 정책 적용
4. 워크스페이스 CRUD + 멤버 초대 기본
5. 사이트 CRUD (변경 1회/월, 30일 cooldown 포함)
6. **분석 엔진 표준화 재작성** (Q3 옵션 B)
   - 표준 결과 스키마 정의
   - 5개 카테고리 모듈 재작성 (병렬 실행)
   - LLM 통합 호출 (insights, improvements)
7. 자동 월간 분석 스케줄러 (pg_cron)
8. Custom 재분석 (카테고리 선택)
9. 기본 대시보드 (시계열 그래프, 점수 표시)
10. 이메일 트랜잭셔널 (Magic Link, 분석 완료, 멤버 초대)

**산출물**: 무료 베타 출시 가능한 코어 시스템

### Phase 2: 결제 + 티어별 제한 + Admin 기본

**기간**: ~4-6주
**목표**: Stripe 통합으로 4-tier (Basic/Pro/Business) + Enterprise 일괄 출시.

**범위**:
1. Stripe Checkout, Customer Portal, Webhook
2. plans / subscriptions / subscription_addons 데이터 모델
3. 티어별 제한 강제 (사이트 수, 멤버 수, Custom 횟수)
4. 시트 추가 add-on ($2.99/u/월, 전 티어 동일)
5. 자사 사이트 추가 add-on ($9.99/site/월), 경쟁사 사이트 추가 add-on ($39.99/site/월, Pro 이상)
6. AI 엔진 추가 add-on ($19.99/engine/월, 전 티어 동일)
7. Custom 재분석 Pack add-on (Basic Pack $4.99 / Pro Pack $14.99 / PAYG $2.99)
8. 7-day free trial → 유료 전환 플로우 (카드 등록 시점은 첫 유료 결제)
9. 트라이얼 만료 후 7+30+90일 자동 이메일 시퀀스
10. 워크스페이스 삭제 grace period (7일)
11. 데이터 보관 grace (1년) — pg_cron 처리
12. Admin 패널 기본 (대시보드, 회원/워크스페이스 관리, 결제 현황)
13. 강제 소유권 이양
14. 결제 관련 이메일 (영수증, 실패, 만료)
15. Enterprise white-glove 온보딩 워크플로우 (수동 처리 가이드)

**산출물**: 유료 서비스 정식 출시 가능

### Phase 3: PDF 리포트 + 경쟁사 + i18n + CSV

**기간**: ~5-7주
**목표**: Pro/Business 가치 강화 + 다국어 지원.

**범위**:
1. PDF 리포트 파이프라인 (@react-pdf/renderer, 8-13p 구성, Business 이상은 Industry Benchmark 페이지 추가)
2. PDF 브랜딩 커스텀 add-on ($19.99 1회, Enterprise 무료)
3. CSV export (Pro+)
4. 경쟁사 사이트 관리 (Pro: 사이트당 1건 옵션 / Business: 사이트당 3건 옵션 / Enterprise: 5건)
5. 경쟁사 비교 분석 + 시각화 (Business는 심층 분석)
6. 경쟁사 추이 그래프 (Pro 12개월 / Business 24개월 / Enterprise 무제한)
7. 산업 벤치마크 (Business 이상)
8. **i18n 본격 도입** (next-intl, 한/영/스페인어)
9. 메시지 번들 작성 (UI 정적 텍스트)
10. 메트릭 이름/설명 i18n 키 매핑
11. LLM 출력 다국어 (workspace primary_language 저장 + on-demand 번역 캐시)
12. 이메일 템플릿 다국어 (트라이얼 7+30+90일 시퀀스 포함)
13. PDF 리포트 다국어
14. Looker Studio Connector add-on ($19.99/월, Pro 이상)

**산출물**: Business 가치 차별화 완성, 글로벌 시장 대응

### Phase 4: Wiki + Q&A + 쿠폰 + Admin 고도화

**기간**: ~5-7주
**목표**: self-serve / 마케팅 인프라 완성.

**범위**:
1. Wiki 데이터 모델 + Admin 작성/관리 UI
2. Wiki 공개 페이지 (다국어 라우트, SEO 메타, hreflang)
3. Sitemap, robots.txt, JSON-LD 자동 생성
4. pgvector + Voyage AI 임베딩 파이프라인
5. Q&A RAG 시스템 (Claude Haiku, Redis 캐시)
6. Q&A UI (전체 페이지 + floating widget)
7. 쿠폰 시스템 (일반 + 블라인드)
8. 블라인드 쿠폰 세그먼트 빌더 (Admin)
9. Stripe 쿠폰 동기화
10. Admin 통계 고도화 (MRR, retention, 분석 통계)
11. Audit logs UI

**산출물**: 완전한 self-serve SaaS

---

## 22. 미해결 / 별도 세션 항목

### 22-1. ✅ 시장조사 세션 완료 (2026-05-02 확정)
- ✅ 요금제 최종 가격: **Basic $19.99 / Pro $79.99 / Business $299.99 / Enterprise $1,499.99** (4-tier)
- ✅ 시트 추가 단가: **$2.99/멤버/월** (전 티어 동일)
- ✅ 사이트 추가 단가: **자사 $9.99 / 경쟁사 $39.99** (Pro 이상)
- ✅ AI 엔진 추가 단가: **$19.99/엔진/월** (전 티어 동일)
- ✅ 트라이얼 정책: **7-day free trial** + 만료 후 7+30+90일 자동 시퀀스
- ✅ Custom 재분석 횟수: Basic 5 / Pro 30 / Business 100 / Enterprise 무제한
- ✅ Custom Pack add-on: Basic Pack $4.99(+5) / Pro Pack $14.99(+20) / PAYG $2.99/회

> 출처: `research/compare-price-policy.md` Section 7 (v3.1 최종)

### 22-2. 사용자 작업 후 공유 예정
- 이메일 도메인 (확정 후 공유)
- Voyage AI API 키 (가입 후 공유)
- 로고 / 브랜딩 자산 (현재 텍스트만)
- Stripe 계정 (한국 법인)

### 22-3. 향후 결정 (Phase 2 이후)
- **SEO 지수 분석** (Ahrefs 견제) — Phase 2에서 검토. 현재는 AEO 전문성 집중
- PDF 리포트 디자인 시안 상세 (브랜딩 적용 후)
- DPA 도입 시점 (enterprise sales 진입 시) — Enterprise 티어에 무료 포함 예정
- 연령 정책 글로벌 16세 vs 한국 14세 (현재 글로벌 16세 권장)
- 1만 명 도달 후 인프라 마이그레이션 (Celery, multi-region)
- 추가 AI 엔진 카탈로그 확장 (Meta AI, DeepSeek, Mistral 등 신규 출시 시)
- Custom 분석 카테고리 (5개 외 사용자 정의 — Enterprise 한정 검토)
- 결제 다양화 (PayPal, 한국 카카오페이 등) — 초기엔 Stripe만
- 모바일 앱 (현재 반응형 웹만)

---

*최종 업데이트: 2026-05-02*
*다음 산출물: `docs/DEV_SPEC.md` (개발 환경/라이브러리/디렉토리 구조/마이그레이션)*
