# 기초 ①
# 숫자 리스트 변환

# 각 요소에 연산을 적용해 새 리스트를 만듭니다.
nums = [1, 2, 3, 4, 5]

# 각 숫자를 제곱
squares = [n**2 for n in nums]
# → [1, 4, 9, 16, 25]

# 각 숫자에 10 곱하기
tens = [n * 10 for n in nums]
# → [10, 20, 30, 40, 50]


# 기초 ②
# 문자열 리스트 변환
# 문자열 메서드도 그대로 사용할 수 있습니다.
words = ["apple", "banana", "cherry"]

# 모두 대문자로
upper = [w.upper() for w in words]
# → ["APPLE", "BANANA", "CHERRY"]

# 글자 수 구하기
lengths = [len(w) for w in words]
# → [5, 6, 6]

# 조건 필터 ③
# if 조건으로 걸러내기
# 조건을 만족하는 요소만 골라 새 리스트를 만듭니다. (else 없음)
nums = [1, 2, 3, 4, 5, 6, 7, 8]

# 짝수만 추출
evens = [n for n in nums if n % 2 == 0]
# → [2, 4, 6, 8]

# 5보다 큰 수만 추출
big = [n for n in nums if n > 5]
# → [6, 7, 8]

# 조건 변환 ④
# if-else로 값 바꾸기
# 조건에 따라 다른 값을 넣습니다. (모든 요소가 결과에 포함됨)
nums = [1, 2, 3, 4, 5]

# 짝수면 "짝", 홀수면 "홀"
labels = ["짝" if n % 2 == 0 else "홀" for n in nums]
# → ["홀", "짝", "홀", "짝", "홀"]

# 음수는 0으로 변환
scores = [-3, 5, -1, 8]
fixed = [s if s >= 0 else 0 for s in scores]
# → [0, 5, 0, 8]

# 중첩 ⑤
# range()와 함께 사용
# 리스트 없이 숫자 범위를 바로 순회합니다.

# 1~10 중 3의 배수
threes = [n for n in range(1, 11) if n % 3 == 0]
# → [3, 6, 9]

# 구구단 2단
dan2 = [2 * i for i in range(1, 10)]
# → [2, 4, 6, 8, 10, 12, 14, 16, 18]

# 중첩 ⑥
# 이중 for문 (2차원 → 1차원)
# 리스트 안의 리스트를 하나로 펼칩니다.
matrix = [[1, 2], [3, 4], [5, 6]]

flat = [x for row in matrix for x in row]
# → [1, 2, 3, 4, 5, 6]

# 일반 for문으로 풀면
flat = []
for row in matrix:
    for x in row:
        flat.append(x)

# 실전 ⑦
# 딕셔너리·문자열 활용
# 다양한 자료형에서 원하는 값만 추출합니다.

# 딕셔너리 리스트에서 특정 필드 추출
users = [
    {"name": "Alice", "age": 25},
    {"name": "Bob", "age": 17},
    {"name": "Carol", "age": 30},
]

# 성인(18세 이상) 이름만
adults = [u["name"] for u in users if u["age"] >= 18]
# → ["Alice", "Carol"]

# 공백 제거 후 빈 문자열 걸러내기
raw = ["  hello  ", "", " world", "  "]
clean = [s.strip() for s in raw if s.strip()]
# → ["hello", "world"]
