def postive(x: int):
    return x > 0


a = [-1, 2, 1, 4]

print(list(filter(postive, a)))
print(list(filter(postive, [-1, 2, 1, 4])))
