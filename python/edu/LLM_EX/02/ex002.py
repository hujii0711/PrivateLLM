# import os
# current_path = os.path.dirname(os.path.abspath(__file__))
# file_path = os.path.join(current_path, "the-verdict.txt")

# with open(file_path, "r", encoding="utf-8") as f:
#     raw_text = f.read()

# print("총 문자 개수:", len(raw_text))
# print(raw_text[:99])

import re

# 단편 소설을 텍스트 샘플 파일로 읽기
with open("the-verdict.txt", "r", encoding="utf-8") as f:
    raw_text = f.read()

print("총 문자 개수:", len(raw_text))
print(raw_text[:99])


text = "Hello, world. This, is a test."
# 다음 정규 표현식은 공백을 기준으로 텍스트를 나눕니다.
result1 = re.split(r'(\s)', text)
print(result1)

# 공백으로만 나누지 않고 쉼표나 마침표도 나눕니다.
result2 = re.split(r'([,.]|\s)', text)
print(result2)

# 결과에 빈 문자열이 포함되어 있으므로 이를 삭제합니다.
# ""은 False로, 내용이 있는 문자열은 True
# 결과가 True인 경우에만 그 item을 새로운 리스트에 포함
result3 = [item for item in result2 if item.strip()]
print(result3)

preprocessed = re.split(r'([,.:;?_!"()\']|--|\s)', raw_text)
# " world"에서 앞의 공백까지 완전히 제거된 깨끗한 리스트
preprocessed = [item.strip() for item in preprocessed if item.strip()]
print(preprocessed[:30])

# 총 토큰 개수
print(len(preprocessed))

