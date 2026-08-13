# 1. 초기 딕셔너리 생성 (키: 값)
student = {
    "name": "이몽룡",
    "age": 20
}
print("초기 상태:", student)


# 2. 데이터 추가 (또는 수정)
# 없는 키에 값을 할당하면 새로 추가되고, 있는 키면 값이 수정됩니다.
student["major"] = "컴퓨터공학"
student["age"] = 21  # 기존 age 수정
print("추가/수정 후:", student)


# 3. 데이터 조회 (가져오기)
# 방법 A: 대괄호 [] 사용 (키가 없으면 에러 발생)
name_value = student["name"]
print("조회(대괄호):", name_value)

# 방법 B: .get() 메서드 사용 (키가 없으면 None 반환 - 더 안전함)
major_value = student.get("major")
hobby_value = student.get("hobby", "독서") # 키가 없을 때 기본값(독서) 지정도 가능
print("조회(.get):", major_value)
print("조회(기본값):", hobby_value)


# 4. 데이터 삭제
# 방법 A: del 키워드 사용 (삭제와 동시에 값을 반환하지 않음)
del student["age"]
print("del 삭제 후:", student)

# 방법 B: .pop() 메서드 사용 (삭제하면서 그 값을 꺼내옴)
removed_major = student.pop("major")
print("pop으로 꺼낸 값:", removed_major)
print("pop 삭제 후:", student)


# 예제 딕셔너리 (과일 재고)
fruit_stock = {
    "apple": 3,
    "banana": 5,
    "cherry": 2
}

# 패턴 1: 키(Key)만 순회하기
print("--- 1. 키만 순회 ---")
for fruit in fruit_stock:  # dict.keys()를 사용해도 결과는 같습니다.
    print(f"과일 이름: {fruit}")

print("\n--- 2. 값(Value)만 순회 ---")
# 패턴 2: 값(Value)만 순회하기 (.values() 사용)
for count in fruit_stock.values():
    print(f"재고 수량: {count}")

print("\n--- 3. 키와 값(Key, Value) 동시에 순회 ---")
# 패턴 3: 키와 값을 쌍으로 순회하기 (.items() 사용)
# 딕셔너리 순회에서 가장 많이 쓰이는 방식입니다. (Key, Value) (키와 값의 튜플 쌍)
for fruit, count in fruit_stock.items():
    print(f"{fruit}의 재고는 {count}개 남았습니다.")