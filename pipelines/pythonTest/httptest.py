import requests


def fetch_users():
    try:
        response = requests.get("https://jsonplaceholder.typicode.com/users", timeout=5)
        response.raise_for_status()  # 4xx/5xx 에러 시 예외 발생
        return response.json()

    except requests.exceptions.Timeout:
        print("요청 시간 초과")
    except requests.exceptions.HTTPError as e:
        status_code = e.response.status_code if e.response is not None else "알 수 없음"
        print(f"HTTP 에러: {status_code}")
    except requests.exceptions.RequestException as e:
        print(f"요청 실패: {e}")
    return []


users = fetch_users()
for user in users:
    print(f"{user['id']}. {user['name']} | {user['email']} | {user['phone']}")
