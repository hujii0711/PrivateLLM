# 배포 계획 03 — AWS 클라우드 (EC2 GPU + vLLM, VPC 내)

> 작성일: 2026-06-05 · 공통 결정·하드닝은 [00 개요·공통](00-overview-and-common.md) 참조.
> 본 문서는 [02 Linux GPU](02-linux-gpu.md)의 컨테이너·vLLM 아키텍처를 **AWS 관리형 서비스 위에** 올려 탄력 확장·관리형 HA로 정식 운영하는 계획이다.

---

## 1. 언제 이 환경을 선택하나

- 자체 데이터센터/GPU 서버가 없고 **빠르게 구축**하고 싶음.
- 트래픽 변동에 **탄력 확장**(ASG/HPA)·관리형 HA·백업·DR을 활용.
- 트레이드오프: **데이터가 AWS(자사 VPC/계정) 내에 상주** → 사내 개인정보·보안 정책상 클라우드 반입 가능 여부를 **사전 검토**해야 함(법률 상담 도메인). GPU 인스턴스 **시간당 과금**으로 상시 가동 시 비용 큼.

> 데이터의 외부 반출이 절대 불가하면 [01](01-onprem-mac.md)/[02](02-linux-gpu.md)(온프렘)를 택한다. AWS라도 데이터는 **자사 VPC·계정 내부**에 머물며 인터넷에 노출되지 않게 설계한다(아래 §4).

---

## 2. 서빙 방식 선택지

| 방식 | 장점 | 단점 | 판정 |
|---|---|---|---|
| **EC2 g5 + vLLM (자가관리)** | [02](02-linux-gpu.md)와 동일 스택·완전 통제·프라이버시 | GPU 인스턴스·운영 직접 | **권장** |
| EKS + vLLM | k8s HA·오토스케일 표준화 | 운영 복잡도↑ | 대규모·다서비스 시 |
| SageMaker 엔드포인트 | 관리형 서빙·오토스케일·배포 관리 | 커스텀 컨테이너 작업·비용·종속 | 운영 인력 적을 때 대안 |
| Bedrock | 완전관리·인프라 0 | Qwen 비네이티브, 커스텀 모델 반입 제약, **"private/자체호스팅" 취지와 상충** | **부적합** |

- **권장: EC2 g5 + vLLM**(또는 규모 커지면 EKS). [02](02-linux-gpu.md)의 `OpenAICompatLLM`·컨테이너 구성을 그대로 재사용 → **단일 코드베이스 유지**([00 D2](00-overview-and-common.md)).
- Bedrock은 자체 RAG 코퍼스·자체 모델·프라이버시 통제라는 본 프로젝트 취지와 맞지 않아 제외(필요 시 별도 검토).

---

## 3. 아키텍처 (AWS, VPC)

```
  사용자(사내) ─TLS─▶ ALB (ACM 인증서, OIDC/Cognito 인증) ──┐  Public/Internal Subnet
                                                          │
   ┌──────────────────────────────────────────────────────┼─────────────────────────┐
   │ VPC                                                   │                          │
   │   ┌─────────────┐        ┌───────────────────────────▼──────────┐               │
   │   │ web (ECS/    │        │ api (ECS Fargate or EC2, ASG, 무상태)    │               │
   │   │  S3+CloudFront│       │  - 토큰검증(ALB+Cognito 신뢰헤더)         │               │
   │   └─────────────┘        │  - run_chat·감사·PII·레이트리밋           │               │
   │                          └───┬───────────────┬──────────┬────────┘               │
   │                  검색(in-proc)│               │ 생성(HTTP) │ 감사                   │
   │                  ┌───────────▼──┐    ┌────────▼────────┐ │  ┌──────────────┐       │
   │                  │ Chroma(EBS/EFS│    │ vLLM @ EC2 g5    │ └─▶│ RDS Postgres  │       │
   │                  │ on api host)  │    │ (GPU ASG, 사설)   │    │ (감사, 사설)    │       │
   │                  └──────────────┘    └─────────────────┘    └──────────────┘       │
   │   S3(모델·코퍼스·백업) · Secrets Manager · CloudWatch(로그·메트릭·알림) · ECR(이미지)        │
   └─────────────────────────────────────── Private Subnets ──────────────────────────┘
```

- **GPU(vLLM)·RDS는 프라이빗 서브넷**(인터넷 직접 노출 없음). ALB만 진입점. 사내 전용이면 **Internal ALB + VPN/Direct Connect/PrivateLink**로 인터넷 비노출.
- api는 무상태 → Fargate(서버리스 컨테이너) 또는 EC2 ASG. GPU는 Fargate 미지원이라 **EC2(g5) ASG**.

---

## 4. 핵심 AWS 구성요소 매핑

| 관심사 | AWS 서비스 | 비고 |
|---|---|---|
| 진입·TLS | **ALB + ACM** | TLS 종단, 경로 라우팅(`/`→web, `/api`·`/chat`→api). SSE: idle timeout↑(예 180s) |
| 인증 | **Cognito** (또는 사내 SSO 연동 OIDC) + ALB authenticate | ALB가 인증 종단→api는 신뢰헤더(`x-amzn-oidc-*`) 검증([00](00-overview-and-common.md) §5.2 게이트웨이 패턴) |
| api 실행 | **ECS Fargate**(무상태·오토스케일) 또는 EC2 ASG | 이미지 ECR |
| GPU 추론 | **EC2 g5.xlarge**(A10 24GB) + ASG | vLLM 컨테이너, 사설 서브넷. ALB 또는 내부 NLB로 api→vLLM |
| 벡터 | Chroma on **EBS**(단일) 또는 **EFS**(공유) | 1264청크 소규모→api 호스트 EBS면 충분 |
| 감사 DB | **RDS PostgreSQL**(Multi-AZ) | 자동백업·암호화·사설 |
| 시크릿 | **Secrets Manager** / SSM Parameter Store | DB·OIDC 시크릿 |
| 모델·코퍼스·백업 | **S3** | 모델 가중치 사전 적재→인스턴스 기동 시 동기화(런타임 HF 다운로드 회피) |
| 이미지 | **ECR** | api·web·(자가)vLLM 이미지 |
| 관측 | **CloudWatch**(로그·메트릭·알람) + Container Insights | vLLM/GPU 메트릭 커스텀 게시. 필요시 AMP/AMG(Prometheus/Grafana) |
| 네트워크 | VPC, 프라이빗 서브넷, **VPC Endpoint**(S3·ECR·Secrets) | 트래픽 인터넷 미경유 |
| 웹 정적 | **S3 + CloudFront** (Next 정적/SSR은 Fargate) | 캐시·보안헤더 |

---

## 5. 사이징·비용

- **GPU**: `g5.xlarge`(A10G 24GB, 1 GPU) 1대로 7B vLLM 중규모 동시 수십 가능(부하 테스트로 확정). 피크/HA용 ASG min 1~2.
- **api**: Fargate 0.5~1 vCPU·1~2GB ×N(오토스케일). 임베더를 api 내장하면 CPU·메모리 상향 또는 별도 임베딩 태스크.
- **RDS**: 소형(db.t4g.medium) Multi-AZ.
- **비용 관리(중요)**: GPU 인스턴스 **시간당 과금**이 주 비용. 완화책:
  - 업무시간 외 **스케줄 축소**(ASG min 0~1) — 사내 서비스면 야간 스케일다운으로 절감.
  - **Savings Plans/예약**으로 상시 GPU 할인.
  - 트래픽 낮으면 단일 g5로 충분 — 과확장 금지(YAGNI).
- 정확한 월비용은 인스턴스 타입·가동시간·RDS·데이터전송으로 산정(운영 전 추정표 작성).

---

## 6. IaC·배포 파이프라인

- **IaC**: Terraform(또는 CDK)로 VPC·서브넷·ALB·ECS·ASG·RDS·S3·IAM·Secrets 정의. 환경(stg/prod) 분리, 상태는 S3+DynamoDB 잠금.
- **CI/CD**: GitHub Actions/CodePipeline → 테스트([00](00-overview-and-common.md) §5.12) → 이미지 ECR 푸시 → **스테이징 배포** → 평가 회귀 게이트 → **프로덕션 롤링**(ECS rolling/blue-green via CodeDeploy).
- **모델 파이프라인**: 모델 가중치를 S3에 버전 적재 → 인스턴스 user-data/init이 동기화. 인덱스(Chroma)는 빌드 잡 산출물을 S3→EBS/EFS 배치, 블루/그린 컬렉션 전환.

```hcl
# deploy/aws/main.tf (개념 발췌)
module "vpc"     { source = "terraform-aws-modules/vpc/aws"  /* private+public subnets */ }
resource "aws_lb" "app"            { load_balancer_type = "application"; /* + ACM, OIDC action */ }
resource "aws_ecs_service" "api"   { desired_count = 3; /* Fargate, autoscaling target */ }
resource "aws_autoscaling_group" "vllm_gpu" { min_size = 1; max_size = 2 /* g5.xlarge, ECR vllm */ }
resource "aws_db_instance" "audit" { engine = "postgres"; multi_az = true; storage_encrypted = true }
resource "aws_s3_bucket" "artifacts" { /* models, corpus, backups; versioning + SSE-KMS */ }
```

---

## 7. 보안·컴플라이언스 (클라우드 특화)

- **데이터 상주 검토(선결)**: 질의·답변·코퍼스가 AWS에 저장됨. 사내 개인정보처리방침·법무 검토로 **클라우드 반입 승인** 확보. 리전은 국내(서울 `ap-northeast-2`) 고정.
- **암호화**: 전송 TLS, 저장 KMS(S3·RDS·EBS). 감사 DB·S3는 SSE-KMS.
- **네트워크 격리**: GPU·RDS 프라이빗, SG 최소 개방(ALB→api, api→vLLM/RDS만). 사내 전용은 Internal ALB + VPN/Direct Connect.
- **IAM 최소권한**: 태스크 역할별 S3/Secrets 한정. 루트키 미사용.
- **감사·PII**([00](00-overview-and-common.md) §5.4): RDS 적재, 마스킹 동일. CloudTrail로 인프라 접근 감사. 보관기간 잡(EventBridge+Lambda 또는 RDS 잡).

---

## 8. 확장·HA·DR

- **api**: ECS Service Auto Scaling(요청수·CPU). 무상태라 즉시 확장.
- **GPU**: g5 ASG. 트래픽 증가 시 인스턴스 추가→vLLM replica를 NLB/ALB 뒤로 api가 호출. 야간 축소.
- **HA**: ALB·Fargate·RDS Multi-AZ로 가용존 분산. GPU ASG min≥2면 단일 AZ 장애 견딤.
- **DR**: S3 버전관리·교차리전 복제(선택), RDS 자동 백업·스냅샷. IaC로 전체 재구축 가능(복구 리허설 문서화).

---

## 9. 장애·롤백

| 시나리오 | 탐지 | 대응 |
|---|---|---|
| vLLM/GPU 인스턴스 실패 | ALB/NLB 헬스·ASG | ASG 자동 교체, api 서킷브레이커로 우아한 오류 |
| api 과부하 | CloudWatch·ALB 5xx | ECS 오토스케일, 레이트리밋 429 |
| RDS 장애 | RDS 이벤트·헬스 | Multi-AZ 페일오버, 감사 적재 재시도 큐 |
| 배포 회귀 | 평가 게이트·스모크 | CodeDeploy 블루/그린 롤백 |
| 비용 급증 | Cost 알람·GPU 사용률 | ASG 상한·스케줄, 예약 검토 |

---

## 10. 비용·운영 부담

- **장점**: 빠른 구축, 탄력 확장, 관리형 HA/백업/DR, 자체 상면·전력 불요.
- **단점/부담**: GPU 시간당 비용(상시 가동 시 큼), **데이터 클라우드 상주 컴플라이언스**, AWS 종속·요금 관리, IaC/클라우드 운영 역량 필요.
- **권장**: 자체 GPU 인프라가 없고 데이터 클라우드 반입이 정책상 허용되는 경우의 **빠른 정식 운영 경로**. 데이터 반출 불가면 온프렘([01](01-onprem-mac.md)/[02](02-linux-gpu.md)).

---

## 11. AWS 전용 Go-live 체크리스트

[00 §7 공통] + 아래:
- [ ] **데이터 클라우드 반입 컴플라이언스 승인**(법무·개인정보), 국내 리전 고정
- [ ] `OpenAICompatLLM`·vLLM(EC2 g5) 서빙, MLX→vLLM 품질 회귀 통과([02](02-linux-gpu.md) §2.2)
- [ ] VPC 프라이빗 격리(GPU·RDS), SG 최소개방, VPC Endpoint, (사내전용) Internal ALB+VPN
- [ ] ALB+ACM TLS, ALB SSE idle timeout↑, Cognito/OIDC 인증·api 신뢰헤더 검증
- [ ] KMS 암호화(S3·RDS·EBS), Secrets Manager 주입, IAM 최소권한, CloudTrail
- [ ] RDS Multi-AZ 감사·PII 마스킹·보관기간 잡, 적재 실패 재시도·알람
- [ ] CloudWatch 로그·메트릭·알람(GPU/vLLM 커스텀), 대시보드
- [ ] 모델·코퍼스 S3 버전 적재→인스턴스 동기화(런타임 다운로드 회피)
- [ ] Terraform/CDK로 stg·prod 재현, CI/CD 평가 게이트, CodeDeploy 블루/그린 롤백
- [ ] 부하 테스트로 동시 한계·GPU 수 확정, 비용 추정·스케줄 축소·예약 검토
- [ ] DR(백업·스냅샷·재구축) 리허설
