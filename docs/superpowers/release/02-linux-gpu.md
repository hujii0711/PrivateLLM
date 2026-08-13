# 배포 계획 02 — Linux GPU 서버 (vLLM) **[권장]**

> 작성일: 2026-06-05 · 공통 결정·하드닝은 [00 개요·공통](00-overview-and-common.md) 참조.
> 본 문서는 MLX 추론을 **vLLM(연속 배칭)으로 포팅**해 온프렘 Linux + NVIDIA GPU에 컨테이너로 정식 운영 배포하는 계획이다. 중규모(수백 명·동시 수십) 정식 운영의 **균형점(권장)**.

---

## 1. 왜 권장 환경인가

- **표준 운영**: Docker/NVIDIA·systemd·k8s 등 성숙한 리눅스 서버 생태계 그대로.
- **처리량**: vLLM **연속 배칭(continuous batching)** + PagedAttention으로 단일 GPU가 동시 수십 요청을 효율 흡수 → 7B에 이상적. Mac의 동시성 한계([01](01-onprem-mac.md))를 정면 해소.
- **온프렘 유지**: 데이터가 사내를 벗어나지 않음(클라우드 컴플라이언스 부담 없음).
- **단일 코드베이스**: [00 D2](00-overview-and-common.md)의 `OpenAICompatLLM` 한 개만 추가하면 앱 로직은 Mac과 동일.
- 비용: GPU 서버 1회성 조달. AWS 대비 장기 운영 시 저렴, 단 자체 데이터센터/상면·전력·운영 인력 필요.

---

## 2. 추론 백엔드 포팅: MLX → vLLM

### 2.1 vLLM 선택 이유
- OpenAI 호환 서버(`/v1/chat/completions`, `stream=true`)를 기본 제공 → 앱은 표준 HTTP 클라이언트로 호출.
- 연속 배칭·KV 캐시 페이징으로 **동시 처리량**이 7B 단일 GPU에서 최고 수준.
- 대안: **TGI**(HuggingFace, 유사 성능·OpenAI 호환), **Ollama**(가장 간단하나 동시 배칭·관측성 약함 → 중규모엔 vLLM 우위). 본 계획은 vLLM 기준, Ollama는 소규모 폴백.

### 2.2 모델 형식
- base **`Qwen2.5-7B-Instruct`**. 정밀도 선택:
  - **FP16/BF16**(≈15GB VRAM): 품질 기준, 24GB GPU에 KV 캐시 여유.
  - **AWQ/GPTQ 4bit**(≈6GB VRAM): VRAM 절감·더 큰 배치/컨텍스트, 품질 미세 손실. 중규모·24GB면 FP16 권장, VRAM 빠듯하면 AWQ.
- ⚠️ MLX 4bit 가중치는 vLLM에서 못 씀 → **HF 원본 또는 AWQ 변환본**을 별도 준비. 운영 모델이 base(어댑터 없음, [00 D1](00-overview-and-common.md))이라 변환 단순.
- **품질 회귀 검증 필수**: 백엔드가 MLX→vLLM로 바뀌면 출력이 미세하게 달라질 수 있다 → 평가셋([00](00-overview-and-common.md) §5.12)으로 recall/citation/disclaimer/groundedness 재측정해 베이스라인 이상 확인 후 출시.

### 2.3 앱 코드 변경 ([00](00-overview-and-common.md) C1)
- 신규 `OpenAICompatLLM(LLM)`: `base_url`·`model`·`api_key`(내부면 더미)로 `/v1/chat/completions` **스트리밍** 호출, 델타 토큰을 `yield`. `apply_chat_template`은 vLLM 서버가 처리하므로 앱은 `messages`를 그대로 전송.
- `Settings`: `LLM_BACKEND=openai`, `OPENAI_BASE_URL=http://vllm:8000/v1`, `OPENAI_MODEL=Qwen2.5-7B-Instruct`. `from_env` 분기.
- 재시도/타임아웃/서킷브레이커([00](00-overview-and-common.md) §5.10)를 이 HTTP 경로에 적용.

```python
# apps/api/src/api/llm.py (개념)
class OpenAICompatLLM:
    def __init__(self, base_url, model, api_key="-", timeout=120):
        self._base_url, self._model = base_url.rstrip("/"), model
        self._client = httpx.Client(timeout=timeout)  # 재시도/서킷은 래퍼에서
    def stream(self, messages, *, max_tokens=768, temperature=0.3):
        with self._client.stream("POST", f"{self._base_url}/chat/completions",
            json={"model": self._model, "messages": messages, "stream": True,
                  "max_tokens": max_tokens, "temperature": temperature}) as r:
            for line in r.iter_lines():
                if line.startswith("data: ") and line[6:] != "[DONE]":
                    delta = json.loads(line[6:])["choices"][0]["delta"].get("content")
                    if delta: yield delta
```

---

## 3. 아키텍처 (단일 GPU 노드, 컨테이너)

```
                  ┌──────────────────────────────────────────────┐
   사용자 ─TLS──▶ │ nginx / Traefik (TLS 종단, SSE 버퍼링 off)        │ :443
                  └───────┬───────────────────────────┬───────────┘
                          │ /                          │ /api,/chat
                  ┌───────▼────────┐          ┌────────▼───────────────┐
                  │ web (Next.js)  │          │ api (FastAPI) ×N replica │  무상태
                  │  container     │          │  - OIDC 검증·레이트리밋     │
                  └────────────────┘          │  - run_chat·감사·PII       │
                                              └───┬───────────┬──────────┘
                                       검색(in-proc)│           │ 생성(HTTP)
                                       ┌───────────▼──┐   ┌─────▼───────────────┐
                                       │ Chroma(영속)  │   │ vLLM (GPU)            │
                                       │ + bge-m3 임베더│   │ Qwen2.5-7B, 연속 배칭  │
                                       │ (api 내 or 분리)│   │ /v1, /metrics         │
                                       └──────────────┘   └─────────────────────┘
   상태/관측: Postgres(감사) · Prometheus · Grafana · Loki  (모두 컨테이너 or 사내 공용)
```

- **GPU는 vLLM 컨테이너만 점유**. API/web/Chroma/DB는 CPU 컨테이너. api는 무상태라 N replica로 수평 확장(CPU 바운드: 검색·임베딩·오케스트레이션).
- 임베더(bge-m3): GPU 여유가 있으면 GPU, 아니면 CPU. 트래픽 큼/지연 민감하면 별도 임베딩 서비스로 분리. 초기엔 api 내 로드.

---

## 4. 하드웨어 사이징

| GPU | VRAM | 7B 서빙 | 동시(대략) | 비고 |
|---|---|---|---|---|
| RTX 4090 / L4 | 24GB | FP16 여유 / AWQ 큰 배치 | 수십 | 비용효율, 중규모 권장 |
| L40S / A10 | 24–48GB | FP16 + 긴 컨텍스트 | 수십~ | 헤드룸 |
| A100 40GB | 40GB | 과사양(7B엔 큼) | 다수 | 다모델/확장 대비 |

- **중규모(동시 수십)**: 24GB 1장으로 vLLM 연속 배칭이면 충분히 가능. 정확한 동시 한계·p95는 부하 테스트로 확정(§7).
- 호스트: NVIDIA 드라이버 + CUDA + **NVIDIA Container Toolkit**(컨테이너 GPU 패스스루). CPU·RAM은 api replica·Chroma·임베더 수용분(예: 16+ vCPU, 64GB RAM).
- 디스크: 모델 가중치(FP16 ≈15GB)·Chroma·감사 DB·로그용 SSD. 모델 캐시는 영속 볼륨에 사전 동기화(런타임 다운로드 금지).

---

## 5. 컨테이너 구성

### 5.1 docker compose (중규모 단일 노드 권장 출발점)
서비스: `nginx`(또는 traefik), `web`, `api`(replica), `vllm`(GPU), `chroma`(또는 api 내장), `postgres`(감사), `prometheus`, `grafana`, `loki`.

```yaml
# deploy/linux/compose.yaml (개념 발췌)
services:
  vllm:
    image: vllm/vllm-openai:latest
    command: ["--model","Qwen/Qwen2.5-7B-Instruct","--max-model-len","8192",
              "--gpu-memory-utilization","0.9","--served-model-name","Qwen2.5-7B-Instruct"]
    volumes: ["./models:/root/.cache/huggingface"]   # 사전 동기화 캐시
    deploy: { resources: { reservations: { devices: [{capabilities: ["gpu"]}] } } }
    healthcheck: { test: ["CMD","curl","-f","http://localhost:8000/health"] }
  api:
    build: { context: ., dockerfile: deploy/linux/api.Dockerfile }
    environment:
      LLM_BACKEND: openai
      OPENAI_BASE_URL: http://vllm:8000/v1
      OPENAI_MODEL: Qwen2.5-7B-Instruct
      CHROMA_DIR: /data/chroma
      CORS_ORIGINS: https://chat.example.internal
      OIDC_ISSUER: https://sso.example.internal/realms/main
      AUDIT_DB_URL: postgresql://app:***@postgres:5432/audit
    volumes: ["chroma:/data/chroma:ro", "./models:/root/.cache/huggingface"]
    depends_on: [vllm, postgres]
    deploy: { replicas: 3 }
  web:
    build: { context: ./apps/web }
    environment: { NEXT_PUBLIC_API_BASE: https://chat.example.internal }  # 동일출처면 /api 상대경로
  postgres: { image: postgres:16, volumes: ["pgdata:/var/lib/postgresql/data"] }
  nginx: { image: nginx, ports: ["443:443"], volumes: ["./nginx.conf:/etc/nginx/nginx.conf:ro"] }
volumes: { chroma: {}, pgdata: {} }
```

- **api.Dockerfile**: uv 워크스페이스 빌드(`uv sync --package api`), 비루트 유저, `uvicorn api.main:app`. vLLM은 공식 이미지 사용(빌드 불필요).
- **nginx**: `/`→web, `/api`·`/chat`→api(업스트림 라운드로빈). SSE: `proxy_buffering off; proxy_read_timeout 120s; proxy_set_header X-Accel-Buffering no;`.
- 시크릿은 compose `secrets`/SOPS/사내 Vault로 주입([00](00-overview-and-common.md) §5.1) — 위 평문은 예시.

### 5.2 Kubernetes (HA·다노드 확장 시)
- compose로 시작 → 트래픽·가용성 요구 커지면 k8s 이전. 매핑:
  - `api` Deployment + **HPA**(CPU·동시요청 기준 replica 자동), Service.
  - `vllm` Deployment(`nvidia.com/gpu: 1` 리소스), GPU 노드풀(`nodeSelector`/taint), 필요시 replica로 GPU 추가.
  - `web` Deployment, `postgres`는 StatefulSet 또는 사내 관리형 DB, Chroma는 PVC.
  - Ingress(nginx-ingress/Traefik) + cert-manager(TLS). kube-prometheus-stack(관측).
- **GPU 오토스케일**은 노드풀 단위(Cluster Autoscaler) — GPU는 비싸므로 보통 고정 풀 + api만 HPA.

---

## 6. 확장·HA

- **api**: 무상태 → replica/HPA로 수평 확장(검색·오케스트레이션 CPU 바운드 흡수).
- **vLLM/GPU**: 단일 GPU 연속 배칭이 1차 확장. 부족하면 GPU 추가 → vLLM replica를 api가 라운드로빈/로드밸런싱(여러 `OPENAI_BASE_URL` 또는 앞단 LB).
- **무중단 배포**: api 롤링(레디니스+그레이스풀), vLLM은 블루/그린(새 버전 띄우고 트래픽 전환). 모델/인덱스 교체는 평가 게이트 후.
- **단일 노드 SPOF 주의**: 진정한 HA는 2노드 이상 + LB. 단일 노드면 빠른 복구(이미지·IaC 재기동) 절차로 보완.

---

## 7. 부하·성능 검증

- 동시 1·10·20·50 점증, 측정: TTFT p95, 총응답 p95, GPU 사용률·VRAM, vLLM 배치 점유, 큐 대기, 처리량(req/s·tok/s).
- vLLM 튜닝 레버: `--max-num-seqs`(동시 시퀀스), `--max-model-len`(컨텍스트, KV 메모리), `--gpu-memory-utilization`. 동시 상한 초과는 api에서 우아한 거절(429).
- 산출물: SLO([00](00-overview-and-common.md) §8) 충족 동시 한계·필요 GPU 수.

---

## 8. 장애·롤백

| 시나리오 | 탐지 | 대응 |
|---|---|---|
| vLLM 다운/OOM | `/health`·api 서킷브레이커 | api가 "일시 오류" 안내, vLLM 재기동, `--max-model-len`/util 하향 |
| GPU 드라이버/하드웨어 | 노드 메트릭·dmesg | 노드 격리, 예비 GPU/노드, 드라이버 복구 |
| api 과부하 | 동시·큐 메트릭 | HPA 확장, 레이트리밋, 429 |
| Chroma 손상 | `/ready` | 백업 복원/재색인(블루/그린) |
| 배포 회귀 | 평가 게이트·스모크 | 이전 이미지/인덱스/모델 롤백 |

---

## 9. 비용·운영 부담

- **장점**: 표준 리눅스/컨테이너 운영, 최고 처리량/동시성, 온프렘 프라이버시, 장기 운영 비용 우위.
- **단점/부담**: GPU 조달·드라이버/CUDA 운영, 자체 상면·전력·냉각·온콜, 단일 노드면 HA를 별도 설계.
- **권장**: 자체 데이터센터/서버랙이 있고 데이터 온프렘 요구가 있는 중규모 정식 운영의 **기본 선택**.

---

## 10. Linux GPU 전용 Go-live 체크리스트

[00 §7 공통] + 아래:
- [ ] `OpenAICompatLLM` 구현·테스트, `LLM_BACKEND=openai` 분기 동작
- [ ] vLLM에서 Qwen2.5-7B(FP16 또는 AWQ) 서빙, OpenAI 스트림 동작
- [ ] **MLX→vLLM 품질 회귀**: 평가셋 recall/citation/disclaimer/groundedness ≥ 베이스라인
- [ ] NVIDIA Container Toolkit·GPU 패스스루 확인, 모델 캐시 사전 동기화(오프라인 로드)
- [ ] nginx SSE 설정 E2E 토큰 스트리밍, `/api` 상대경로(동일출처) 또는 CORS 정합
- [ ] api 무상태·롤링 배포·레디니스·그레이스풀 셧다운 검증
- [ ] 부하 테스트로 동시 한계·GPU 수 확정, 429 우아한 거절
- [ ] Postgres 감사·PII 마스킹, Prometheus(vLLM `/metrics` 포함)·Grafana·Loki 연결
- [ ] 백업(Chroma·DB·모델)·복구 리허설, 블루/그린 인덱스 전환 리허설
- [ ] (k8s 시) HPA·Ingress·cert-manager·GPU 노드풀 검증
