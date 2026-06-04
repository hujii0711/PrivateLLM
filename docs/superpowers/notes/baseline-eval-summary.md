# 베이스라인 평가 요약 (RAG only, QLoRA 없음)

평가셋: packages/eval/eval_set.jsonl (16문항)
모델: mlx-community/Qwen2.5-7B-Instruct-4bit, temp 0.2

```json
{
  "n": 16,
  "recall_at_k": 0.8125,
  "citation_rate": 1.0,
  "structure_rate": 0.75,
  "disclaimer_rate": 1.0,
  "sources_rate": 1.0,
  "mention_coverage": 0.65625,
  "groundedness": 0.690625
}
```

Plan 3C에서 QLoRA 어댑터 적용 후 동일 평가셋으로 재측정하여 이 수치와 A/B 비교한다.
