
import re
from tokenizer.SimpleTokenizerV1 import SimpleTokenizerV1
from tokenizer.SimpleTokenizerV2 import SimpleTokenizerV2

# aaa = ["A", "B", "C", "D"]
# bbb = {token : integer for integer,token in enumerate(aaa)} #{'A': 0, 'B': 1, 'C': 2, 'D': 3}
# print(bbb)
# print(bbb.items()) #dict_items([('A', 0), ('B', 1), ('C', 2), ('D', 3)])
# print(vocab)

# 단편 소설을 텍스트 샘플 파일로 읽기
with open("the-verdict.txt", "r", encoding="utf-8") as f:
    raw_text = f.read()

preprocessed = re.split(r'([,.:;?_!"()\']|--|\s)', raw_text)
# " world"에서 앞의 공백까지 완전히 제거된 깨끗한 리스트
preprocessed = [item.strip() for item in preprocessed if item.strip()]

# 중복 제거후 오름차순으로 정렬하여 리스트 형태로 반환
all_words = sorted(set(preprocessed))
vocab_size = len(all_words)
#print(vocab_size)

vocab = {token : integer for integer,token in enumerate(all_words)}
for i, item in enumerate(vocab.items()): # print(bbb.items()) #dict_items([('A', 0), ('B', 1), ('C', 2), ('D', 3)])
    #print(item) 
    if i >= 50:
        break
    
tokenizer = SimpleTokenizerV1(vocab)
text = """"It's the last he painted, you know,"
           Mrs. Gisburn said with pardonable pride."""
ids = tokenizer.encode(text)
de=tokenizer.decode(ids)

tokenizer2 = SimpleTokenizerV2(vocab)
text1 = "Hello, do you like tea?"
text2 = "In the sunlit terraces of the palace."
text3 = " <|endoftext|> ".join((text1, text2))
print(text3)