from TModule import FourCal

a = FourCal(4, 2)
print("-------------------")
print(a.add())

# from TModule import * TModule 모듈의 모든 함수를 불러와 사용하겠다는 의미
from TModule import *

b = FourCal(4, 2)
print("-------------------")
print(a.add())
