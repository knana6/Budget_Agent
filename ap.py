import streamlit as st
import pandas as pd
from openai import OpenAI #최신버전
from dotenv import load_dotenv
import os
from datetime import datetime
from io import BytesIO
import calendar
import matplotlib.pyplot as plt

from utils.auth import authenticate
import re


st.write("✅ API Key 로드됨:", bool(os.getenv("OPENAI_API_KEY")))

load_dotenv()
# api_key = os.getenv("OPENAI_API_KEY") 버전 모듈 오출 수정 
# openai.api_key = os.getenv("OPENAI_API_KEY")
#client = OpenAI(api_key=api_key)# 버전 모듈 오류 수정 
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY")) ###


if not st.session_state.username:
    st.markdown("""
        <style>
        .main {opacity: 0.3;}
        .login-box {
            position: fixed;
            top: 30%;
            left: 50%;
            transform: translate(-50%, -50%);
            background-color: transparent;
            padding: 2rem;
            border-radius: 10px;
            box-shadow: 0 0 10px rgba(0,0,0,0.3);
            z-index: 9999;
            text-align: center;
        }
        </style>
        """, unsafe_allow_html=True)

    st.markdown('<div class="login-box"><h3>환영합니다! 가계부 비서를 만들어 볼까요?</h3></div>', unsafe_allow_html=True)

    username = st.text_input("이름 (한글 또는 영어)")
    password = st.text_input("비밀번호 (4자리 숫자)", type="password")

    if st.button("시작하기"):
        if not re.match(r"^[가-힣a-zA-Z]+$", username):
            st.error("이름은 한글 또는 영어만 입력 가능합니다.")
        elif not re.match(r"^\d{4}$", password):
            st.error("비밀번호는 4자리 숫자여야 합니다.")
        else:
            if authenticate(username, password):
                st.session_state.username = username
                st.rerun()
            else:
                st.error("비밀번호가 틀렸습니다.")
    st.stop()  # 로그인 전엔 아래 코드 차단



username = st.session_state.username
CSV_PATH = f"data/{username}_ledger.csv"
# CSV_PATH = "data/ledger.csv"


os.makedirs("data", exist_ok=True)

# 기록 불러오기
def load_data():
    if os.path.exists(CSV_PATH):
        df = pd.read_csv(CSV_PATH)
        df["날짜"] = pd.to_datetime(df["날짜"], errors="coerce")
        return df
    return pd.DataFrame(columns=["날짜", "항목", "금액", "분류"])

# 기록 저장
def save_data(df):
    df.to_csv(CSV_PATH, index=False)

# 되돌리기
def undo_last():
    if st.session_state.undo_count > 0 and len(st.session_state.records) > 0:
        st.session_state.records = st.session_state.records.iloc[:-1]
        st.session_state.undo_count -= 1
        save_data(st.session_state.records)

# 초기화
def clear_all():
    st.session_state.records = pd.DataFrame(columns=["날짜", "항목", "금액", "분류"])
    st.session_state.undo_count = 0
    st.session_state.gpt_advice = ""
    save_data(st.session_state.records)
    if os.path.exists(CSV_PATH):
        os.remove(CSV_PATH)

#다시실행
def redo_last():
    if st.session_state.undo_count > 0 and len(st.session_state.records) > 0:
        st.session_state.records = st.session_state.records.iloc[:1]
        st.session_state.undo_count += 1
        save_data(st.session_state.records)

# GPT 조언 생성 함수
# def generate_advice(record):
#     messages = [
#         {"role": "system", "content": "너는 AI 에이전트야. 사람들의 소비/소득 패턴을 분석하고 돈을 절약할 수 있도록 조언해주는 금융 어시스턴트야. 한 문장으로 도와줘."},
#         {"role": "user", "content": f"카테고리: {record['분류']}, 항목: {record['항목']}, 금액: {record['금액']}원. 돈을 절약하는 조언을 해줘."}
#     ]
#     try:
#         #  response = client.chat.completions.create( 버전 모듈 호출 수
#         response = openai.chat.completions.create(
#             model="gpt-3.5-turbo",
#             messages=messages,
#             temperature=0.7
#         )
#         # return response.choices[0].message.content.strip() 버전 모듈 호출 수정
#         return response.choices[0].message.content.strip()
#     except Exception as e:
#         return "(GPT 조언을 가져오는 데 실패했어요)"

def generate_advice(record):
    messages = [
        {"role": "system", 
         "content": "너는 AI 에이전트야. 사람들의 소비/소득 패턴을 분석하고 돈을 절약할 수 있도록 조언해주는 금융 어시스턴트야. 한 문장으로 도와줘."},
        {"role": "user", 
         "content": f"카테고리: {record['분류']}, 항목: {record['항목']}, 금액: {record['금액']}원. 돈을 절약하는 조언을 해줘."}
    ]
    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=messages,
            temperature=0.7
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        st.error(f"GPT 호출 오류: {e}")
        return "(GPT 조언을 가져오는 데 실패했어요)"

# 사용자 입력 파싱
def parse_user_input(text):
    try:
        parts = text.strip().split()
        if len(parts) != 4:
            raise ValueError("입력 형식은 '소득/소비 항목 금액 날짜(6.25)'입니다.")
        category, item, amount_str, date_str = parts
        if category not in ["소비", "소득"]:
            raise ValueError("'소비' 또는 '소득'만 입력 가능합니다.")

        amount_str = amount_str.replace("원", "").replace(",", "")
        amount = int(amount_str)
        amount = -abs(amount) if category == "소비" else abs(amount)

        now = datetime.now()
        month, day = map(int, date_str.split("."))
        date = datetime(now.year, month, day)

        return pd.DataFrame([{ "날짜": date, "항목": item, "금액": amount, "분류": category }])
    except Exception as e:
        st.error(f"입력 오류: {e}")
        return None

# 엑셀로 변환
def to_excel(df):
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="가계부")

        # 열 너비 자동 조정
        worksheet = writer.sheets["가계부"]
        for col in worksheet.columns:
            max_length = 0
            col_letter = col[0].column_letter
            for cell in col:
                try:
                    if cell.value:
                        max_length = max(max_length, len(str(cell.value)))
                except:
                    pass
            adjusted_width = (max_length + 2)
            worksheet.column_dimensions[col_letter].width = adjusted_width

    output.seek(0)
    return output

# 캘린더 시각화
def draw_calendar(df, year, month):
    month_calendar = calendar.monthcalendar(year, month)
    cal_data = {}
    for _, row in df.iterrows():
        if pd.isna(row["날짜"]):
            continue
        if row["날짜"].year != year or row["날짜"].month != month:
            continue
        day = row["날짜"].day
        amt = row["금액"]
        color = "red" if amt < 0 else "blue"
        cal_data.setdefault(day, []).append({"amt": amt, "color": color})

    fig, ax = plt.subplots(figsize=(6, 5))
    ax.axis("off")
    ax.set_title(f"{year:04d}.{month:02d}", fontsize=14, weight="bold")
    for row_idx, week in enumerate(month_calendar):
        for col_idx, day in enumerate(week):
            if day == 0:
                continue
            x, y = col_idx, -row_idx
            ax.text(x, y, str(day), ha="center", va="center", fontsize=10, weight="bold")
            if day in cal_data:
                for idx, entry in enumerate(cal_data[day]):
                    ax.text(x, y - 0.3 - 0.3 * idx, f"{entry['amt']:+,}",
                            ha="center", va="center", color=entry["color"], fontsize=9)
    ax.set_xlim(-0.5, 6.5)
    ax.set_ylim(-len(month_calendar), 0.5)
    return fig


# Streamlit 설정


st.set_page_config(layout="wide")


if "username" not in st.session_state:
    st.session_state.username = None

if not st.session_state.username:
    st.markdown("""
        <style>
        .main {opacity: 0.3;}
        .login-box {
            position: fixed;
            top: 30%;
            left: 50%;
            transform: translate(-50%, -50%);
            background-color: white;
            padding: 2rem;
            border-radius: 10px;
            box-shadow: 0 0 10px rgba(0,0,0,0.3);
            z-index: 9999;
        }
        </style>
        """, unsafe_allow_html=True)

    st.markdown('<div class="login-box">', unsafe_allow_html=True)
    st.markdown("### 환영합니다! 가계부 비서를 만들어 볼까요?")
    username = st.text_input("이름 (한글 또는 영어)")
    password = st.text_input("비밀번호 (4자리 숫자)", type="password")
    st.markdown("</div>", unsafe_allow_html=True)

    if st.button("시작하기"):
        if not re.match(r"^[가-힣a-zA-Z]+$", username):
            st.error("이름은 한글 또는 영어만 가능합니다.")
        elif not re.match(r"^\d{4}$", password):
            st.error("비밀번호는 4자리 숫자여야 합니다.")
        else:
            if authenticate(username, password):
                st.session_state.username = username
                st.rerun()
            else:
                st.error("비밀번호가 틀렸습니다.")
    st.stop()


st.title("💸 AI 가계부 챗봇")

if "records" not in st.session_state:
    st.session_state.records = load_data()
if "undo_count" not in st.session_state:
    st.session_state.undo_count = 0
if "cal_month" not in st.session_state:
    st.session_state.cal_month = datetime.now().month
    st.session_state.cal_year = datetime.now().year
if "chat_input_value" not in st.session_state:
    st.session_state.chat_input_value = ""
if "gpt_advice" not in st.session_state:
    st.session_state.gpt_advice = ""

left, right = st.columns([2, 3])

with left:
    st.subheader("📅 이번 달 소비/소득 캘린더")
    fig = draw_calendar(st.session_state.records, st.session_state.cal_year, st.session_state.cal_month)
    st.pyplot(fig)

    col1, col2, col3, col4, col5 = st.columns([1, 1, 1 ,1, 1])
    with col1:
        if st.button("이전달"):
            if st.session_state.cal_month == 1:
                st.session_state.cal_month = 12
                st.session_state.cal_year -= 1
            else:
                st.session_state.cal_month -= 1
    with col2:
        if st.button("되돌리기"):
            undo_last() #되돌리기 메소드 
            st.rerun()
    with col3:
        if st.button("초기화"):
            clear_all() #
            st.rerun()
    with  col4:
        if st.button("다시실행"):
            redo_last() #다시실행 메소
            st.rerun()
    with col5:
        if st.button("다음달"):
            if st.session_state.cal_month == 12:
                st.session_state.cal_month = 1
                st.session_state.cal_year += 1
            else:
                st.session_state.cal_month += 1

with right:
    st.subheader("💬 오늘의 기록 입력")
    chat_input = st.text_input("입력 양식: '소득 항목 금액 날짜(6.25)' 형식으로 입력", value=st.session_state.chat_input_value, key="chat_input")
    if chat_input != "" and st.session_state.get("last_input") != chat_input:
        result = parse_user_input(chat_input)
        if isinstance(result, pd.DataFrame):
            new_row = result.iloc[0]
            st.session_state.records = pd.concat([st.session_state.records, result], ignore_index=True)
            save_data(st.session_state.records)
            st.session_state.undo_count += 1
            st.session_state.last_input = chat_input
            st.session_state.chat_input_value = ""  # 입력창 초기화

            # ✅ GPT 조언 출력 저장
            st.session_state.gpt_advice = generate_advice(new_row)
            st.rerun()

    now = datetime.now()
    st.session_state.records["날짜"] = pd.to_datetime(st.session_state.records["날짜"])
    month_df = st.session_state.records[
        (st.session_state.records["날짜"].dt.month == st.session_state.cal_month) &
        (st.session_state.records["날짜"].dt.year == st.session_state.cal_year)
    ]
    total_exp = month_df[month_df["분류"] == "소비"]["금액"].sum()
    total_inc = month_df[month_df["분류"] == "소득"]["금액"].sum()

    if not month_df.empty:
        st.markdown(f"**이번 달 소비:** <span style='color:red'>{abs(total_exp):,}원</span>", unsafe_allow_html=True)
        st.markdown(f"**이번 달 소득:** <span style='color:blue'>{total_inc:,}원</span>", unsafe_allow_html=True)

    if st.session_state.gpt_advice:
        st.markdown(f"💡 **AI 조언:** {st.session_state.gpt_advice}")

    st.download_button("📥 엑셀로 저장", data=to_excel(st.session_state.records),
                       file_name="가계부기록.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
