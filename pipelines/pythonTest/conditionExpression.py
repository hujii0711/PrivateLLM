# 조건 표현식(삼항 연산자)

# ① 가장 기본 형태
age = 20
if age >= 18:
    result = "성인"
else:
    result = "미성년자"
# ↓ 한 줄로 줄이면
result = "성인" if age >= 18 else "미성년자"
print(result)  # 출력: 성인

# ② 숫자 비교
# 두 수 중 더 큰 값을 고릅니다.
a, b = 10, 20
bigger = a if a > b else b
print(bigger)  # 출력: 20


# ③ 함수 안에서 바로 반환
# 함수의 return 문에서 직접 사용할 수 있습니다.
def is_even(n):
    return "짝수" if n % 2 == 0 else "홀수"


print(is_even(4))  # → 짝수
print(is_even(7))  # → 홀수

# ④ 리스트 컴프리헨션과 함께
# 리스트를 만들면서 각 요소에 조건을 적용합니다.
nums = [1, 2, 3, 4, 5]
labels = ["짝" if n % 2 == 0 else "홀" for n in nums]
# → ["홀", "짝", "홀", "짝", "홀"]

# 위와 동일
labels2 = []
for n in nums:
    if n % 2 == 0:
        labels2.append("짝")
    else:
        labels2.append("홀")

# 위 코드와 아래 코드의 결과가 동일합니다
# ⑤ 중첩 삼항 연산자 (주의!)
# 중첩은 가능하지만, 가독성이 나빠져서 남용하면 안 됩니다.

score = 75
grade = "A" if score >= 90 else "B" if score >= 80 else "C"
# → "C"
