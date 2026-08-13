result = 0


def add(num):
    global result
    result += num  # 3, 7
    return result


print(add(3))
print(add(4))
