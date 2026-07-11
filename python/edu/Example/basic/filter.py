def postive(x: int):
    return x > 0


print(list(filter(postive, [-1, 2, 1, 4])))
