# 배포 계획 01 — 온프렘 Mac 서버 (MLX)

> 작성일: 2026-06-05 · 공통 결정·하드닝은 [00 개요·공통](00-overview-and-common.md) 참조.
> 본 문서는 **기존 MLX 추론을 그대로 유지**하며 Apple Silicon Mac 하드웨어에 정식 운영 배포하는 계획이다.

---

## 1. 언제 이 환경을 선택하나

- **데이터가 절대 사내(또는 특정 물리망)를 벗어나면 안 됨** — 가장 강한 프라이버시.
- 기존 `MlxLLM` 코드를 **포팅 없이 즉시** 활용하고 싶음(D2의 `OpenAICompatLLM` 신규 구현 불요).
- GPU 서버 조달이 어렵고 Apple Silicon 하드웨어는 확보 가능.
- 트레이드오프 수용: **컨테이너화 불가(모델 서버)**, 수평 확장·동시성 흡수가 약함, Mac 서버 운영 도구 미성숙.

> 중규모(수백 명, 동시 수십)에서 Mac은 **동시성이 가장 큰 제약**이다. §5에서 정량 산정하고, 한계 초과가 예상되면 [02 Linux GPU](02-linux-gpu.md)를 권장한다.

---

## 2. 핵심 제약: 왜 모델 서버는 네이티브인가

MLX는 Apple **Metal** GPU(통합 메모리)를 직접 쓴다. Docker Desktop for Mac의 리눅스 컨테이너는 **Metal에 접근 불가** → 컨테이너 안에서 MLX는 CPU로 떨어지거나 동작하지 않는다. 따라서:

- **LLM(API 프로세스)·임베더는 macOS 네이티브로 실행**(컨테이너 X).
- 보조 서비스(Postgres 감사 DB, Prometheus, Grafana, 리버스 프록시)는 Docker Desktop 컨테이너로 가능하나, 운영 단순화를 위해 **별도 리눅스 보조 노드**(또는 사내 공용 DB/모니터링)에 두는 것을 권장. Mac은 추론·API 전용으로.
- 결과: "12-factor 단일 이미지" 모델이 깨진다 → **재현 가능한 부트스트랩 스크립트 + launchd 서비스**로 대체.

---

## 3. 아키텍처 (Mac 노드)

```
                 ┌───────────────────────────────────────────────┐
   사용자 ─TLS─▶ │ Caddy (TLS 자동, 리버스 프록시, SSE 버퍼링 off)    │  :443
                 └───────┬───────────────────────────┬───────────┘
                         │ / (web)                    │ /api,/chat
                 ┌───────▼────────┐        ┌──────────▼─────────────────────┐
                 │ Next.js (start)│        │ Nginx/Caddy → 워커 풀 (의사 병렬)   │
                 │  :3000         │        │  ┌─────────┬─────────┬─────────┐ │
                 └────────────────┘        │  │uvicorn#1│uvicorn#2│uvicorn#3│ │  각 워커=MLX 모델 1사본
                                           │  │ :8001   │ :8002   │ :8003   │ │  + 임베더 + Chroma(RO)
                                           │  └─────────┴─────────┴─────────┘ │
                                           └──────────┬──────────────────────┘
                                                      │ 감사/관측(네트워크)
                                       ┌──────────────▼───────────────┐
                                       │ 보조 노드(리눅스) 또는 사내 공용:    │
                                       │ Postgres(감사) · Prometheus · Grafana│
                                       └──────────────────────────────┘
```

- **워커 풀이 Mac 동시성의 핵심**: MLX `stream_generate`는 단일 스트림이고 파이썬 GIL·단일 Metal 컨텍스트로 한 프로세스는 사실상 1요청씩 생성. 동시성을 얻으려면 **여러 uvicorn 워커 프로세스(각각 모델 사본 로드)**를 띄우고 앞단에서 로드밸런싱한다. 워커 수는 **통합 메모리가 상한**(§5).
- Chroma는 읽기전용 공유. 임베더(bge-m3)는 각 워커에 로드(또는 단일 임베딩 서비스로 분리해 메모리 절약 — §5.4).

---

## 4. 하드웨어 사이징

7B-4bit(MLX) 1사본 ≈ **4.3GB**(가중치) + KV 캐시/오버헤드(컨텍스트 길이·동시 생성에 비례, 수백 MB~수 GB) + bge-m3 임베더(≈2GB) + OS/버퍼. **워커 1개당 실효 ≈ 7–9GB**로 보수 산정.

| 하드웨어 | 통합 메모리 | 권장 워커 수(모델 사본) | 비고 |
|---|---|---|---|
| Mac mini M4 Pro | 64GB | 4–6 | 소규모 파일럿/저예산 |
| Mac Studio M4 Max | 128GB | 8–12 | **중규모 단일 노드 권장** |
| Mac Studio M3 Ultra | 192–256GB | 12–20 | 피크 여유·헤드룸 |

- 메모리 외에 **생성 속도**가 진짜 병목: M-시리즈에서 7B-4bit는 대략 수십 tok/s(첫 토큰 지연 별도). 워커 N개면 **동시 N개 생성**이 각자 속도로 진행 → 동시 요청이 N 초과하면 큐 대기.
- 권장: **단일 Mac Studio(128GB+) 1노드로 시작**, 피크가 워커 수를 넘으면 노드 추가(§6 HA). 정확한 워커 수·tok/s·동시 한계는 **반드시 실측**(§7 부하테스트)으로 확정.

---

## 5. 구성 요소별 배포

### 5.1 런타임 부트스트랩 (재현 가능)
- macOS에 `uv`(파이썬), `node`(웹), 모델 캐시 준비. HF 캐시에 `mlx-community/Qwen2.5-7B-Instruct-4bit` 리비전 고정 사전 다운로드(런타임 다운로드 금지).
- 레포 체크아웃 → `uv sync` → Chroma 인덱스 배치(`CHROMA_DIR` 영속 경로, §5.3) → 환경변수 파일.
- 부트스트랩을 **셋업 스크립트**(`deploy/mac/bootstrap.sh`, 신규)로 문서화·버전관리. 신규 노드 추가 시 동일 스크립트로 재현.

### 5.2 워커 풀 + 프로세스 관리 (launchd)
- 각 워커: `uv run --package api uvicorn api.main:app --port 80XX --workers 1`. **워커당 1 프로세스**(멀티 `--workers`는 모델 N사본을 한 프로세스가 못 가지므로 프로세스 분리로 관리).
- **launchd**(macOS 표준)로 각 워커를 `KeepAlive` 데몬 등록 → 크래시 자동 재기동, 부팅 시 자동 시작. `/Library/LaunchDaemons/com.privatellm.api.8001.plist` 형태. (대안: `pm2`·`supervisor`.)
- 콜드스타트: 첫 요청은 모델 로딩으로 느림 → launchd 기동 후 **워밍업 요청**으로 사전 로드, `/ready`가 로드 완료 후 200.

### 5.3 상태(Chroma·감사)·백업
- **Chroma**: `CHROMA_DIR`를 Mac의 영속 디스크(예: `/opt/privatellm/chroma`)에. 빌드 원천은 `pipelines/`. 재색인은 별도 시간대 실행 후 블루/그린 컬렉션 전환([00](00-overview-and-common.md) §5.6).
- **감사 Postgres**: Mac 네이티브 설치보다 **보조 리눅스 노드/사내 공용 Postgres** 권장(백업·운영 성숙). Mac 단독이면 Docker Desktop Postgres + Time Machine/외장 백업.
- **백업**: Chroma 디렉터리 + 원천 코퍼스 + 감사 DB 덤프를 사내 백업 대상으로 정기 스냅샷(예: 일 1회). 복구 리허설 문서화.

### 5.4 임베더 메모리 최적화(선택)
- 워커마다 bge-m3(≈2GB)를 로드하면 N×2GB 낭비 → **단일 임베딩 서비스**(별도 프로세스, 내부 HTTP)로 분리하고 워커는 호출만. 메모리 빠듯할 때 적용. 초기에는 단순화를 위해 워커 내 로드로 시작.

### 5.5 리버스 프록시 (Caddy)
- **Caddy** 권장(자동 TLS·간단). `/` → Next.js(:3000), `/api`·`/chat` → 워커 풀(라운드로빈 업스트림 :8001–800N).
- **SSE 필수 설정**: 업스트림 응답 버퍼링 off, `flush_interval -1`(Caddy reverse_proxy), 읽기 타임아웃 ≥ 생성 최대시간. 헬스체크는 `/ready`.
- 사내 PKI/사설 CA면 인증서 수동 배치. mTLS 필요 시 Caddy에서 클라이언트 인증.

### 5.6 인증·감사·관측 (공통 §5)
- 인증: 사내 OIDC. Mac에는 게이트웨이가 없으니 **API 인증 미들웨어(JWT 검증)**로 처리([00](00-overview-and-common.md) C4).
- 감사·PII 마스킹([00](00-overview-and-common.md) §5.4): API가 보조 노드 Postgres에 적재.
- 관측: 각 워커 `/metrics`(Prometheus)를 보조 노드 Prometheus가 스크레이프, Grafana 대시보드. macOS 시스템 메트릭은 `node_exporter`(darwin) 또는 자체 수집.

---

## 6. 고가용성·확장

- **단일 노드 한계**: Mac은 ASG·HPA 같은 자동 확장이 없다. 확장 = **노드 수동 추가**.
- **다중 Mac 노드**: 동일 부트스트랩으로 2~3대 → 앞단에 **사내 LB**(별도 리눅스의 nginx/HAProxy 또는 하드웨어 LB)로 노드 간 분산. 각 노드는 자체 워커 풀. Chroma는 각 노드 로컬 복제(읽기전용·동일 빌드) 또는 공유 NFS(지연 주의 — 로컬 복제 권장).
- **무중단 배포**: 노드/워커를 LB에서 순차 드레인 → 업데이트 → 워밍업 → 복귀(롤링). 그레이스풀 셧다운으로 진행 스트림 보존.
- **물리 운영 주의**: Mac은 IPMI/원격 전원관리·랙 폼팩터·ECC 메모리가 없다. 무정전(UPS)·원격관리(예: 사내 MDM, `screen sharing`)·물리 보안 절차를 별도 마련.

---

## 7. 부하 테스트 (Mac은 필수)

- 목적: **노드당 안전 동시 한계**와 **워커 수**를 실측 확정. Mac 동시성은 이론값이 불확실하므로 출시 전 게이트.
- 방법: 대표 질의 세트로 동시 1·5·10·20·… 점증, 측정: TTFT p95, 총 응답 p95, tok/s, 큐 대기, 메모리·열(thermal throttling) 여부.
- 산출물: "노드 1대 = 안전 동시 X, 워커 N" 표 → 수백 명/동시 수십 목표 대비 노드 수 결정. **목표 미달이면 [02 Linux GPU](02-linux-gpu.md)로 전환 결정**.

---

## 8. 장애·롤백

| 시나리오 | 탐지 | 대응 |
|---|---|---|
| 워커 크래시 | launchd `KeepAlive` 재기동 + `/ready` 실패 알림 | 자동 재기동, 반복 시 노드 드레인 |
| 모델 로드 실패 | `/ready` 미통과 | LB 트래픽 차단, 캐시·디스크 점검 |
| 메모리 고갈/스로틀 | 메모리·온도 메트릭 알림 | 워커 수 하향, 노드 추가, 냉각 점검 |
| Chroma 손상 | `/ready` 검색 실패 | 백업 복원 또는 재색인 |
| 배포 회귀 | 평가 게이트·스모크 실패 | 이전 커밋/인덱스로 롤백(블루/그린) |
| 노드 전체 다운 | LB 헬스 실패 | 타 노드로 트래픽, 물리 점검(UPS·전원) |

- **롤백 단위**: 코드(이전 태그 재배포)·인덱스(이전 컬렉션 별칭)·모델(이전 리비전)을 독립 롤백.

---

## 9. 비용·운영 부담

- **장점**: 추론 하드웨어 1회성 비용(시간당 과금 없음), 데이터 완전 사내, 기존 코드 재사용(포팅 0).
- **단점/부담**: Mac 서버 운영 미성숙(랙·원격관리·ECC 부재), 동시성·수평확장 약함, 컨테이너 표준툴 미적용, 보조 노드(DB/모니터링) 별도 운영, 부하 한계 실측 의존.
- **권장 포지션**: 데이터 상주 제약이 절대적이거나 GPU 조달이 막힌 경우의 **온프렘 강제 해법**. 그 외 중규모 정식운영은 [02 Linux GPU](02-linux-gpu.md)가 운영 효율·처리량에서 우월.

---

## 10. Mac 전용 Go-live 체크리스트

[00 §7 공통 체크리스트] + 아래:
- [ ] 모델 서버 네이티브 실행 확인(컨테이너 아님), HF 캐시 리비전 고정·오프라인 로드
- [ ] launchd 데몬 등록(워커 N개), 크래시 자동복구·부팅 자동시작 검증
- [ ] 워밍업 → `/ready` 200 후 LB 투입 흐름 동작
- [ ] Caddy SSE 설정(버퍼링 off·flush·타임아웃) E2E 토큰 스트리밍 확인
- [ ] 부하 테스트로 노드당 안전 동시 한계·워커 수 확정, 목표 대비 노드 수 결정
- [ ] 보조 노드 Postgres(감사)·Prometheus/Grafana 연결, 백업·복구 리허설
- [ ] UPS·원격관리·물리보안 절차 수립
- [ ] 다중 노드 시 사내 LB 드레인 기반 롤링 배포 리허설

---

## 부록. 워커 풀 launchd 개념 예시 (의사 코드)

```xml
<!-- /Library/LaunchDaemons/com.privatellm.api.8001.plist (워커마다 1개) -->
<dict>
  <key>Label</key><string>com.privatellm.api.8001</string>
  <key>ProgramArguments</key>
  <array>
    <string>/opt/privatellm/run-worker.sh</string><string>8001</string>
  </array>
  <key>EnvironmentVariables</key>
  <dict>
    <key>MLX_MODEL</key><string>mlx-community/Qwen2.5-7B-Instruct-4bit</string>
    <key>LLM_BACKEND</key><string>mlx</string>
    <key>CHROMA_DIR</key><string>/opt/privatellm/chroma</string>
    <key>CORS_ORIGINS</key><string>https://chat.example.internal</string>
    <key>AUDIT_DB_URL</key><string>postgresql://.../audit</string>
  </dict>
  <key>KeepAlive</key><true/>
  <key>RunAtLoad</key><true/>
</dict>
```
> `run-worker.sh`는 `cd /opt/privatellm && uv run --package api uvicorn api.main:app --port "$1" --workers 1` + 기동 후 워밍업 호출. 실제 값은 시크릿 관리로 주입([00](00-overview-and-common.md) §5.1).
