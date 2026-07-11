def my_decorator(func):
    def wrapper():
        print("prev")
        func()
        print('post')
    return wrapper

@my_decorator #say_hello는 my_decorator
def say_hello():
    print("hello!!")

say_hello();