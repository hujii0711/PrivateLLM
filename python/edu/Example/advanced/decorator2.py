# 함수 실행 전 + 후에 동작을 끼워 넣는 데코레이터
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
