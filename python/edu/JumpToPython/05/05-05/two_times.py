# two_times.py
def two_times(numberList):
    result = []
    for number in numberList:
        result.append(number * 2)
    return result


result = two_times([1, 2, 3, 4])
print(result)


def two_times2(x):
    return x * 2


print(list(map(two_times2, [1, 2, 3, 4])))

print(list(zip([1, 2, 3], [4, 5, 6])))
