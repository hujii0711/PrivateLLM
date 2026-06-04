from urllib.parse import urlencode

import requests

BASE = "https://www.law.go.kr/DRF"
# target별 본문 식별자 파라미터: 법령은 MST(법령일련번호), 판례는 ID(판례일련번호)
_ID_PARAM = {"law": "MST", "prec": "ID"}


class LawClient:
    def __init__(self, oc: str, session=None, timeout: int = 20):
        self.oc = oc
        self.session = session or requests.Session()
        self.timeout = timeout

    def _get(self, path: str, params: dict) -> str:
        url = f"{BASE}/{path}?{urlencode(params)}"
        resp = self.session.get(url, timeout=self.timeout)
        resp.raise_for_status()
        return resp.text

    def search(self, *, target: str, query: str, display: int = 20) -> str:
        params = {"OC": self.oc, "target": target, "type": "XML",
                  "query": query, "display": display}
        return self._get("lawSearch.do", params)

    def fetch(self, *, target: str, id: str) -> str:
        params = {"OC": self.oc, "target": target, "type": "XML",
                  _ID_PARAM[target]: id}
        return self._get("lawService.do", params)
