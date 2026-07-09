def inner():
    yield 1
    yield 2


def outer():
    yield from inner()  # inner의 yield를 그대로 위임
    yield from [3, 4, 5]  # 이터러블도 가능
    yield 6


print(list(outer()))  # [1, 2, 3, 4, 5, 6]
