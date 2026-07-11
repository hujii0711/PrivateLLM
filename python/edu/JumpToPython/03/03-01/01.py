money = True
if money:
    print("a")
    print("b")
    print("c")

m = 2000
if m >= 3000:
    print("a")
else:
    print("b")

if m >= 2000 or money:
    print("a")
else:
    print("b")

pocket = ["a", "b", "c"]
if "a" in pocket:
    print("a")
else:
    print("b")

if "a" in pocket:
    pass  # "아무런 동작도 수행하지 않음"을 명시
else:
    print("A")
