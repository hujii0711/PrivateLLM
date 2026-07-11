class FourCal:
    # 생성자란 객체가 생성될 때 자동으로 호출되는 메서드이다.
    # 객체에 first, second와 같은 초기값을 설정해야 할 필요가 있을 때는 setdata와 같은 메서드를 호출하여
    # 초기값을 설정하기보다 생성자를 구현하는 것이 안전한 방법이다.
    def __init__(self, first, second):
        self.first = first
        self.second = second

    def setdata(self, first, second):
        self.first = first
        self.second = second

    def add(self):
        result = self.first + self.second
        return result


# 📁 FourCal.py 직접 실행
#   └─► __name__ == "__main__" → True
#         a = FourCal(4, 2) 실행 ✅
#         print(a.add()) 실행 ✅
#         출력: 6

# 📁 other.py 에서 import FourCal
#   └─► __name__ == "FourCal" → False
#         a = FourCal(4, 2) 실행 안됨 ✅
#         print(a.add()) 실행 안됨 ✅
print(__name__)  # 외부에서 모듈 사용시: TModule2 | 자기 자신 직접 실행시 __main__
# if __name__ == "__main__":를 사용하면 외부에서 모듈 사용시에는 수행되지 않고 자기 파일을 직접 실행할 때만 수행된다.
# 테스트 코드는 직접 실행할 때만 수행
if __name__ == "__main__":
    a = FourCal(4, 2)
    print(a.add())  # 직접 실행 시만 출력 | import 시에는 실행 안됨
