네. `server.tool()`은 **MCP 서버에서 LLM이 호출할 수 있는 Tool을 등록하는 핵심 API**입니다.

앞서 사용한 코드를 기준으로 보면:

```javascript
server.tool(
    "read_file",
    "Workspace 안의 파일 내용을 읽습니다.",
    {
        path: z.string().describe(
            "읽을 파일 경로. Workspace 기준 상대경로"
        )
    },
    async ({ path: filePath }) => {
        // 실제 작업
    }
);
```

이것을 4부분으로 나누어 이해하면 쉽습니다.

---

## 1. `server.tool()`의 기본 형태

현재 MCP TypeScript SDK에서 일반적으로 사용하는 형태는 다음과 같습니다.

```javascript
server.tool(
    name,
    description,
    inputSchema,
    handler
);
```

즉:

```text
server.tool(
    ① Tool 이름,
    ② Tool 설명,
    ③ 입력 파라미터 정의,
    ④ 실제 실행 함수
)
```

각각의 역할은 다음과 같습니다.

| 부분            | 역할                      |
| ------------- | ----------------------- |
| `name`        | LLM이 호출할 Tool의 이름       |
| `description` | LLM에게 이 Tool의 용도를 설명    |
| `inputSchema` | Tool에 전달할 파라미터 정의       |
| `handler`     | Tool이 실제 호출됐을 때 실행되는 코드 |

---

# 2. 첫 번째 인자: Tool 이름

```javascript
server.tool(
    "read_file",
    ...
);
```

`"read_file"`은 **MCP 표준에서 고정된 이름이 아닙니다.**

개발자가 자유롭게 정할 수 있습니다.

예를 들어:

```javascript
server.tool("read_file", ...);
```

또는

```javascript
server.tool("get_file_content", ...);
```

또는

```javascript
server.tool("load_document", ...);
```

모두 가능합니다.

다만 **LLM이 의미를 쉽게 파악할 수 있는 이름**을 사용하는 것이 좋습니다.

추천:

```text
read_file
write_file
search_files
execute_command
```

비추천:

```text
tool1
file_tool
do_something
abc
```

---

# 3. 두 번째 인자: Description

```javascript
server.tool(
    "read_file",

    "Workspace 안의 파일 내용을 읽습니다.",

    ...
);
```

이 부분은 **LLM에게 Tool의 용도를 설명하는 설명문**입니다.

예를 들어:

```javascript
"Workspace 안의 파일 내용을 읽습니다."
```

보다 다음처럼 작성하는 것이 좋습니다.

```javascript
`Workspace 내부의 텍스트 파일을 읽습니다.
파일을 수정하거나 삭제하지 않습니다.
path는 Workspace 기준 상대경로를 사용합니다.`
```

왜냐하면 LLM은 Tool을 선택할 때 **이 설명을 중요한 판단 정보로 사용하기 때문**입니다.

예를 들어 사용자가:

> `src/user.js` 내용을 보여줘.

라고 하면 LLM은 사용 가능한 Tool 중에서:

```text
read_file
→ 파일 내용을 읽음

write_file
→ 파일을 수정함

search_files
→ 파일에서 문자열을 검색함

execute_command
→ 명령어를 실행함
```

을 비교해서 `read_file`을 선택합니다.

---

# 4. 세 번째 인자: Input Schema

여기가 처음 보면 가장 헷갈리는 부분입니다.

```javascript
{
    path: z.string().describe(
        "읽을 파일 경로. Workspace 기준 상대경로"
    )
}
```

이것은 **LLM이 Tool을 호출할 때 어떤 데이터를 보내야 하는지 정의하는 부분**입니다.

즉:

```text
read_file
  └── path: string
```

이라는 의미입니다.

---

## 예를 들어 파라미터가 2개라면

```javascript
server.tool(
    "search_files",

    "파일 내용을 검색합니다.",

    {
        query: z.string().describe(
            "검색할 문자열"
        ),

        extension: z.string().optional().describe(
            "검색할 파일 확장자"
        )
    },

    async ({ query, extension }) => {

        ...
    }
);
```

LLM 입장에서는 대략:

```text
Tool: search_files

Description:
파일 내용을 검색합니다.

Parameters:

query
  type: string
  required
  description: 검색할 문자열

extension
  type: string
  optional
  description: 검색할 파일 확장자
```

처럼 이해할 수 있습니다.

따라서 사용자가:

> `.js` 파일에서 `axios`를 찾아줘.

라고 하면 LLM이:

```json
{
    "query": "axios",
    "extension": ".js"
}
```

형태로 Tool을 호출하게 됩니다.

---

# 5. `z.string()`은 무엇인가?

여기서:

```javascript
z.string()
```

은 **Zod라는 스키마 검증 라이브러리**의 문법입니다.

예를 들어:

```javascript
path: z.string()
```

은:

```text
path는 문자열이어야 한다
```

라는 뜻입니다.

다음과 같이 만들 수도 있습니다.

```javascript
{
    name: z.string(),

    age: z.number(),

    enabled: z.boolean()
}
```

그러면:

```text
name → 문자열
age → 숫자
enabled → true/false
```

가 됩니다.

---

# 6. `.describe()`는 매우 중요합니다

예를 들어:

```javascript
path: z.string().describe(
    "읽을 파일 경로. Workspace 기준 상대경로"
)
```

여기서 `.describe()`는 **개발자에게 보여주는 주석이라기보다 Tool의 파라미터 의미를 설명하는 메타데이터**라고 이해하는 것이 좋습니다.

즉:

```javascript
path: z.string()
```

보다는

```javascript
path: z.string().describe(
    "읽을 파일 경로. Workspace 기준 상대경로"
)
```

가 LLM에게 훨씬 유용합니다.

특히 Agent를 만들 때는 **description을 상당히 구체적으로 작성하는 것이 좋습니다.**

---

# 7. 네 번째 인자: Handler

마지막:

```javascript
async ({ path: filePath }) => {

    const absolutePath = resolveSafePath(filePath);

    const content = await fs.readFile(
        absolutePath,
        "utf8"
    );

    return {
        content: [
            {
                type: "text",
                text: content
            }
        ]
    };
}
```

이 부분이 **실제로 Tool이 실행됐을 때 수행되는 JavaScript 코드**입니다.

예를 들어 LLM이:

```text
read_file({
    path: "src/test.js"
})
```

를 요청하면 MCP SDK가 Handler를 실행합니다.

결과적으로:

```javascript
async ({ path: filePath }) => {
```

여기서:

```javascript
filePath === "src/test.js"
```

가 됩니다.

그리고:

```javascript
fs.readFile(...)
```

이 실제로 실행됩니다.

---

# 8. Handler의 return 형식

MCP Tool은 결과를 반환해야 합니다.

앞서 사용한:

```javascript
return {
    content: [
        {
            type: "text",
            text: content
        }
    ]
};
```

는 MCP의 Tool 결과 형식입니다.

가장 기본적인 텍스트 결과는:

```javascript
return {
    content: [
        {
            type: "text",
            text: "작업 완료"
        }
    ]
};
```

처럼 반환할 수 있습니다.

---

# 9. 실제 동작을 하나로 연결하면

다음 코드가 있다고 해보겠습니다.

```javascript
server.tool(
    "add",

    "두 숫자를 더합니다.",

    {
        a: z.number().describe("첫 번째 숫자"),
        b: z.number().describe("두 번째 숫자")
    },

    async ({ a, b }) => {

        const result = a + b;

        return {
            content: [
                {
                    type: "text",
                    text: String(result)
                }
            ]
        };
    }
);
```

사용자가:

> 10과 20을 더해줘.

라고 합니다.

LLM은 Tool 정보를 보고:

```text
add
a = 10
b = 20
```

을 호출합니다.

그러면 MCP 서버에서:

```javascript
async ({ a, b }) => {
```

가 실행되고:

```javascript
a = 10
b = 20
```

이 들어옵니다.

결과:

```text
30
```

이 다시 LLM에게 전달됩니다.

---

# 10. 여러 Tool을 등록할 수 있습니다

하나의 MCP Server에 여러 Tool을 등록할 수 있습니다.

```javascript
server.tool(
    "read_file",
    "...",
    {...},
    async (...) => {...}
);

server.tool(
    "write_file",
    "...",
    {...},
    async (...) => {...}
);

server.tool(
    "search_files",
    "...",
    {...},
    async (...) => {...}
);

server.tool(
    "execute_command",
    "...",
    {...},
    async (...) => {...}
);
```

그러면 LLM에게:

```text
사용 가능한 Tool

1. read_file
2. write_file
3. search_files
4. execute_command
```

가 제공되고, LLM이 상황에 따라 선택합니다.

---

# 11. `server.tool()`을 이해하는 가장 중요한 관점

`server.tool()`을 단순히 **"함수를 MCP에 등록하는 API"**라고 생각하면 조금 부족합니다.

좀 더 정확하게는:

```text
server.tool()
       │
       ├── 이름
       │
       ├── LLM에게 보여줄 설명
       │
       ├── LLM이 전달할 입력의 구조
       │
       └── 실제 실행할 함수
```

를 **하나의 Tool로 정의하는 것**입니다.

즉 아래 두 부분을 분리해서 생각하면 이해가 빠릅니다.

### LLM에게 알려주는 부분

```javascript
"read_file"

"Workspace 안의 파일 내용을 읽습니다."

{
    path: z.string().describe(
        "읽을 파일 경로"
    )
}
```

↓

**"이런 Tool이 있고 이렇게 사용해"**

### 실제 서버에서 실행되는 부분

```javascript
async ({ path }) => {

    const content =
        await fs.readFile(path, "utf8");

    return ...;
}
```

↓

**"실제로 이 코드를 실행해"**

---

## 12. 그래서 MCP Agent의 핵심은 결국 이겁니다

```text
사용자
  │
  │ "src/test.js 읽어줘"
  ▼
LLM
  │
  │ Tool 설명을 보고 판단
  ▼
read_file
  │
  │ { path: "src/test.js" }
  ▼
MCP Server
  │
  │ handler 실행
  ▼
fs.readFile()
  │
  ▼
파일 내용
  │
  ▼
LLM
```

그리고 LLM이 파일 내용을 보고

> "이 코드를 수정해야겠다."

라고 판단하면 다시:

```text
write_file
```

을 호출합니다.

**이 `server.tool()`의 개념을 이해하면 MCP 서버 개발의 핵심 구조를 거의 이해한 것입니다.**

원하시면 다음 단계로 **`server.tool()`의 실제 MCP SDK TypeScript/JavaScript API 스펙을 기준으로 `z.object()`, optional/default/enum/array/object 파라미터, 에러 처리, `isError`, 구조화된 반환값까지** 하나씩 예제와 함께 설명해드릴 수 있습니다.


---

Python에서는 공식 MCP Python SDK인 **`mcp` 패키지**를 사용해서 `server.tool()`을 비슷한 방식으로 구현할 수 있습니다.

Node.js에서:

```javascript
server.tool(
    "read_file",
    "Workspace 안의 파일 내용을 읽습니다.",
    {
        path: z.string()
    },
    async ({ path }) => {
        ...
    }
);
```

Python에서는 보통 **타입 힌트와 함수 docstring을 이용하는 방식**이 훨씬 간결합니다.

## 1. 설치

```bash
pip install mcp
```

## 2. 가장 간단한 `read_file`

```python
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("local-file-server")


@mcp.tool()
def read_file(path: str) -> str:
    """
    Workspace 안의 파일 내용을 읽습니다.

    Args:
        path: 읽을 파일 경로. Workspace 기준 상대경로
    """
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


if __name__ == "__main__":
    mcp.run()
```

Node.js의:

```javascript
server.tool(
    "read_file",
    "Workspace 안의 파일 내용을 읽습니다.",
    {
        path: z.string().describe(
            "읽을 파일 경로. Workspace 기준 상대경로"
        )
    },
    async ({ path: filePath }) => {
        ...
    }
);
```

와 거의 대응됩니다.

---

## 3. Node.js ↔ Python 대응

### Node.js

```javascript
server.tool(
    "read_file",

    "Workspace 안의 파일 내용을 읽습니다.",

    {
        path: z.string().describe(
            "읽을 파일 경로"
        )
    },

    async ({ path }) => {
        ...
    }
);
```

### Python

```python
@mcp.tool()
def read_file(path: str) -> str:
    """
    Workspace 안의 파일 내용을 읽습니다.

    Args:
        path: 읽을 파일 경로
    """
    ...
```

즉 Python에서는 함수 자체가 Tool의 정의가 됩니다.

```text
@mcp.tool()
     │
     ├── 함수 이름 → Tool 이름
     │
     ├── docstring → Tool 설명
     │
     ├── type hint → 입력 타입
     │
     └── 함수 코드 → 실제 실행 코드
```

---

# 4. 네 가지 Tool을 Python으로 구현하면

앞서 만들었던 4개를 Python으로 작성하면 다음과 같습니다.

```python
from mcp.server.fastmcp import FastMCP

import subprocess
from pathlib import Path


# --------------------------------------------------
# MCP Server
# --------------------------------------------------

mcp = FastMCP("local-file-server")


# --------------------------------------------------
# Workspace
# --------------------------------------------------

WORKSPACE = Path("./workspace").resolve()
WORKSPACE.mkdir(parents=True, exist_ok=True)


# --------------------------------------------------
# Workspace 밖 접근 방지
# --------------------------------------------------

def resolve_safe_path(file_path: str) -> Path:

    path = (WORKSPACE / file_path).resolve()

    try:
        path.relative_to(WORKSPACE)
    except ValueError:
        raise ValueError(
            f"Workspace 밖의 파일에는 접근할 수 없습니다: {file_path}"
        )

    return path


# ==================================================
# 1. read_file
# ==================================================

@mcp.tool()
def read_file(path: str) -> str:
    """
    Workspace 안의 파일 내용을 읽습니다.

    Args:
        path: 읽을 파일 경로. Workspace 기준 상대경로
    """

    file_path = resolve_safe_path(path)

    return file_path.read_text(
        encoding="utf-8"
    )


# ==================================================
# 2. write_file
# ==================================================

@mcp.tool()
def write_file(path: str, content: str) -> str:
    """
    Workspace 안의 파일을 생성하거나 수정합니다.

    Args:
        path: 수정할 파일 경로. Workspace 기준 상대경로
        content: 저장할 파일 전체 내용
    """

    file_path = resolve_safe_path(path)

    file_path.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    file_path.write_text(
        content,
        encoding="utf-8"
    )

    return f"파일을 저장했습니다: {path}"


# ==================================================
# 3. search_files
# ==================================================

@mcp.tool()
def search_files(
    query: str,
    extension: str | None = None
) -> str:
    """
    Workspace의 파일에서 문자열을 검색합니다.

    Args:
        query: 검색할 문자열
        extension: 검색할 파일 확장자. 예: .py, .js, .ts
    """

    results = []

    for file_path in WORKSPACE.rglob("*"):

        if not file_path.is_file():
            continue

        # node_modules, .git 제외
        if any(
            part in {"node_modules", ".git"}
            for part in file_path.parts
        ):
            continue

        if extension and not file_path.name.endswith(
            extension
        ):
            continue

        try:

            content = file_path.read_text(
                encoding="utf-8"
            )

        except (UnicodeDecodeError, PermissionError):
            continue

        for line_number, line in enumerate(
            content.splitlines(),
            start=1
        ):

            if query in line:

                results.append(
                    f"{file_path.relative_to(WORKSPACE)}:"
                    f"{line_number}: "
                    f"{line.strip()}"
                )

    if not results:
        return "검색 결과가 없습니다."

    return "\n".join(results)


# ==================================================
# 4. execute_command
# ==================================================

@mcp.tool()
def execute_command(command: str) -> str:
    """
    Workspace에서 shell 명령을 실행합니다.

    Args:
        command: 실행할 shell 명령
    """

    result = subprocess.run(
        command,
        shell=True,
        cwd=WORKSPACE,
        capture_output=True,
        text=True,
        timeout=30
    )

    output = []

    if result.stdout:
        output.append(
            f"[stdout]\n{result.stdout}"
        )

    if result.stderr:
        output.append(
            f"[stderr]\n{result.stderr}"
        )

    output.append(
        f"[exit code] {result.returncode}"
    )

    return "\n\n".join(output)


# --------------------------------------------------
# MCP Server 실행
# --------------------------------------------------

if __name__ == "__main__":
    mcp.run()
```

---

# 5. Python에서 특히 재미있는 부분

Node.js에서는 Tool 정의를 위해:

```javascript
{
    path: z.string(),
    content: z.string()
}
```

처럼 **Zod Schema를 별도로 작성**했는데, Python FastMCP에서는:

```python
def write_file(
    path: str,
    content: str
) -> str:
```

처럼 **Python의 Type Hint를 이용해서 Schema를 자동으로 생성**합니다.

예를 들어:

```python
@mcp.tool()
def search_files(
    query: str,
    extension: str | None = None
) -> str:
```

이면 MCP가 대략 다음과 같은 Tool Schema를 만들어줍니다.

```text
search_files

query:
    string
    required

extension:
    string
    optional
```

따라서 Python MCP에서는 **Type Hint가 굉장히 중요합니다.**

---

# 6. Python에서는 함수 이름도 Tool 이름이 된다

예를 들어:

```python
@mcp.tool()
def read_file(path: str) -> str:
```

이면 Tool 이름은:

```text
read_file
```

입니다.

```python
@mcp.tool()
def search_files(query: str) -> str:
```

이면:

```text
search_files
```

가 됩니다.

즉:

```text
Python 함수
    ↓
@mcp.tool()
    ↓
MCP Tool
```

입니다.

그리고 docstring:

```python
"""
Workspace 안의 파일 내용을 읽습니다.

Args:
    path: 읽을 파일 경로
"""
```

은 Tool의 **description과 parameter 설명을 생성하는 데 사용**됩니다.

---

## 7. Node.js와 Python의 차이를 한눈에 보면

| 개념        | Node.js         | Python           |
| --------- | --------------- | ---------------- |
| Tool 등록   | `server.tool()` | `@mcp.tool()`    |
| Tool 이름   | 문자열로 지정         | 함수 이름            |
| 설명        | 문자열             | docstring        |
| 입력 Schema | Zod             | Python Type Hint |
| 실행 코드     | handler         | 함수 본문            |
| 반환값       | MCP content 구조  | 보통 `str` 반환      |
| 비동기       | `async`         | `async def`      |

그래서 Python MCP는 상당히 깔끔합니다.

```python
@mcp.tool()
def read_file(path: str) -> str:
    """파일을 읽습니다."""
    ...
```

이 몇 줄만으로 **Tool 이름 + 설명 + 입력 Schema + 실행 함수**가 모두 정의됩니다.

다음 단계에서는 이 Python 서버에 **`@mcp.resource()`와 `@mcp.prompt()`까지 추가하면 Tools / Resources / Prompts를 모두 사용하는 하나의 완성된 MCP 서버**가 됩니다.
