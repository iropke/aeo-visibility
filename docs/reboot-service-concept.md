# AEO Visibility — v2 서비스 컨셉 (Reboot)

> 본 문서는 새 채팅 세션에서 v2 시스템 스펙 작성을 시작하기 위한 입력 자료입니다.
> 현재까지의 결정사항과 컨텍스트를 모두 정리했습니다.

---

## 0. 배경

현재 `D:\Claude\aeo-visibility`에 배포된 버전은 **목업/MVP 수준**입니다. 단일 분석을 제공하는 단방향 도구로 작동합니다.

이를 **구독형 SaaS**로 재설계하는 것이 v2의 목표입니다.

### 현재 라이브 서비스
- Frontend: https://aeo-visibility.vercel.app
- Backend: https://aeo-visibility-production.up.railway.app
- Health: https://aeo-visibility-production.up.railway.app/api/health

### 참고 문서
- 기존 시스템 개요: `D:\Claude\aeo-visibility\docs\PROJECT_OVERVIEW.md`
- 배포 가이드: `D:\Claude\aeo-visibility\DEPLOY.md`
- 원본 요구사항 (스펙 초안): `D:\Claude\aeo-visibility-spec\` (리포 외부)
  - `searchless_aeo_visibility_spec.md`
  - `searchless_dev_spec.md`

---

## 1. 요금제 플랜 (4 Tier)

| 티어 | 가격 | 사이트 수 | 모니터링 | 멤버 수 | 핵심 가치 |
|---|---|---|---|---|---|
| **Free** | $0 | 1회 트라이얼 | 단발성 | 1 | 회원가입 후 1회 분석 제공 |
| **Basic** | TBD | 1개 | 월 1회 자동 + 수동 재분석 | 1 | 정기 모니터링 |
| **Medium** | TBD | 3개 (추가 과금으로 증설 가능) | 월 1회 자동 + 수동 + 정기 레포트 | 다중 멤버 | 회사 운영 사이트 정기 모니터링 |
| **Premium** | TBD | 자사 1개 + 경쟁사 3개 (추가 과금 가능) | 월 1회 자동 + 수동 + 경쟁사 비교 | 다중 멤버 | 경쟁사 대비 현황 점검 |

**가격은 별도 결정 예정.** 모든 티어 USD 단일 통화.

---

## 2. 확정된 결정사항

| 항목 | 결정 |
|---|---|
| **인프라 전략** | 현재 스택 유지 (Vercel + Railway + Supabase + Upstash). AWS 전환하지 않음 |
| **결제 수단** | Stripe 단독 (PayPal 미사용) |
| **결제 통화** | USD 단일 |
| **한국 법인 Stripe** | 가능 (2024년부터 정식 지원). 가입 시점 최신 상태 확인 필요 |
| **인증 방식** | Supabase Auth + Magic Link |
| **팀/조직 계정** | Medium/Premium만 다중 멤버 워크스페이스 지원 (Basic은 1인) |
| **무료 트라이얼** | 회원가입(이메일 인증) 후 1회 분석 제공 |
| **Premium 경쟁사 분석** | 나란히 비교 + 월간 추이 그래프 |
| **모니터링 주기** | 월 1회 자동 + 사용자 요청 시 수동 재분석 |
| **PDF 리포트** | @react-pdf/renderer 사용, 프론트에서 다운로드/열람 |
| **지원 언어** | 한국어 / 영어 / 스페인어 |
| **Admin 패널** | 별도 앱 ❌. 같은 Next.js에 `/admin` 라우트 + RBAC |
| **스케줄링** | Supabase Cron (pg_cron) → 백엔드 API 호출 → BackgroundTasks 실행 |
| **이메일 발송** | Resend 유지 (트랜잭셔널 + Magic Link + 리포트 발송) |

---

## 3. 인프라 비용 추정 (1년차 기준)

가정: 월 1,000명 미만, 월 1회 자동 분석 + 수동 재분석.

| 항목 | 계산 근거 | 월 비용 |
|---|---|---|
| Claude API | 1,000명 × 1회/월 × ~$0.05 | ~$50 |
| Railway (Backend) | Hobby 플랜 | $5~10 |
| Vercel (Frontend) | Hobby 무료 (트래픽 한도 내) | $0 |
| Supabase | Free → Pro 필요시 | $0~25 |
| Upstash | 무료 (월 1회 분석 캐시 부하 미미) | $0 |
| Resend | 월 3,000통 무료 | $0 |
| Stripe | 거래 수수료만 (월 고정비 0) | 수수료 |
| **합계** | | **~$60~90/월** |

> AWS 동일 구성 시 최소 $200~400/월 + 운영 복잡도 10배.
> **1만 명 이상 성장 전엔 AWS 전환 불필요.**

### 단계별 인프라 전략

```
[지금 ~ 1년차]    현재 스택 + 필요시 Pro 티어 업그레이드
       ↓
[1년차 ~ 1만명]   현재 스택 유지, 모든 SaaS Pro 플랜
       ↓
[1만명 이상]      AWS/GCP 검토, multi-region 아키텍처
```

---

## 4. v2에서 신규 추가되어야 할 시스템 컴포넌트

### 4-1. 인증 시스템
- Supabase Auth (Magic Link)
- 한국어/영어/스페인어 이메일 템플릿
- 세션 관리, 로그아웃

### 4-2. 결제 시스템 (Stripe)
- Stripe Checkout (가입/업그레이드)
- Stripe Customer Portal (구독 관리/해지)
- Stripe Webhooks (구독 상태 동기화)
- Subscription 상태 관리 (active / past_due / canceled)
- 사이트/경쟁사 추가 시 추가 과금 (metered billing 또는 add-on)

### 4-3. 데이터 모델 (개념적 ERD)

```
users (Supabase Auth)
  └─ workspaces                        # 회사/조직 단위
       ├─ workspace_members            # 워크스페이스 ↔ 사용자 N:M
       ├─ subscriptions                # Stripe 연동
       │    └─ subscription_addons     # 사이트 추가 과금
       ├─ sites                        # 모니터링 대상 URL들
       │    ├─ analysis_results        # 기존 테이블 (FK 추가)
       │    └─ monitoring_schedule     # 자동 분석 일정
       ├─ competitors                  # Premium 전용
       │    └─ competitor_analyses
       └─ reports                      # PDF 생성 기록
audit_logs                             # 감사 로그
```

### 4-4. 권한 시스템 (RBAC)
- 역할: `owner` / `admin` / `member` / `viewer` (워크스페이스 내)
- 시스템 역할: `super_admin` (Admin 패널 접근)
- Supabase RLS(Row Level Security)로 데이터 격리

### 4-5. 스케줄링 시스템
- pg_cron으로 매월 정해진 일자에 트리거
- 트리거 → 백엔드 API 호출 → BackgroundTasks로 분석 실행
- 분석 완료 시 이메일 알림 + 리포트 생성

### 4-6. PDF 리포트 파이프라인
- 분석 완료 시 자동 생성 (Premium은 매월 정기)
- @react-pdf/renderer 사용
- 차트는 SVG → PDF 임베드 (recharts 등)
- Supabase Storage에 저장, 프론트에서 다운로드

### 4-7. Admin 패널
- `/admin` 라우트 + `super_admin` 역할로 접근
- 회원 관리 (조회/정지/삭제)
- 결제 현황 (Stripe 대시보드 보완)
- 분석 통계 (총 분석 수, 평균 점수 등)
- 시스템 헬스체크

### 4-8. 다국어 (i18n)
- 기존 `[lang]/` 라우팅 확장
- `en.json`, `ko.json`, `es.json` 사전 파일
- 결제 UI의 통화는 USD 고정 (언어와 분리)
- Magic Link 이메일도 언어별 템플릿

### 4-9. 이메일 알림 종류
- 회원가입 Magic Link
- 분석 완료 알림
- 정기 리포트 (PDF 첨부 또는 다운로드 링크)
- 구독 갱신 / 결제 실패 / 만료 안내
- 워크스페이스 멤버 초대

---

## 5. 분석 엔진 (기존 유지 + 일부 확장)

기존 5가지 카테고리 점수 산정 로직은 그대로 유지:
- Technical / Structured / Content / Authority / Visibility

신규 추가:
- **시계열 추적**: 월간 점수 변화 그래프
- **경쟁사 비교 분석** (Premium): 동일 5개 카테고리를 경쟁사에도 적용 후 나란히 표시

---

## 6. 마이그레이션 전략

현재 MVP 코드는 **참고용으로 유지**하고, v2는 사실상 새로 구현하는 방향.

### 옵션 A: 같은 리포 + 새 브랜치 (권장)
- `main` 브랜치는 현재 MVP 라이브 유지
- `v2` 브랜치에서 신규 구현
- 완성 후 `main`으로 머지하면서 라이브 교체

### 옵션 B: 새 리포
- 코드 분리는 깔끔하지만 배포 인프라 재설정 필요
- GitHub Actions, Vercel, Railway 모두 재연결

### 권장
**옵션 A**. 배포 인프라(Railway, Vercel, GitHub Secrets)가 이미 구축되어 있으므로 그대로 활용하는 것이 효율적.

---

## 7. 새 세션 시작 시 작성할 문서

다음 세션에서 만들어야 할 산출물:

1. **`docs/v2_SPEC.md`** — 종합 스펙 문서
   - 티어별 기능 매트릭스 (상세)
   - 데이터 모델 ERD
   - 시스템 아키텍처 다이어그램
   - 유저 저니 (가입 → 결제 → 모니터링 → 리포트)
   - 권한 정책 (RLS 룰셋)
   - Stripe 결제 플로우 + Webhook 시나리오
   - 스케줄링 시스템 설계
   - PDF 리포트 파이프라인
   - Admin 패널 스코프
   - i18n 전략
   - 이메일 알림 종류와 트리거
   - 단계별 개발 로드맵 (Phase 1~4)

2. **`docs/v2_DEV_SPEC.md`** — 개발 스펙
   - 사용 라이브러리 목록 + 버전
   - 디렉토리 구조 (변경분)
   - 환경변수 추가분
   - DB 마이그레이션 계획
   - 테스트 전략

---

## 8. 새 세션 시작 프롬프트 예시

> "D:\Claude\aeo-visibility 프로젝트의 v2 설계를 진행하려고 해.
> 먼저 다음 문서들을 읽어줘:
> - D:\Claude\aeo-visibility\docs\reboot-service-concept.md (이번 작업의 시작점)
> - D:\Claude\aeo-visibility\docs\PROJECT_OVERVIEW.md (현재 MVP 구조)
> - D:\Claude\aeo-visibility-spec\ 폴더의 스펙 문서 2개 (원본 요구사항)
>
> 읽은 후 reboot-service-concept.md에 정리된 결정사항을 바탕으로
> v2_SPEC.md와 v2_DEV_SPEC.md를 작성해줘.
> 작성 전에 추가로 확인하고 싶은 부분이 있으면 질문해줘."

---

## 9. 미결정 / 추후 결정 항목

다음 세션에서 결정이 필요한 항목들:

1. **각 티어별 정확한 가격** (Basic, Medium, Premium)
2. **사이트/경쟁사 추가 과금 단가**
3. **연간 결제 할인율** (보통 2개월 무료 = ~17% 할인)
4. **무료 트라이얼 만료 정책** (1회 사용 후 영구? 30일? 결제 안 하면 readonly?)
5. **워크스페이스 멤버 수 상한** (Medium / Premium 각각)
6. **PDF 리포트 디자인 시안** (브랜딩, 레이아웃)
7. **Admin 역할 부여 방법** (DB 직접 업데이트 vs 초대)
8. **이메일 발신 도메인** (도메인 인증 필요)
9. **로고 / 브랜딩** (현재 텍스트 로고만 있음)
10. **개인정보처리방침 / 이용약관** (Stripe 가입 시 필수)

---

## 10. 본 세션에서 수행한 작업 요약 (참고)

이 세션에서 다음 작업을 완료했습니다:

1. MVP 인프라 배포 (Supabase, Upstash, Railway, Vercel, GitHub)
2. CI/CD 구축 (GitHub Actions)
3. Celery → FastAPI BackgroundTasks 전환
4. 다음 이슈들 디버깅 완료:
   - resend 패키지 버전 오류
   - Dockerfile `$PORT` 확장 이슈
   - Railway 헬스체크 타임아웃
   - Next.js `next.config.ts` 호환성
   - Supabase Direct Connection IPv6 → Session Pooler 전환
   - 데이터베이스 SSL 설정
5. 보안 처리: `.env.template` 키 제거, `.claude/` gitignore 추가
6. 문서화: `PROJECT_OVERVIEW.md`, `DEPLOY.md` 작성
7. `tool_requirement/` 폴더를 리포 외부(`D:\Claude\aeo-visibility-spec\`)로 이동

---

*최종 업데이트: 2026-04-14*
*다음 세션에서 본 문서를 기반으로 v2 설계를 시작하세요.*
