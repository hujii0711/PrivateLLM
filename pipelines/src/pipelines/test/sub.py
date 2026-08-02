import re

s = "  Hello   World  "

a = re.sub(r"\s+", "_", s.strip())
print(a)  # 출력: Hello_World
