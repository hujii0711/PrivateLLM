def add_many(*args): # 매개변수 이름 앞에 *을 붙이면 입력값을 전부 모아 튜플로 만들어준다.
    result = 0
    for i in args:
        result = result + i
    return result

print(add_many(1, 2, 3, 4, 5))

def print_kwargs(**kwargs): # 매개변수 이름 앞에 **을 붙이면 매개변수 kwargs는 딕셔너리가 되고 모든 key=value 형태의 입력값이 그 딕셔너리에 저장된다
    print(kwargs)

print_kwargs(a=1)
print_kwargs(name='foo', age=3)

def add_and_mul(a, b):
    return a+b, a*b
result = add_and_mul(3, 4)
print(result)
result1, result2 = add_and_mul(3, 4)
print(result1)
print(result2)