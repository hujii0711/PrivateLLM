# 파이썬 표준 라이브러리 sys 모듈을 불러옵니다. 시스템 관련 정보(경로, 버전 등)에 접근할 수 있습니다
import sys


class Calulator:
    # 객체 생성 시 자동 호출되는 생성자
    def __init__(self):
        # self: 인스턴스 자기 자신을 가리키는 참조
        self.result = 0  # 인스턴스 변수 초기화 (각 객체가 독립적으로 보유)

    # self.result += num → 누적 합산
    # 호출할 때마다 이전 결과에 더해서 반환
    # cal1과 cal2는 각자의 result 를 독립적으로 유지
    def add(self, num):
        self.result += num
        return self.result

    # add 메서드를 객체 생성시 자동으로 호출되는 call 메서드로 등록하는 방법 --> __call__을 정의하면 객체를 함수처럼 호출할 수 있습니다.
    def __call__(self, num):
        return self.add(num)

# 매직 메서드 정리
# __init__   # 객체 생성 시 자동 호출    cal1 = Calculator()
# __call__   # 객체를 함수처럼 호출      cal1(10)
# __str__    # print() 시 출력 형태     print(cal1)
# __add__    # + 연산자 오버로딩         cal1 + cal2
# __len__    # len() 호출 시            len(cal1)
cal1 = Calulator()
cal2 = Calulator()
type(cal1)
# __call__(10) 자동 실행 → add(10) 호출
# 마치 함수처럼 사용 가능!
print(cal2(10))  # -> 10

print(type(cal1))
print(cal1.add(3))
print(cal1.add(4))
print(cal2.add(3))
print(cal2.add(7))
print(sys.path)
