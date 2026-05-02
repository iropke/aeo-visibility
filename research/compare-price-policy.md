# AEO 시장 — 가격 정책 비교 리포트

> **작성일**: 2026-05-02
> **개정일**: 2026-05-02 (Ahrefs 추가 → v2 결정안 v2 → **최종 v3: 4-tier A안 채택**)
> **목적**: AEO Visibility v2 가격 정책 확정을 위한 시장조사
> **조사 방식**: 각 서비스 공식 pricing 페이지 직접 fetch (Claude in Chrome) + 보조 웹 검색
> **통화 기준**: USD (별도 표기 없는 경우)
> **조사 대상**: 9개 (심층 6개 + 보조 3개), Ahrefs는 SEO에서 AEO로 확장한 인컴번트로 별도 분석
> **🎯 최종 확정안 (v3.1)**: Section 7 — **Basic $19.99 / Pro $79.99 / Business $299.99 / Enterprise $1,499.99** (4-tier 단순화 + Free trial), 월 1회 모니터링, Q&A 무제한, Enterprise만 white-glove, **경쟁사 사이트 추가 $39.99**, **AI 엔진 추가 $19.99**, 7+30+90일 트라이얼 시퀀스

---

## 0. 핵심 요약 (TL;DR)

> **🎯 v2 최종 확정 가격 (Section 7 참조) — 4-tier A안**
>
> | Free | Basic | Pro | Business | Enterprise |
> |---|---|---|---|---|
> | $0 (7-day trial) | **$19.99** | **$79.99** | **$299.99** | **$1,499.99** |
>
> **추가 결정**:
> - 모든 유료 티어 **월 1회 자동 모니터링** + Custom 재분석 차등 (Basic 5 / Pro 30 / Business 100 / Enterprise 무제한)
> - Q&A 무제한 (rate limit만)
> - **Enterprise만 white-glove 온보딩**, 나머지 셀프
> - 시트 추가 **$2.99** (전 티어 동일, 허들 낮춤)
> - 자사 사이트 추가 **$9.99**, **경쟁사 사이트 추가 $39.99** (Pro 이상, 분석 부하 4배 반영 + Business 업셀 유도)
> - **AI 엔진 추가 $19.99** (전 티어 동일, 자연스러운 Pro 전환 유도) — 시장 최저가 절대 단가, Pro 이상에서 per-prompt 단가도 시장 최우위
> - 트라이얼 만료 후 **7+30+90일 자동 이메일 시퀀스**
> - SEO 지수 분석 → **Phase 2로 보류** (AEO 전문성 집중)

| 항목 | 시장 현황 | v2 확정안 비교 |
|---|---|---|
| **주력 가격대** | $99~$495/월 (Mid-tier 중심) | **$19.99~$1,799** — 최저가 진입 + Enterprise까지 풀 커버 |
| **저가 진입선** | $20~$29/월 (RankScale, Airefs[^1], Otterly Lite, Ahrefs Starter) | **$19.99 Basic** — 시장 최저 진입선과 동급 |
[^1]: **Airefs**(getairefs.com) — Ahrefs와 별개 회사. AEO 전용 저가 도구 ($24/월).
| **요금제 수** | 평균 3~4개 (Self-serve + Enterprise). Ahrefs는 4 + Enterprise 5개 | **6개 티어** (Free/Basic/Medium/Pro/Premium/Enterprise) — 시장 최다 |
| **공통 핵심 단위** | "Prompt 수" + "AI 모델 수". Ahrefs는 PAYG per-check도 도입 | v2: "사이트 수 + AI 엔진 수 + 분석 횟수" — Ahrefs와 유사 다축 단위 |
| **공통 업셀 항목** | 추가 prompts, 추가 AI 모델, 추가 사용자, Custom Prompt 패키지 (Ahrefs $50~$250) | v2: **시트 $2.99**, **자사 사이트 $9.99 / 경쟁사 사이트 $39.99**, **AI 엔진 $19.99** + Custom 재분석 패키지 ($4.99/$14.99) |
| **인컴번트 위협** | **Ahrefs (SEO → AEO 확장)**, HubSpot AEO | v2는 SEO 도구 미보유 — 번들링 한계 vs 한국어 + 액션 인사이트로 차별화 |
| **트라이얼** | 7-day free trial이 표준 (카드 등록 무) | v2: 1회 분석 트라이얼 + 7일 결과 열람 (카드 등록 무) |
| **연간 할인** | 15~17% 할인 (또는 "2개월 무료") | v2: **15% 할인** + 쿠폰 시스템 (중복 적용 ❌) |

### 가장 중요한 시사점 4가지

1. **가격대 갭 존재 확인됨**: $50~$100/월 구간이 시장에서 가장 비어 있는 구간입니다. v2의 Pro($59.99), Premium($99.99) 티어가 정확히 이 갭을 노립니다.
2. **"Prompt"가 시장 표준 과금 단위**: 경쟁사들은 모두 prompt 수로 가격을 차등화합니다. v2는 "사이트 수 + 자동 분석 + Custom 재분석 횟수"라는 다른 단위 — **유저 친화적이지만 시장 표준과 다른 것은 마케팅 시 설명이 필요**합니다.
3. **저가 시장의 최강자는 Otterly($29 Lite)**: v2 Basic($7.99)이 Otterly Lite보다 저렴하지만, Otterly Lite도 15 prompts로 매우 제한적입니다. **Basic 티어가 너무 저렴하면 "장난감 같은 서비스"로 인식될 위험** 존재.
4. **Ahrefs (SEO 인컴번트)의 AEO 진입은 가장 큰 위협**: Ahrefs는 Brand Radar(AEO)를 모든 SEO 메인 플랜($129~$1,499)에 기본 포함시키고, 단독 구매($199)도 제공합니다. **번들링 우위 + 10년 SEO 인지도가 신생 AEO 도구들을 압박**하는 구조입니다. 단, Ahrefs도 약점이 명확합니다 — Claude/Grok 미지원, 콘텐츠 추천 부재, 사용자 추가 비용 매우 높음 ($40~$100/u/월). v2는 이 약점을 정확히 파고들 기회가 있습니다.

---

## 1. 조사 대상 서비스 (9개)

### 1-1. 심층 조사 (6개)

| # | 서비스 | 공식 사이트 | 본사 | 시장 포지션 |
|---|---|---|---|---|
| 1 | **Profound** | tryprofound.com | 미국 | 엔터프라이즈 리더 (Khosla, Kleiner Perkins, Sequoia 투자 — $58.5M 펀딩) |
| 2 | **Peec AI** | peec.ai | 독일 (베를린) | 미드마켓 SEO 팀 |
| 3 | **AthenaHQ** | athenahq.ai | 미국 (샌프란시스코) | 자기계정 + 엔터프라이즈 (Credit 모델) |
| 4 | **Otterly.ai** | otterly.ai | 오스트리아 (비엔나) | SMB/저가 시장의 강자 (Gartner Cool Vendor 2025) |
| 5 | **Scrunch AI** | scrunch.com | 미국 | 신생 미드마켓 (Agent Experience 특화) |
| 6 | **Ahrefs (Brand Radar)** | ahrefs.com | 싱가포르 | **SEO 글로벌 강자가 AEO로 확장** — 기존 SEO 스택과 통합 판매 |

### 1-2. 보조 조사 (3개, 가격대 분포 확인용)

| # | 서비스 | 시작 가격 | 메모 |
|---|---|---|---|
| 7 | **HubSpot AEO** | $50/월 | 거대 SaaS의 AEO 진입 |
| 8 | **Goodie AI** | $399/월 | 11+ AI 플랫폼 추적 |
| 9 | **RankScale** | €20/월 (~$22) | 시장 최저가 |

---

## 2. 가격 정책 비교 (심층 6개사)

### 2-1. 요금제 가격 한눈 비교

| 서비스 | Free/Trial | Tier 1 (Starter) | Tier 2 (Mid) | Tier 3 (Pro) | Tier 4 (Enterprise) |
|---|---|---|---|---|---|
| **Profound** | 무료 트라이얼 | **$99/월** Starter | **$399/월** Growth | — | Custom |
| **Peec AI** | 무료 가입 | **$95/월** Starter | **$245/월** Pro | **$495/월** Advanced | Custom |
| **AthenaHQ** | 첫 달 67% 할인 | — | **$295/월** Self-Serve | — | Custom |
| **Otterly.ai** | 무료 트라이얼 | **$29/월** Lite | **$189/월** Standard | **$489/월** Premium | Custom |
| **Scrunch AI** | 7일 무료 | — | **$250/월** Core | — | Custom |
| **Ahrefs** | Free 플랜 + Starter $29 | **$129/월** Lite | **$249/월** Standard | **$449/월** Advanced | **$1,499/월** Enterprise |
| **Ahrefs Brand Radar** (단독) | — | **$199/월** (단독 구매) | — | — | — |

> 모든 가격은 월간 결제 기준. 연간 결제 시 15~17% 할인 (또는 2개월 무료).
> Ahrefs는 SEO 메인 플랜에 Brand Radar(AEO)가 기본 포함되며, 별도로 단독 구매 옵션($199/월)도 제공.

### 2-2. Profound 상세 (대표 경쟁사)

| 항목 | Starter ($99/월) | Growth ($399/월) | Enterprise (Custom) |
|---|---|---|---|
| AI 엔진 | ChatGPT만 | 3개 (ChatGPT + Perplexity + AI Overviews) | 최대 10개 (모든 주요 모델) |
| Prompts | 50개 (1,500 응답/월) | 100개 (9,000 응답/월) | Custom |
| Frequency | Daily | Daily | Daily |
| 최적화 콘텐츠 | — | 6개 article/월 | Custom |
| Agent Credits | 100/월 | 400/월 | Custom |
| Export | None | CSV, JSON | CSV, JSON, **API** |
| 지원 | 이메일 | 이메일 | Dedicated Slack + 24h SLA |
| SSO | — | — | SSO/SAML + SOC2 |

> **Note**: Lite 플랜이 $499였던 이전 버전 대비 현재는 $99 Starter / $399 Growth로 가격을 크게 낮추고 Lite를 단계화했음 — 시장 경쟁에 따른 가격 조정의 시그널.

### 2-3. Peec AI 상세

| 항목 | Starter ($95) | Pro ($245) | Advanced ($495) | Enterprise |
|---|---|---|---|---|
| Prompts | 50 | 150 | 350 | Fully customisable |
| Models | 3 선택 | 3 선택 | 3 선택 | All models |
| Projects | 1 | 2 | 5 | Unlimited |
| Users | Unlimited | Unlimited | Unlimited | Unlimited |
| Multi-country | — | — | ✓ | ✓ |
| Looker Studio | — | — | ✓ | ✓ |
| API access | — | — | — | ✓ |
| SSO | — | — | — | ✓ |
| 지원 | Chats | Chats + Email | Chats + Email | Dedicated Support |

### 2-4. AthenaHQ 상세 (Credit 모델)

| 항목 | Self-Serve ($295/월) | Enterprise (Custom) |
|---|---|---|
| Credits | 3,600/월 (1 credit = 1 AI response) | Custom |
| AI 모델 | 8개 (ChatGPT, Perplexity, AI Overviews, AI Mode, Gemini, Claude, Copilot, Grok) | + Persona/Multi-region/ACE |
| 경쟁사 모니터링 | ✓ (impersonation 포함) | Unlimited |
| Multi-country | Single | Multiple |
| Seats | Unlimited + RBAC | Unlimited + RBAC |
| API | — | ✓ |
| SSO | Google/Microsoft OAuth | + SAML SSO |
| 지원 | 표준 | Dedicated GEO Specialist + 2-hour SLA |
| 프로모션 | 첫 달 67% 할인, $300 free credit | — |

### 2-5. Otterly.ai 상세 (저가형 강자)

| 항목 | Lite ($29/월) | Standard ($189/월) | Premium ($489/월) | Enterprise |
|---|---|---|---|---|
| Search Prompts | 15 | 100 | 400 | Custom |
| AI 엔진 | 4개 (ChatGPT, AI Overviews, Perplexity, MS Copilot) | 동일 | 동일 | + Custom |
| Workspaces | 1 | Unlimited | Unlimited | Unlimited |
| Brand Reports | Unlimited | Unlimited | Unlimited | Unlimited |
| Recommendations | 3/월 | Unlimited | Unlimited | Unlimited |
| GEO URL Audits | 1,000/월 | 5,000/월 | 10,000/월 | Custom |
| Looker Studio | — | ✓ | ✓ | ✓ |
| SSO | — | — | — | ✓ |
| Multi-country | ✓ (50+) | ✓ (50+) | ✓ (50+) | ✓ |

> **연간 결제 시**: Standard $160, Premium $422 (~15% 할인)

### 2-6. Scrunch AI 상세

| 항목 | Core ($250/월) | Enterprise (Custom) |
|---|---|---|
| Prompts | 125 unique | Custom |
| AI 모델 | 4개 (ChatGPT, Perplexity, Google AIO, Copilot) | 9개 (+ Claude, Gemini, Meta AI, AI Mode, Grok) |
| Site Audits | 5/월 | Full Site Audit(s) |
| Brand Workspaces | 1 | Custom |
| User Licenses | 제한적 | Custom |
| API access | — | ✓ |
| SSO | Google SSO | SAML, OIDC |
| 지원 | Email | Email + Slack, Dedicated Account Team |
| 트라이얼 | 7-day free | — |

### 2-7. Ahrefs (Brand Radar) 상세 — SEO에서 AEO로 확장한 인컴번트

Ahrefs는 본래 SEO/백링크 분석의 글로벌 강자였으며, 2025년부터 **Brand Radar**라는 AEO 모듈을 추가하여 모든 메인 플랜에 기본 포함시키는 전략을 채택했습니다. 또한 Brand Radar 단독 구매도 가능합니다.

#### Ahrefs 메인 SEO+AEO 통합 플랜

| 항목 | Lite ($129/월) | Standard ($249/월) | Advanced ($449/월) | Enterprise ($1,499/월) |
|---|---|---|---|---|
| Projects | 5 | 20 | 50 | Unlimited |
| Historical data | 6 months | 2 years | 5 years | Unlimited |
| Tracked keywords | 750 | 2,000 | 5,000 | 10,000+ |
| **Tracked prompts (AEO)** | **5** | **10** | **20** | **83+** |
| Crawl credits | 100,000 | 500,000 | 1,500,000 | 5M+ |
| 포함 사용자 | 1 | 1 | 1 | 3+ |
| **추가 사용자 단가** | **$40/월** | **$60/월** | **$80/월** | **$100/월** |
| Brand Radar (AEO) | ✓ (기본) | ✓ + advanced | ✓ + Looker Studio | ✓ + 모든 기능 |
| API access | — | — | — | Unlimited |
| SSO | — | — | — | ✓ |
| 연간 할인 | up to 17% | up to 17% | up to 17% | (annual commit 필수) |

#### Ahrefs Brand Radar 단독 구매

| 항목 | 단독 ($199/월) |
|---|---|
| AEO 추적 모델 | 6개 (Google AI Overviews, AI Mode, ChatGPT, Perplexity, Gemini, Copilot) |
| 함께 제공 | Ahrefs Free 계정 (제한적 SEO 도구 무료 사용) |
| 한계 | Claude, Grok 미지원 (시장의 약점으로 지적됨) |

#### Ahrefs 추가 과금 (Add-ons) — **시장에서 가장 정교한 add-on 구조**

| Add-on | 단가 | 설명 |
|---|---|---|
| **Custom Prompts — Basic** | **$50/월** | 2,500 checks/월, overage $0.020/check |
| **Custom Prompts — Growth** | **$100/월** | 7,000 checks/월, overage $0.015/check |
| **Custom Prompts — Scale** | **$250/월** | 25,000 checks/월, overage $0.010/check |
| **Content Kit** | $99/월~ | AI Content Helper, Grader, Inventory |
| **Report Builder** | $99/월 | 50 reports + 500 widgets + 스케줄링 |
| **Project Boost Pro** | $20/월 per project | Auto-submit, Always-on audit, Instant recrawl |
| **Project Boost Max** | $200/월 per project | Patches, Batch AI, Unlimited URL detection |
| **Starter (별도 제품)** | $29/월 | 입문용, 경쟁사 분석 + Brand Radar 미포함 |

> **핵심 인사이트**:
> 1. Ahrefs는 **사용량 기반(per-check) 과금**을 도입한 유일한 메이저 서비스. 경쟁사들은 모두 정액제 prompt 한도 모델.
> 2. **Custom Prompts overage**: 0.02 → 0.015 → 0.010 USD per check로 볼륨 디스카운트 적용.
> 3. **추가 사용자 단가가 시장 최고 수준** ($40~$100/월) — 팀 확장이 매우 비싸다는 약점.
> 4. **Brand Radar 단독 $199**는 Profound Starter $99의 2배지만, Ahrefs의 SEO 데이터(381M+ organic prompts) 자산과의 통합이 차별화 포인트.

---

## 3. 업셀링 / 추가 과금 정책 비교

### 3-1. 업셀 항목 매트릭스

| 서비스 | 추가 사용자 | 추가 AI 모델 | 추가 Prompts | 추가 Workspace | 기타 |
|---|---|---|---|---|---|
| **Profound** | 비공개 (Custom) | 비공개 | 한도 초과 시 Enterprise 권유 | 비공개 | Agent Credits 패키지 (Custom) |
| **Peec AI** | **무제한 (모든 티어)** | **티어별 추가 모델 단가 명시** | 상위 티어 업그레이드 권장 | Project 단위로 상위 티어 | Annual 15% 할인 |
| **AthenaHQ** | 무제한 + RBAC | 추가 credit 구매 가능 | 추가 credit 구매 가능 | 비공개 (Enterprise) | Annual 17% 할인, 첫 달 67% off |
| **Otterly.ai** | Lite는 unlimited team members 명시 | **AI Mode/Gemini 별도 add-on** | **+100 search prompts add-on** | Standard부터 unlimited | Annual 15% 할인 |
| **Scrunch AI** | **$25/월 per user** | — | 한도 초과 시 안내 | 추가 brand workspace 옵션 | Enterprise만 annual 할인 |
| **Ahrefs** | **$40~$100/월 per user** (티어별 차등) | (Brand Radar 6개 고정) | **Custom Prompts $50/$100/$250/월** + per-check overage | Project 단위 Boost ($20/$200/월) | Content Kit / Report Builder / PAYG credits 등 풍부한 add-on |

### 3-2. 가장 명확한 add-on 사례 (Peec AI)

| 추가 항목 | Starter 추가 단가 | Pro 추가 단가 | Advanced 추가 단가 |
|---|---|---|---|
| 추가 AI 모델 1개 | $35/월 | $85/월 | $165/월 |

> **인사이트**: 티어가 높을수록 한 모델 추가 가격이 비싸짐 (prompt 수와 비례) — **티어 자체 가격에 비해 add-on 마진이 높은 구조**.

### 3-3. 가장 명확한 add-on 사례 (Otterly.ai)

| 추가 항목 | Standard 단가 | Premium 단가 |
|---|---|---|
| +100 search prompts | (월간 가격 비공개, 페이지에 명시) | (월간 가격 비공개) |
| Google AI Mode 추가 | $149/월 (월간) / $610/년 (연간) | $1,540/년 (연간) |
| Google Gemini 추가 | $149/월 (월간) / $610/년 (연간) | $1,540/년 (연간) |

> **인사이트**: 기본 플랜에 핵심 4개 엔진(ChatGPT/AI Overviews/Perplexity/Copilot)은 포함하되, **신생/추가 엔진(AI Mode, Gemini)은 별도 과금**으로 분리. 매우 영리한 업셀 전략.

### 3-4. 공통 패턴 정리

| 패턴 | 채택 서비스 | 시사점 |
|---|---|---|
| 추가 사용자 별도 과금 | Scrunch ($25/u/월), Ahrefs ($40~$100/u/월), Profound (Custom) | v2 $2.99/멤버는 **Scrunch 대비 88%, Ahrefs Lite 대비 92% 저렴** |
| 추가 AI 모델 별도 과금 | Peec AI, Otterly.ai | v2: **모든 티어가 동일 5개 카테고리 분석** — 모델 단위 add-on 부재 |
| 추가 Prompts/credits | Profound, AthenaHQ, Otterly.ai, **Ahrefs (PAYG per-check)** | v2: **Custom 재분석 횟수**가 유사 개념 — add-on 화 가능 |
| 추가 Workspace/Project/Brand | Peec AI, Scrunch, **Ahrefs (Project Boost)** | v2: **사이트 추가 단가**가 유사 — 단가 미정 |
| 연간 결제 할인 | 거의 모두 (15~17%) | v2: **고정 할인 ❌, 쿠폰 시스템 채택** — 차별화 포인트 |
| **PAYG (사용량 기반) 모델** | **Ahrefs만** (per-check overage) | v2 채택 시 → 신규 차별화 가능. 단, billing 복잡도 증가 |

---

## 4. 포지셔닝 / 타겟 고객 분석

### 4-1. 시장 세그먼트 매핑

| 서비스 | 명시된 ICP | 가격대 | 차별화 포인트 |
|---|---|---|---|
| **Profound** | "From bootstrapped startups to global enterprises" — 실질적으로 미드마켓 ~ 엔터프라이즈 | $99~$399, Custom | Marketing Engineering 컨셉, Agents (자동화), 가장 깊은 데이터 |
| **Peec AI** | "Marketing teams, SEO managers, agencies" | $95~$495, Custom | 사용성 우선, 멀티 프로젝트, Looker Studio 연동 |
| **AthenaHQ** | "Self-Guided SMBs" + "Enterprises & Agencies" | $295, Custom | Credit 모델 (사용량 기반), Citation Engine, 산업별 솔루션 |
| **Otterly.ai** | "Solo marketers, SMEs, agencies, mid-sized" | $29~$489, Custom | 저가 진입선, 50+ 국가 지원, GEO URL Audit (1k~10k) |
| **Scrunch AI** | "Brands, Agencies, Enterprise" | $250, Custom | Agent Experience Platform (AXP), 9 LLM, ADP/Lenovo 등 큰 고객 |
| **Ahrefs** | **기존 SEO 사용자 + AEO 신규 고객 통합** | $129~$1,499 + $199 단독 | **SEO 강자의 AEO 확장 — 기존 SEO 데이터(381M+ prompts) 자산 결합 + Bot Analytics + Site Audit 통합 패키지** |
| **HubSpot AEO** | HubSpot 기존 고객 (CRM/Marketing Hub 통합) | $50 | 대형 SaaS 통합 |
| **Goodie AI** | 미드~엔터프라이즈 | $399+ | 11+ AI 플랫폼 (DeepSeek, Grok 포함) |
| **RankScale** | 솔로/SMB 최저가 | €20 (~$22) | 시장 최저가, 7개 AI 플랫폼 |

### 4-2. 가격대별 시장 지도

```
  ~$30        $50         $100         $200         $400         $1,000+
   │           │           │            │            │            │
   ▼           ▼           ▼            ▼            ▼            ▼
 RankScale  HubSpot    Profound     Ahrefs       Profound     Ahrefs
 Otterly    Otterly    Starter      Brand        Growth       Enterprise
 Lite ($29) ($50)      ($99)        Radar        ($399)       ($1,499)
 Ahrefs               Ahrefs       단독 ($199)   Goodie AI    + 모든 서비스의
 Starter              Lite ($129)  Otterly       ($399)       Custom Enterprise
 ($29)                Otterly      Standard      Ahrefs        ($1k+ 추정)
                      Standard     ($189)        Advanced
                      ($189)       Peec Pro      ($449)
                                   ($245)        Otterly
                                   Ahrefs        Premium
                                   Standard      ($489)
                                   ($249)        Peec
                                   Scrunch       Advanced
                                   Core ($250)   ($495)
                                   AthenaHQ
                                   Self-Serve
                                   ($295)
            ◄────── 빈 구간 ──────►
            v2 Basic·Medium·Pro 가 정확히 이 구간
            ($7.99 / $23.99 / $59.99)
```

> **Ahrefs 진입 후 시장 변화**: Ahrefs Lite($129)와 Brand Radar 단독($199)이 추가되면서 $100~$200 구간이 더 빽빽해짐. v2의 Premium($99.99)이 이 구간 직전에서 가격 우위를 확보.

### 4-3. 차별화 축 6가지

| 차별화 축 | 가장 강한 서비스 | v2의 위치 |
|---|---|---|
| 1. **데이터 깊이** (가장 많은 모델, 가장 많은 prompts) | Profound, Goodie AI, **Ahrefs (SEO+AEO 통합)** | 5개 카테고리 분석 — **데이터 깊이 ❌, 인사이트 깊이 ✅** |
| 2. **저가** | Otterly, RankScale | **시장 최저가** ($7.99) |
| 3. **자동화 / Agents** | Profound (Agents), Scrunch (AXP) | Custom 재분석 — 사용자 트리거 |
| 4. **에이전시 친화** | Peec, Otterly, Scrunch, Ahrefs (Agency directory listing) | 멀티 워크스페이스 미설계 (단일 워크스페이스 모델) |
| 5. **엔터프라이즈** | AthenaHQ, Profound, **Ahrefs Enterprise ($1,499)** | v2 미타겟 (의도적) |
| 6. **SEO 통합 (one-stop shop)** | **Ahrefs 독점** | **v2는 AEO-only** — 잠재 고객이 SEO 도구도 따로 구매해야 하는 한계 |

### 4-4. Ahrefs 진입의 시장 임팩트 — 별도 분석

| 관점 | 영향 |
|---|---|
| **번들링 위협** | 기존 Ahrefs 사용자는 Brand Radar가 기본 포함되므로 별도 AEO 도구 구매 필요성 ↓ |
| **신뢰도 압박** | 10년+ SEO 인지도가 AEO에도 그대로 전이됨 — 신생 AEO-only 도구는 신뢰 확보가 어려움 |
| **가격 압박** | Brand Radar 단독 $199는 Profound 등 대비 비싸지만, SEO 사용자에게는 "공짜처럼 보이는" 효과 |
| **차별화 기회** | Ahrefs의 약점: ① Claude/Grok 미지원 ② Content 추천 부재 ③ CMS 통합 부재 ④ 추가 사용자 비쌈 ⑤ 대시보드 위주, 액션 부족 |
| **v2 시사점** | 한국 시장 + 다국어 + 저가 + 액션 가능한 인사이트(개선 제안 3개)로 차별화 — **글로벌 SEO 강자가 못 다루는 영역에 집중** |

---

## 5. v2 5-Tier 플랜 vs 시장 직접 비교

### 5-1. 가격 직접 비교

| v2 티어 | v2 가격 | 시장 등가 가격대 | 가장 가까운 경쟁 플랜 | v2 가격 위치 |
|---|---|---|---|---|
| Free | $0 (1회 트라이얼) | 무료 트라이얼 (Profound, Peec, Otterly, Scrunch, Ahrefs Free) | 모두 7-day free trial | **시장 표준** |
| **Basic** | **$7.99/월** | $20~$30 zone | RankScale (€20), Airefs ($24, getairefs.com — Ahrefs와 별개 신생 도구), Otterly Lite ($29), **Ahrefs Starter ($29)** | **시장 최저가의 1/3** |
| **Medium** | **$23.99/월** | $29~$50 zone | Otterly Lite ($29), HubSpot AEO ($50) | **저가형 zone 정합** |
| **Pro** | **$59.99/월** | $50~$130 zone | HubSpot AEO ($50), Profound Starter ($99), **Ahrefs Lite ($129)** | **시장 빈 구간 진입** |
| **Premium** | **$99.99/월** | $99~$250 zone | Profound Starter ($99), **Ahrefs Lite ($129)**, Otterly Standard ($189), **Ahrefs Brand Radar 단독 ($199)**, Scrunch Core ($250) | **Profound와 동일 가격 + 경쟁사 분석 차별화 + Ahrefs Brand Radar 대비 50% 저렴** |

### 5-2. 기능 vs 시장 비교

| 항목 | v2 (Premium 기준) | Profound Starter | Peec Starter | Otterly Standard | **Ahrefs Lite** | **Ahrefs Brand Radar 단독** | 평가 |
|---|---|---|---|---|---|---|---|
| 가격 | $99.99/월 | $99/월 | $95/월 | $189/월 | **$129/월** | **$199/월** | v2가 가장 저렴 |
| 모니터링 사이트 | 자사 1 + 경쟁사 3 | 1 (자사만) | 1 project | 1 brand | 5 projects | 1 (Free 계정 포함) | **Ahrefs Lite는 5 프로젝트** — v2 사이트 수 약점 |
| AI 엔진 추적 | (구현 예정 — 동일 5개 카테고리) | ChatGPT만 | 3개 선택 | 4개 | Brand Radar 6개 모델 | 6개 모델 | **v2 명세 미확정 — Ahrefs와 비슷한 6개 추적 권장** |
| Prompt 수 | "사이트 단위 분석"으로 다른 단위 | 50 | 50 | 100 | 5 tracked prompts | (PAYG) | **Ahrefs Lite는 prompt 수가 가장 적음** — v2 강점 가능 |
| 멤버 | 5명 (하드캡 50) | 비공개 | Unlimited | Unlimited | 1 (+$40/u 추가) | 1 | **v2 ($2.99/멤버)는 Ahrefs($40) 대비 압도적 저렴** |
| 자동 분석 | 월 1회 + Custom 재분석 | Daily | Daily | Daily | Daily | Daily | **v2 빈도 낮음** |
| PDF/CSV 리포트 | 전 티어 PDF, Pro+ CSV | CSV/JSON (Growth) | — | Detailed Reports & Export | (Looker은 Advanced부터) | — | v2 강점 |
| Wiki/Q&A | 신규 추가 기능 | — | — | — | — | — | **v2 차별화** |
| 다국어 (한/영/스페인어) | ✓ | 영어 위주 | 영어 위주 | 영어 위주 | 영어 위주 | 영어 위주 | **v2 차별화 (특히 한국 시장)** |
| SEO 도구 통합 | ❌ (AEO-only) | ❌ | ❌ | ❌ | **✓ (Site Explorer 등)** | ❌ | **Ahrefs 압도적 — 유저는 SEO+AEO 한 번에 해결** |

### 5-3. v2의 강점과 약점 정리

| 구분 | 항목 | 비고 |
|---|---|---|
| **강점** | 시장 최저가 진입 ($7.99 Basic) | RankScale($22)보다 64% 저렴 |
| **강점** | 5개 티어 세분화 | 시장 평균 3~4개 |
| **강점** | 다국어 (한/영/스페인어) | 글로벌 경쟁사 대부분 영어 위주 |
| **강점** | 경쟁사 비교 ($59.99~) | Profound Starter($99)는 단일 사이트만 |
| **강점** | 한국 시장 공백 | 한국어 AEO 도구가 사실상 부재 |
| **강점** | 시트 단가 $2.99 | Scrunch $25, Ahrefs $40~$100 대비 압도적 |
| **약점** | 모니터링 빈도 낮음 (월 1회) | 경쟁사 모두 Daily 추적 |
| **약점** | 추적 모델 명세 미공개 | 경쟁사는 4~10개 명시 |
| **약점** | Prompt 단위 부재 | 시장 표준 단위 (prompts) 안 쓰면 가치 비교 어려움 |
| **약점** | API 액세스 부재 | Enterprise 진입 시 필수 |
| **약점** | SEO 도구 미제공 (AEO-only) | **Ahrefs 같은 SEO+AEO 번들에 비해 단일 도구 한계** |
| **위험** | $7.99가 너무 저렴 | "장난감 서비스" 인식 위험, CAC 회수 어려움 |
| **위험** | Ahrefs 같은 인컴번트의 가격 인하 가능성 | Ahrefs Brand Radar 단독($199)이 추후 더 저렴해질 수 있음 |

---

## 6. 가격 정책 권장사항

### 6-1. 핵심 권장사항 (우선순위 순)

| 우선순위 | 권장사항 | 근거 |
|---|---|---|
| 🔴 **High** | **Basic 가격을 $7.99 → $14.99~$19.99로 상향 검토** | 시장 최저가 RankScale($22)·Otterly Lite($29)·Ahrefs Starter($29)보다 30% 정도 낮은 수준이 적절. $7.99는 LTV/CAC 회수 어렵고 "장난감" 인식 위험 |
| 🔴 **High** | **모니터링 빈도 차등화** (Basic 월 1회 / Medium 주 1회 / Pro 일 1회) | 경쟁사 모두 Daily — v2가 월 1회만 제공하면 결정적 약점 |
| 🔴 **High** | **추적 AI 엔진 수를 티어별 차등화** (Basic 3개 → Pro/Premium 6~8개) | "Prompt 수"는 v2 단위와 다르지만 "AI 엔진 수"는 시장 표준. Ahrefs Brand Radar 6개와 동등 이상으로 매칭 권장 |
| 🔴 **High** | **Ahrefs 대응 차별화 메시지 정립** | Ahrefs(SEO+AEO 번들)와 정면 경쟁하지 말고 ① 한국어 ② 액션 가능한 인사이트 ③ 압도적 저가 ④ Claude/Grok 추적 (Ahrefs 약점) 으로 차별화 |
| 🟡 **Med** | **Custom 재분석 횟수를 add-on으로 판매** | 모든 경쟁사가 prompt/credit 추가 add-on 운영 — 자연스러운 업셀. Ahrefs는 PAYG per-check도 도입 — 참고 가능 |
| 🟡 **Med** | **사이트 추가 단가 = $9.99~$14.99/사이트/월 검토** | Peec Pro $245(2 projects)/Advanced $495(5 projects)에서 역산 시 1 project = $50~$80. **Ahrefs Lite는 5 projects를 $129에 제공** — 1 project = $26 → v2는 이보다 저렴해야 경쟁력 |
| 🟡 **Med** | **Pro 티어를 $79.99로 인상 검토** | $59.99는 HubSpot AEO($50)와 너무 가까움. $79.99로 올려도 Profound Starter($99)·Ahrefs Lite($129) 대비 20~38% 저렴 |
| 🟢 **Low** | **연간 할인 15% 제공 검토** | 시장 표준이 15~17% — 쿠폰 시스템과 별개로 기본 할인 운영 검토 가치 |
| 🟢 **Low** | **Enterprise 티어 추가 검토** (Premium 위) | 멤버 50명 하드캡 초과 + API 접근 + SSO + Dedicated Slack — 대형 고객 확보 시 필요. Ahrefs Enterprise($1,499) 대비 가격 우위 가능 |

### 6-2. 권장 가격 조정안 (참고용 — 시뮬레이션)

| 시나리오 | Free | Basic | Medium | Pro | Premium | Enterprise |
|---|---|---|---|---|---|---|
| **초기 v2 초안** | $0 | $7.99 | $23.99 | $59.99 | $99.99 | (없음) |
| A안 (안정형) | $0 | $14.99 | $29.99 | $69.99 | $119.99 | Custom |
| B안 (성장형) | $0 | $9.99 | $24.99 | $59.99 | $99.99 | Custom |
| C안 (공격형) | $0 | $7.99 (그대로) | $23.99 (그대로) | $59.99 (그대로) | $99.99 (그대로) | Custom |

> **참고**: 위 시나리오는 권장사항 도출 단계의 시뮬레이션입니다. **최종 확정 가격은 Section 7 참고**.

### 6-3. 업셀 항목 권장 가격

| Add-on | 권장 단가 | 시장 비교 |
|---|---|---|
| 추가 멤버 (시트) | **$2.99/멤버/월** (현 v2 그대로) | Scrunch $25 대비 88% 저렴 — **유지** |
| 추가 사이트 | **Basic +$9.99/월, Pro/Premium +$14.99/월** | 단가 차등화로 상위 플랜 유도 |
| 추가 AI 엔진 추적 | **$4.99/엔진/월** (Basic), **$9.99/엔진/월** (Pro+) | Peec($35~$165), Otterly($149) 대비 매우 저렴 |
| Custom 재분석 추가 횟수 | **Basic 5회 $4.99 / Pro 20회 $9.99** | 신규 add-on (시장에 없는 단위) |
| 연간 결제 | **15% 할인** | 시장 표준 정합 |
| 한 번에 PDF 디자인 커스텀 | **$49 (1회)** | 신규 add-on |

### 6-4. 트라이얼 정책 권장사항

| 항목 | v2 현재 | 시장 표준 | 권장 |
|---|---|---|---|
| 트라이얼 기간 | 1회 분석 (회수 기반) | 7-day free trial (시간 기반) | **두 가지 병행** — "1회 무료 분석 + 7일 동안 결과 열람 가능" |
| 카드 등록 | ❌ (첫 결제 시점) | 대부분 ❌ | **유지 ✅** — 시장 표준 |
| 트라이얼 만료 후 | 재가입 유인 제외 | (각자 정책) | **30일 cooldown 후 재트라이얼 1회 더 허용** 검토 |

---

## 7. ✅ 최종 확정 가격 정책 (사용자 결정안 v3 — A안 채택)

> **결정 (2026-05-02 최종 갱신)**: **4-tier 단순화 구조** + Free + Enterprise = 총 5 line
> **가격 범위**: Free ~ Enterprise $1,499.99
> **선택된 안**: A안 (균형형) — Pro $79.99 / Business $299.99
> **반영 사항**: 5-tier → 4-tier 단순화, **모니터링 월 1회 (전 티어)**, Q&A 무제한, **Enterprise만 white-glove**, 시트 추가 $2.99 유지 (허들 낮춤), 경쟁사 사이트 추가 $14.99, **AI 엔진 추가 $19.99**, **트라이얼 7+30+90일 시퀀스**, **SEO 지수는 Phase 2로 보류**

### 7-1. 결정 가격표 (4-Tier + Free + Enterprise)

| 티어 | **확정 가격 (월간)** | 연간 결제 (15% 할인) | 핵심 가치 | 시장 비교 |
|---|---|---|---|---|
| **Free** | **$0** | — | **7-day free trial** (시간 기반, 카드 등록 ❌) | 시장 표준 |
| **Basic** | **$19.99/월** | $16.99/월 ($203.88/년) | 1 사이트, 1 시트 — **후킹 가격** (한정 37% 할인 마케팅 운용) | RankScale ($22), Otterly Lite ($29), Ahrefs Starter ($29) **아래** |
| **Pro** | **$79.99/월** | $67.99/월 ($815.88/년) | 3 사이트, 3 시트, 경쟁사 1건/사이트, 자사 분석 본격 진입 | HubSpot AEO ($50)와 Profound Starter ($99) 사이 **시장 빈 구간 진입** |
| **Business** | **$299.99/월** | $254.99/월 ($3,059.88/년) | 5 사이트, 5 시트, 경쟁사 3건/사이트 심층, **산업 벤치마크** | AthenaHQ Self-Serve ($295)와 **동급 정면 경쟁** + 한국어 차별화 |
| **Enterprise** | **$1,499.99/월** | $1,274.99/월 (annual commit 필수) | 모든 AI 엔진, 자사 + 경쟁사 5, 20 시트, white-glove 온보딩 | **Ahrefs Enterprise ($1,499)와 동가** + 한국어/다국어/Dedicated CS 차별화 |

### 7-2. 가격 ladder 검증

| 단계 | 가격 변화 | Ratio | 평가 |
|---|---|---|---|
| Basic → Pro | $19.99 → $79.99 | **4.0x** | ✅ 정상 (시장 빈 구간 진입) |
| Pro → Business | $79.99 → $299.99 | **3.75x** | ✅ 정상 (산업 벤치마크 가치 차별) |
| Business → Enterprise | $299.99 → $1,499.99 | **5.0x** | ✅ 정상 (Enterprise 통상 5~10x) |
| **평균 ratio** | — | **4.22x** | ✅ **이론적 균형값과 일치** (75배 격차의 3제곱근 = 4.22x) |

> **Ladder 평가**: 4-tier 구조에서 가장 균형적인 분배. 인접 티어 간 ratio가 3.75~5.0x로 일관되어 사용자가 "다음 티어로 가야 하는 이유"를 명확히 인식할 수 있습니다.

### 7-3. 티어별 기능 매트릭스

| 항목 | Free | Basic ($19.99) | Pro ($79.99) | Business ($299.99) | Enterprise ($1,499.99) |
|---|---|---|---|---|---|
| **자사 사이트** | 1회 | 1 | 3 | 5 | 무제한 |
| **경쟁사 사이트** | — | — | 사이트당 1건 옵션 | 사이트당 3건 옵션 | 자사 + 경쟁사 5 |
| **기본 AI 엔진** | 3 | 3 (Google AI Overviews, Claude, ChatGPT) | 3 | 3 | **모든 엔진 포함 (10+)** |
| **자동 모니터링 빈도** | 단발 1회 | **월 1회** | **월 1회** | **월 1회** | **월 1회** |
| **5개 카테고리 분석** | ✓ | ✓ | ✓ | ✓ | ✓ |
| **Custom 재분석 (월 기본)** | 0 | **5회** | **30회** | **100회** | **무제한** |
| **시계열 그래프** | — | 6개월 | 12개월 | 24개월 | 무제한 |
| **PDF 리포트** | — | ✓ | ✓ | ✓ | ✓ + 브랜딩 무료 |
| **CSV 다운로드** | — | — | ✓ | ✓ | ✓ |
| **경쟁사 비교 그래프** | — | — | ✓ (1건) | ✓ (심층, 3건) | ✓ (심층, 5건) |
| **산업 벤치마크** | — | — | — | ✓ | ✓ |
| **기본 시트 (멤버)** | 1 | 1 | 3 | 5 | 20 |
| **Q&A 사용 횟수** | rate limit만 | **무제한** | **무제한** | **무제한** | **무제한** |
| **다국어 (한/영/스페인어)** | ✓ | ✓ | ✓ | ✓ | ✓ |
| **Wiki 액세스** | 공개만 | 공개+멤버 | 공개+멤버 | 공개+멤버 | + 워크스페이스 전용 Wiki |
| **API 액세스** | — | — | Add-on ($99/월) | Add-on ($99/월) | ✓ (기본 포함) |
| **SSO (SAML/OIDC)** | — | — | — | — | ✓ |
| **감사 로그** | — | — | 30일 | 90일 | 무제한 |
| **지원** | 셀프 | Email | Email + Chat | Email + Chat + 4시간 SLA | **Dedicated Slack + 2시간 SLA + Account Manager** |
| **온보딩** | — | **셀프** | **셀프** | **셀프** | **White-glove** |

> **공통 (모든 유료 티어)**: 월 1회 자동 모니터링 + Custom 재분석 차등 적용, Q&A 무제한, 다국어 지원, 한국어 UI/리포트
> **SEO 지수 분석**: Phase 2에서 검토 (현재 v2 스코프 제외)

### 7-4. 업셀링 / 추가 과금 정책 (확정안)

#### 추가 시트 (사용자) — 핵심 차별화 ⭐

| 적용 티어 | 추가 단가 |
|---|---|
| **모든 유료 티어 (전 티어 동일)** | **+$2.99/멤버/월** |
| Enterprise | 20명 기본, 추가 무제한 협의 |

> **시장 비교**: Scrunch ($25/u/월) 대비 **88% 저렴**, Ahrefs Lite ($40/u/월) 대비 **92% 저렴** — **시장 최저가 시트 단가 (강력한 차별화)**
> **정책 의도**: 시트 비용 허들을 낮춰 팀 확장 친화적 환경. 실질 매출 동력은 **사이트 추가**와 **상위 티어 업셀**에서 확보.

#### 추가 사이트

| 사이트 종류 | 적용 티어 | 추가 단가 |
|---|---|---|
| **자사 사이트** | 모든 유료 티어 | **+$9.99/사이트/월** |
| **경쟁사 사이트** | Pro 이상 | **+$39.99/사이트/월** |
| Enterprise | — | 협의 (사용량 기반) |

> **시장 비교 (자사)**: Ahrefs Lite는 5 projects를 $129에 제공 (1 site = $25.8) — v2가 **61% 저렴**
> **경쟁사 사이트 단가 정책 의도** ($14.99 → **$39.99**로 인상):
> ① 경쟁사 분석은 자사 분석 + 비교 그래프 + 시계열 매칭이 추가되어 분석 부하가 약 4배
> ② Pro에서 경쟁사 1~3건 추가는 자연스럽게 (~$120~$200), **4건 이상 시 Business($299.99) 업셀 명확히 유리**
> ③ "경쟁사 분석"이 Pro 이상의 핵심 가치 — 단순 add-on이 아닌 **본격 분석 모듈 가격**으로 책정
> ④ 자사($9.99) 대비 4배 — **경쟁사 분석의 추가 가치 정당화**

#### 추가 AI 엔진 추적

| 기본 포함 | 추가 가능 | 추가 단가 |
|---|---|---|
| Google AI Overviews, Claude, ChatGPT (3개) | Perplexity, Gemini, Copilot, Grok, AI Mode 등 | **+$19.99/엔진/월** (전 티어 동일) |

##### 시장 비교 — 정직한 두 축 분석

| 비교 축 | 결과 |
|---|---|
| **절대 단가 (월간)** | ✅ 시장 최저가. Otterly add-on $149 대비 **87% 저렴**, Peec Pro 추가 모델 $85 대비 **76% 저렴**, Peec Starter 추가 $35 대비 **43% 저렴** |
| **Per-prompt 정규화 (Basic)** | ⚠️ 동등 수준. v2 Basic의 분석량(월 6회 = ~30 prompts) 기준 $0.67/prompt = Peec Pro($0.57)와 비슷 |
| **Per-prompt 정규화 (Pro)** | ✅ 시장 최우위. Custom 재분석 30회 활용 시 $0.13/prompt — Peec Advanced($0.47) 대비 **3.5배 저렴** |
| **Per-prompt 정규화 (Business)** | ✅ 압도적 우위. Custom 재분석 100회 활용 시 $0.04/prompt — 시장 최저가의 약 1/12 |

> **마케팅 메시지 권장**:
> - "**시장 최저가의 AI 엔진 추가 옵션**" (절대 단가 기준 — 정확)
> - "**Pro 티어 이상에서 분석량 대비 단가 시장 최우위**" (per-prompt 기준 — 정확)
> - ❌ "압도적 저가" 단독 사용은 부정확 (Basic은 절대 단가만 우위, per-prompt는 동등)

> **정책 의도**: $9.99 → $19.99 인상으로 **자연스러운 Pro 전환 유도**. (Basic + 엔진 3개 = $79.96 → Pro $79.99와 동가 → 상위 티어 선택 유도)
> **단위 차이 주의**: 경쟁사는 "엔진 + prompt 패키지"로 묶어 판매. v2는 "엔진"과 "Custom 재분석"을 분리 판매 → **마케팅 시 단위 차이 설명 필수**

#### Custom 재분석 추가 횟수 (Add-on Pack)

| 패키지 | 가격 | 추가 횟수 | 적용 티어 | 시장 비교 |
|---|---|---|---|---|
| **Basic Pack** | **+$4.99/월** | +5회 | Basic, Pro | Ahrefs Custom Prompts Basic ($50/월) 대비 90% 저렴 |
| **Pro Pack** | **+$14.99/월** | +20회 | Pro, Business | Ahrefs Growth ($100/월) 대비 85% 저렴 |
| **PAYG (단건)** | **$2.99/회** | +1회 | 모든 유료 티어 | 한도 소진 후 자동 청구 (사용자 옵트인 시) |
| Enterprise | 포함 (무제한) | — | Enterprise | — |

> **정책 의도**: 모니터링 월 1회로 통일했으므로 **Custom 재분석 횟수 = 진짜 사용량의 차등 단위**. 티어별 기본 횟수가 곧 가치 차별화의 핵심.

#### PDF 리포트 브랜딩 커스텀

| 적용 티어 | 가격 |
|---|---|
| Basic / Pro / Business (전 티어 공통) | **$19.99 (1회성)** |
| Enterprise | **무료** (자동 적용) |

> **내용**: 사용자의 로고 + 색상 + 회사명을 PDF 리포트에 적용. 1회 결제 후 영구 적용 (브랜드 재변경 시 추가 결제).

#### Looker Studio Connector

| 적용 티어 | 가격 |
|---|---|
| Basic | ❌ (이용 불가) |
| Pro / Business | **+$19.99/월** |
| Enterprise | 포함 (무료) |

#### 기타 Add-on

| 항목 | 가격 | 적용 티어 |
|---|---|---|
| **API 액세스 (단독)** | +$99/월 | Pro 이상 |
| **추가 워크스페이스** (조직 단위) | +$99/월/워크스페이스 | Pro 이상 |
| **외부 컨설턴트(Viewer) 시트** | +$1.99/멤버/월 | Pro 이상 |
| **데이터 보관 연장** (5년 → 7년) | +$49/월 | Business 이상 |
| **GDPR DPA / HIPAA / SOC2 docs** | 무료 | Enterprise만 |

### 7-5. 트라이얼 정책 (확정 — 7+30+90일 시퀀스)

| 항목 | 정책 |
|---|---|
| **트라이얼 형식** | **7-day free trial** (시간 기반) |
| **트라이얼 중 기능** | Pro 티어 수준 기능 사용 가능 (자사 1, 경쟁사 1, Custom 재분석 일부 허용, 3 시트) |
| **카드 등록** | 트라이얼 시 ❌, **첫 유료 결제 시점**에 등록 |

#### 트라이얼 만료 후 이메일 시퀀스

| 시점 | 액션 | 메시지 예시 |
|---|---|---|
| **Day 7 (만료 직후)** | 1차 이메일 — 즉시 전환 인센티브 | "지금 가입 시 첫 달 30% 할인 (3일 한정)" |
| **Day 30** | 2차 이메일 — 재참여 유도 | "잊으셨나요? 다시 시작하면 첫 달 50% 할인" |
| **Day 90** | 3차 이메일 — **최종 제안** | "마지막 기회: 첫 3개월 50% 할인 + 1:1 데모 제공" |
| **Day 90+** | 시퀀스 종료 | 마케팅 동의자만 일반 뉴스레터로 전환 |

> **재트라이얼**: ❌ (만료 후 추가 트라이얼 ❌, 단 위 시퀀스의 최종 제안에 한정)

### 7-6. 결제 / 할인 정책 (확정)

| 항목 | 정책 |
|---|---|
| **연간 할인** | **모든 티어 15% 할인** (시작 표준). **시즌별 적극적 할인은 쿠폰 시스템으로 운용** |
| **연간 약정 (Enterprise)** | 필수 (annual commit) — 중도 해지 시 잔여 12개월 정산 |
| **쿠폰 시스템** | Section 12의 일반/블라인드 쿠폰 + 시즌 캠페인 (블랙프라이데이, 사이버먼데이, 신규 가입 등). **연간 할인과 중복 적용 ❌** |
| **결제 통화** | USD 단일 (한국 사용자도 USD 결제) |
| **결제 수단** | Stripe (Visa, MC, Amex, UnionPay), Enterprise는 wire transfer 가능 |
| **환불 정책** | 월간: 7일 이내 미사용 시 가능. 연간: 30일 이내 환불, 이후 prorated. Enterprise: 계약별 협의 |

### 7-7. 스펙 변경 사항 (확정)

| 항목 | 결정 | 근거 / 영향 |
|---|---|---|
| **모니터링 빈도** | 모든 티어 **월 1회** | AEO는 daily 변화 미미. **월 1회 자동 + Custom 재분석 차등**으로 가치 차별 — API 비용 75~80% 절감, 사이트당 월 ~$0.10 |
| **경쟁사 대비 데이터 비교** | **핵심 세일즈 포인트**로 강화 (Pro부터 진입) | UX/대시보드 디자인에서 "경쟁사 비교 뷰" 우선 노출 필수 |
| **Q&A 무제한** | Rate limit (시간당 10회 등 abuse 방지)만 적용 | CS 비용 절감 효과, 고객 만족도 직결 항목 |
| **온보딩** | **Self-serve 티어 셀프**, **Enterprise만 white-glove** | CS 인력 절감 + Enterprise churn 방지 |
| **SEO 지수 분석** | **Phase 2로 보류** | AEO 전문성 집중 — Ahrefs와 정면 경쟁 회피, "AEO 전용 도구" 포지셔닝 강화 |

### 7-8. 가격 정책 한 장 요약

| 구분 | Free | Basic | Pro | Business | Enterprise |
|---|---|---|---|---|---|
| **가격** | $0 | **$19.99** | **$79.99** | **$299.99** | **$1,499.99** |
| **연간 (월 환산, 15% 할인)** | — | $16.99 | $67.99 | $254.99 | $1,274.99 |
| **자사 사이트** | 1회 | 1 | 3 | 5 | 무제한 |
| **경쟁사 사이트** | — | — | 1/site 옵션 | 3/site 옵션 | 자사 + 5 |
| **기본 AI 엔진** | 3 | 3 | 3 | 3 | 10+ (전부) |
| **모니터링 빈도** | 1회 | 월 1회 | 월 1회 | 월 1회 | 월 1회 |
| **Custom 재분석/월** | 0 | 5 | 30 | 100 | 무제한 |
| **시트 기본** | 1 | 1 | 3 | 5 | 20 |
| **시트 추가** | — | $2.99/u | $2.99/u | $2.99/u | 협의 |
| **사이트 추가 (자사)** | — | $9.99 | $9.99 | $9.99 | 협의 |
| **사이트 추가 (경쟁사)** | — | — | $39.99 | $39.99 | 협의 |
| **AI 엔진 추가** | — | $19.99 | $19.99 | $19.99 | 포함 |
| **PDF 브랜딩** | — | $19.99 (1회) | $19.99 | $19.99 | 무료 |
| **Looker Studio** | — | ❌ | $19.99/월 | $19.99/월 | 포함 |
| **API / SSO** | — | — | API add-on | API add-on | 기본 포함 |
| **Q&A** | rate limit | 무제한 | 무제한 | 무제한 | 무제한 |
| **온보딩** | — | 셀프 | 셀프 | 셀프 | White-glove |

### 7-9. 가격 시뮬레이션 (대표 사용 케이스)

| # | 케이스 | 티어 | Add-on | 월 청구액 |
|---|---|---|---|---|
| 1 | 1인 솔로 마케터 | Basic | — | **$19.99** |
| 2 | 1인 + Custom 재분석 5회 추가 | Basic | Basic Pack | $19.99 + $4.99 = **$24.98** |
| 3 | 1인 + AI 엔진 3개 추가 | Basic | +3 engines | $19.99 + $59.97 = **$79.96** ⚠️ Pro $79.99와 동가 → **Pro 전환 유도** |
| 4 | 3인 팀 (자사 사이트 3개) | Pro | — | **$79.99** (3 시트 기본 포함) |
| 5 | 3인 팀 + 경쟁사 1건 추가 | Pro | +1 경쟁사 site | $79.99 + $39.99 = **$119.98** |
| 6 | 5인 팀 + 경쟁사 1건 + AI 엔진 2개 | Pro | +2 seats, +1 경쟁사, +2 engines | $79.99 + $5.98 + $39.99 + $39.98 = **$165.94** |
| 7 | 5인 팀 + 경쟁사 3건 추가 | Pro | +2 seats, +3 경쟁사 | $79.99 + $5.98 + $119.97 = **$205.94** ⚠️ Business($299.99) 향한 path |
| 8 | 5인 팀 + 경쟁사 5건 추가 | Pro | +2 seats, +5 경쟁사 | $79.99 + $5.98 + $199.95 = **$285.92** ⚠️ **Business($299.99)와 거의 동가 → Business 업셀 유리** ⭐ |
| 9 | 7인 팀, 5 사이트, 경쟁사 심층 + 산업 벤치마크 | Business | +2 seats | $299.99 + $5.98 = **$305.97** |
| 10 | 글로벌 팀, 모든 AI 엔진, 20 시트, SSO 필요 | Enterprise | — | **$1,499.99** (연간 $1,274.99/월) |

> **업셀 메커니즘 검증**:
> - 케이스 3: AI 엔진 3개 추가 → Pro 가격 도달 → **Basic→Pro 업셀 트리거** ✅
> - 케이스 7: 경쟁사 3건 추가 시 $205.94 → 아직 Pro가 유리하나 4건 임계점 근접
> - 케이스 8: 경쟁사 5건 추가 시 $285.92 → **Business($299.99)와 $14 차이 → 업셀 명확** ✅

### 7-10. 가격 전략의 시장 포지셔닝

```
  ~$30        ~$50~$130        ~$300        ~$1,500
   │           │                 │            │
   ▼           ▼                 ▼            ▼
 v2 Basic    v2 Pro           v2 Business   v2 Enterprise
 ($19.99)    ($79.99)         ($299.99)     ($1,499.99)
   │           │                 │            │
 vs           vs                vs            vs
 RankScale    HubSpot ($50)    AthenaHQ      Ahrefs
 $22         Profound          Self-Serve    Enterprise
 Otterly     Starter ($99)     ($295)        $1,499
 Lite $29    Ahrefs Lite       Profound      (v2 = 동가
 Ahrefs      ($129)            Growth $399    + 한국어/CS
 Starter $29 (v2 = 시장        (v2가 25%      차별화)
             빈 구간 진입)     저렴)

 ◄── 핵심 차별화: 한국어 + 다국어 + 시장 최저가 시트 ($2.99) ──►
 ◄── Pro = "Profound 미만, HubSpot 위" 시장 빈 구간 독자 점유 ──►
 ◄── Business = AthenaHQ와 동가 — 한국어 + 산업 벤치마크 차별화 ──►
 ◄── Enterprise = Ahrefs Enterprise와 동가 — 한국어/Dedicated CS 우위 ──►
```

### 7-11. 다음 액션 (To-Do)

| 항목 | 담당 | 비고 |
|---|---|---|
| ① v2_SPEC.md "Section 1. 요금제 플랜" 본 표로 교체 | 다음 세션 | 4-tier 구조로 단순화 (이전 5-tier 안 폐기) |
| ② Stripe Product/Price 등록 | 개발 | 4 main + Enterprise + add-on 약 12개 SKU 생성 (이전 안 대비 추가 단순화) |
| ③ 가격 페이지 UI 디자인 | 디자인 | 4-tier 노출, **"Pro = most popular"** 강조, Business = "산업 벤치마크 차별화", Enterprise는 "Talk to sales" |
| ④ 한국 시장 마케팅 메시지 | 마케팅 | "Ahrefs와 동가에 한국어 AEO + Dedicated CS" (Enterprise), "$19.99로 시작하는 글로벌 AEO" (Basic), "Profound보다 합리적, HubSpot보다 강력" (Pro) |
| ⑤ Custom 재분석 add-on UI/UX | 디자인+개발 | 2종 패키지 (Basic Pack/Pro Pack) + PAYG 옵션 |
| ⑥ Enterprise 영업 자료 (deck) | 영업 | $1,499.99 = Ahrefs Enterprise와 동가 — 한국어/다국어/Dedicated CS 차별점 강조 |
| ⑦ 트라이얼 7+30+90일 이메일 시퀀스 작성 | 마케팅 | 3개 이메일 카피 + Resend 자동화 설정 |
| ⑧ Basic 후킹 가격 마케팅 캠페인 설계 | 마케팅 | "한정 기간 37% 할인" 메시지 — 정상가/할인가 표시 방식, 캠페인 종료일 정책 등 |
| ⑨ AI 엔진 $19.99 인상에 따른 자동 업셀 트리거 설계 | 제품 | Basic 사용자가 엔진 2~3개 추가 시 "Pro로 업그레이드 시 절약" 알림 |

---

## 8. 부록 A — 출처

| 서비스 | URL | 확인일 |
|---|---|---|
| Profound | [tryprofound.com/pricing](https://www.tryprofound.com/pricing) | 2026-05-02 |
| Peec AI | [peec.ai/pricing](https://peec.ai/pricing) | 2026-05-02 |
| AthenaHQ | [athenahq.ai/plans](https://www.athenahq.ai/pricing) | 2026-05-02 |
| Otterly.ai | [otterly.ai/pricing](https://otterly.ai/pricing) | 2026-05-02 |
| Scrunch AI | [scrunch.com/pricing](https://scrunch.com/pricing/) | 2026-05-02 |
| **Ahrefs (Brand Radar 포함)** | [ahrefs.com/pricing](https://ahrefs.com/pricing) | 2026-05-02 |
| HubSpot AEO | [hubspot.com/products/aeo](https://www.hubspot.com/products/aeo) | 2026-05-02 (보조) |
| Goodie AI | [pikaseo.com/articles/goodie-ai-review](https://pikaseo.com/articles/goodie-ai-review) | 2026-05-02 (보조) |
| RankScale | [getairefs.com/blog/3-aeo-tools-under-50/](https://getairefs.com/blog/3-aeo-tools-under-50/) | 2026-05-02 (보조) |

### 보조 출처

- [10 Best AEO Tools in 2026 — xseek.io](https://www.xseek.io/blogs/articles/10-best-aeo-tools-in-2026-answer-engine-optimization-platforms-ranked)
- [Top 5 AEO Tools 2026 — Meltwater](https://www.meltwater.com/en/blog/best-answer-engine-optimization-tools)
- [Profound vs Peec vs Otterly — Discovered Labs](https://discoveredlabs.com/blog/profound-vs-peec-vs-otterly-which-ai-visibility-platform-should-you-buy)
- [Most Affordable AEO Tools — LLM Pulse](https://llmpulse.ai/blog/most-affordable-aeo-tools/)
- [3 AEO Tools Under $50 — Airefs](https://getairefs.com/blog/3-aeo-tools-under-50/)
- [Ahrefs Brand Radar Review (2026) — EWR Digital](https://www.ewrdigital.com/blog/ahrefs-brand-radar-review-alternatives-pricing-comparison/)
- [Ahrefs Brand Radar Review (2026) — Connor Kimball](https://connorkimball.com/blog/ahrefs-brand-radar-review-pricing-competitor-comparison/)
- [Ahrefs Brand Radar Review — Profound 블로그 (경쟁사 분석)](https://www.tryprofound.com/blog/ahrefs-brand-radar-review)
- [Ahrefs Pricing Change 2026 — AEO Engine Blog](https://aeoengine.ai/blog/ahrefs-pricing-change)

---

## 9. 부록 B — 본 리포트의 한계

| 한계 | 설명 |
|---|---|
| Profound 가격 변동 | 외부 자료에 따르면 과거 Lite $499였으나 현재 $99 Starter — **시장 가격 인하 추세** 진행 중. 6개월마다 재조사 권장. |
| HubSpot AEO 가격 정확성 | 보조 자료에서 $50 인용. 공식 페이지 직접 확인 필요. |
| Bluefish AI / 일부 신생 서비스 | 가격이 비공개(quote-only)인 서비스 다수 — 본 리포트 미포함. |
| 한국 시장 | 한국어 전용 AEO 도구는 본 조사 시점에 사실상 부재 — **블루오션 가능성** 시사. |
| Currency / VAT | 모든 가격 USD 기준. 유럽 가격(€)은 환율 변동 영향. |

---

*최종 업데이트: 2026-05-02 (**v3.1 — 경쟁사 사이트 단가 $14.99 → $39.99 인상 + AI 엔진 마케팅 표현 정정**)*
*다음 단계: Section 7-11의 To-Do 항목 — v2_SPEC.md 갱신, Stripe Product 등록, UI 디자인, 트라이얼 시퀀스 카피, Basic 후킹 마케팅 등*
