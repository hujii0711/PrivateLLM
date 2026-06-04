# QLoRA A/B 결과 (RAG only vs RAG + QLoRA 어댑터)

평가셋: packages/eval/eval_set.jsonl (16문항, 학습 질문 풀과 disjoint)
학습: data/ft(train 45 / valid 4)로 mlx_lm.lora, 300 iters, num-layers 8, lr 1e-5.
측정: 양 arm 같은 세션·동일 temp(run_chat 기본 0.3) — 평가 러너는 settings.temperature를 안 넘김(서빙 0.2와 다름; 양 arm 동일하므로 A/B 타당). qlora arm은 생성만 어댑터, judge는 base(공정 비교).

## 결과

| 지표 | baseline | qlora | Δ |
|---|---|---|---|
| recall_at_k | 0.812 | 0.812 | +0.000 |
| citation_rate | 1.000 | 1.000 | +0.000 |
| structure_rate | 0.750 | 0.750 | +0.000 |
| disclaimer_rate | 1.000 | 1.000 | +0.000 |
| sources_rate | 1.000 | 1.000 | +0.000 |
| mention_coverage | 0.625 | 0.594 | -0.031 |
| groundedness | 0.681 | 0.650 | -0.031 |

## 해석 (정직한 음성 결과)

- **recall@k Δ=0** — 양 arm 검색이 동일하므로 불변. A/B 측정의 정합성을 확인하는 검증 포인트(통과).
- **structure_rate / citation_rate / disclaimer_rate / sources_rate Δ=0** — 베이스라인이 이미 높음(인용·면책·출처 1.0, 구조 0.75). 강화 프롬프트 + 파이프라인의 결정적 면책/인용 검증이 형식을 이미 잘 만들어, 자기-distillation 파인튜닝이 더 끌어올리지 못함.
- **mention_coverage / groundedness 소폭 하락(−0.031)** — 파인튜닝이 도움이 안 됐을 뿐 아니라 약간 해가 됨.

### 원인 분석
1. **자기-distillation 상한**: 학습 타깃이 base 모델 자신의 best-of-N 출력 → 새 능력 없이 기존 행동 강화에 그침. 베이스라인이 이미 강해 개선 여지가 작음.
2. **소규모 + 과적합**: train 45예제로 train loss 0.12까지 하강(val 0.29) → 작은 자기생성 셋을 암기, 평가셋 일반화가 오히려 미세 저하.
3. **시퀀스 절단(2048)**: FT 예제(시스템+다중 근거 블록+답변)가 길어 다수가 2048로 잘림(최장 6213). 일부 타깃 답변/근거가 잘린 채 학습 → 데이터 품질 저하.

### 결론
**이 설정(소규모 자기-distillation)에서 QLoRA는 RAG 베이스라인을 개선하지 못했고 소폭 하락시켰다.** 이는 유효한 연구 결과다 — 베이스라인(강화 프롬프트 + 결정적 보장)이 이미 형식 측면에서 강할 때, 자기-distillation 파인튜닝의 한계를 보여준다. A/B 측정 자체는 타당(recall 불변).

### 개선 경로 (후속)
- **절단 방지**: 근거 블록 토큰 길이 가드 또는 max_seq_len 상향(긴 예제 손실 제거) — 가장 직접적.
- **더 강한 teacher**: Qwen2.5-32B-4bit로 타깃 품질을 base 상한 위로.
- **실데이터**: 생활법령/상담사례(해설·상담사례 source_type) 보강 → 새 지식·표현.
- **데이터 확장 + 과적합 완화**: 질문 풀↑, iters↓ 또는 정규화.
