a = 1
def vartest(a):
    a = a + 1
vartest(a)
print(a)

def vartest2(a):
    a = a + 1
    return a
a = vartest2(a)
print(a)
    