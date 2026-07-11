def time_decorator(func):
    def wrapper(*args, **kwargs): # 전달 받아야 하는 기존 함수의 입력 인수를 알 수 없는 경우에 *args, **kwargs 매개변수 이용
        print("prev")
        print(args)
        print(kwargs)
        result = func(*args, **kwargs)
        print('post')
    return wrapper

@time_decorator #say_hello는 my_decorator의 인자가 된다.
def sample_function(n):
    sum = 0
    for i in range(n):
        print("i=====",i)
        sum +=i
    return sum

sample_function(1000);