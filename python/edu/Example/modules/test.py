# import mod — 모듈 전체 임포트
# mod 모듈 전체를 가져옴
# 사용 시 반드시 모듈명.함수명 형태로 호출
# 어느 모듈의 함수인지 명확하게 드러남 ✅
# 호츨 방법: mod.add()
import mod

# import mod as md — 별칭(alias) 지정
# mod를 md라는 짧은 이름으로 사용
# 모듈명이 길거나 충돌할 때 유용
# 호츨 방법: md.add()
import mod as md

# from mod import * — 모든 것을 임포트
# 모듈 안의 모든 함수/변수를 한번에 가져옴
# 모듈명 없이 바로 호출 가능
# ⚠️ 실무에서는 비권장
# 호츨 방법: add()
from mod import *

# from mod import add — 특정 함수만 임포트
# mod에서 add 함수만 가져옴
# 모듈명 없이 함수명만으로 바로 호출 가능
# 필요한 것만 가져오므로 메모리 효율적 ✅
# 호츨 방법: add()
from .mod import add, sub  # from mod import add, sub

print(mod.add(1, 2))
print(add(1, 2))
print(md.add(1, 2))
print(add(1, 2))
print(sub(5, 3))
