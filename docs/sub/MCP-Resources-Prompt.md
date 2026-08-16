네. MCP의 **Tools / Resources / Prompts**는 역할이 서로 다릅니다.

```text
MCP Server
├── Tools
│   └── LLM이 "행동"을 수행
│       예: 파일 읽기, 파일 수정, 명령 실행
│
├── Resources
│   └── LLM에게 "데이터"를 제공
│       예: 설정 파일, 문서, DB 데이터
│
└── Prompts
    └── LLM에게 사용할 "프롬프트 템플릿" 제공
        예: 코드 리뷰 프롬프트, 파일 분석 프롬프트
```

앞서 만든 파일 MCP 서버에 각각 추가해보겠습니다.

---

# 1. Resources 예제

Resources는 **LLM이 읽을 수 있는 데이터/정보를 MCP 서버가 제공하는 기능**입니다.

예를 들어 다음 파일이 있다고 하겠습니다.

```text
workspace/
├── README.md
├── package.json
└── src/
    └── test.js
```

`README.md`를 Resource로 제공할 수 있습니다.

개념적으로:

```text
MCP Server
    │
    └── Resource
          │
          └── file:///workspace/README.md
```

## Resource 등록

MCP SDK에서는 URI를 이용해서 Resource를 식별합니다.

```javascript
server.resource(
    "project_readme",
    "file:///workspace/README.md",
    {
        description: "프로젝트 README 문서",
        mimeType: "text/markdown"
    },
    async (uri) => {

        const content = await fs.readFile(
            path.join(WORKSPACE, "README.md"),
            "utf8"
        );

        return {
            contents: [
                {
                    uri: uri.href,
                    mimeType: "text/markdown",
                    text: content
                }
            ]
        };
    }
);
```

여기서 중요한 점은 Tool과 상당히 다르다는 것입니다.

### Tool

```javascript
server.tool(
    "read_file",
    ...
);
```

LLM이:

```text
"이 파일을 읽어야겠다"
```

라고 판단해서 **Tool을 호출**합니다.

### Resource

```javascript
server.resource(
    "project_readme",
    ...
);
```

MCP Client가 Resource를 발견하고 **해당 데이터를 컨텍스트로 가져올 수 있습니다.**

---

# 2. Resource를 URI로 생각하면 쉽습니다

Resource는 일반적으로 이런 형태로 생각하면 됩니다.

```text
file:///workspace/README.md
```

또는:

```text
config://application
```

```text
db://users/100
```

```text
docs://api/authentication
```

즉 **"어떤 데이터를 식별하는 주소"**에 가깝습니다.

예를 들어:

```text
docs://project/architecture
```

라는 Resource를 만들었다면 MCP 서버가:

```text
docs://project/architecture
        ↓
프로젝트 아키텍처 문서
```

를 반환하도록 만들 수 있습니다.

---

# 3. Resource와 `read_file`의 차이

이 부분이 상당히 중요합니다.

### `read_file`

Tool입니다.

```text
LLM
 ↓
read_file("src/test.js")
 ↓
MCP Server
 ↓
파일 읽기
```

즉 **행동(action)** 입니다.

반면 Resource는:

```text
MCP Server
 ↓
Resource 목록
 ↓
file:///workspace/README.md
 ↓
문서 내용
```

처럼 **데이터(data)**를 제공합니다.

간단하게 기억하면:

```text
Tool     = 무엇인가를 해라
Resource = 이것을 읽어라
Prompt   = 이렇게 질문해라
```

라고 생각하면 됩니다.

---

# 4. Prompt 예제

Prompt는 **재사용할 수 있는 프롬프트 템플릿**을 MCP 서버에서 제공하는 기능입니다.

예를 들어 우리가 코딩 Agent를 만들고 있고:

> 이 파일을 코드 리뷰해줘.

라는 작업을 자주 한다고 해보겠습니다.

그러면 MCP Server에 `code_review` Prompt를 만들어둘 수 있습니다.

```javascript
server.prompt(
    "code_review",

    "소스 코드를 코드 리뷰합니다.",

    {
        file: z.string().describe(
            "리뷰할 파일 경로"
        )
    },

    ({ file }) => {

        return {
            messages: [
                {
                    role: "user",
                    content: {
                        type: "text",
                        text: `
다음 파일을 코드 리뷰해주세요.

파일:
${file}

다음 항목을 확인해주세요.

1. 버그 가능성
2. 보안 문제
3. 성능 문제
4. 가독성
5. 유지보수성
6. 개선할 코드

문제가 발견되면 구체적인 수정 방법도 제안해주세요.
`
                    }
                }
            ]
        };
    }
);
```

그러면 MCP Client가 이 Prompt를 발견할 수 있습니다.

```text
code_review
```

그리고:

```text
file = src/auth.js
```

를 전달하면 다음과 같은 프롬프트가 만들어집니다.

```text
다음 파일을 코드 리뷰해주세요.

파일:
src/auth.js

다음 항목을 확인해주세요.

1. 버그 가능성
2. 보안 문제
3. 성능 문제
4. 가독성
5. 유지보수성
6. 개선할 코드
```

---

# 5. Prompt는 Tool과 다릅니다

이 둘을 헷갈리기 쉽습니다.

### Tool

```javascript
server.tool(
    "read_file",
    ...
);
```

하면 실제로:

```javascript
fs.readFile(...)
```

이 실행됩니다.

즉 **컴퓨터에서 무언가를 실행**합니다.

반면:

```javascript
server.prompt(
    "code_review",
    ...
);
```

는 파일을 읽거나 수정하지 않습니다.

단순히:

```text
"코드 리뷰를 할 때 사용할 프롬프트 템플릿"
```

을 제공합니다.

---

# 6. 세 가지를 하나의 예제로 연결

예를 들어 우리가 **코드 분석 MCP Server**를 만든다고 해보겠습니다.

```text
                  MCP Server
                      │
        ┌─────────────┼─────────────┐
        │             │             │
       Tool        Resource       Prompt
        │             │             │
        ▼             ▼             ▼
    read_file     README.md      code_review
    write_file    API 문서       bug_analysis
    search_files  설정 정보       refactoring
    execute_cmd
```

각각의 역할은:

### Tool

```text
read_file
```

→ 실제 파일을 읽는다.

### Resource

```text
docs://project/architecture
```

→ 프로젝트 아키텍처 문서를 제공한다.

### Prompt

```text
code_review
```

→ 코드 리뷰를 위한 표준 프롬프트를 제공한다.

---

# 7. 실제 Agent에서는 세 가지가 같이 사용될 수 있습니다

예를 들어 사용자가:

> `src/login.js`의 보안 문제를 분석하고 수정해줘.

라고 하면 Agent가 다음과 같은 작업을 할 수 있습니다.

```text
사용자
 │
 │ "login.js 보안 문제 분석하고 수정"
 ▼
LLM
 │
 ├── Resource 읽기
 │      │
 │      └── docs://project/security-guideline
 │
 ├── Tool
 │      │
 │      └── read_file("src/login.js")
 │
 ├── 분석
 │
 ├── Tool
 │      │
 │      └── write_file(...)
 │
 └── Tool
        │
        └── execute_command("npm test")
```

Prompt는 이 과정에서:

```text
code_security_review
```

라는 **표준화된 분석 방법**을 제공하는 데 사용할 수 있습니다.

---

# 8. 그런데 실제로는 중요한 차이가 하나 있습니다

**Tools는 LLM이 능동적으로 호출하는 것**이 핵심입니다.

예:

```text
사용자
 ↓
LLM
 ↓
"read_file이 필요하다"
 ↓
Tool 호출
```

반면 Resources는 **MCP Client/호스트가 Resource를 어떻게 노출하느냐**가 중요합니다.

즉:

```text
Resource
    ↓
MCP Client
    ↓
LLM Context
```

라는 흐름을 이해해야 합니다.

그리고 Prompts 역시 단순히 "LLM이 알아서 사용하는 프롬프트"라기보다는 **MCP 서버가 재사용 가능한 프롬프트 템플릿을 제공하고, 클라이언트가 그것을 선택/사용하는 구조**에 가깝습니다.

---

# 9. 파일 MCP 서버라면 어떻게 설계하는 게 좋나?

지금 만들고 계신 목적이라면 저는 다음처럼 나누는 것을 추천합니다.

```text
File MCP Server
│
├── Tools
│   ├── read_file
│   ├── write_file
│   ├── search_files
│   ├── delete_file
│   └── execute_command
│
├── Resources
│   ├── project://readme
│   ├── project://package-json
│   └── project://config
│
└── Prompts
    ├── code_review
    ├── bug_analysis
    └── refactoring
```

### 특히 중요한 것은

```text
Tool
```

과

```text
Resource
```

의 구분입니다.

예를 들어 **프로젝트의 `package.json`을 항상 읽을 수 있게 제공**하고 싶다면 Resource가 적합하고,

```text
"package.json을 읽어라"
```

라는 요청에 따라 **동적으로 파일을 찾아 읽게 하는 것**이라면 Tool이 적합합니다.

---

## 한 줄로 정리하면

```text
Tools     → LLM이 "행동"하도록 만든다
Resources → LLM에게 "데이터"를 제공한다
Prompts   → LLM에게 "작업 방법/프롬프트"를 제공한다
```

그리고 지금 만들고 있는 **로컬 파일 조작 Agent**에서는 `Tools`가 가장 핵심이고, `Resources`와 `Prompts`는 Agent가 커졌을 때 프로젝트 문서나 작업 규칙을 표준화하는 용도로 추가하는 것이 좋습니다.
