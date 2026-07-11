def add_many(*args):
    result = 0
    for i in args:
        result = result + i
    return result

a = add_many(1,2,3)
print(a)

def add_many2(args):
    result = 0
    for i in args:
        result = result + i
    return result

b = add_many2([1,2,3])
print(b)