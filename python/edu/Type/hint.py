# 변수
name: str = "Alice"
age: int = 30
height: float = 1.75
is_active: bool = True

# 함수
def greet(name: str, age: int) -> str:
    return f"안녕하세요, {name}님! 나이: {age}"

print(greet(name=name, age=age))