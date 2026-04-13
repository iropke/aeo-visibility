# AEO Visibility 배포 가이드

## 아키텍처 개요

```
[사용자] → [Vercel/Frontend] → [Railway/Backend API] → [Supabase/DB]
                                        ↕
                                [Upstash/Redis Cache]
```

> Celery Worker 없이 FastAPI BackgroundTasks로 비동기 분석을 처리합니다.
> Railway 서비스 1개만 필요합니다.

---

## 순서: Supabase → Upstash → Railway → Vercel → GitHub

---

## 1. Supabase 설정 (DB)

### 1-1. 테이블 생성
1. [Supabase 대시보드](https://supabase.com/dashboard) 로그인
2. 프로젝트 선택 → **SQL Editor** 클릭
3. `supabase/001_initial_schema.sql` 내용 복사 → 실행

### 1-2. 연결 정보 확인
- **Settings → Configuration → Database** → Connection string (URI) 복사
  - `postgresql+asyncpg://` 로 시작하도록 프로토콜 수정
- **Settings → API** → Project URL, anon key, service_role key 복사

### 1-3. GitHub 연동으로 DB 자동 업데이트
스키마를 변경할 때마다:
1. `backend/alembic/versions/` 에 새 마이그레이션 파일 추가
2. `git push origin main`
3. GitHub Actions가 자동으로 `alembic upgrade head` 실행 → DB 업데이트

---

## 2. Upstash 설정 (Redis — 캐싱 전용)

1. [Upstash 콘솔](https://console.upstash.com) 로그인
2. **Create Database** → Region: 가까운 리전 선택 (예: ap-northeast-1)
3. **TLS(SSL) 활성화** 확인
4. 연결 문자열 복사 (`rediss://default:...@...upstash.io:6379`)

> Celery를 제거했으므로 Redis는 캐싱에만 사용됩니다.
> 무료 플랜으로도 충분합니다.

---

## 3. Railway 설정 (Backend — 단일 서비스)

1. [Railway](https://railway.app) → **New Project** → **Deploy from GitHub repo**
2. GitHub 리포지토리 연결
3. **Root Directory**: `backend` 설정
4. **Settings → Environment Variables** 추가:
   ```
   DATABASE_URL=postgresql+asyncpg://...
   SUPABASE_URL=https://...
   SUPABASE_ANON_KEY=...
   SUPABASE_SERVICE_ROLE_KEY=...
   REDIS_URL=rediss://...
   CLAUDE_API_KEY=sk-ant-...
   FRONTEND_URL=https://aeo-visibility.vercel.app
   CORS_ORIGINS=https://aeo-visibility.vercel.app
   ENV=production
   ```
5. 배포 후 발급된 URL 확인 (예: `https://xxx.up.railway.app`)

> Worker 서비스가 불필요합니다. 단일 서비스만 운영하면 됩니다.

---

## 4. Vercel 설정 (Frontend)

1. [Vercel](https://vercel.com) → **Add New Project** → GitHub 리포 연결
2. **Framework Preset**: Next.js (자동 감지됨)
3. **Root Directory**: `frontend`
4. **Environment Variables** 추가:
   ```
   NEXT_PUBLIC_API_URL=https://xxx.up.railway.app
   ```
   (Railway에서 발급받은 백엔드 URL)
5. 배포 → 완료 후 URL 확인

### 4-1. Railway에 Vercel URL 업데이트
Vercel 배포 URL이 확정되면 Railway에서:
```
FRONTEND_URL=https://your-app.vercel.app
CORS_ORIGINS=https://your-app.vercel.app
```
를 업데이트합니다.

---

## 5. GitHub 설정

### 5-1. 리포지토리 생성
```bash
cd aeo-visibility
git init
git add .
git commit -m "Initial commit: AEO Visibility SaaS"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/aeo-visibility.git
git push -u origin main
```

### 5-2. GitHub Secrets 설정 (CI/CD용)
**Settings → Secrets and variables → Actions → New repository secret**

| Secret Name | 값 |
|---|---|
| `DATABASE_URL` | Supabase 연결 문자열 |
| `SUPABASE_URL` | Supabase 프로젝트 URL |
| `SUPABASE_ANON_KEY` | Supabase anon key |
| `SUPABASE_SERVICE_ROLE_KEY` | Supabase service role key |
| `REDIS_URL` | Upstash 연결 문자열 |
| `CLAUDE_API_KEY` | Claude API 키 |
| `NEXT_PUBLIC_API_URL` | Railway 백엔드 URL |

### 5-3. 자동 배포 흐름
```
git push origin main
  ├→ GitHub Actions: 린트 → 빌드 검증 → DB 마이그레이션
  ├→ Railway: 자동 감지 → 백엔드 재배포
  └→ Vercel: 자동 감지 → 프론트엔드 재배포
```

---

## 트러블슈팅

### DB 마이그레이션 실패
- GitHub Actions 로그에서 에러 확인
- Supabase 대시보드 → SQL Editor에서 수동 실행 가능

### CORS 에러
- Railway의 `CORS_ORIGINS`에 Vercel URL이 정확히 포함되어 있는지 확인
- `https://` 포함, 끝에 `/` 없이

### 분석이 시작되지 않음
- Railway 로그에서 에러 확인
- `CLAUDE_API_KEY`가 유효한지 확인
- Upstash Redis 연결 문자열이 `rediss://` (SSL)인지 확인

### 502 Bad Gateway
- Railway 헬스체크 경로가 `/api/health`인지 확인
- PORT 환경변수를 Railway가 자동 주입하므로 수동 설정 불필요
