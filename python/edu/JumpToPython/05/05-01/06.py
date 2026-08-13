class Family:
    lastname = "김"


# 클래스 변수는 객체 변수와 달리 클래스로 만든 모든 객체에 공유된다.
a = Family()
b = Family()
print(a.lastname)
Family.lastname = "박"
print(b.lastname)
