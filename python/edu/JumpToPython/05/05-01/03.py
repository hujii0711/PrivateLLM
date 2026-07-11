class FourCal:
    # __init__ 없이 setdata로 초기값을 수동 설정하는 방식입니다.
    def setdata(self, first, second):
        self.first = first
        self.second = second

    def add(self):
        result = self.first + self.second
        return result


a = FourCal()
a.setdata(4, 2)  # 객체 + 메서드 호출시 self를 생략해서 호출해야 한다. a = self
# ⚠️ FourCal.add(a, 4, 2)는 오류는 아니지만 add(self) 정의상 추가 인자 4, 2는 받지 않으므로 사실상 a.add()와 동일하게 동작합니다.
# FourCal.add(a, 4, 2)

print(a.first)
print(a.second)
print(a.add())
# self는 "이 메서드를 호출한 객체가 나야" 라고 알려주는 역할입니다. a가 self가 되어 a.first, a.second에 접근할 수 있게 됩니다.
