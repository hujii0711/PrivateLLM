## ChromaDB 데이터를 눈으로 보는 방법

### 방법 1: SQLiteViewer (가장 쉬움) — VS Code 확장

ChromaDB는 내부적으로 **SQLite** 파일(`chroma.sqlite3`)을 사용합니다. VS Code에서 바로 열 수 있습니다.

Ran command: `code --install-extension qwtel.sqlite-viewer`

`code` CLI가 없으니 수동으로 설치하시면 됩니다. 사용 방법을 안내합니다.

---

## 방법별 가이드

### ✅ 방법 1: VS Code + SQLite Viewer (추천 — 설치 없이 바로)

1. VS Code 확장 탭 (`Cmd+Shift+X`) → **"SQLite Viewer"** (qwtel 작성) 검색 후 설치
2. VS Code 탐색기에서 아래 파일을 클릭하여 열기:
   ```
   /Users/fujii0711/Claude/PrivateLLM/data/chroma/chroma.sqlite3
   ```
3. 테이블 목록에서 **`embedding_metadata`**, **`embeddings`** 클릭 → 데이터 확인

> 주요 테이블:
> | 테이블 | 내용 |
> |--------|------|
> | `collections` | 컬렉션 목록 (`jeonse_deposit`) |
> | `embeddings` | 각 청크 ID + 임베딩 벡터 |
> | `embedding_metadata` | source_type, title, ref, url, date |

---

### ✅ 방법 2: Python 스크립트로 직접 조회 (가장 확실)

아래 스크립트를 실행하면 터미널에서 바로 데이터를 확인할 수 있습니다.

Created view_chroma.py
Ran command: `cd /Users/fujii0711/Claude/PrivateLLM/pipelines && uv run python scripts/view_chroma.py --stats`

스크립트가 잘 작동합니다. 이제 목록 조회도 테스트합니다.

Ran command: `cd /Users/fujii0711/Claude/PrivateLLM/pipelines && uv run python scripts/view_chroma.py --limit 5 --source 판례`

완벽하게 동작합니다. 전체 가이드를 정리합니다.

---

## ChromaDB 데이터 조회 방법 정리

현재 DB 상태: **총 1,264개 청크** (법령 1,235개 + 판례 29개)

---

### ✅ 방법 1: 직접 만든 Python 뷰어 스크립트 (지금 바로 사용 가능)

[view_chroma.py](file:///Users/fujii0711/Claude/PrivateLLM/pipelines/scripts/view_chroma.py)

```bash
# 실행 위치: pipelines/ 디렉터리에서

# 통계 확인
uv run python scripts/view_chroma.py --stats

# 목록 조회 (기본 20개)
uv run python scripts/view_chroma.py

# 판례만 조회
uv run python scripts/view_chroma.py --source 판례

# 법령 50개 조회
uv run python scripts/view_chroma.py --source 법령 --limit 50

# 유사도 검색 (bge-m3 모델 사용, 처음 실행 시 느림)
uv run python scripts/view_chroma.py --query "보증금 반환"
```

---

### ✅ 방법 2: VS Code + SQLite Viewer 확장 (GUI)

1. `Cmd+Shift+X` → **SQLite Viewer** (작성자: qwtel) 설치
2. 탐색기에서 아래 파일을 클릭
   ```
   data/chroma/chroma.sqlite3
   ```
3. 아래 테이블을 클릭하면 데이터가 표로 보임

| 테이블 | 볼 수 있는 것 |
|--------|--------------|
| `collections` | 컬렉션 이름·설정 |
| `embedding_metadata` | title, ref, source_type, url, date |
| `embeddings` | 청크 ID 목록 |

> **주의**: 임베딩 벡터(1024차원 float 배열)는 binary blob으로 저장되어 SQLite로는 숫자로 읽기 어렵습니다. 텍스트 메타데이터 확인용으로 활용하세요.

---

### ✅ 방법 3: ChromaDB 공식 Web UI (Chroma 0.6+)

```bash
# pipelines 디렉터리에서
uv run chroma run --path ../data/chroma --port 8000
```

브라우저에서 `http://localhost:8000` 접속 → 컬렉션 목록·문서 브라우징 가능

> `chromadb >= 0.5` 버전이라면 버전에 따라 `chroma run` 명령이 없을 수 있습니다. 그 경우 방법 1이 가장 안정적입니다.