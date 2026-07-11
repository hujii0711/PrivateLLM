a = [1,2,3,4]
result = []
for num in a:
  result.append(num*3)
print(result)

b = [1,2,3,4]
result2 = [num*3 for num in b]
print(result2)