"""yield 함수를 어떻게 선언하고 어떻게 호출하는지 모아 놓은 예제.

실행::

    python -X utf8 examples/yield_basics.py
"""

from collections.abc import Iterator


def title(text: str) -> None:
    print()
    print("-" * 58)
    print(text)
    print("-" * 58)


# ===========================================================================
# 1. 가장 단순한 선언
# ===========================================================================
# def 안에 yield 가 하나라도 있으면 그 함수는 '제너레이터 함수'가 된다.
# return 이 없어도 되고, 몸통에 yield 만 있으면 된다.


def greet():
    yield "안녕"
    yield "반가워"
    yield "잘 가"


def demo_basic() -> None:
    title("1. 선언과 호출")

    print("\n  선언:")
    print("    def greet():")
    print("        yield '안녕'")
    print("        yield '반가워'")
    print("        yield '잘 가'")

    gen = greet()  # <- 호출. 몸통은 아직 한 줄도 실행되지 않는다.
    print(f"\n  호출 결과 : {gen}")
    print(f"  타입      : {type(gen).__name__}")

    print("\n  next() 로 하나씩 꺼낸다 (yield 를 만날 때까지 실행되고 멈춘다):")
    print(f"    next(gen) -> {next(gen)}")
    print(f"    next(gen) -> {next(gen)}")
    print(f"    next(gen) -> {next(gen)}")

    print("\n  더 꺼내면 StopIteration:")
    try:
        next(gen)
    except StopIteration:
        print("    StopIteration  <- 끝났다는 신호")


# ===========================================================================
# 2. 호출하는 네 가지 방법
# ===========================================================================


def countdown(n: int) -> Iterator[int]:
    """인자를 받는 제너레이터. 타입 힌트는 Iterator[내보내는 타입]."""
    while n > 0:
        yield n
        n -= 1


def demo_call_styles() -> None:
    title("2. 호출하는 네 가지 방법")

    print("\n  (a) for 문 — 가장 흔하다. StopIteration 을 알아서 처리해 준다.")
    print("      ", end="")
    for i in countdown(5):
        print(i, end=" ")
    print()

    print("\n  (b) list() — 전부 꺼내 리스트로 만든다.")
    print(f"       {list(countdown(5))}")

    print("\n  (c) 다른 함수에 그대로 넘긴다 — sum, max, any, ' '.join ...")
    print(f"       sum : {sum(countdown(5))}")
    print(f"       max : {max(countdown(5))}")

    print("\n  (d) next() — 한 개씩 직접 꺼낸다. 끝나면 기본값을 받을 수도 있다.")
    gen = countdown(2)
    print(f"       {next(gen)}, {next(gen)}, {next(gen, '없음')}")

    print("\n  주의: 호출할 때마다 새 제너레이터가 생긴다. 위 (a)~(d)는 서로 별개다.")


# ===========================================================================
# 3. 조건에 따라 걸러 내보내기 (필터 형태)
# ===========================================================================
# yield 는 루프 안, if 안, 어디에 놔도 된다. 실행이 그 줄에 닿을 때 하나 나간다.


def evens_only(numbers) -> Iterator[int]:
    for n in numbers:
        if n % 2 == 0:
            yield n  # 짝수일 때만 내보낸다. 홀수면 그냥 다음 반복으로.


def demo_filter() -> None:
    title("3. 조건부 yield")

    data = [1, 2, 3, 4, 5, 6, 7, 8]
    print(f"\n  입력   : {data}")
    print(f"  짝수만 : {list(evens_only(data))}")


# ===========================================================================
# 4. return 으로 끝내기 / 반환값 받기
# ===========================================================================
# 제너레이터 안의 return 은 '값을 돌려주는' 게 아니라 '거기서 끝'이라는 뜻이다.
# 굳이 값을 붙이면 StopIteration.value 에 실려 온다.


def take_until_zero(numbers) -> Iterator[int]:
    count = 0
    for n in numbers:
        if n == 0:
            return f"0을 만나 {count}개에서 멈췄습니다"  # 여기서 종료
        count += 1
        yield n


def demo_return() -> None:
    title("4. return — 도중에 끝내기")

    print(f"\n  [1, 2, 0, 3, 4] -> {list(take_until_zero([1, 2, 0, 3, 4]))}")
    print("    0 뒤의 3, 4 는 나오지 않는다.")

    print("\n  return 에 붙인 값을 받고 싶다면:")
    gen = take_until_zero([1, 2, 0, 3, 4])
    try:
        while True:
            next(gen)
    except StopIteration as stop:
        print(f"    StopIteration.value = {stop.value!r}")


# ===========================================================================
# 5. yield from — 다른 제너레이터에게 넘기기
# ===========================================================================


def inner() -> Iterator[str]:
    yield "안"
    yield "쪽"


def outer() -> Iterator[str]:
    yield "["
    yield from inner()  # inner 가 내보내는 걸 그대로 흘려보낸다
    yield "]"


def demo_yield_from() -> None:
    title("5. yield from — 위임")

    print(f"\n  {''.join(outer())}")
    print("\n  yield from inner() 는 아래와 같은 뜻이다:")
    print("      for value in inner():")
    print("          yield value")


# ===========================================================================
# 6. 실전 형태 — 파일을 한 줄씩 (이 프로젝트 iter_records 와 같은 구조)
# ===========================================================================


def read_lines(text: str) -> Iterator[tuple[int, str]]:
    """줄 번호와 내용을 함께 내보낸다. 빈 줄은 건너뛴다."""
    for lineno, raw in enumerate(text.splitlines(), start=1):
        line = raw.strip()
        if not line:
            continue  # 아무것도 yield 하지 않으면 그 줄은 그냥 건너뛴 것이 된다
        yield lineno, line


def demo_real_shape() -> None:
    title("6. 실전 형태 — 줄 단위로 흘려보내기")

    sample = "첫 줄\n\n  셋째 줄  \n\n다섯째 줄\n"
    print("\n  입력 (빈 줄 포함):")
    for lineno, line in read_lines(sample):
        print(f"    {lineno}번째: {line!r}")

    print("\n  튜플을 yield 하면 for 문에서 바로 풀어 받을 수 있다.")
    print("  jsonl_to_json.iter_records 도 이 구조다 — 읽는 즉시 하나씩 내보낸다.")


def main() -> None:
    demo_basic()
    demo_call_styles()
    demo_filter()
    demo_return()
    demo_yield_from()
    demo_real_shape()
    print()


if __name__ == "__main__":
    main()
