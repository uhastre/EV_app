import streamlit as st
import os
from datetime import datetime
import streamlit.components.v1 as components

st.set_page_config(page_title="EV 충전소 현황", layout="wide")
st.title("🏠전기차 충전소 데이터 홈")

# ✅ 세션 초기화
st.session_state.last_region = "충청남도"
st.session_state.last_district = "논산시 "
st.session_state.clicked_station_id = None
st.session_state.page = 0

# st.markdown("왼쪽 사이드바에서 기능을 선택하세요.")


# 파일 이름과 실행 시간
filename = os.path.basename(__file__) if '__file__' in globals() else "app1-2.py"
run_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

# # 제목 위에 메모처럼 표시
# st.markdown(
#     f"<div style='color:red; font-size:13px; margin-bottom:6px;'>📌 실행 파일: <b>{filename}</b> | 실행 시간: <b>{run_time}</b></div>",
#      unsafe_allow_html=True
# )
# # ---------
# # # -
# st.title("🏠 EV 충전소 시스템 홈")
st.markdown("📰데이터구조")
scale_ratio = 0.8

with open("diagram.html", 'r', encoding='utf-8') as f:
    html_raw = f.read()

scaled_html = f"""
<div style="transform: scale({scale_ratio}); transform-origin: top left;">
    {html_raw}
</div>
"""

components.html(scaled_html, height=int(800 * scale_ratio) + 100, scrolling=True)