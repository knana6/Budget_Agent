import pandas as pd
import os

USERS_PATH = "data/users.csv"
os.makedirs("data", exist_ok=True)

def load_users():
    if os.path.exists(USERS_PATH):
        return pd.read_csv(USERS_PATH)
    return pd.DataFrame(columns=["username", "password"])

def save_user(username, password):
    df = load_users()
    new_row = pd.DataFrame([{"username": username, "password": password}])
    df = pd.concat([df, new_row], ignore_index=True)
    df.to_csv(USERS_PATH, index=False)

def authenticate(username, password):
    df = load_users()
    user = df[df["username"] == username]
    if user.empty:
        save_user(username, password)  # 새로운 사용자 → 자동 등록
        return True
    return user.iloc[0]["password"] == password
