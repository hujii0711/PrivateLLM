# 코드 재사용성 향상
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
# print(multiply(1, 3))
