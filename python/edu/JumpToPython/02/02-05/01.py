a = {1 : "a"}
a[2] = "b"
print(a)

a["name"] = "pey"
print(a)

del a[1]
print(a)
print(a["name"])
print(a.keys())

for k in a.keys():
    print("key--------------------", k)
print(list(a.keys()))
print(a.values())
print(a.items())

print(a["name"])
print(a.get("name1"))

b = dict()
print(b)