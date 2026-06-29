from urllib.parse import parse_qs, urlsplit

from pipelines.ingest.law_client import LawClient


class FakeResponse:
    def __init__(self, text):
        self.text = text
        self.status_code = 200

    def raise_for_status(self): pass


class FakeSession:
    def __init__(self): self.calls = []
    def get(self, url, timeout=None):
        self.calls.append(url)
        return FakeResponse("<xml/>")


def _q(url):
    return {k: v[0] for k, v in parse_qs(urlsplit(url).query).items()}


def test_search_url_has_expected_params():
    sess = FakeSession()
    client = LawClient(oc="myoc", session=sess)
    client.search(target="law", query="주택임대차보호법", display=5)
    url = sess.calls[0]
    assert urlsplit(url).path == "/DRF/lawSearch.do"
    q = _q(url)
    assert q["OC"] == "myoc"
    assert q["target"] == "law"
    assert q["type"] == "XML"
    assert q["query"] == "주택임대차보호법"
    assert q["display"] == "5"


def test_fetch_law_uses_MST_param():
    sess = FakeSession()
    client = LawClient(oc="myoc", session=sess)
    client.fetch(target="law", id="123456")
    q = _q(sess.calls[0])
    assert urlsplit(sess.calls[0]).path == "/DRF/lawService.do"
    assert q["MST"] == "123456"
    assert q["target"] == "law"


def test_fetch_prec_uses_ID_param():
    sess = FakeSession()
    client = LawClient(oc="myoc", session=sess)
    client.fetch(target="prec", id="98765")
    q = _q(sess.calls[0])
    assert q["ID"] == "98765"
    assert q["target"] == "prec"


def test_returns_response_text():
    client = LawClient(oc="myoc", session=FakeSession())
    assert client.search(target="prec", query="보증금") == "<xml/>"
