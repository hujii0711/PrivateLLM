# - GPT-2는 바이트 페어 인코딩(BPE) 토크나이저를 사용합니다.
# - 어휘사전에 없는 단어를 더 작은 부분단어나 개별 문자로 분할하여 처리할 수 있습니다.
# - 예를 들어 GPT-2의 어휘사전에 단어 "unfamiliarword"가 없다면 이를 ["unfam", "iliar", "word"] 같이 토큰화할 수 있습니다. BPE의 훈련에 따라 결과가 달라질 수 있습니다.

import tiktoken

tokenizer = tiktoken.get_encoding("gpt2")

text = (
    "Hello, do you like tea? <|endoftext|> In the sunlit terraces"
     "of someunknownPlace."
)

integers = tokenizer.encode(text, allowed_special={"<|endoftext|>"})

print(integers)
print(tokenizer.special_tokens_set)
strings = tokenizer.decode(integers)
print(strings)