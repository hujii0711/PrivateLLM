# 파이썬의 데코레이터는 기본적으로 다른 함수를 수정하지 않고 그 기능을 확장하거나 변경할 수 있도록 해주는 고급 기능이다.
# 데코레이터는 함수를 다른 함수의 인자로써 받아 어떤 처리를 한 후 그 함수를 반환하거나 다른 함수를 반환한다.
def my_decorator(func):
    def wrapper():
        print("prev")
        func()
        print('post')
    return wrapper

def say_hello():
    print("hello!!")

say_hello = my_decorator(say_hello)
say_hello();