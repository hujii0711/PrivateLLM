"""임의의 스키마를 가진 XML을 JSON Lines(한 줄에 JSON 객체 하나)로 변환한다.

문서 구조를 미리 알 필요가 없도록, 모든 엘리먼트를 아래의 고정된 규칙으로 매핑한다.

* 속성(attribute)  -> ``"@이름"`` 키
* 자식 엘리먼트      -> 태그 이름을 키로 사용. 같은 태그가 반복되면 리스트가 된다.
* 텍스트            -> 리프 노드는 값 그 자체. 속성이나 자식이 함께 있으면 ``"#text"`` 키.
* 빈 엘리먼트        -> ``None``

레코드는 :func:`xml.etree.ElementTree.iterparse` 로 스트리밍하며, 한 건을 내보낸 뒤
바로 트리에서 떼어내므로 입력 파일이 아무리 커도 메모리 사용량은 일정하게 유지된다.

CLI 사용 예::

    uv run xml2jsonl data/catalog.xml -o data/catalog.jsonl --coerce
    uv run xml2jsonl data/catalog.xml --record-tag book --include-tag

참고: 표준 라이브러리 ElementTree는 신뢰할 수 없는 입력에 대한 방어가 완전하지 않다.
외부에서 받은 XML을 다룬다면 ``defusedxml`` 사용을 검토할 것.
"""

import argparse
import json
import re
import sys
from collections.abc import Iterator
from pathlib import Path
from typing import Any, BinaryIO, TextIO
from xml.etree.ElementTree import Element, iterparse

ATTR_PREFIX = "@"
TEXT_KEY = "#text"
TAG_KEY = "_tag"

# 앞자리 0이 붙은 값("007", "01234")은 우편번호/사번처럼 의미가 있으므로 숫자로 바꾸지 않는다.
_INT_RE = re.compile(r"^[+-]?(0|[1-9][0-9]*)$")
_FLOAT_RE = re.compile(r"^[+-]?(0|[1-9][0-9]*)(\.[0-9]+)?([eE][+-]?[0-9]+)?$")
_NULL_LITERALS = {"null", "nil", "none"}


def local_name(tag: str) -> str:
    """``{urn:example}book`` 처럼 네임스페이스가 붙은 이름에서 로컬 이름만 돌려준다."""
    return tag.rpartition("}")[2] if tag.startswith("{") else tag


def coerce_scalar(text: str) -> Any:
    """문자열을 bool/int/float/None 으로 추론한다. 실패하면 원본 문자열."""
    stripped = text.strip()
    if not stripped:
        return None
    lowered = stripped.lower()
    if lowered == "true":
        return True
    if lowered == "false":
        return False
    if lowered in _NULL_LITERALS:
        return None
    if _INT_RE.match(stripped):
        return int(stripped)
    if _FLOAT_RE.match(stripped):
        return float(stripped)
    return stripped


def element_to_obj(
    element: Element,
    *,
    strip_namespaces: bool = True,
    coerce: bool = False,
) -> Any:
    """엘리먼트 하나를 JSON 직렬화 가능한 값으로 변환한다."""
    to_key = local_name if strip_namespaces else str
    convert = coerce_scalar if coerce else _identity

    obj: dict[str, Any] = {}
    for attr_name, attr_value in element.attrib.items():
        obj[ATTR_PREFIX + to_key(attr_name)] = convert(attr_value)

    for child in element:
        key = to_key(child.tag)
        value = element_to_obj(child, strip_namespaces=strip_namespaces, coerce=coerce)
        if key not in obj:
            obj[key] = value
        elif isinstance(obj[key], list):
            obj[key].append(value)
        else:
            obj[key] = [obj[key], value]

    text = (element.text or "").strip()
    if not obj:
        # 속성도 자식도 없는 리프 노드는 값 자체가 된다.
        return convert(text) if text else None
    if text:
        obj[TEXT_KEY] = convert(text)
    return obj


def iter_records(
    source: BinaryIO | str | Path,
    *,
    record_tag: str | None = None,
    strip_namespaces: bool = True,
    coerce: bool = False,
) -> Iterator[tuple[str, Any]]:
    """XML을 스트리밍하며 ``(태그 이름, 변환된 값)`` 을 하나씩 내보낸다.

    ``record_tag`` 를 주면 깊이와 무관하게 그 태그를 레코드로 삼고,
    주지 않으면 루트의 직계 자식들을 레코드로 삼는다.
    """
    stack: list[Element] = []

    for event, element in iterparse(source, events=("start", "end")):
        if event == "start":
            stack.append(element)
            continue

        stack.pop()
        parent = stack[-1] if stack else None
        name = local_name(element.tag) if strip_namespaces else element.tag

        # record_tag 가 없으면 루트 바로 아래(깊이 1)를 레코드로 본다.
        selected = len(stack) == 1 if record_tag is None else name == record_tag
        if not selected:
            continue

        yield name, element_to_obj(element, strip_namespaces=strip_namespaces, coerce=coerce)

        # 처리한 레코드를 트리에서 떼어내 메모리를 회수한다. 루트의 직계 자식일 때만
        # 떼어내는데, 중첩된 레코드까지 제거하면 바깥 레코드가 손상되기 때문이다.
        element.clear()
        if parent is not None and parent is stack[0]:
            parent.remove(element)


def convert(
    source: BinaryIO | str | Path,
    out: TextIO,
    *,
    record_tag: str | None = None,
    strip_namespaces: bool = True,
    coerce: bool = False,
    include_tag: bool = False,
    ensure_ascii: bool = False,
) -> int:
    """XML을 읽어 JSONL로 써 넣고, 기록한 레코드 수를 돌려준다."""
    count = 0
    records = iter_records(
        source,
        record_tag=record_tag,
        strip_namespaces=strip_namespaces,
        coerce=coerce,
    )
    for tag, value in records:
        # JSONL 각 줄은 객체여야 하므로 스칼라 레코드는 "#text"로 감싼다.
        obj = value if isinstance(value, dict) else {TEXT_KEY: value}
        if include_tag:
            obj = {TAG_KEY: tag, **obj}
        out.write(json.dumps(obj, ensure_ascii=ensure_ascii))
        out.write("\n")
        count += 1
    return count


def _identity(value: str) -> str:
    return value


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="xml2jsonl",
        description="임의 스키마의 XML을 JSON Lines로 변환한다.",
    )
    parser.add_argument("input", help="입력 XML 경로 ('-' 이면 표준 입력)")
    parser.add_argument(
        "-o",
        "--output",
        help="출력 JSONL 경로 (생략하면 표준 출력)",
    )
    parser.add_argument(
        "--record-tag",
        help="레코드로 삼을 태그 이름 (생략하면 루트의 직계 자식)",
    )
    parser.add_argument(
        "--coerce",
        action="store_true",
        help="문자열을 bool/int/float/null 로 추론한다",
    )
    parser.add_argument(
        "--keep-namespaces",
        action="store_true",
        help="키에서 네임스페이스를 벗기지 않는다",
    )
    parser.add_argument(
        "--include-tag",
        action="store_true",
        help=f"각 줄에 원본 태그 이름을 {TAG_KEY!r} 키로 넣는다",
    )
    parser.add_argument(
        "--ascii",
        action="store_true",
        help="비 ASCII 문자를 \\uXXXX 로 이스케이프한다",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)

    source: BinaryIO | Path
    source = sys.stdin.buffer if args.input == "-" else Path(args.input)

    options = {
        "record_tag": args.record_tag,
        "strip_namespaces": not args.keep_namespaces,
        "coerce": args.coerce,
        "include_tag": args.include_tag,
        "ensure_ascii": args.ascii,
    }

    if args.output:
        out_path = Path(args.output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with out_path.open("w", encoding="utf-8", newline="\n") as out:
            count = convert(source, out, **options)
        print(f"{count} records -> {out_path}", file=sys.stderr)
    else:
        count = convert(source, sys.stdout, **options)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
