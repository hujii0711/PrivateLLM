# 배포 계획 00 — 개요 및 공통 (Production Release: Overview & Common)

> 작성일: 2026-06-05
> 대상 서비스: 주택임대차 **보증금 반환 상담 챗봇** (privateLLM)
> 목표 성숙도: **정식 운영 서비스** / 규모: **중규모(수백 명, 동시 수십)** / 로깅: **전체 로깅 + 감사 + PII 처리**
> 본 문서는 세 배포 환경([01 온프렘 Mac](01-onprem-mac.md) / [02 Linux GPU](02-linux-gpu.md) / [03 AWS 클라우드](03-aws-cloud.md))에 **공통**으로 적용되는 아키텍처·결정·운영 하드닝을 정의한다. 각 환경 문서는 인프라 차이만 다루고 본 문서를 참조한다.

---

## 1. 현재 상태(PoC)와 운영 격차

### 1.1 지금 가진 것 (연구 PoC 완료, main 병합)

| 구성요소 | 구현 | 위치 |
|---|---|---|
| 데이터 파이프라인 | 주택임대차보호법·민법·판례 → 1264 청크 → Chroma `jeonse_deposit` | `pipelines/` |
| RAG 코어 | bge-m3(1024-dim cosine) 검색 + 근거판정 + 프롬프트 + 인용정리 | `packages/rag/` |
| 추론 백엔드 | Qwen2.5-7B-Instruct-4bit (MLX, Apple Silicon 전용) | `apps/api/src/api/llm.py` |
| API | FastAPI `POST /chat`(SSE) · `GET /health` | `apps/api/` |
| 프론트엔드 | Next.js 16 채팅 UI(SSE 스트리밍) | `apps/web/` |
| 평가/FT | 평가 하니스 + QLoRA A/B (음성 결과) | `packages/eval`,`ftdata`,`finetune` |

핵심 도메인 안전장치는 이미 구현돼 있다: **면책고지 결정적 append**(`pipeline.py:_ensure_disclaimer`), **근거 부족 시 거절**(`NO_GROUNDING_MSG`, `min_similarity=0.35`), **환각 인용 제거**(`strip_invalid_citations`).

### 1.2 운영 전환을 막는 격차 (PoC → 정식 서비스)

`memory/privatellm-project-status.md`의 "미보완" 항목 + 정식 운영 요건을 종합한 격차:

1. **인증/인가 없음** — 누구나 `/chat` 호출 가능.
2. **CORS·API base 하드코딩** — `main.py`는 `allow_origins=["http://localhost:3000"]`, `chatClient.ts`는 `NEXT_PUBLIC_API_BASE ?? "http://localhost:8000"`.
3. **SSE 오류 채널 없음** — LLM 예외 시 제너레이터가 죽어 **잘린 스트림**만 전달(프론트는 `done`을 영원히 못 받음).
4. **동시성 모델 부재** — 7B 생성은 사실상 직렬. 동시 수십 요청 시 큐/타임아웃/백프레셔 없음.
5. **감사/PII 정책 없음** — 질의·답변 저장소, PII 마스킹, 보관기간, 접근통제 미구현(법률 도메인 필수).
6. **관측성 없음** — 메트릭/구조적 로그/알림/대시보드 없음.
7. **상태 영속/백업 없음** — Chroma 인덱스·모델 가중치·감사로그의 백업·복구·재색인 운영 절차 부재.
8. **CI/CD 없음** — 테스트는 있으나(파이썬 pytest·웹 vitest) 자동 빌드·배포 파이프라인 없음.
9. **소스 중복·abort 미처리** — 같은 판례 2회 검색 시 dedup 없음, 스트림 중단 미지원.

본 계획은 위 9개를 모두 닫는다. 1~3·9는 환경 무관 **앱 코드 변경**(§6), 4~8은 **공통 운영 하드닝**(§5) + 환경별 인프라.

---

## 2. 목표 아키텍처 (논리)

```
                         ┌─────────────────────────────────────────────┐
   사용자(사내 수백 명) ──TLS──▶ │  Reverse Proxy / LB (TLS 종단, 라우팅)        │
                         └───────────────┬───────────────┬─────────────┘
                                         │               │
                              정적/SSR   │               │  /api, /chat(SSE)
                                ┌────────▼───────┐  ┌─────▼──────────────────────┐
                                │ Web (Next.js)  │  │ API (FastAPI, 무상태, N replica) │
                                │  prod build    │  │  - 인증 미들웨어(OIDC 검증)        │
                                └────────────────┘  │  - 레이트리밋 / 타임아웃             │
                                                     │  - run_chat 오케스트레이션          │
                                                     │  - 감사 로깅 + PII 마스킹           │
                                                     └───┬───────────┬────────────┬───┘
                                                         │ 검색       │ 생성        │ 감사
                                              ┌──────────▼──┐  ┌──────▼──────┐  ┌──▼────────┐
                                              │ RAG/Embedder│  │ LLM 백엔드    │  │ 감사 DB     │
                                              │ + Chroma    │  │ (환경별 교체)  │  │ (Postgres) │
                                              │ (영속·백업)  │  │ MLX | vLLM   │  │ (PII 마스킹)│
                                              └─────────────┘  └─────────────┘  └───────────┘
                                                         observability: 메트릭/로그/트레이스/알림
```

**무상태 API**가 핵심: API replica는 상태를 갖지 않고, 상태는 ① Chroma(벡터) ② LLM 백엔드(외부 프로세스/서버) ③ 감사 DB로 외부화한다. 이로써 모든 환경에서 API를 수평 확장할 수 있다(Mac은 제약 있음 — [01](01-onprem-mac.md) §동시성 참조).

---

## 3. 횡단 결정 (Cross-cutting Decisions)

### D1. 운영 모델 = **순수 RAG 베이스라인** (QLoRA 어댑터 미적용)

- 근거: A/B 최종 결과(`docs/superpowers/notes/ab-result.md`)에서 소규모 자기-distillation QLoRA는 강한 RAG 베이스라인을 **개선하지 못하고 소폭 하락**(groundedness/mention_coverage −0.031). 인용·면책·구조는 이미 프롬프트+파이프라인이 결정적으로 보장.
- 결정: 프로덕션은 **base Qwen2.5-7B-Instruct + 강화 프롬프트 + temp 0.2**로 서빙. 어댑터 경로(`MlxLLM(adapter_path=)`, `--adapter`)는 **config 옵션으로만 유지**하여 향후 강한 teacher(32B)·실데이터 재실험 여지를 남긴다.
- 영향: 모델 아티팩트 = base 4bit/GGUF/FP16 가중치 1종. 어댑터 학습 인프라는 운영 경로에서 제외.

### D2. **LLM 백엔드 추상화 스왑** — 세 배포를 하나의 코드베이스로

`apps/api/src/api/llm.py`에 이미 `LLM` Protocol(`stream(messages, *, max_tokens, temperature) -> Iterator[str]`)이 존재. 환경별로 **구현 1개만 교체**:

| 환경 | LLM 구현 | 백엔드 |
|---|---|---|
| Mac | `MlxLLM` (기존) | in-process MLX, Metal |
| Linux GPU / AWS | `OpenAICompatLLM` (신규) | 별도 vLLM 서버의 OpenAI 호환 `/v1/chat/completions` (stream) |

- `Settings`에 `llm_backend: "mlx" | "openai"` 추가, `from_env`로 분기. 앱의 나머지(`pipeline.run_chat`, API, 프론트)는 **완전히 동일**.
- 효과: 배포 환경이 달라도 검색·프롬프트·인용·면책·감사 경로가 100% 동일 → 평가셋으로 검증한 품질이 그대로 이전.

### D3. 무상태 API + 상태 외부화

- API 컨테이너/프로세스는 디스크 상태를 갖지 않음. Chroma는 영속 볼륨/별도 서비스, 감사는 Postgres, 모델은 외부 서버 또는 캐시 볼륨.
- 효과: 무중단 배포(롤링), 수평 확장, 장애 복구가 모든 환경에서 동일 패턴.

---

## 4. 환경 비교 요약

| 항목 | 01 온프렘 Mac | 02 Linux GPU | 03 AWS 클라우드 |
|---|---|---|---|
| 추론 백엔드 | MLX(in-proc) | vLLM(연속 배칭) | vLLM on EC2 g5 / (대안 SageMaker) |
| 동시성 흡수 | 멀티 워커+큐(약함) | vLLM 배칭(강함) | vLLM 배칭 + ASG |
| 컨테이너화 | ❌ 모델은 네이티브(Metal) | ✅ Docker+NVIDIA | ✅ ECR/EKS or compose |
| 수평 확장 | 노드 추가(수동, 어려움) | replica/k8s HPA | ASG 자동 |
| 데이터 상주 | 사내(최강 프라이버시) | 사내 | VPC 내(컴플라이언스 검토) |
| 초기 비용 | Mac 하드웨어 1회성 | GPU 서버 1회성 | 낮음(종량, 그러나 GPU 시간당 과금) |
| 운영 부담 | Mac 서버운영 미성숙 | 표준 리눅스/GPU 운영 | 관리형으로 경감 |
| **권장 시나리오** | 데이터 절대 외부 불가·기존 코드 즉시 활용 | **균형점(권장)**: 표준운영+처리량+온프렘 | 탄력 확장·빠른 구축·자체 데이터센터 없음 |

---

## 5. 공통 운영 하드닝 (모든 환경 필수)

각 항목은 **무엇을·왜·어떻게(구현 위치)** 순으로. 환경별 구체 도구는 각 문서에서 확정.

### 5.1 구성/시크릿 관리
- 모든 환경 설정을 **환경변수**로 외부화: `MLX_MODEL`/`LLM_BACKEND`/`OPENAI_BASE_URL`/`CHROMA_DIR`/`CORS_ORIGINS`/`OIDC_ISSUER`/`AUDIT_DB_URL` 등. `Settings.from_env`·`RagConfig.from_env` 확장(§6).
- 시크릿(DB 비밀번호, OIDC client secret)은 코드/이미지에 넣지 않음 → 환경별 시크릿 저장소(Mac: `.env`+파일권한 600 / Linux: Docker secret·SOPS / AWS: Secrets Manager).
- 12-factor: 빌드 산출물(이미지)은 환경 무관, 설정만 주입.

### 5.2 인증/인가 (AuthN/AuthZ)
- 정식 운영 + 사내 수백 명 → **기업 SSO/OIDC**(예: Keycloak, Azure AD, Okta) 연동.
- 패턴: 프론트가 OIDC 로그인 → access token(JWT) 획득 → `/chat` 호출 시 `Authorization: Bearer`. API에 **JWT 검증 미들웨어**(issuer·audience·exp·서명(JWKS)) 추가. 미인증 401.
- 인가: 최소 "인증된 사내 사용자" 단일 롤. 감사 로그용 `sub`(사용자 식별자) 추출. 관리/감사 조회는 별도 admin 롤.
- 대안(환경 위임): API 앞단 게이트웨이(oauth2-proxy / ALB+Cognito / API Gateway authorizer)에서 인증 종단 → API는 신뢰 헤더만 검증. AWS는 이 방식 권장([03](03-aws-cloud.md)).

### 5.3 TLS / 리버스 프록시
- 외부 노출 지점은 **항상 HTTPS**. 리버스 프록시가 TLS 종단 + 라우팅(`/` → web, `/api`·`/chat` → API) + 타임아웃/버퍼링 제어.
- **SSE 주의**: 프록시에서 응답 버퍼링을 끄고(`X-Accel-Buffering: no`, nginx `proxy_buffering off`) 읽기 타임아웃을 생성 최대시간 이상으로(예: 120s) 설정해야 토큰 스트리밍이 끊기지 않음.
- 환경별: Mac=Caddy(자동 TLS) / Linux=nginx·Traefik / AWS=ALB+ACM.

### 5.4 로깅·감사·PII (법률 도메인 — 심층)

**전체 로깅 + 감사** 요구. 두 계층을 분리한다:

1. **운영 로그(structured JSON)**: 요청ID·사용자sub·지연(검색/생성/총)·토큰수·검색 hit 수·grounded 여부·HTTP 상태·오류. **질의 원문·답변 본문은 운영 로그에 넣지 않음**(PII 누출 방지) → 감사 저장소로 분리.
2. **감사 저장소(Postgres, append-only)**: 상담 1건 = 1 레코드. 컬럼: `id, ts, user_sub, query_masked, answer, sources(jsonb), grounded(bool), latency_ms, model_id, prompt_version`. 품질개선·감사·민원대응 용도.

**PII 처리 정책**:
- **수집 단계 마스킹**: 저장 직전 `query`에 정규식 마스킹 적용 — 주민등록번호(`\d{6}-?\d{7}`), 휴대전화(`01[016-9]-?\d{3,4}-?\d{4}`), 계좌/카드 번호, 이메일. 마스킹된 `query_masked`를 저장(원문 비저장이 기본). 답변 본문은 법령·판례 기반이라 PII 위험 낮으나 동일 마스킹 통과.
- **접근통제**: 감사 DB는 admin 롤만 조회. 네트워크 격리(같은 VPC/서브넷, 외부 비공개). 조회 행위 자체도 로깅.
- **보관기간/파기**: 기본 **180일 후 자동 파기**(배치 삭제 잡). 분쟁 보존 필요 시 예외 플래그. 보관기간은 사내 개인정보 방침에 맞춰 운영 전 확정.
- **고지**: 첫 화면에 "상담 내용이 품질개선·감사 목적으로 저장될 수 있음" 고지 + 기존 면책고지 유지.
- 구현: API에 `audit.record(...)`를 `run_chat` 완료(`done` 이벤트) 시 호출. 마스킹 유틸은 `packages/rag` 또는 신규 `packages/common`에 두고 단위 테스트.

### 5.5 관측성 (Observability)
- **메트릭(Prometheus)**: 요청수/상태별, 지연 히스토그램(p50/p95/p99: 검색·첫토큰(TTFT)·총생성), 동시 진행 요청 수, 큐 대기시간, LLM 토큰/초, grounded 비율, 오류율. FastAPI는 `prometheus-fastapi-instrumentator` + LLM 백엔드 자체 메트릭(vLLM은 `/metrics` 노출).
- **로그 집계**: 구조적 JSON → 환경별 수집(Mac: 파일+Vector/Loki / Linux: Loki·ELK / AWS: CloudWatch). 요청ID로 상관.
- **대시보드/알림(Grafana)**: 지연 SLO·오류율·GPU/메모리 사용률 대시보드. 알림: p95 지연 임계 초과, 오류율 급증, 백엔드 헬스 실패, 디스크/메모리 고갈, 감사 DB 적재 실패.
- **헬스/레디니스**: `/health`(liveness)에 더해 `/ready`(Chroma 연결·LLM 백엔드 reachable 확인) 추가. LB는 `/ready`로 트래픽 투입 판단.

### 5.6 벡터 스토어 수명주기 (Chroma)
- **영속화**: `CHROMA_DIR`를 영속 볼륨에. PoC의 `data/chroma`는 gitignore 재생성 산출물 → 운영은 **재현 가능한 색인 빌드**가 원천.
- **재색인 파이프라인**: `pipelines/`의 `build_index`를 운영 잡으로. 코퍼스(법령/판례/해설/상담사례) 갱신 → 빌드 → **새 컬렉션 버전**(`jeonse_deposit_vN`)으로 생성 → 평가셋 recall 회귀 통과 시 별칭 전환(블루/그린 색인). 인덱싱·질의 임베딩은 **동일 bge-m3 1024-dim cosine** 필수(불일치 시 검색 붕괴).
- **백업**: Chroma 디렉터리 스냅샷(또는 빌드 산출물 + 원천 코퍼스)을 정기 백업. 복구 = 백업 복원 또는 파이프라인 재실행.
- **규모**: 1264 청크는 소규모 → 단일 Chroma(영속 파일/단일 서비스)로 충분. 코퍼스 대폭 확장 시 Chroma 서버 모드/대체(pgvector·Qdrant) 검토(현 단계 불필요, YAGNI).
- **임베더 서빙**: bge-m3는 API 프로세스 내 로드(검색 질의 임베딩). Mac=MPS·CPU, Linux/AWS=GPU 공유 또는 CPU. 모델 캐시 볼륨 필요.

### 5.7 모델 아티팩트 관리
- 버전 **고정**(모델 리비전 pin). 환경별 형식: Mac=MLX 4bit(`mlx-community/Qwen2.5-7B-Instruct-4bit`), Linux/AWS=vLLM용 FP16 또는 AWQ/GPTQ 4bit.
- 저장/캐시: 런타임마다 HF 허브 다운로드 금지 → **사전 동기화된 캐시 볼륨/오브젝트 스토어**(AWS S3)에서 로드. 폐쇄망이면 내부 미러.

### 5.8 동시성·큐·타임아웃·백프레셔
- 7B 생성은 비용 큼. 무한 동시성 금지: **최대 동시 생성 수 제한 + 대기 큐 + 큐 타임아웃 + 생성 타임아웃**.
- 환경별: vLLM(Linux/AWS)은 **연속 배칭**으로 동시 수십을 한 GPU가 효율 흡수 → API는 동시 상한만 관리. MLX(Mac)는 단일 스트림 → **N개 워커 프로세스(각 모델 사본) + 프론트 큐**로 의사 병렬, 메모리가 상한([01](01-onprem-mac.md)).
- API는 요청별 타임아웃·취소(클라이언트 disconnect 시 생성 중단, abort) 처리.

### 5.9 레이트리밋·남용 방지
- 사용자별/IP별 레이트리밋(예: 분당 N요청, 동시 1스트림). 게이트웨이 또는 API 미들웨어(`slowapi`)에서.
- 입력 길이 상한(현 `min_length=1`만 있음 → `max_length` 추가), 프롬프트 인젝션 완화는 RAG 구조상 영향 제한적이나 입력 정화 권장.

### 5.10 신뢰성 (Reliability)
- **SSE 오류 이벤트**: `ChatEvent`에 `{"type":"error","message":...}` 추가. `run_chat`/`event_gen`을 try/except로 감싸 LLM·검색 예외 시 error 이벤트 전송 후 정상 종료. 프론트(`lib/sse`,`hooks/useChat`)도 error 처리·재시도 UI. (격차 #3 해소)
- LLM 백엔드 호출 **재시도(지수 백오프)+서킷브레이커**(특히 `OpenAICompatLLM`의 HTTP 호출). 백엔드 다운 시 사용자에 "일시적 오류" 안내.
- **그레이스풀 셧다운**: 진행 중 스트림 마무리 후 종료(롤링 배포 무중단). uvicorn graceful timeout 설정.
- 소스 dedup(같은 ref 중복 제거)·`SourceOut` 연결(격차 #9).

### 5.11 프론트엔드 프로덕션
- `next build` 프로덕션 빌드. `NEXT_PUBLIC_API_BASE`를 배포 도메인으로 주입(빌드/런타임 env). 동일 출처 역프록시면 상대경로(`/api`)로 단순화 권장 → CORS 불필요.
- 보안 헤더(CSP·HSTS·X-Frame-Options)는 프록시/Next에서. 정적 자산 캐시/압축.

### 5.12 CI/CD·테스트
- 파이프라인: 푸시 → **테스트**(파이썬 `cd packages/rag && uv run pytest`·`apps/api` fast·웹 `npm run test`, 주의: 루트 `--package rag pytest`는 pipelines까지 수집) → **빌드**(이미지 또는 산출물) → **스테이징 배포** → **평가 회귀**(평가셋 recall/citation/disclaimer 임계 통과) → **프로덕션 배포(롤링)**.
- 모델/인덱스 변경은 평가 게이트 필수: recall@k·citation_rate·disclaimer_rate가 베이스라인(0.81 / 1.0 / 1.0) 이하로 떨어지면 차단.
- IaC·구성은 버전관리. 시크릿 제외.

---

## 6. 필요한 앱 코드 변경 (환경 무관, 선행 작업)

세 배포 모두의 전제. **별도 구현 계획(writing-plans)으로 진행 권장.**

| # | 변경 | 파일 | 비고 |
|---|---|---|---|
| C1 | `LLM_BACKEND` 분기 + `OpenAICompatLLM` 신규 | `apps/api/src/api/llm.py`,`settings.py`,`main.py` | D2. vLLM OpenAI 호환 스트림 |
| C2 | CORS·API base env화 | `main.py`(`CORS_ORIGINS`), `apps/web/lib/chatClient.ts` | 격차 #2 |
| C3 | SSE `error` 이벤트 + 예외 처리 | `pipeline.py` 또는 `main.py:event_gen`, web `lib/sse`·`hooks/useChat` | 격차 #3 |
| C4 | 인증 미들웨어(JWT/OIDC 검증) | `apps/api`(신규 `auth.py`) | §5.2 |
| C5 | 감사 기록 + PII 마스킹 | 신규 `packages/common`(마스킹) + `apps/api`(`audit.py`, Postgres) | §5.4 |
| C6 | 관측성(Prometheus 계측, `/ready`) | `apps/api/main.py` | §5.5 |
| C7 | 레이트리밋·입력상한·타임아웃·abort·소스 dedup | `apps/api`, `pipeline.py` | §5.8–5.10 |
| C8 | 프론트 프로덕션 빌드·보안헤더·고지문 | `apps/web` | §5.11 |

> `LLM` Protocol·`Settings.from_env`·`RagConfig.from_env`가 이미 있어 C1·C2는 작은 변경으로 가능. 이게 D2(단일 코드베이스·3배포)를 값싸게 만든다.

---

## 7. 롤아웃 단계 & 운영 준비 체크리스트

**단계**: ① 앱 하드닝(§6 C1–C8) → ② 환경 인프라 구축(01/02/03 택1 또는 단계적) → ③ 스테이징 통합·부하 테스트(동시 수십, p95 측정) → ④ 평가 회귀 통과 → ⑤ 제한 파일럿(소수 사용자) → ⑥ 정식 오픈 → ⑦ 운영(모니터링·백업·재색인 주기).

**Go-live 체크리스트(환경 공통)**:
- [ ] HTTPS 강제, SSE 버퍼링 off, 타임아웃 정합
- [ ] OIDC 인증 동작, 미인증 401
- [ ] 감사 적재 + PII 마스킹 단위테스트 통과, 보관기간 잡 동작
- [ ] 메트릭/로그/대시보드/알림 연결, `/ready` LB 연동
- [ ] Chroma 영속·백업, 재색인+평가 게이트 리허설
- [ ] 모델 캐시 사전 동기화, 콜드스타트 시간 측정·문서화
- [ ] SSE error 이벤트 E2E 확인(백엔드 강제 종료 시나리오)
- [ ] 레이트리밋·입력상한 동작
- [ ] 부하 테스트 p95 SLO 충족, 동시 상한 초과 시 우아한 거절
- [ ] 롤링 배포·롤백 리허설, 백업 복구 리허설
- [ ] 면책·저장 고지문 노출, 개인정보 방침 검토 완료

---

## 8. 비기능 목표(SLO 초안, 운영 전 확정)

- 가용성 99.5%(사내 업무시간 기준 가중), 정식 운영.
- 응답: 첫 토큰(TTFT) p95 ≤ 3s, 전체 답변 p95 ≤ 20s(중규모·GPU 기준; Mac은 [01](01-onprem-mac.md)에서 별도 산정).
- 정확도 회귀 게이트: recall@k ≥ 0.78, citation_rate = 1.0, disclaimer_rate = 1.0.
- 감사 적재 성공률 ≥ 99.9%(실패 시 알림·재시도).

---

## 9. 리스크 & 완화

| 리스크 | 영향 | 완화 |
|---|---|---|
| 7B 동시성 한계 | 피크 지연 급증 | GPU+vLLM 배칭(권장), 동시 상한·큐·우아한 거절, 부하 테스트 |
| MLX 컨테이너 불가(Mac) | 표준 운영툴 미적용 | 네이티브+launchd+Caddy, [01](01-onprem-mac.md) 전용 운영 절차 |
| PII 누출 | 법적/신뢰 리스크 | 수집 단계 마스킹·접근통제·보관기간·원문 비저장, 단위테스트 |
| 데이터 클라우드 상주(AWS) | 컴플라이언스 | VPC 격리·암호화·데이터 거버넌스 검토, 필요시 온프렘 선택 |
| 잘못된 법률 정보 | 사용자 피해 | 면책 결정적 append·근거부족 거절·인용검증 유지, 평가 게이트 |
| 코퍼스 노후화 | 답변 부정확 | 정기 재색인 + 평가 회귀, 코퍼스 버전관리 |

---

## 부록 A. 용어
- **TTFT**: Time To First Token. **연속 배칭**: vLLM이 서로 다른 요청을 토큰 단위로 묶어 GPU 활용을 높이는 기법. **무상태 API**: 로컬 디스크 상태 없이 외부 저장소만 쓰는 API(수평 확장 가능).

## 부록 B. 관련 문서
- 설계: `docs/superpowers/specs/2026-06-04-jeonse-deposit-chatbot-design.md`
- A/B 결과: `docs/superpowers/notes/ab-result.md` · 베이스라인: `docs/superpowers/notes/baseline-eval-summary.md`
- 환경별: [01 온프렘 Mac](01-onprem-mac.md) · [02 Linux GPU](02-linux-gpu.md) · [03 AWS 클라우드](03-aws-cloud.md)
