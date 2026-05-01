# AEO Visibility 검증 툴 — 프로젝트 개요

> AI 검색 환경(ChatGPT, Claude, Google AI 등)에서 웹사이트가 얼마나 잘 노출되는지 진단하는 SaaS 도구

---

## 1. 요구사항

### 1-1. 비즈니스 요구사항
- 사용자가 자신의 웹사이트 URL을 입력하면, AI 답변 엔진(Answer Engine)에 얼마나 잘 노출되는지 자동 분석
- 분석 결과를 5가지 핵심 카테고리별 점수와 종합 등급(A~F)으로 제공
- 개선이 필요한 항목에 대한 구체적인 권장사항 제시
- 이메일 입력 시 상세 리포트를 메일로 발송 (리드 수집)
- 한국어/영어 다국어 지원

### 1-2. 기능 요구사항
- **URL 입력 → 분석 시작**: 사용자가 URL 입력 후 분석 요청
- **비동기 백그라운드 처리**: 분석은 시간이 걸리므로 백그라운드에서 처리
- **실시간 진행률 표시**: 5단계 분석 과정을 사용자에게 시각적으로 표시
- **결과 캐싱**: 동일 도메인 재분석 시 7일간 캐시된 결과 반환
- **이메일 리포트**: 분석 완료 후 이메일로 상세 리포트 발송
- **다국어 i18n**: 영어(en), 한국어(ko) 지원

### 1-3. 비기능 요구사항
- **성능**: 분석은 30초 이내 타임아웃
- **안정성**: 분석 실패 시 에러 상태 기록 및 사용자에게 안내
- **보안**: API 키 등 비밀 정보는 환경변수로 관리, GitHub에 노출 금지
- **확장성**: 단일 서비스로 시작하되, 향후 워커 분리 가능한 구조
- **비용 효율**: 무료/저비용 SaaS 조합으로 운영 가능

---

## 2. 구현된 기능

### 2-1. 분석 엔진 (5가지 카테고리)

| 카테고리 | 가중치 | 평가 항목 |
|---|---|---|
| **Technical** (기술 기반) | 20% | robots.txt, XML sitemap, SSL/HTTPS, canonical 태그, mobile viewport, page speed |
| **Structured** (구조화 데이터) | 20% | JSON-LD Schema.org, Open Graph, meta description, heading 계층, Twitter cards |
| **Content** (콘텐츠 품질) | 20% | content word count, Flesch-Kincaid 가독성, FAQ 섹션, content freshness |
| **Authority** (권위 신호) | 20% | 도메인 연식(WHOIS), 소셜 미디어 링크, 연락처 정보, 보안 헤더 |
| **Visibility** (AI 가시성) | 20% | Claude API로 5개 업계 질문 생성 → 도메인 멘션율 측정 |

### 2-2. 점수 산정 및 등급
- **종합 점수**: 5개 카테고리의 가중 평균 (0-100점)
- **등급**: A(85+), B(70-84), C(50-69), D(30-49), F(<30)
- **권장사항**: 점수가 낮은 항목 기반으로 우선순위(high/medium/low) 부여, 최대 10개 표시

### 2-3. API 엔드포인트
| 엔드포인트 | 메서드 | 용도 |
|---|---|---|
| `/api/analyze` | POST | 분석 시작 (BackgroundTasks로 비동기 처리) |
| `/api/result/{id}` | GET | 분석 진행률/결과 조회 |
| `/api/lead` | POST | 이메일 수집 + 리포트 발송 |
| `/api/health` | GET | DB/Redis 연결 상태 헬스체크 |

### 2-4. 프론트엔드 기능
- URL 입력 폼 + 분석 시작 버튼
- 5단계 진행률 시각화 (체크리스트 + 프로그레스 바)
- 카테고리별 점수 카드 + 종합 등급 배지
- 권장사항 리스트 (우선순위별 색상)
- 이메일 입력 폼 (분석 완료 후)
- 한국어/영어 라우팅 (`/ko`, `/en`)

### 2-5. 이메일 리포트
- Resend API 활용
- Jinja2 템플릿 기반 HTML 메일
- 도메인, 등급, 점수, 권장사항 포함
- CTA 버튼으로 전체 리포트 페이지 이동

### 2-6. 인프라 및 배포
- **GitHub Actions CI/CD**: lint → 빌드 검증 → DB 마이그레이션 자동화
- **Vercel**: 프론트엔드 자동 배포 (push 시)
- **Railway**: 백엔드 Docker 자동 배포 (push 시)
- **Alembic**: 데이터베이스 스키마 마이그레이션

---

## 3. 개발 스펙

### 3-1. 기술 스택

#### Backend
| 항목 | 사용 기술 | 버전 |
|---|---|---|
| 언어 | Python | 3.12 |
| 웹 프레임워크 | FastAPI | 0.115.6 |
| ASGI 서버 | Uvicorn | 0.34.0 |
| ORM | SQLAlchemy (async) | 2.0.36 |
| DB 드라이버 | asyncpg | 0.30.0 |
| 마이그레이션 | Alembic | 1.14.1 |
| 비동기 작업 | FastAPI BackgroundTasks | (내장) |
| HTTP 클라이언트 | httpx | 0.28.1 |
| HTML 파싱 | BeautifulSoup4, lxml | 4.12.3 / 5.3.0 |
| Redis 클라이언트 | redis-py | 5.2.1 |
| AI API | anthropic | 0.43.0 |
| 이메일 | resend | 2.5.1 |
| 템플릿 | Jinja2 | 3.1.5 |
| WHOIS 조회 | python-whois | 0.9.5 |
| 가독성 평가 | textstat | 0.7.4 |

#### Frontend
| 항목 | 사용 기술 | 버전 |
|---|---|---|
| 프레임워크 | Next.js (App Router) | 14.2 |
| 언어 | TypeScript | 5.0 |
| UI | React | 18.3 |
| 스타일 | Tailwind CSS | 3.4 |
| 빌드 설정 | next.config.mjs | (Next 14.2는 .ts 미지원) |

#### Infrastructure (SaaS)
| 서비스 | 역할 | 비용 |
|---|---|---|
| **Supabase** | PostgreSQL DB | 무료 플랜 |
| **Upstash** | Redis (캐싱 전용) | 무료 플랜 |
| **Railway** | 백엔드 호스팅 (Docker) | 사용량 기반 |
| **Vercel** | 프론트엔드 호스팅 | 무료 플랜 |
| **GitHub** | 소스코드 + Actions CI/CD | 무료 |
| **Resend** | 이메일 발송 | 월 3,000통 무료 |
| **Anthropic Claude** | AI 가시성 분석 | 종량제 |

### 3-2. 아키텍처

```
[사용자]
   │
   ▼
[Vercel / Next.js Frontend]  ←─── HTTPS
   │
   │ NEXT_PUBLIC_API_URL
   ▼
[Railway / FastAPI Backend]  ←─── Docker 컨테이너 (단일 서비스)
   │
   ├──→ [Supabase / PostgreSQL]   (analysis_results, leads)
   ├──→ [Upstash / Redis]         (도메인별 결과 캐시, 7일 TTL)
   ├──→ [Anthropic Claude API]    (AI 가시성 분석)
   └──→ [Resend API]              (이메일 발송)
```

> Celery + Worker 분리 구조에서 **FastAPI BackgroundTasks** 단일 프로세스로 단순화하여 비용/복잡도를 낮춤.

### 3-3. 데이터베이스 스키마

#### `analysis_results` 테이블
- `id` (UUID, PK)
- `url`, `domain`, `language`
- `status` (pending / processing / completed / failed)
- 5개 카테고리별 점수 + JSONB 상세
- `overall_score`, `grade`, `summary`
- `recommendations` (JSONB)
- `created_at`, `completed_at`, `expires_at`
- 인덱스: `domain`

#### `leads` 테이블
- `id` (UUID, PK)
- `analysis_id` (FK)
- `email`, `report_sent`, `created_at`
- 인덱스: `email`

### 3-4. 디렉토리 구조

```
aeo-visibility/
├── backend/
│   ├── app/
│   │   ├── main.py                    # FastAPI 앱 진입점
│   │   ├── config.py                  # 환경변수 관리 (pydantic-settings)
│   │   ├── models/                    # DB 모델, Pydantic 스키마
│   │   ├── routers/                   # API 엔드포인트
│   │   │   ├── analysis.py            # 분석 시작/조회 + BackgroundTasks
│   │   │   ├── leads.py               # 이메일 리드 수집
│   │   │   └── health.py              # 헬스체크
│   │   ├── services/                  # 분석 오케스트레이션, 크롤러, 캐시, 이메일
│   │   ├── scoring/                   # 5개 카테고리별 점수 산정 모듈
│   │   └── templates/                 # 이메일 HTML 템플릿
│   ├── alembic/                       # DB 마이그레이션
│   ├── Dockerfile
│   ├── Procfile
│   ├── railway.json                   # Railway 배포 설정
│   └── requirements.txt
│
├── frontend/
│   ├── src/
│   │   ├── app/[lang]/                # 다국어 라우팅
│   │   ├── components/analysis/       # 분석 관련 UI 컴포넌트
│   │   ├── components/layout/         # 헤더, 푸터
│   │   ├── hooks/useAnalysis.ts       # 분석 상태 폴링
│   │   ├── lib/i18n/                  # 다국어 사전
│   │   └── lib/api.ts                 # 백엔드 API 클라이언트
│   ├── next.config.mjs
│   ├── package.json
│   ├── tailwind.config.ts
│   └── vercel.json
│
├── supabase/
│   └── 001_initial_schema.sql         # Supabase 대시보드 직접 실행용 SQL
│
├── .github/
│   └── workflows/
│       └── deploy.yml                 # GitHub Actions CI/CD
│
├── docs/
│   └── PROJECT_OVERVIEW.md            # 본 문서
│
├── .env.template                      # 환경변수 템플릿 (플레이스홀더)
├── .gitignore
├── DEPLOY.md                          # 배포 가이드
└── README.md
```

### 3-5. 환경변수

| 변수명 | 용도 | 설정 위치 |
|---|---|---|
| `DATABASE_URL` | Supabase Session Pooler 연결 (`postgresql+asyncpg://...:5432/...`) | Railway, GitHub Secrets |
| `SUPABASE_URL` | Supabase 프로젝트 URL | Railway, GitHub Secrets |
| `SUPABASE_ANON_KEY` | Supabase anon 키 | Railway, GitHub Secrets |
| `SUPABASE_SERVICE_ROLE_KEY` | Supabase service role 키 | Railway, GitHub Secrets |
| `REDIS_URL` | Upstash Redis 연결 (`rediss://...`) | Railway, GitHub Secrets |
| `CLAUDE_API_KEY` | Anthropic Claude API 키 | Railway, GitHub Secrets |
| `RESEND_API_KEY` | Resend 이메일 API 키 (선택) | Railway |
| `FRONTEND_URL` | 프론트엔드 도메인 (CORS 및 이메일 CTA용) | Railway |
| `CORS_ORIGINS` | 허용 origin 목록 | Railway |
| `NEXT_PUBLIC_API_URL` | 프론트엔드에서 사용할 백엔드 URL | Vercel, GitHub Secrets |

### 3-6. 주요 의사결정 (Architecture Decisions)

1. **Celery 제거 → BackgroundTasks 채택**
   - 이유: Celery는 Redis 사용량을 폭증시키고 별도 워커 프로세스가 필요해 비용/복잡도 증가
   - 효과: Railway 서비스 1개로 운영, Upstash 무료 플랜으로 충분

2. **Supabase Session Pooler 사용**
   - 이유: Direct Connection(5432, IPv6)이 Railway 네트워크에서 도달 불가(`OSError 101`)
   - 사용: `aws-1-us-east-1.pooler.supabase.com:5432` (Session mode, IPv4)

3. **이메일 서비스로 Resend 채택**
   - 이유: 월 3,000통 무료, Python SDK 단순, 도메인 인증 간편
   - 대안: SendGrid(100통), Postmark(100통), Mailgun(3개월만 무료)

4. **Dockerfile CMD를 shell form으로 작성**
   - 이유: Railway가 `$PORT`를 주입하는데 JSON array CMD는 쉘 변수를 확장하지 않음
   - 작성: `CMD uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}`

5. **Health check에 timeout 적용**
   - 이유: DB/Redis 연결 시도가 hang하면 Railway healthcheck가 무한 실패
   - 작성: `asyncio.timeout(3)` / `asyncio.timeout(5)` 으로 단축 응답 보장

### 3-7. 배포 워크플로우

```
git push origin main
   │
   ├──→ GitHub Actions
   │     ├── Backend: pip install → py_compile → alembic upgrade head
   │     └── Frontend: npm ci → tsc --noEmit → next build
   │
   ├──→ Railway (자동 감지)
   │     └── Docker build → 컨테이너 재배포 → /api/health 헬스체크
   │
   └──→ Vercel (자동 감지)
         └── Next.js build → Edge 배포
```

---

## 라이브 서비스

- **Frontend**: https://aeo-visibility.vercel.app
- **Backend**: https://aeo-visibility-production.up.railway.app
- **Health Check**: https://aeo-visibility-production.up.railway.app/api/health

---

*최종 업데이트: 2026-04-14*
