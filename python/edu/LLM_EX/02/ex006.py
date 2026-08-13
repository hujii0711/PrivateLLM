import tiktoken

tokenizer = tiktoken.get_encoding("gpt2")

with open("the-verdict.txt", "r", encoding="utf-8") as f:
    raw_text = f.read()

enc_text = tokenizer.encode(raw_text)
print(len(enc_text))

# - 텍스트 청크에 대해 입력과 타깃이 있어야 합니다.
# - 모델이 다음 단어를 예측해야 하므로 타깃은 오른쪽으로 한 토큰 이동한 입력입니다.
enc_sample = enc_text[50:]

context_size = 4

x = enc_sample[:context_size] #[:4]
y = enc_sample[1:context_size+1] #[1:5]

print(f"x: {x}")
print(f"y:      {y}")

for i in range(1, context_size+1):
    context = enc_sample[:i]
    desired = enc_sample[i]

    print(context, "---->", desired)