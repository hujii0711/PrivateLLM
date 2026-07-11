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


a = FourCal(4, 2)
print(a.add())
