import re

class SimpleTokenizerV1:
    def __init__(self, vocab):
        self.str_to_int = vocab
        self.int_to_str = {i:s for s,i in vocab.items()}

    # - `encode` 함수는 텍스트를 토큰 ID로 바꿉니다.
    def encode(self, text):
        preprocessed = re.split(r'([,.:;?_!"()\']|--|\s)', text) # 'hello,. world'

        preprocessed = [
            item.strip() for item in preprocessed if item.strip()
        ]
        ids = [self.str_to_int[s] for s in preprocessed]
        return ids

    # - `decode` 함수는 토큰 ID를 텍스트로 바꿉니다.
    def decode(self, ids):
        text = " ".join([self.int_to_str[i] for i in ids])
        # 구둣점 문자 앞의 공백을 삭제합니다.
        text = re.sub(r'\s+([,.?!"()\'])', r'\1', text)
        return text