"""JSON Lines 파일을 읽어 하나의 JSON 문서로 합친다.

:mod:`pythontest.xml_to_jsonl` 의 역방향 도구다. JSONL은 한 줄에 JSON 값 하나가
들어 있는 형식이라, 줄 단위로 읽으면 파일 전체를 메모리에 올리지 않고도 파싱할 수 있다.
출력 역시 배열 원소를 하나씩 흘려 쓰므로 입력이 커져도 메모리 사용량은 일정하다.

JSONL을 다룰 때 실제로 문제가 되는 지점들을 처리한다.

* 빈 줄은 건너뛴다 (파일 끝 개행, 편집기가 남긴 공백 줄).
* 깨진 줄은 **몇 번째 줄인지** 알려준다. 수만 줄짜리 파일에서 이 정보가 없으면 손을 못 댄다.
* ``--skip-invalid`` 로 깨진 줄만 버리고 계속 진행할 수 있다.
* Windows 편집기가 붙인 BOM을 자동으로 벗긴다.

CLI 사용 예::

    uv run jsonl2json data/catalog.jsonl -o data/catalog.json
    uv run jsonl2json data/catalog.jsonl --wrap-key records --indent 4
    uv run jsonl2json data/catalog.jsonl --compact --skip-invalid
"""

import argparse
import json
import sys
import textwrap
from collections.abc import Callable, Generator, Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any, TextIO

DEFAULT_INDENT = 2


class JsonlDecodeError(ValueError):
    """JSONL 한 줄을 파싱하지 못했을 때. 몇 번째 줄인지 함께 담는다."""

    def __init__(self, lineno: int, reason: str, line: str) -> None:
        self.lineno = lineno
        self.reason = reason
        self.line = line
        preview = line if len(line) <= 80 else line[:77] + "..."
        super().__init__(f"{lineno}번째 줄을 파싱할 수 없습니다: {reason}\n  {preview}")


@contextmanager
def _open_text(source: str | Path | TextIO) -> Generator[TextIO]:
    """경로면 열고 닫아 주고, 이미 열린 파일 객체면 그대로 넘긴다."""
    if isinstance(source, (str, Path)):
        # utf-8-sig 로 열면 BOM이 있든 없든 올바르게 읽힌다.
        with Path(source).open("r", encoding="utf-8-sig") as handle:
            yield handle
    else:
        yield source


def iter_records(
    source: str | Path | TextIO,
    *,
    skip_invalid: bool = False,
    on_error: Callable[[JsonlDecodeError], None] | None = None,
) -> Iterator[Any]:
    """JSONL을 한 줄씩 파싱해 파이썬 객체로 내보낸다.

    ``skip_invalid`` 가 거짓이면 첫 번째 깨진 줄에서 :class:`JsonlDecodeError` 를 던지고,
    참이면 그 줄을 건너뛰며 ``on_error`` 콜백에 알린다.
    """
    with _open_text(source) as handle:
        for lineno, raw_line in enumerate(handle, start=1):
            line = raw_line.strip()
            if not line:
                continue
            try:
                yield json.loads(line)
            except json.JSONDecodeError as exc:
                error = JsonlDecodeError(lineno, exc.msg, line)
                if not skip_invalid:
                    raise error from exc
                if on_error is not None:
                    on_error(error)


def load(source: str | Path | TextIO, *, skip_invalid: bool = False) -> list[Any]:
    """JSONL 전체를 리스트로 읽어 들인다. 파일이 작을 때 쓰는 편의 함수."""
    return list(iter_records(source, skip_invalid=skip_invalid))


def write_json(
    records: Iterator[Any],
    out: TextIO,
    *,
    indent: int | None = DEFAULT_INDENT,
    ensure_ascii: bool = False,
    wrap_key: str | None = None,
) -> int:
    """레코드를 JSON 배열로 흘려 쓰고, 기록한 개수를 돌려준다.

    ``indent`` 가 ``None`` 이면 공백 없이 최소 크기로 출력한다.
    ``wrap_key`` 를 주면 배열을 ``{"<키>": [...]}`` 객체로 감싼다.
    """
    compact = indent is None
    newline = "" if compact else "\n"
    dump_options: dict[str, Any] = {"ensure_ascii": ensure_ascii}
    if compact:
        dump_options["separators"] = (",", ":")
    else:
        dump_options["indent"] = indent

    def pad(level: int) -> str:
        return "" if compact else " " * (indent * level)

    level = 0
    if wrap_key is not None:
        key = json.dumps(wrap_key, ensure_ascii=ensure_ascii)
        out.write("{" + newline + pad(1) + key + (":" if compact else ": "))
        level = 1

    out.write("[")
    count = 0
    for record in records:
        out.write("," if count else "")
        out.write(newline)
        text = json.dumps(record, **dump_options)
        out.write(textwrap.indent(text, pad(level + 1)) if not compact else text)
        count += 1
    if count:
        out.write(newline + pad(level))
    out.write("]")

    if wrap_key is not None:
        out.write(newline + "}")
    out.write("\n")
    return count


def convert(
    source: str | Path | TextIO,
    out: TextIO,
    *,
    indent: int | None = DEFAULT_INDENT,
    ensure_ascii: bool = False,
    wrap_key: str | None = None,
    skip_invalid: bool = False,
    on_error: Callable[[JsonlDecodeError], None] | None = None,
) -> int:
    """JSONL을 읽어 JSON 문서로 써 넣고, 기록한 레코드 수를 돌려준다."""
    records = iter_records(source, skip_invalid=skip_invalid, on_error=on_error)
    return write_json(
        records,
        out,
        indent=indent,
        ensure_ascii=ensure_ascii,
        wrap_key=wrap_key,
    )


def _convert_to_file(source: str | Path | TextIO, out_path: Path, options: dict[str, Any]) -> int:
    """임시 파일에 쓴 뒤 성공했을 때만 목적지로 옮긴다.

    레코드를 흘려 쓰기 때문에 도중에 실패하면 잘린 JSON이 남는다. 임시 파일을 거치면
    목적지는 '완전한 JSON' 아니면 '건드리지 않은 원래 상태' 둘 중 하나만 된다.
    """
    out_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = out_path.with_name(out_path.name + ".tmp")
    succeeded = False
    try:
        with tmp_path.open("w", encoding="utf-8", newline="\n") as out:
            count = convert(source, out, **options)
        succeeded = True
    finally:
        if not succeeded:
            tmp_path.unlink(missing_ok=True)
    tmp_path.replace(out_path)
    print(f"{count} records -> {out_path}", file=sys.stderr)
    return count


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="jsonl2json",
        description="JSON Lines 파일을 하나의 JSON 문서로 합친다.",
    )
    parser.add_argument("input", help="입력 JSONL 경로 ('-' 이면 표준 입력)")
    parser.add_argument("-o", "--output", help="출력 JSON 경로 (생략하면 표준 출력)")
    parser.add_argument(
        "--indent",
        type=int,
        default=DEFAULT_INDENT,
        help=f"들여쓰기 칸 수 (기본 {DEFAULT_INDENT})",
    )
    parser.add_argument(
        "--compact",
        action="store_true",
        help="공백 없이 한 줄로 출력한다 (--indent 무시)",
    )
    parser.add_argument(
        "--wrap-key",
        help="배열을 '{\"<키>\": [...]}' 객체로 감싼다",
    )
    parser.add_argument(
        "--skip-invalid",
        action="store_true",
        help="파싱 못 한 줄을 건너뛴다 (기본은 오류로 중단)",
    )
    parser.add_argument(
        "--ascii",
        action="store_true",
        help="비 ASCII 문자를 \\uXXXX 로 이스케이프한다",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)

    source: str | Path | TextIO
    source = sys.stdin if args.input == "-" else Path(args.input)

    skipped = 0

    def report(error: JsonlDecodeError) -> None:
        nonlocal skipped
        skipped += 1
        print(f"건너뜀: {error}", file=sys.stderr)

    options: dict[str, Any] = {
        "indent": None if args.compact else args.indent,
        "ensure_ascii": args.ascii,
        "wrap_key": args.wrap_key,
        "skip_invalid": args.skip_invalid,
        "on_error": report,
    }

    try:
        if args.output:
            _convert_to_file(source, Path(args.output), options)
        else:
            convert(source, sys.stdout, **options)
    except JsonlDecodeError as error:
        # 트레이스백 대신 줄 번호가 담긴 메시지만 보여 준다.
        print(f"오류: {error}", file=sys.stderr)
        print("깨진 줄을 무시하려면 --skip-invalid 를 쓰세요.", file=sys.stderr)
        return 1

    if skipped:
        print(f"{skipped}개 줄을 건너뛰었습니다.", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
