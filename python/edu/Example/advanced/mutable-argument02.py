"""
실행 흐름
1. add_many(korean=90, english=85, math=100) 처럼 이름=값 형태로 인자를 넘기면,
2. 함수 내부의 args는 자동으로 딕셔너리로 묶입니다
args = {'korean': 90, 'english': 85, 'math': 100}
3. print(args) → 딕셔너리 전체 출력
4. for key, value in args.items(): → 딕셔너리를 key(과목명)와 value(점수)로 하나씩 꺼냄
5. result += value → 점수를 계속 더함 (0 → 90 → 175 → 275)
6. return result → 합계 275 반환

* 왜 이런 방식이 유용한가요?
**kwargs의 진짜 장점은 몇 개의 값이 들어올지 모를 때, 그리고 각 값에 "이름표(키)"를 붙이고 싶을 때 빛을 발합니다.
python# 과목이 2개일 때도, 5개일 때도 함수 정의는 그대로!
add_many(korean=90, english=85)
add_many(korean=90, english=85, math=100, science=95, history=88)
만약 **kwargs 없이 함수를 만들었다면, 인자 개수가 다를 때마다 함수를 새로 정의하거나 매번 딕셔너리를 직접 만들어 넘겨야 했을 거예요.
"""


def add_many(**args):
    print(args)
    result = 0
    for key, value in args.items():
        print(f"{key} = {value}")
        result += value
    return result


a = add_many(korean=90, english=85, math=100)
print(a)
