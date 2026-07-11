class FourCal:
    def __init__(self, first, second):
        self.first = first
        self.second = second

    def setdata(self, first, second):
        self.first = first
        self.second = second

    def add(self):
        result = self.first + self.second
        return result


# class 클래스 이름(상속할 클래스 이름)
class MoreFourCal(FourCal):
    def pow(self):
        result = self.first**self.second
        return result

    # 부모 클래스에 있는 메서드를 동일한 이름으로 다시 만드는 것을 메서드 오버라이딩이라고 한다.
    def add(self):
        result = self.first + self.second + 1
        return result


a = MoreFourCal(4, 2)
print(a.add())
print(a.pow())
