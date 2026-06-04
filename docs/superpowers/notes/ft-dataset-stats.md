# FT 데이터셋 빌드 통계 (rejection-sampling distillation)

질문 풀: packages/ftdata/question_pool.jsonl (평가셋과 disjoint, 30문항)
teacher: base Qwen2.5-7B-4bit, temp 0.7, 형식(①②③+[n]+면책+출처)+근거(judge≥0.5) 필터
검수: train 45/45 형식 완비, 평가셋 질문 누출 0

```json
{
  "questions": 30,
  "candidates": 120,
  "kept": 49,
  "pass_rate": 0.4083333333333333,
  "train": 45,
  "valid": 4,
  "k": 4,
  "per_q": 2,
  "min_ground": 0.5
}
```

Plan 3C에서 이 train/valid(data/ft/)로 QLoRA 어댑터를 학습한다.
