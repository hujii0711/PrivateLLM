# 클로저 방식 — 함수로 동일하게 구현
def mul(m):
    def wrapper(n):
        return m * n

    return wrapper


mul3 = mul(3)
mul5 = mul(5)

print(mul3(10))  # 30
print(mul5(10))  # 50

#                 클래스 방식             클로저 방식
# 상태 저장         self.m                외부 함수 변수 m
# 호출 방식         __call__              내부 함수 wrapper
# 코드 길이         길다                   짧다
# 확장성            높다(메서드 추가 가능)    낮다
# 결과             동일 30, 50            동일 30, 50