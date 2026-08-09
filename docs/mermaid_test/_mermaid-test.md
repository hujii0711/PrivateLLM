# mermaid 렌더링 진단 파일

각 케이스가 **그림으로 보이는지 / 빈 영역인지 / 에러 박스인지** 확인해 주세요.
이 파일은 진단 후 삭제합니다.

---

## 케이스 1 — 최소 다이어그램 (영문, 장식 없음)

```mermaid
graph TD
    A --> B
```

---

## 케이스 2 — 한글 라벨

```mermaid
graph TD
    A["사용자 질문"] --> B["검색"]
```

---

## 케이스 3 — `<br/>` 줄바꿈

```mermaid
graph TD
    A["apps/web<br/>Next.js"] --> B["apps/api<br/>FastAPI"]
```

---

## 케이스 4 — subgraph

```mermaid
graph TD
    subgraph G1["패키지 A"]
        A --> B
    end
    subgraph G2["패키지 B"]
        C --> D
    end
    B --> C
```

---

## 케이스 5 — 점선 화살표 + 라벨 (§3에서 사용)

```mermaid
graph LR
    A["1단계"] --> B["2단계"]
    B -.선택.-> C["3단계"]
    C -.->|되돌아감| A
```

---

## 케이스 6 — 굵은 화살표 + 실린더 노드 (§1, §2에서 사용)

```mermaid
graph LR
    A["api"] ==> B["rag"]
    B --> C[("ChromaDB<br/>jeonse_deposit")]
```

---

## 케이스 7 — 마름모 분기 + 특수문자 ≥ (§4에서 사용)

```mermaid
graph TB
    A["검색"] --> G{"유사도 ≥ 0.35"}
    G -->|No| N["거부"]
    G -->|Yes| Y["생성"]
```
