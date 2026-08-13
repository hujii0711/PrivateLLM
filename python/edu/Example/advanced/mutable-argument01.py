"""
*args는 **"인자를 몇 개를 넘기든 다 받아서 하나의 튜플(tuple)로 묶어준다"**는 뜻이에요.
별표(*)가 핵심이고 args라는 이름 자체는 관례일 뿐 다른 이름을 써도 됩니다.

가변 인자 (variable-length argument): 개수가 정해지지 않은 인자를 받을 수 있다는 의미의 일반적인 명칭

*args → 가변 위치 인자 (variable positional arguments)
콤마로 나열된 값들을 튜플로 묶음

**kwargs → 가변 키워드 인자 (variable keyword arguments)
key=value 형태로 넘긴 값들을 딕셔너리로 묶음
"""


def add_many(*args):
    # args = (1, 2, 3)   # 자동으로 튜플로 묶임
    result = 0
    for i in args:
        result = result + i
    return result


a = add_many(1, 2, 3)
print(a)


def add_many2(args):
    result = 0
    for i in args:
        result = result + i
    return result


b = add_many2([1, 2, 3])
print(b)
