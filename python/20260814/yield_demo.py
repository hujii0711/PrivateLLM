"""yield 가 있을 때와 없을 때의 차이를 눈으로 확인하는 예제.

실행::

    uv run python examples/yield_demo.py
    python examples/yield_demo.py
"""

import sys
import time
import tracemalloc


def title(text: str) -> None:
    print()
    print("=" * 60)
    print(text)
    print("=" * 60)


# ---------------------------------------------------------------------------
# 실험 1: 함수 몸통이 "언제" 실행되는가
# ---------------------------------------------------------------------------
# 두 함수는 하는 일이 똑같다. 리스트로 모으느냐, yield 로 흘려보내느냐만 다르다.


def make_list(n: int) -> list[int]:
    result = []
    for i in range(1, n + 1):
        print(f"    [만드는 중] {i}")
        result.append(i * i)
    return result


def make_gen(n: int):
    for i in range(1, n + 1):
        print(f"    [만드는 중] {i}")
        yield i * i


def demo_when_it_runs() -> None:
    title("실험 1. 함수 몸통이 언제 실행되나")

    print("\n[리스트] 호출하는 순간 ...")
    values = make_list(3)
    print(f"  -> 호출이 끝났다. 결과: {values}")
    print("  이제 하나씩 꺼내 본다:")
    for v in values:
        print(f"    [받음] {v}")

    print("\n[yield] 호출하는 순간 ...")
    gen = make_gen(3)
    print(f"  -> 아무것도 출력되지 않았다. 결과: {gen}")
    print("  이제 하나씩 꺼내 본다:")
    for v in gen:
        print(f"    [받음] {v}")

    print("\n  차이: 리스트는 '만들기'가 다 끝난 뒤 '받기'가 시작된다.")
    print("        yield 는 만들기와 받기가 한 개씩 번갈아 일어난다.")


# ---------------------------------------------------------------------------
# 실험 2: 메모리
# ---------------------------------------------------------------------------


def squares_list(n: int) -> list[int]:
    """전부 리스트에 담아 반환한다."""
    result = []
    for i in range(n):
        result.append(i * i)
    return result


def squares_yield(n: int):
    """하나씩 흘려보낸다. 나머지 실험과 같은 def + yield 형태."""
    for i in range(n):
        yield i * i


def demo_memory(n: int = 1_000_000) -> None:
    title(f"실험 2. 메모리 사용량 ({n:,}개)")

    tracemalloc.start()
    total_list = sum(squares_list(n))  # 100만 개를 전부 메모리에 올린 뒤 더한다
    peak_list = tracemalloc.get_traced_memory()[1]
    tracemalloc.stop()

    tracemalloc.start()
    total_yield = sum(squares_yield(n))  # 하나 만들어 더하고 버리기를 반복한다
    peak_yield = tracemalloc.get_traced_memory()[1]
    tracemalloc.stop()

    # 참고: (i * i for i in range(n)) 같은 제너레이터 표현식도 위 squares_yield 와
    # 똑같은 제너레이터 객체를 만든다. 문법만 짧을 뿐 동작은 동일하다.
    tracemalloc.start()
    total_expr = sum(i * i for i in range(n))
    peak_expr = tracemalloc.get_traced_memory()[1]
    tracemalloc.stop()

    print(f"\n  리스트로 모으기      : {peak_list / 1024 / 1024:8.2f} MB")
    print(f"  yield 로 흘려보내기  : {peak_yield / 1024 / 1024:8.2f} MB")
    print(f"  제너레이터 표현식    : {peak_expr / 1024 / 1024:8.2f} MB  <- yield 와 같은 물건")
    print(f"\n  차이 : {peak_list / max(peak_yield, 1):,.0f} 배")
    print(f"  (세 방식 모두 합계는 같다: {total_list == total_yield == total_expr})")


# ---------------------------------------------------------------------------
# 실험 3: 첫 결과가 나오기까지 걸리는 시간
# ---------------------------------------------------------------------------
# 한 건 처리에 0.2초가 걸리는 느린 작업이라고 가정한다.


def slow_list(n: int) -> list[int]:
    result = []
    for i in range(n):
        time.sleep(0.2)
        result.append(i)
    return result


def slow_gen(n: int):
    for i in range(n):
        time.sleep(0.2)
        yield i


def demo_latency(n: int = 5) -> None:
    title("실험 3. 첫 결과가 나오기까지")

    start = time.perf_counter()
    for i, _ in enumerate(slow_list(n), start=1):
        print(f"    [리스트] {i}번째 결과 도착 ... {time.perf_counter() - start:.2f}초")

    start = time.perf_counter()
    for i, _ in enumerate(slow_gen(n), start=1):
        print(f"    [yield ] {i}번째 결과 도착 ... {time.perf_counter() - start:.2f}초")

    print("\n  차이: 리스트는 전부 끝나야 첫 결과가 나온다.")
    print("        yield 는 0.2초 만에 첫 결과가 나오고 이어서 계속 흐른다.")


# ---------------------------------------------------------------------------
# 실험 4: 제너레이터는 한 번 쓰면 끝 (yield 를 쓸 때 치르는 대가)
# ---------------------------------------------------------------------------


def demo_one_shot() -> None:
    title("실험 4. 두 번 순회하면?")

    values = [1, 2, 3]
    print(f"\n  [리스트] 1차: {list(values)}")
    print(f"  [리스트] 2차: {list(values)}   <- 몇 번이든 다시 볼 수 있다")

    gen = (v for v in [1, 2, 3])
    print(f"\n  [yield ] 1차: {list(gen)}")
    print(f"  [yield ] 2차: {list(gen)}          <- 비어 있다! 이미 다 써 버렸다")

    print("\n  len() 도 안 된다:")
    try:
        len(v for v in [1, 2, 3])
    except TypeError as exc:
        print(f"    TypeError: {exc}")

    print("\n  그래서 다시 봐야 하면 list() 로 한 번 붙잡아 둬야 한다.")


# ---------------------------------------------------------------------------
# 실험 5: 리스트로는 아예 불가능한 것 — 끝이 없는 수열
# ---------------------------------------------------------------------------


def fibonacci():
    """무한 피보나치. 리스트로 만들면 영원히 끝나지 않는다."""
    a, b = 0, 1
    while True:
        yield a
        a, b = b, a + b


def demo_infinite() -> None:
    title("실험 5. 끝이 없는 수열")

    picked = []
    for value in fibonacci():
        if value > 1000:
            break  # 필요한 만큼만 받고 멈춘다
        picked.append(value)

    print(f"\n  1000 이하 피보나치: {picked}")
    print("\n  리스트로 만들려면 무한 루프에 빠진다. yield 라서 가능한 일이다.")


# ---------------------------------------------------------------------------
# 실험 6: 이 프로젝트의 실제 코드 (jsonl_to_json.iter_records)
# ---------------------------------------------------------------------------


def demo_real_module() -> None:
    title("실험 6. 실제 코드: iter_records vs load")

    sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parents[1] / "src"))
    try:
        from pythontest.jsonl_to_json import iter_records, load
    except ImportError as exc:  # pragma: no cover
        print(f"\n  모듈을 불러오지 못했습니다: {exc}")
        return

    import io

    jsonl = '{"id": 1}\n{"id": 2}\n{"id": 3}\n'

    records = iter_records(io.StringIO(jsonl))
    print(f"\n  iter_records(...) 호출 결과 : {records}")
    print("    -> 아직 파일을 한 줄도 안 읽었다. 꺼낼 때 비로소 읽는다.")
    print(f"    첫 줄만 꺼내 보면      : {next(records)}")
    print("    -> 나머지 두 줄은 여전히 안 읽은 상태다.")

    rows = load(io.StringIO(jsonl))
    print(f"\n  load(...) 호출 결과        : {rows}")
    print("    -> 전부 읽어서 리스트로 들고 있다. list(iter_records(...)) 와 같다.")


def main() -> None:
    demo_when_it_runs()
    demo_memory()
    demo_latency()
    demo_one_shot()
    demo_infinite()
    demo_real_module()
    print()


if __name__ == "__main__":
    main()
