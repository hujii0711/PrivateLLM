# 1. 코드 재사용성 향상
# 같은 기능을 여러 함수에 반복 작성할 필요 없이, 데코레이터 하나로 적용할 수 있습니다.
def log(func):
    def wrapper(*args, **kwargs):
        print(args)
        print(kwargs)
        print(f"{func.__name__} 호출됨")
        return func(*args, **kwargs)

    return wrapper


@log
def add(a, b):
    return a + b


@log
def multiply(a, b):
    return a * b


print(add(1, 3))
print(multiply(1, 3))


# 2. 실행 전 + 후에 동작을 끼워 넣는 데코레이터
# func(...)의 반환값을 변수에 담아두면, 실행 후 동작도 추가할 수 있습니다.
def log_before_after(func):
    def wrapper(*args, **kwargs):
        print(f"[전] {func.__name__} 호출됨, 인자={args}, {kwargs}")
        result = func(*args, **kwargs)  # 원래 함수 실행 (결과 보관)
        print(f"[후] {func.__name__} 반환값={result}")
        return result  # 보관한 결과 반환

    return wrapper


@log_before_after
def subtract(a, b):
    return a - b


print(subtract(10, 3))
