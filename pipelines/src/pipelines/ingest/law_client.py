from urllib.parse import urlencode

import requests

BASE = "https://www.law.go.kr/DRF"
# target별 본문 식별자 파라미터: 법령은 MST(법령일련번호), 판례는 ID(판례일련번호)
_ID_PARAM = {"law": "MST", "prec": "ID"}


class LawClient:
    """국가법령정보센터 DRF API를 호출하는 얇은 HTTP 클라이언트."""

    def __init__(self, oc: str, session=None, timeout: int = 20):
        """API 인증값과 요청 세션을 설정한다.

        테스트에서는 `session`을 주입해 실제 네트워크 호출 없이 응답을 흉내낼 수
        있고, 운영 실행에서는 requests.Session을 기본으로 재사용한다.
        """

        self.oc = oc
        self.session = session or requests.Session()
        self.timeout = timeout

    def _get(self, path: str, params: dict) -> str:
        """DRF 엔드포인트에 GET 요청을 보내고 XML 문자열을 반환한다."""

        url = f"{BASE}/{path}?{urlencode(params)}"
        print(f"_get >>> GET:::  {url}")
        resp = self.session.get(url, timeout=self.timeout)
        resp.raise_for_status()
        return resp.text

    def search(self, *, target: str, query: str, display: int = 20) -> str:
        """법령 또는 판례 검색 API를 호출해 검색 결과 XML을 받는다."""

        params = {
            "OC": self.oc,
            "target": target,
            "type": "XML",
            "query": query,
            "display": display,
        }
        return self._get("lawSearch.do", params)

    def fetch(self, *, target: str, id: str) -> str:
        """검색 결과의 식별자로 법령/판례 본문 XML을 조회한다.

        API가 대상별로 다른 식별자 파라미터명을 요구하므로 `target`에 맞춰
        법령은 MST, 판례는 ID를 사용한다.
        """

        params = {"OC": self.oc, "target": target, "type": "XML", _ID_PARAM[target]: id}
        return self._get("lawService.do", params)
