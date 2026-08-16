## `jeonse_deposit` 컬렉션 조회 방법

### 방법 A: Python 코드로 직접 조회

```python
import chromadb

client = chromadb.PersistentClient(path="data/chroma")
col = client.get_collection("jeonse_deposit")
```

---

#### 1. 총 개수 확인

```python
col.count()  # → 1264
```

---

#### 2. `get()` — ID 또는 필터로 조회 (유사도 없이)

```python
# ① ID로 특정 청크 1개 가져오기
col.get(
    ids=["prec-197932-판시사항"],
    include=["documents", "metadatas"]
)

# ② source_type 필터 (where절)
col.get(
    where={"source_type": "판례"},   # "법령" | "판례"
    limit=10,
    include=["metadatas", "documents"]
)

# ③ 특정 날짜 이후 법령만 조회
col.get(
    where={"$and": [
        {"source_type": {"$eq": "법령"}},
        {"date": {"$gte": "2023-01-01"}}
    ]},
    limit=20,
    include=["metadatas", "documents"]
)
```

---

#### 3. `query()` — 유사도 벡터 검색

```python
from pipelines.index.embedder import Embedder  # 프로젝트 임베더 사용

embedder = Embedder()
vec = embedder.embed(["보증금 반환 요건"])[0]

col.query(
    query_embeddings=[vec],
    n_results=5,
    include=["metadatas", "documents", "distances"]
)
# distances: 코사인 거리 (0에 가까울수록 유사)
```

---

#### `include` 에 넣을 수 있는 값들

| 값 | 내용 |
|----|------|
| `"documents"` | 청크 원문 텍스트 |
| `"metadatas"` | source_type, title, ref, url, date |
| `"embeddings"` | 1024차원 벡터 (거의 필요 없음) |
| `"distances"` | `query()` 전용, 유사도 거리 |

---

### 방법 B: 만들어둔 뷰어 스크립트로 빠르게

```bash
cd pipelines

# 판례 5개 목록
uv run python scripts/view_chroma.py --source 판례 --limit 5

# 법령 목록 (기본 20개)
uv run python scripts/view_chroma.py --source 법령

# 키워드 유사도 검색 (처음 실행시 모델 다운로드로 느릴 수 있음)
uv run python scripts/view_chroma.py --query "보증금 반환"

# 통계만
uv run python scripts/view_chroma.py --stats
```

---

### `where` 필터 연산자 정리

| 연산자 | 의미 | 예시 |
|--------|------|------|
| `$eq` | 같음 | `{"source_type": {"$eq": "법령"}}` |
| `$ne` | 다름 | `{"source_type": {"$ne": "판례"}}` |
| `$gte` | 이상 | `{"date": {"$gte": "2023-01-01"}}` |
| `$lte` | 이하 | `{"date": {"$lte": "2024-12-31"}}` |
| `$in` | 목록 포함 | `{"source_type": {"$in": ["법령", "판례"]}}` |
| `$and` | AND | `{"$and": [{조건1}, {조건2}]}` |
| `$or` | OR | `{"$or": [{조건1}, {조건2}]}` |


---
Viewed ChromaDB_select.md:1-29
Edited ChromaDB_select.md

먼저 `chroma.sqlite3`의 실제 테이블 구조를 확인합니다.

Ran command: `sqlite3 /Users/fujii0711/Claude/PrivateLLM/data/chroma/chroma.sqlite3 "
.mode column
.headers on
SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;
"`
Ran command: `sqlite3 /Users/fujii0711/Claude/PrivateLLM/data/chroma/chroma.sqlite3 "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;"`
Ran command: `sqlite3 /Users/fujii0711/Claude/PrivateLLM/data/chroma/chroma.sqlite3 "SELECT * FROM collections;"`
Ran command: `sqlite3 /Users/fujii0711/Claude/PrivateLLM/data/chroma/chroma.sqlite3 "PRAGMA table_info(embedding_metadata);"`
Ran command: `sqlite3 /Users/fujii0711/Claude/PrivateLLM/data/chroma/chroma.sqlite3 "PRAGMA table_info(embeddings);"`
Ran command: `sqlite3 /Users/fujii0711/Claude/PrivateLLM/data/chroma/chroma.sqlite3 "SELECT id, key, string_value FROM embedding_metadata LIMIT 10;"`

구조를 파악했습니다. 핵심 정보가 담긴 SQL 쿼리들을 알려드립니다.

---

## SQLite Viewer에서 `jeonse_deposit` 데이터 조회하기

`chroma.sqlite3`를 VS Code에서 열면 상단에 **SQL 쿼리 입력창**이 있습니다. 아래 SQL을 붙여넣으면 됩니다.

---

### ✅ 핵심 구조 이해

ChromaDB는 메타데이터를 **세로 방향(EAV 구조)**으로 저장합니다.

```
embedding_metadata 테이블
─────────────────────────────────────────
 id │ key              │ string_value
────┼──────────────────┼─────────────────
  1 │ title            │ 민법 제1조(법원)
  1 │ ref              │ 제1조
  1 │ source_type      │ 법령
  1 │ chroma:document  │ 제1조(법원) 민사에 관하여...   ← 본문
  1 │ url              │ https://...
  1 │ date             │ 2023-07-19
  2 │ title            │ 민법 제2조(신의성실)
  ...
```

따라서 **가로로 읽으려면 피벗(PIVOT) SQL이 필요**합니다.

---

### 📋 SQL 쿼리 모음 (SQLite Viewer에 바로 붙여넣기)

#### 1. 청크 목록 가로로 보기 (핵심 쿼리)

```sql
SELECT
    e.embedding_id                                          AS chunk_id,
    MAX(CASE WHEN m.key = 'source_type'     THEN m.string_value END) AS source_type,
    MAX(CASE WHEN m.key = 'title'           THEN m.string_value END) AS title,
    MAX(CASE WHEN m.key = 'ref'             THEN m.string_value END) AS ref,
    MAX(CASE WHEN m.key = 'date'            THEN m.string_value END) AS date,
    MAX(CASE WHEN m.key = 'chroma:document' THEN m.string_value END) AS text,
    MAX(CASE WHEN m.key = 'url'             THEN m.string_value END) AS url
FROM embeddings e
JOIN embedding_metadata m ON e.id = m.id
GROUP BY e.id
ORDER BY e.id
LIMIT 50;
```

---

#### 2. 판례만 조회

```sql
SELECT
    e.embedding_id                                          AS chunk_id,
    MAX(CASE WHEN m.key = 'source_type'     THEN m.string_value END) AS source_type,
    MAX(CASE WHEN m.key = 'title'           THEN m.string_value END) AS title,
    MAX(CASE WHEN m.key = 'ref'             THEN m.string_value END) AS ref,
    MAX(CASE WHEN m.key = 'date'            THEN m.string_value END) AS date,
    MAX(CASE WHEN m.key = 'chroma:document' THEN m.string_value END) AS text
FROM embeddings e
JOIN embedding_metadata m ON e.id = m.id
GROUP BY e.id
HAVING MAX(CASE WHEN m.key = 'source_type' THEN m.string_value END) = '판례'
ORDER BY e.id;
```

---

#### 3. source_type별 개수 통계

```sql
SELECT
    string_value AS source_type,
    COUNT(DISTINCT id) AS chunk_count
FROM embedding_metadata
WHERE key = 'source_type'
GROUP BY string_value
ORDER BY chunk_count DESC;
```

---

#### 4. 본문 키워드 검색 (LIKE)

```sql
SELECT
    e.embedding_id AS chunk_id,
    MAX(CASE WHEN m.key = 'title'           THEN m.string_value END) AS title,
    MAX(CASE WHEN m.key = 'ref'             THEN m.string_value END) AS ref,
    MAX(CASE WHEN m.key = 'chroma:document' THEN m.string_value END) AS text
FROM embeddings e
JOIN embedding_metadata m ON e.id = m.id
GROUP BY e.id
HAVING MAX(CASE WHEN m.key = 'chroma:document' THEN m.string_value END) LIKE '%보증금%'
LIMIT 20;
```

---

#### 5. 컬렉션 설정 확인

```sql
SELECT id, name FROM collections;
```

---

> **💡 포인트**: `chroma:document` 키가 원문 텍스트입니다. `embedding_metadata` 테이블을 날 것으로 보면 세로로 나열되어 읽기 어렵지만, 위 피벗 쿼리를 쓰면 Excel처럼 한 줄에 청크 1개가 깔끔하게 표시됩니다.


---
관련 파일들을 살펴보겠습니다.

Viewed ChromaDB_select.md:1-277
Listed directory PrivateLLM

`ChromaDB_select.md` 파일을 이미 다 확인했습니다. `chroma:document` 키에 대해 설명드리겠습니다.

---

## `chroma:document` 키란?

ChromaDB가 `embedding_metadata` 테이블에 데이터를 저장할 때, **청크 원문 텍스트(본문)**를 보관하는 특별한 내부 키입니다.

### ChromaDB의 EAV 구조

ChromaDB는 메타데이터를 **세로 방향 (EAV: Entity–Attribute–Value)** 으로 저장합니다.

```
embedding_metadata 테이블
──────────────────────────────────────────
 id │ key              │ string_value
────┼──────────────────┼─────────────────
  1 │ title            │ 민법 제1조(법원)
  1 │ ref              │ 제1조
  1 │ source_type      │ 법령
  1 │ chroma:document  │ 제1조(법원) 민사에 관하여...  ← 📌 본문 텍스트
  1 │ url              │ https://...
  1 │ date             │ 2023-07-19
```

---

### 다른 키와의 차이점

| key | 역할 | 출처 |
|-----|------|------|
| `title` | 문서 제목 | 사용자가 add할 때 `metadatas=` 로 전달 |
| `ref` | 조항/판례 번호 | 사용자가 `metadatas=` 로 전달 |
| `source_type` | 법령 / 판례 구분 | 사용자가 `metadatas=` 로 전달 |
| `url` | 원문 링크 | 사용자가 `metadatas=` 로 전달 |
| `date` | 날짜 | 사용자가 `metadatas=` 로 전달 |
| **`chroma:document`** | **청크 원문 텍스트** | **ChromaDB가 `documents=` 인자를 자동으로 저장** |

---

### 왜 `chroma:` 접두사가 붙나?

ChromaDB가 **자체적으로 예약한 내부 키**이기 때문입니다. `col.add()` 를 호출할 때 `documents=["텍스트..."]` 로 넘기면, ChromaDB 내부적으로 `chroma:document` 라는 키로 `embedding_metadata` 테이블에 함께 저장합니다.

```python
col.add(
    ids=["prec-197932-판시사항"],
    documents=["보증금 반환에 관한 판례 본문..."],  # ← 이게 chroma:document 로 저장됨
    metadatas=[{"title": "...", "source_type": "판례", ...}],
    embeddings=[vec]
)
```

---

### SQLite에서 직접 조회할 때

SQLite Viewer로 `embedding_metadata` 테이블을 날 것으로 보면 세로로 나열되어 읽기 어렵습니다. 그래서 피벗 쿼리가 필요합니다:

```sql
MAX(CASE WHEN m.key = 'chroma:document' THEN m.string_value END) AS text
```

이 부분이 `chroma:document` 키를 꺼내 `text` 컬럼으로 가로로 펼치는 부분입니다.

---

**요약**: `chroma:document`는 사용자가 직접 만드는 키가 아니라, ChromaDB가 `documents=` 파라미터로 받은 **원문 텍스트를 내부적으로 저장할 때 자동으로 사용하는 예약 키**입니다.