import pandas as pd
import os
import time

USERS_PATH = "data/users.csv"
os.makedirs("data", exist_ok=True)

def load_users():
    if os.path.exists(USERS_PATH):
        return pd.read_csv(USERS_PATH, encoding="utf-8-sig", dtype=str)
    return pd.DataFrame(columns=["username", "password"])

# def save_user(username, password):
#     df = load_users()
#     new_row = pd.DataFrame([{"username": username, "password": password}])
#     df = pd.concat([df, new_row], ignore_index=True)
#     try:
#         df.to_csv(USERS_PATH, index=False)
#         print(f"[✅ 저장 완료] 사용자: {username}")
#     except Exception as e:
#         print(f"[❌ 저장 실패] 사용자: {username}, 에러: {e}")   
         
def save_user(username, password):
    df = load_users()
    new_row = pd.DataFrame([{"username": str(username), "password": str(password)}])
    df = pd.concat([df, new_row], ignore_index=True)
    # print(f"[DEBUG] 저장 대상 데이터프레임:\n{df}")

    try:
        # print(f"[DEBUG] 저장 경로: {os.path.abspath(USERS_PATH)}")
        df.to_csv(USERS_PATH, index=False, encoding="utf-8-sig")
        # print(f"[✅ 저장됨] 사용자: {username}")
    except Exception as e:
        # print(f"[❌ 저장 실패] 사용자: {username}, 에러: {e}")


def authenticate(username, password):
    df = load_users()

    df["username"] = df["username"].astype(str)
    df["password"] = df["password"].astype(str)

    input_username = str(username)
    input_password = str(password)

    # user = df[df["username"] == input_username]
    # print(f"[DEBUG] users.csv에서 찾은 유저: {user}")

    # if user.empty:
    #     save_user(username, password)  # 새로운 사용자 → 자동 등록
    #     return True
    # return str(user.iloc[0]["password"]) == str(password)

    # username 존재 여부 확인
    if input_username not in df["username"].values:
        print("환영합니다! 이름과 비밀번호를 기억해 주세요")
        time.sleep(2)
        save_user(input_username, input_password)
        return True

    # 기존 유저의 비밀번호 확인
    stored_pw = df[df["username"] == input_username].iloc[0]["password"]
    match = stored_pw == input_password
    # print(f"[DEBUG] 저장된 비번: '{stored_pw}' / 입력 비번: '{input_password}' → 일치 여부: {match}")
    return match
