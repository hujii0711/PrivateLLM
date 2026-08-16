**단계별 상세**

1. **사용자 질문**: "지난주에 가장 많이 팔린 상품 19개 보여줘"라는 자연어 요청이 호스트 앱(Claude Desktop, LangChain 앱 등)에 입력됩니다.

2. **LLM 오케스트레이터**: LLM이 이 요청을 보고 "이건 DB 조회가 필요하다"고 판단합니다. 이 시점에서 이미 로드된 도구 목록(`@mysql/mcp-server`가 노출한 `query` 같은 도구의 스키마)을 참고해서, 어떤 도구를 어떤 파라미터로 호출할지 결정합니다. 보통 LLM이 직접 SQL 문자열을 만들어서 넘기거나(예: `run_query(sql="SELECT ...")`), 서버가 자연어→SQL 변환을 대신 해주는 구조라면 조건(기간, 정렬 기준, limit)만 파라미터로 넘깁니다.

3. **MCP 클라이언트**: 호스트 내부의 MCP 클라이언트가 LLM의 도구 호출 결정을 실제 `tools/call` 요청(JSON-RPC)으로 변환해서 MySQL MCP 서버로 전송합니다.

4. **MySQL MCP 서버 (`@mysql/mcp-server`)**: 요청을 받아 SQL을 검증하고(인젝션 방지, 허용된 쿼리 타입인지 등), 미리 설정된 커넥션 정보로 실제 MySQL에 연결해서 쿼리를 실행합니다. 예를 들면 내부적으로 이런 쿼리가 실행될 수 있어요.
```sql
SELECT product_name, SUM(quantity) AS total_sold
FROM order_items
JOIN orders ON orders.id = order_items.order_id
WHERE orders.created_at >= DATE_SUB(CURDATE(), INTERVAL 1 WEEK)
GROUP BY product_name
ORDER BY total_sold DESC
LIMIT 19;
```

5. **결과 반환**: 쿼리 결과(19개 행)를 JSON 형태로 MCP 클라이언트에 반환하고, 클라이언트는 이를 다시 LLM의 컨텍스트에 도구 실행 결과로 넣어줍니다.

6. **LLM 응답 생성**: LLM이 원시 JSON 데이터를 사람이 읽기 좋은 표나 목록 형태로 정리해서 최종 답변을 사용자에게 보여줍니다.

**참고할 점**

- `npm install @mysql/mcp-server` 같은 패키지명은 예시로 든 것이라, 실제로 설치하려면 정확한 공식 MySQL MCP 서버 패키지명(예: 커뮤니티에서 관리하는 `mysql-mcp-server` 계열)을 npm이나 GitHub에서 확인하시는 걸 권장해요.
- 실무에서는 LLM이 자유롭게 임의 SQL을 생성하게 두기보다, 서버 쪽에서 **읽기 전용(SELECT만 허용)**, **화이트리스트 테이블/컬럼**, **쿼리 타임아웃** 등을 강제하는 게 안전합니다. 특히 이번 예시처럼 매출/판매량 데이터를 다룰 땐 실수로 `UPDATE`나 `DELETE`가 실행되지 않도록 서버 단에서 쿼리 종류를 검증하는 게 중요해요.