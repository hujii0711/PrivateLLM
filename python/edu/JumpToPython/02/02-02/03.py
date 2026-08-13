# 문자열 안의 특정한 값을 바꾸는 것을 문자열 포매팅이다.
a = "I eat %d apples." %2
print(a)

number = 2
a = "I eat %d apples." % number
print(a)

a = "I eat %s apples." % "two"
print(a)

number = 10
day = "three"
a = "I ate %d apples. so I was sick for %s days." % (number, day)
print(a)

a = "Error is %d%%." % 98
print(a)

a = "%10s" % "hi"
print(a)

a = "%-10sjane" %"hi"
print(a)

a = "%0.4f" % 3.412345678
print(a)

a = "I eat {0} apples".format(3)
print(a)

number = 10
day = "three"
a = "I ate {0} apples. so I was sick for {1} days.".format(number, day)
print(a)

a = "I ate {number} apples. so I was sick for {day} days.".format(number=10, day="three")
print(a)

a = "I ate {0} apples. so I was sick for {day} days.".format(10, day="three")
print(a)