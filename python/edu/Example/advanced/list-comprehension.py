a = [1, 2, 3, 4]

# 방법 1 — 전통적인 for 루프
result = []
for num in a:
    result.append(num * 3)
print(result)

# 방법 2 — 리스트 컴프리헨션
result2 = [num * 3 for num in a]
print(result2)

# 리터럴 직접 사용
result2_ = [num * 3 for num in [1, 2, 3, 4]]
print(result2_)

# 조건 필터링 — 짝수만
result3 = [num * 3 for num in a if num % 2 == 0]
print(result3)

# 조건 필터링 — 홀수만
result4 = [num * 3 for num in a if num % 2 == 1]
print(result4)

result5 = [num * 3 for num in a if num % 2 == 0 for num in a if num % 2 == 1]
print(result5)
