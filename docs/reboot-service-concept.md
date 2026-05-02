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
- 배포 가이드: `D:\Claude\aeo-visibility\DEPLOY.md`
- 본 문서 (v2 설계 시작점): `D:\Claude\aeo-visibility\docs\reboot-service-concept.md`

> 이전 MVP 참고용으로 있던 `PROJECT_OVERVIEW.md` 및 외부 스펙 폴더(`D:\Claude\aeo-visibility-spec\`)는 v2 설계 혼선 방지를 위해 삭제됨.

---

## 1. 요금제 플랜 (4 Tier + Free Trial + Enterprise) — **최종 확정안 (2026-05-02)**

> **확정 출처**: `research/compare-price-policy.md` Section 7 (시장조사 결과 + 사용자 결정 v3.1)
> **결정 요약**: 5-tier 단순화 → 4-tier + Free trial + Enterprise. Pro는 시장 빈 구간($50~$129) 진입, Business는 AthenaHQ와 동가 정면 경쟁, Enterprise는 Ahrefs Enterprise와 동가 + 한국어/Dedicated CS 차별화

### 1-1. 티어별 가격표 (확정)

| 티어 | **확정 가격 (월)** | 연간 (월 환산, 15% 할인) | 사이트 | 멤버 (기본) | Custom 재분석/월 | 핵심 가치 |
|---|---|---|---|---|---|---|
| **Free** | $0 | — | 7-day free trial | 1 | 0 | 7일 동안 Pro 수준 기능 체험, 카드 등록 ❌ |
| **Basic** | **$19.99** | $16.99 ($203.88/년) | 자사 1 | 1 | 5 | 후킹 가격 (시장 최저가 진입선, 한정 37% 할인 마케팅 가능) |
| **Pro** | **$79.99** | $67.99 ($815.88/년) | 자사 3 + 경쟁사 1건/사이트 옵션 | 3 | 30 | HubSpot AEO($50)와 Profound Starter($99) 사이 시장 빈 구간 진입 |
| **Business** | **$299.99** | $254.99 ($3,059.88/년) | 자사 5 + 경쟁사 3건/사이트 옵션 + 산업 벤치마크 | 5 | 100 | AthenaHQ Self-Serve($295)와 동가 정면 경쟁 + 한국어 차별화 |
| **Enterprise** | **$1,499.99** | $1,274.99 (annual commit 필수) | 무제한 + 자사+경쟁사 5 | 20 | 무제한 | Ahrefs Enterprise($1,499)와 동가 + 한국어/다국어/Dedicated CS 차별화 |

### 1-2. 가격 ladder 검증

| 단계 | Ratio | 평가 |
|---|---|---|
| Basic → Pro | 4.0x | ✅ 정상 |
| Pro → Business | 3.75x | ✅ 정상 |
| Business → Enterprise | 5.0x | ✅ 정상 (Enterprise 통상 5~10x) |
| **평균** | **4.22x** | ✅ 75배 격차의 3제곱근 = 4.22x — **이론적 균형값과 일치** |

### 1-3. 추가 과금 (확정)

| 항목 | 가격 | 적용 티어 | 비고 |
|---|---|---|---|
| **시트 추가 (멤버)** | **$2.99/멤버/월** | 전 유료 티어 동일 | 시장 최저가 (Scrunch $25 대비 88% 저렴) — **허들 낮춤** |
| **자사 사이트 추가** | **$9.99/사이트/월** | 전 유료 티어 동일 | Ahrefs Lite 1 site = $25.8 대비 61% 저렴 |
| **경쟁사 사이트 추가** | **$39.99/사이트/월** | Pro 이상 | 자사 대비 4배 (분석 부하 + Business 업셀 유도) |
| **AI 엔진 추가** | **$19.99/엔진/월** | 전 유료 티어 동일 | 시장 최저가 절대 단가, Pro 이상 per-prompt 단가 시장 최우위 |
| **Custom 재분석 Basic Pack** | $4.99/월 (+5회) | Basic, Pro | Ahrefs Custom Prompts $50 대비 90% 저렴 |
| **Custom 재분석 Pro Pack** | $14.99/월 (+20회) | Pro, Business | Ahrefs Growth $100 대비 85% 저렴 |
| **Custom 재분석 PAYG (단건)** | $2.99/회 | 전 유료 티어 | 한도 소진 후 옵트인 자동 청구 |
| **PDF 리포트 브랜딩 커스텀** | $19.99 (1회) | 전 유료 티어 (Enterprise 무료) | 로고+색상+회사명 적용, 영구 |
| **Looker Studio Connector** | $19.99/월 | Pro 이상 (Enterprise 포함) | — |
| **API 액세스 단독** | $99/월 | Pro 이상 (Enterprise 포함) | — |
| **추가 워크스페이스** | $99/월/워크스페이스 | Pro 이상 | — |
| **외부 컨설턴트 (Viewer 시트)** | $1.99/멤버/월 | Pro 이상 | — |
| **데이터 보관 연장 (5년 → 7년)** | $49/월 | Business 이상 | — |
| **GDPR DPA / HIPAA / SOC2 docs** | 무료 | Enterprise만 | — |

> 모든 가격 USD 단일 통화. 한국 사용자도 USD 결제.

### 1-4. 기본 AI 엔진 (전 티어 공통, 추가는 add-on)

- **기본 포함 (3개)**: Google AI Overviews, Claude, ChatGPT
- **추가 가능**: Perplexity, Gemini, Copilot, Grok, AI Mode 등 (각 $19.99/월)
- **Enterprise**: 모든 엔진 자동 포함 (10+)

### 1-5. 모니터링 / Custom 재분석 정책

| 구분 | 정책 |
|---|---|
| **자동 모니터링 빈도** | 모든 유료 티어 **월 1회** (AEO 변화 속도 고려, daily 의미 미미) |
| **Custom 재분석** | 사용자 트리거 — 5개 카테고리 중 일부 선택 가능, 즉시 큐잉, 결과는 대시보드 + PDF/CSV |
| **Custom 한도 차등** | Basic 5회 / Pro 30회 / Business 100회 / Enterprise 무제한 |
| **한도 초과 시** | Basic/Pro Pack 또는 PAYG로 추가 가능 (사용자 옵트인) |

### 1-6. 트라이얼 / 결제 / 할인 정책 (확정)

| 항목 | 정책 |
|---|---|
| **트라이얼 형식** | **7-day free trial** (시간 기반) — Pro 수준 기능 사용 가능 |
| **카드 등록** | 트라이얼 시 ❌, 첫 유료 결제 시점 |
| **트라이얼 만료 후 시퀀스** | Day 7 (1차, 첫 달 30% off, 3일 한정) → Day 30 (2차, 첫 달 50% off) → Day 90 (3차, 첫 3개월 50% off + 1:1 데모) → 종료 |
| **연간 할인** | 모든 티어 15% (시즌별 적극적 할인은 쿠폰 시스템 운용) |
| **연간 약정 (Enterprise)** | 필수 (annual commit) — 중도 해지 시 잔여 12개월 정산 |
| **결제 통화** | USD 단일 |
| **결제 수단** | Stripe (Visa, MC, Amex, UnionPay) + Enterprise wire transfer |
| **환불 정책** | 월간: 7일 이내 미사용 시 가능 / 연간: 30일 이내 환불, 이후 prorated / Enterprise: 계약별 |

### 1-7. 온보딩 / 지원 정책

| 티어 | 온보딩 | 지원 채널 | SLA |
|---|---|---|---|
| Basic | 셀프 (인간 개입 ❌) | Email | — |
| Pro | 셀프 | Email + Chat | — |
| Business | 셀프 | Email + Chat | 4시간 |
| Enterprise | **White-glove** (2회 콜) | Dedicated Slack + Email + Chat + Account Manager | 2시간 |

> **운영 의도**: Self-serve 티어는 인간 개입 최소화로 CS 비용 절감. **Enterprise만 dedicated** — churn 방지에 집중.

### 1-8. 추후 확장 (Phase 2)

| 항목 | 비고 |
|---|---|
| **SEO 지수 분석** | Phase 2에서 검토. 현재는 AEO 전문성 집중 — Ahrefs와 정면 경쟁 회피 |
| **추가 AI 엔진 카탈로그 확장** | Meta AI, DeepSeek, Mistral 등 신규 엔진 출시 시 점진 추가 |
| **Custom 분석 카테고리** | 5개 카테고리 외 사용자 정의 카테고리 (Enterprise 한정 검토) |

---

## 2. 확정된 결정사항

| 항목 | 결정 |
|---|---|
| **인프라 전략** | 현재 스택 유지 (Vercel + Railway + Supabase + Upstash). AWS 전환 ❌ |
| **결제 수단** | Stripe 단독 (PayPal 미사용) |
| **결제 통화** | USD 단일 |
| **연간 결제 할인** | 고정 할인율 ❌ → **Admin 쿠폰 시스템**으로 운영 (섹션 12) |
| **트라이얼 카드 등록** | 가입 시 ❌. **첫 유료 결제 시점**에 카드 등록 |
| **인증 방식** | Supabase Auth + Magic Link |
| **팀/조직 계정** | Pro/Business 다중 멤버 워크스페이스 (Basic 1인, Pro 3, Business 5, Enterprise 20) |
| **Pro/Business 경쟁사 분석** | 나란히 비교 + 월간 추이 그래프 (Business는 심층, 사이트당 3건) |
| **모니터링 주기** | 월 1회 자동 + Custom 재분석 (사용자 트리거) |
| **Custom 재분석** | 사용자가 5개 카테고리 중 선택, 결과는 대시보드 + 다운로드 (섹션 5) |
| **PDF 리포트** | @react-pdf/renderer, 시각화 중심 (섹션 4-6) |
| **데이터 다운로드** | PDF: 전 티어 / CSV: Pro 이상 |
| **시계열 시각화** | 전체 분석 = 진한 색 / 부분 분석 = 연한 색 (시각 구분) |
| **지원 언어** | 한국어 / 영어 / 스페인어 |
| **Q&A 답변 언어** | 사용자 언어 자동 감지 |
| **Admin 패널** | 같은 Next.js에 `/admin` 라우트 + RBAC (별도 앱 ❌) |
| **권한 모델** | super_admin / workspace_owner / workspace_admin / member / viewer (섹션 13) |
| **스케줄링** | Supabase pg_cron → 백엔드 API → BackgroundTasks |
| **이메일 발송** | Resend, 도메인 1개 + alias 3개 (no-reply, hello, support) |
| **사이트 변경 제한** | 월 1회 (단, 첫 분석 전 변경은 허용) |
| **사이트 삭제 cooldown** | 삭제 후 30일간 동일 도메인 재등록 ❌ |
| **워크스페이스 삭제** | 7일 grace period (취소 가능) → 영구 삭제 |
| **데이터 보관** | 활성 워크스페이스: 영구 / 만료·삭제 후 1년 grace → 영구 삭제 / GDPR 즉시 삭제 요청 대응 |
| **마케팅 동의** | 가입 시 별도 옵트인 (필수 ❌). 동의 미체크 사용자에게 블라인드 쿠폰 발송 ❌ |
| **약관 종류** | 이용약관 / 개인정보처리방침 / Cookie Policy / Refund Policy (DPA는 enterprise 단계로 보류) |
| **Wiki + Q&A** | 추가 기능 (섹션 4-10, 4-11) |
| **임베딩 벤더** | Voyage AI `voyage-3` (Anthropic 공식 권장) |

---

## 3. 인프라 비용 추정 (1년차 기준)

가정: 월 1,000명 미만, 월 1회 자동 분석 + Custom 재분석 + Q&A 사용.

| 항목 | 계산 근거 | 월 비용 |
|---|---|---|
| Claude API (분석) | 1,000명 × ~$0.10 (자동+Custom 평균) | ~$100 |
| Claude API (Q&A, Haiku) | 사용자당 월 5회 × $0.01 | ~$50 |
| Voyage AI (임베딩) | Wiki 인덱싱 1회 + 쿼리당 미미 | ~$5 |
| Railway (Backend) | Hobby → Pro | $5~25 |
| Vercel (Frontend) | Hobby 무료 → Pro 필요 시 | $0~25 |
| Supabase | Free → Pro (pgvector 포함) | $0~25 |
| Upstash | 무료 | $0 |
| Resend | 월 3,000통 무료 → Pro 필요 시 | $0~20 |
| Stripe | 거래 수수료만 | 수수료 |
| **합계** | | **~$160~250/월** |

> AWS 동일 구성 시 최소 $300~500/월 + 운영 복잡도 10배.
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
- 한/영/스페인어 이메일 템플릿
- 세션 관리, 로그아웃

### 4-2. 결제 시스템 (Stripe)
- Stripe Checkout (가입/업그레이드)
- Stripe Customer Portal (구독 관리/해지)
- Stripe Webhooks (구독 상태 동기화)
- 구독 상태: active / past_due / canceled / paused
- 사이트/시트 추가 시 add-on (fixed quantity)
- 카드 등록은 첫 유료 결제 시점

### 4-3. 데이터 모델 (개념적 ERD)

```
users (Supabase Auth)
  └─ workspaces                        # 회사/조직 단위
       ├─ workspace_members            # 워크스페이스 ↔ 사용자 N:M (역할 포함)
       ├─ workspace_invitations        # 초대 토큰
       ├─ subscriptions                # Stripe 연동
       │    └─ subscription_addons     # 시트/사이트 추가 과금
       ├─ sites                        # 모니터링 대상 URL
       │    ├─ analysis_results        # trigger_type, categories[], triggered_by
       │    ├─ site_change_history     # 변경 1회/월 enforcement
       │    └─ monitoring_schedule     # 자동 분석 일정
       ├─ competitors                  # Pro/Business (Enterprise는 무제한)
       │    └─ competitor_analyses
       ├─ reports                      # PDF 생성 기록
       └─ monthly_usage                # workspace × year-month: 횟수 카운터

wiki_articles                          # Wiki 문서 (다국어, 카테고리, 태그)
  └─ wiki_embeddings                   # pgvector
qa_sessions                            # Q&A 대화 이력
coupons                                # 쿠폰 마스터 (일반/블라인드)
  └─ coupon_redemptions                # 사용 이력
audit_logs                             # 감사 로그
marketing_consents                     # 사용자별 마케팅 동의 상태
deletion_grace_queue                   # 워크스페이스 7일 grace, 데이터 1년 grace
```

### 4-4. 권한 시스템 (RBAC)
섹션 13 참고. Supabase RLS 기반 워크스페이스 격리.

### 4-5. 스케줄링 시스템
- pg_cron → 매월 1일 자동 트리거
- 트리거 → 백엔드 API → BackgroundTasks → Claude API
- 분석 완료 시: 이메일 알림 + PDF 자동 생성 (자동 분석)
- Custom 재분석은 사용자 트리거 → 즉시 큐잉
- 삭제 grace 주기 작업도 pg_cron으로 처리

### 4-6. PDF 리포트 파이프라인
- 자동 분석 완료 시 자동 생성, Custom 재분석은 사용자 다운로드 요청 시 생성
- @react-pdf/renderer 사용
- 차트는 SVG → PDF 임베드 (recharts 등)
- Supabase Storage 저장, 프론트에서 다운로드

**페이지 구성 (8-12p)**:
1. Executive Summary — 5개 카테고리 점수 + 전월 대비 (▲▼)
2. Radar Chart — 5축 시각화
3. Category Deep Dive (5p, 카테고리당 1p) — 점수, 메트릭, 의미 해석, 개선 제안 3개
4. Time Series — 월간 추이 라인 차트 (전체/부분 분석 시각 구분)
5. Action Items — 우선순위 TOP 5 (impact × effort)
6. (Pro/Business) Competitor Comparison — 나란히 비교 + 갭 분석 (Business 이상은 산업 벤치마크 페이지 추가)

### 4-7. CSV 다운로드 (Pro 이상)
- 분석 결과 raw data export
- 시계열 데이터, 카테고리별 메트릭, 경쟁사 데이터
- UTF-8 BOM 포함 (Excel 한글 호환)

### 4-8. Admin 패널
- `/admin` 라우트 + `super_admin` 역할로 접근
- 회원 관리 (조회/정지/삭제)
- 워크스페이스 관리 (조회/소유권 강제 이양)
- 결제 현황 (Stripe 대시보드 보완)
- **쿠폰 관리** (섹션 12)
- **Wiki 관리** (작성/편집/번역)
- 분석 통계 (총 분석 수, 평균 점수, MRR 등)
- 시스템 헬스체크
- 감사 로그 조회

### 4-9. 다국어 (i18n)
- 기존 `[lang]/` 라우팅 확장
- `en.json`, `ko.json`, `es.json` 사전 파일
- 결제 UI의 통화는 USD 고정 (언어와 분리)
- Magic Link / 알림 / 마케팅 이메일 모두 언어별 템플릿

### 4-10. Wiki 시스템
- Admin 패널에서 작성/관리 (Markdown editor)
- 카테고리, 태그, 검색
- 다국어 (한/영/스페인어)
- 공개/비공개 (멤버 전용 vs 누구나)
- 변경 이력 (audit_logs)

### 4-11. Q&A 시스템 (RAG)

**아키텍처**:
```
질문 입력 → Voyage AI 임베딩 → pgvector 유사도 검색 (top 3-5)
       → Claude (Haiku 4.5)에 청크 + 질문 전달
       → 답변 + 출처 wiki 링크 표기
```

**가드**:
- 답변 캐싱 (유사 질문 ≥0.95 → 캐시)
- Rate limit (사용자당 시간당 10회)
- system prompt: "출처 wiki에 없는 내용은 답하지 않음"
- 사용자 언어 자동 감지하여 답변 (Wiki 원본 언어와 무관)

### 4-12. 쿠폰 시스템
섹션 12 참고.

### 4-13. 이메일 알림 종류

**트랜잭셔널** (모든 사용자, 마케팅 동의 무관):
- 회원가입 Magic Link
- 분석 완료 알림 (자동)
- 정기 리포트 (PDF 첨부 또는 다운로드 링크)
- 구독 갱신 / 결제 실패 / 만료 안내
- 워크스페이스 멤버 초대
- 데이터 삭제 grace 알림 (7일/3일/1일 전)

**마케팅** (옵트인 사용자만):
- 신기능 안내
- 프로모션 / 쿠폰
- 블라인드 쿠폰
- 뉴스레터

---

## 5. 분석 엔진

### 5-1. 자동 분석 (월간)
- 5개 카테고리 전체 (Technical / Structured / Content / Authority / Visibility)
- 모든 사이트에 대해 매월 1일 실행
- 완료 시 이메일 알림 + PDF 자동 생성

### 5-2. Custom 재분석 (수동, 사용자 트리거)

**UX 흐름**:
```
사이트 상세 페이지
  └─ [Re-analyze] 버튼
       ├─ 클릭 → 카테고리 선택 모달 (체크박스 5개, 최소 1개)
       ├─ 잔여 횟수 ≥1 → 즉시 큐잉 (BackgroundTasks)
       │    └─ 진행률 표시 (polling 5초 간격)
       │    └─ 완료 → 대시보드 즉시 갱신
       │    └─ [Download PDF] / (Pro 이상) [Download CSV]
       └─ 잔여 0 → 버튼 비활성화 + "다음 가능: YYYY-MM-DD"
```

**구현 규칙**:
- 5개 카테고리 중 사용자가 체크박스로 선택 (최소 1개)
- 선택한 카테고리만 분석 → API 비용 절감
- 결과는 **대시보드 즉시 표시** + 사용자가 PDF/CSV 다운로드
- 시계열 그래프에서 **전체 분석 = 진한 색**, **부분 분석 = 연한 색**으로 시각 구분
- 워크스페이스 × 월 기준 횟수 한도 (티어별 잠정, 시장조사 세션에서 최종 확정)

**가드 규칙**:
- 워크스페이스당 동시 1개 분석만 (큐잉)
- 동일 사이트 마지막 분석 후 **1시간 내 재분석 ❌**
- analysis_results에 trigger_type (auto/manual), categories[] (분석된 카테고리 목록), triggered_by (user_id), triggered_at 저장
- Custom 분석 완료 시 트리거한 사용자에게만 알림 (자동 분석은 owner+admin 모두에게)

### 5-3. 신규 기능
- **시계열 추적**: 월간 점수 변화 그래프 (전체/부분 시각 구분)
- **경쟁사 비교** (Pro/Business): 동일 5개 카테고리 적용 후 나란히 표시 (Business는 심층 분석 + 산업 벤치마크)

---

## 6. 마이그레이션 전략

기존 결정 유지: **옵션 A** (같은 리포 + `v2` 브랜치).
- `main`: 현재 MVP 라이브 유지
- `v2`: 신규 구현 → 완성 후 `main` 머지

배포 인프라(Railway, Vercel, GitHub Secrets)가 이미 구축되어 있으므로 그대로 활용.

---

## 7. 새 세션 시작 시 작성할 문서

다음 세션에서 만들어야 할 산출물:

1. **`docs/SPEC.md`** — 종합 스펙 문서 ✅ (작성 완료)
   - 티어별 기능 매트릭스 (상세)
   - 데이터 모델 ERD (실제 SQL 수준)
   - 시스템 아키텍처 다이어그램
   - 유저 저니 (가입 → 결제 → 모니터링 → 리포트)
   - 권한 정책 (RLS 룰셋)
   - Stripe 결제 플로우 + Webhook 시나리오
   - 스케줄링 시스템 설계
   - PDF/CSV 리포트 파이프라인
   - Custom 재분석 UX 흐름
   - Wiki + Q&A 시스템 설계
   - 쿠폰 시스템 설계
   - Admin 패널 스코프
   - i18n 전략
   - 이메일 알림 종류와 트리거
   - 단계별 개발 로드맵 (Phase 1~4)

2. **`docs/DEV_SPEC.md`** — 개발 스펙 ✅ (작성 완료)
   - 사용 라이브러리 목록 + 버전
   - 디렉토리 구조 (변경분)
   - 환경변수 추가분 (Voyage AI, Stripe, 등)
   - DB 마이그레이션 계획 (pgvector, 새 테이블)
   - 테스트 전략

3. **`research/compare-price-policy.md`** — 가격 정책 시장조사 ✅ (작성 완료, 2026-05-02)
   - ✅ 9개 경쟁사 심층 분석 (Profound, Peec AI, AthenaHQ, Otterly, Scrunch, Ahrefs 등)
   - ✅ 4-tier 최종 가격: Basic $19.99 / Pro $79.99 / Business $299.99 / Enterprise $1,499.99
   - ✅ 시트 추가 $2.99, 자사 사이트 $9.99, 경쟁사 사이트 $39.99, AI 엔진 $19.99
   - ✅ 7-day free trial + 7+30+90일 만료 후 시퀀스
   - ✅ Custom 재분석 횟수 차등 (Basic 5 / Pro 30 / Business 100 / Enterprise 무제한)

---

## 8. 새 세션 시작 프롬프트 예시

> "D:\Claude\aeo-visibility 프로젝트의 v2 개발을 시작하려고 해.
> 먼저 docs/SPEC.md와 docs/DEV_SPEC.md를 읽고,
> Phase 1 첫 작업(Supabase Auth + 워크스페이스 모델)부터 시작해줘.
> reboot-service-concept.md는 의사결정 히스토리 참조용."

---

## 9. 미결정 / 별도 세션에서 결정 항목

### ✅ 시장조사 세션 (가격) — 2026-05-02 완료
1. ✅ 4-tier 최종 가격: **Basic $19.99 / Pro $79.99 / Business $299.99 / Enterprise $1,499.99**
2. ✅ 시트 추가 단가: **$2.99/멤버/월** (전 티어 동일)
3. ✅ 사이트 추가 단가: **자사 $9.99 / 경쟁사 $39.99** (Pro 이상)
4. ✅ AI 엔진 추가 단가: **$19.99/엔진/월** (전 티어 동일)
5. ✅ 트라이얼 정책: **7-day free trial + 7+30+90일 자동 시퀀스**
6. ✅ Custom 재분석 횟수: **Basic 5 / Pro 30 / Business 100 / Enterprise 무제한**

> 출처: `research/compare-price-policy.md` Section 7 (v3.1 최종)

### 사용자 작업 후 공유 예정
6. 이메일 도메인 (확정 후 공유)
7. Voyage AI 계정 (가입 후 공유)
8. 로고 / 브랜딩 자산 (현재 텍스트 로고만)

### 향후 결정
9. PDF 리포트 디자인 시안 상세 (브랜딩 적용 후)
10. DPA 도입 시점 (enterprise sales 진입 시)
11. 연령 정책 (글로벌 기본 16세 권장 vs 한국 14세)

---

## 10. 본 세션에서 수행한 작업 요약

이 세션에서 다음을 완료했습니다:

1. MVP 인프라 배포 (Supabase, Upstash, Railway, Vercel, GitHub)
2. CI/CD 구축 (GitHub Actions)
3. Celery → FastAPI BackgroundTasks 전환
4. 디버깅 완료: resend 패키지, Dockerfile $PORT, Railway 헬스체크, Next.js next.config.ts, Supabase IPv6/SSL
5. 보안 처리: `.env.template` 키 제거, `.claude/` gitignore
6. v2 설계 의사결정 (본 문서)

---

## 11. 브랜딩 가이드

### 11-1. 색상 팔레트

**Primary**:
- Royal Blue: `#0011BB` (포인트 컬러)
- White: `#FFFFFF` (메인 배경)

**Accent (그래프, 보조)**:
- Mint: `#6BB6B0`
- Light Blue: `#C7E1E4`

**Status**:
- Success: `#22C55E`
- Warning: `#F59E0B`
- Error: `#EF4444`
- Info: `#0011BB` (메인 블루 재사용)

**Neutral (5단계 그레이)**:
- Background: `#FFFFFF`
- Surface: `#F8F9FA`
- Border: `#E9ECEF`
- Text-muted: `#6C757D`
- Text: `#212529`

**Dark accent (강조 대비)**:
- `#0A0E27`

### 11-2. 타이포그래피

| 언어 | 본문 (sans-serif) | 헤드라인 (serif) |
|---|---|---|
| 영문 / 스페인어 | Noto Sans | Noto Serif |
| 국문 | Pretendard | Pretendard (세리프 ❌) |

### 11-3. 디자인 톤
전문적, 차가운, 깔끔한 느낌. 화이트 베이스 + 로얄블루 포인트.

---

## 12. 쿠폰 시스템 스펙

### 12-1. 일반 쿠폰 (코드 공개형)

```
필드:
- code                   # 사용자 입력 코드 (e.g., "BLACKFRIDAY30")
- target_plans           # ['basic', 'pro', 'business', 'enterprise'] 또는 'all'
- target_billing_cycles  # ['monthly'] / ['annual'] / ['monthly','annual']
- discount_type          # 'percent' | 'fixed_amount'
- discount_value         # 30 (%) 또는 19.99 (USD)
- valid_from             # 시작일
- valid_until            # 만료일
- max_uses               # 총 사용 횟수 (옵션)
- max_uses_per_user      # 사용자당 사용 횟수 (기본 1)
- applies_to             # 'first_payment' | 'all_renewals' | 'first_n_renewals(N)'
```

### 12-2. 블라인드 쿠폰 (타겟팅 자동 발급)

```
필드 (위 + 추가):
- segment_query          # 조건식 (e.g., "trial_only AND last_login < NOW() - 90d")
- delivery_channel       # 'email' | 'in_app' | 'both'
- unique_per_user        # true (사용자별 고유 토큰)
```

### 12-3. 자동 적용 쿠폰 (스케줄형 시즌 프로모션)

```
필드 (12-1 + 추가):
- auto_apply             # true (사용자 코드 입력 불필요)
- code                   # NULL (코드 없음)
```

**용도**: 슈퍼 관리자가 기간 한정 % 할인을 특정 plan + billing cycle에 자동 적용.
예: 월간 Pro 요금제에 대해 2026-11-11 ~ 2026-11-30 Cyber Monday 30% off.

**작동**: pricing 페이지가 active 자동 쿠폰을 조회 → 정가 옆에 할인가 노출
(`~~$79.99~~ $55.99 · Cyber Monday`). Checkout 시 Stripe Coupon ID 자동 attach.

### 12-4. 작동 방식 (블라인드 쿠폰)
1. Admin 패널에서 segment 정의 → 일치 사용자 미리보기 → 발송 버튼
2. 사용자별 고유 URL 발급 (e.g., `/redeem?token=abc123`)
3. URL 클릭 → 자동 로그인 → 결제 페이지에 쿠폰 자동 적용

### 12-5. Stripe 통합
- 우리 DB → Stripe `Coupon` + `PromotionCode` API 동기화
  (auto_apply는 PromotionCode 없이 Coupon만 생성)
- Stripe가 결제 시점에 할인 처리, 우리는 메타데이터/사용 이력 관리
- 만료/비활성화 시 양쪽 동시 비활성화

### 12-6. 우선순위 / 가드
- 동시 적용 가능한 쿠폰이 여러 개일 때 우선순위: **블라인드 > 코드형 > auto_apply**
  (가장 큰 할인 1건만 최종 적용)
- 동일 plan × billing_cycle에 active auto_apply 쿠폰은 **1개로 제한**
- 연간 할인과 쿠폰 **중복 적용 ❌**
- 마케팅 미동의 사용자에게 **블라인드 쿠폰 발송 ❌**
- 트랜잭셔널 알림(분석 완료 등)에는 쿠폰 임베드 ❌

---

## 13. 권한 / 역할 정의

### 13-1. 시스템 역할

| 역할 | 권한 | 위치 |
|---|---|---|
| `super_admin` | 시스템 전체 관리 (회원/결제/통계/Wiki/쿠폰) | `/admin` |

### 13-2. 워크스페이스 역할

| 역할 | 권한 | 비고 |
|---|---|---|
| `workspace_owner` | 결제 수정, 소유권 이양, 워크스페이스 삭제, 멤버 관리, 분석 실행, 모든 데이터 조회 | 워크스페이스당 **1명** |
| `workspace_admin` | 멤버 초대/제거, 사이트 관리, 분석 실행, 모든 데이터 조회 (결제/이양/삭제 ❌) | 다수 가능 |
| `member` | 분석 실행, 리포트 조회, Q&A 사용 | 다수 |
| `viewer` | 읽기 전용 (외부 컨설턴트 등) | 다수 |

### 13-3. 오너십 이양

- Owner는 admin/member 중 1명에게 owner 권한 양도 가능 (1워크스페이스 = 1 owner)
- **퇴사 시나리오 대응**:
  - Owner 미응답 30일 + 결제 실패 → super_admin이 강제 이양 가능
  - 잔여 멤버 중 가장 오래된 admin → owner로 승격
  - 회사 도메인 검증 시 추가 가중치
  - 강제 이양 모든 단계 audit_logs 기록

### 13-4. Supabase RLS 정책 (개념)
- 모든 워크스페이스 데이터는 `workspace_id` 기준 격리
- `workspace_members` 매핑 테이블 기반 조회 권한
- super_admin은 RLS 우회 (service_role 키 사용)

---

## 14. 이메일 계정

Resend 도메인 1개 + alias 운영.

### 14-1. 실제 이메일 계정 (3개)

| 주소 | 용도 |
|---|---|
| `no-reply@[domain]` | 자동 발송 (Magic Link, 분석 알림, 결제 영수증, 시스템 알림) |
| `hello@[domain]` | 일반 문의 (사용자가 답장 가능한 메인 채널) |
| `support@[domain]` | 고객지원 (Wiki/Q&A로 해결 안 되는 case) |

### 14-2. 약관 페이지 명시용 (메일링 그룹, hello로 포워딩)
- `legal@[domain]` — 개인정보 / DPA 문의
- `privacy@[domain]` — 개인정보처리방침 명시
- `security@[domain]` — 향후 enterprise 진입 시 분리

> Resend는 1개 도메인에서 무제한 alias 지원하므로 추가 비용 없음.
> SPF/DKIM/DMARC 설정 + 도메인 인증 작업 필요 (반나절).

---

## 15. 가입 시 동의 항목

| 항목 | 필수/선택 | 비고 |
|---|---|---|
| 서비스 이용약관 | ✅ 필수 | 동의 안 하면 가입 불가 |
| 개인정보처리방침 | ✅ 필수 | 동의 안 하면 가입 불가 |
| 만 16세 이상 (글로벌 GDPR 기준) | ✅ 필수 | 한국 14세 vs EU 16세 — 글로벌이면 16세 권장 |
| **마케팅 정보 수신 동의** | ⬜ 선택 | 프로모션 메일/쿠폰/블라인드 쿠폰 발송 가능 여부 |

> 마케팅 미동의 사용자는 트랜잭셔널 메일(분석 완료, 결제 등)만 수신.

---

*최종 업데이트: 2026-05-02*
*SPEC.md, DEV_SPEC.md 작성 완료 (2026-05-02). 다음 단계: Phase 1 개발 착수.*
