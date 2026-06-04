from typing import Literal, TypedDict

SOURCE_TYPES = ("법령", "판례", "해설", "상담사례")
SourceType = Literal["법령", "판례", "해설", "상담사례"]


class Chunk(TypedDict):
    id: str
    text: str
    source_type: SourceType
    title: str
    ref: str
    url: str
    date: str


def make_chunk(*, id: str, text: str, source_type: str, title: str,
               ref: str, url: str, date: str) -> Chunk:
    if source_type not in SOURCE_TYPES:
        raise ValueError(f"unknown source_type: {source_type!r}")
    return Chunk(id=id, text=text, source_type=source_type, title=title,
                 ref=ref, url=url, date=date)
