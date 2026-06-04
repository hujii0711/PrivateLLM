from dataclasses import dataclass


@dataclass
class Retrieved:
    id: str
    text: str
    similarity: float          # cosine 유사도 (1 - distance)
    source_type: str
    title: str
    ref: str
    url: str
    date: str


@dataclass
class Source:
    n: int                     # 인용 번호 [n]
    title: str
    ref: str
    url: str
    source_type: str
