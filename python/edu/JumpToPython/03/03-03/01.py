test_list = ["one", "two", "three"]
for i in test_list:
    print(i)

a = [(1, 2), (3, 4), (5, 6)]
for f, s in a:
    print(f + s)

print(range(10))
b = range(10)
print(b)

add = 0
for i in range(1, 11):
    add = add + i
print(add)

c = [1, 2, 3, 4]
result = []
for num in c:
    result.append(num * 3)
print(result)

result2 = [num * 3 for num in c]
print(result2)
