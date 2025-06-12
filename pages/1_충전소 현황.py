
# pages/1_충전소_현황.py
import streamlit as st
import pandas as pd
import folium
from folium.plugins import MarkerCluster
from streamlit_folium import st_folium
from db_utils import get_use_time_by_station_id
from utils import get_marker_color, get_marker_icon
from ev_ui_utils import (
    render_region_district_with_summary,
    render_station_detail,
    generate_summary,load_or_generate_summary,Legend_Customization,
    get_map_center,
    render_station_cards,
    render_pagination_controls
)


def get_map_center(summary_all, summary_visible, clicked_station_id):
    # 1. 선택된 충전소가 있다면
    if clicked_station_id:
        row = summary_all[summary_all['station_id'] == clicked_station_id]
        if not row.empty:
            lat = row.iloc[0]['latitude']
            lon = row.iloc[0]['longitude']
            if not pd.isna(lat) and not pd.isna(lon):
                return lat, lon

    # 2. 현재 페이지에서 NaN 제외 후 평균 좌표 계산
    latitudes = summary_visible['latitude'].dropna()
    longitudes = summary_visible['longitude'].dropna()

    if not latitudes.empty and not longitudes.empty:
        return latitudes.mean(), longitudes.mean()

    # 3. fallback: 대한민국 중앙 좌표
    return 36.5, 127.9



st.set_page_config(page_title="충전소 목록", layout="wide")
st.title("⚡ 지역별 전기차 충전소 현황")

st.markdown("""
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.0/css/all.min.css">
""", unsafe_allow_html=True)

# ✅ 캐시된 지도 생성 함수
@st.cache_data(ttl=60)
def generate_map(df_all, summary_all, clicked_station_id, center_lat, center_lon):
    visible_ids = summary_all['station_id'].tolist()
    df = df_all[df_all['station_id'].isin(visible_ids)].copy()
    df = df.drop_duplicates("station_id")
    station_df = df.set_index("station_id")

    # ✅ 조건부 zoom 적용
    if clicked_station_id and not pd.isna(center_lat) and not pd.isna(center_lon):
        m = folium.Map(location=[center_lat, center_lon], zoom_start=17)
    else:
        m = folium.Map(location=[center_lat, center_lon], zoom_start=13)  # 기본값
        # zoom_start 생략해도 되지만 명시적으로 줘도 무방
    cluster = MarkerCluster().add_to(m)
    
    bounds = []

    for station_id in visible_ids:
        if station_id not in station_df.index:
            continue

        row = station_df.loc[station_id]
        if isinstance(row, pd.DataFrame):
            row = row.iloc[0]

        if pd.isna(row['latitude']) or pd.isna(row['longitude']):
            continue

        is_selected = (station_id == clicked_station_id)
        type_string = f"{row['charger_type']}({row['capacity']}kW)"
        color = get_marker_color(type_string)
        icon = "star" if is_selected else get_marker_icon(type_string)

        popup_html = f"""<div style='width:250px;'>
            <b>📍 {row['station_name']}</b><br>
            🔌 충전기 수: {row['charger_local_id']}<br>
            ⚡ {row['capacity']}
        </div>"""
        popup = folium.Popup(folium.Html(popup_html, script=True), max_width=300)

        marker = folium.Marker(
            location=[row['latitude'], row['longitude']],
            popup=popup,
            tooltip=row['station_name'],
            icon=folium.Icon(color=color, icon=icon, prefix="fa")
        )
        marker.add_to(cluster)
        bounds.append([row['latitude'], row['longitude']])

    
    return m

# 📍 필터 및 데이터 로딩

# 1. 이전 상태 저장
prev_region = st.session_state.get("last_region")
prev_district = st.session_state.get("last_district")

# 2. 현재 선택값 가져오기
region, district, df = render_region_district_with_summary()

# 3. 지역 변경 감지 → 클릭 초기화
if prev_region != region or prev_district != district:
    st.session_state.clicked_station_id = None

# 4. 새 상태 저장
st.session_state.last_region = region
st.session_state.last_district = district

# 5. 요약 데이터 생성
summary = load_or_generate_summary(region, district)


# 🔢 페이지 계산
cards_per_page = 9
total_cards = len(summary)
total_pages = (total_cards - 1) // cards_per_page + 1
if "page" not in st.session_state:
    st.session_state.page = 0
start_idx = st.session_state.page * cards_per_page
end_idx = start_idx + cards_per_page
summary_visible = summary.iloc[start_idx:end_idx]

# 지도 중심 위치 계산
center_lat, center_lon = get_map_center(summary, summary_visible, st.session_state.get("clicked_station_id"))

# 📍 지도 + 카드 UI 출력
col1, col2 = st.columns([1, 2])
with col1:
    st.markdown("🗺️ **지도**")
    m = generate_map(df, summary, st.session_state.get("clicked_station_id"), center_lat, center_lon)
    clicked = st_folium(m, width=700, height=500, returned_objects=["zoom"])
    Legend_Customization()

    if clicked and "zoom" in clicked:
        st.markdown(f"📏 현재 지도 확대 수준: <b>{clicked['zoom']}</b>", unsafe_allow_html=True)
        
with col2:
    # 선택된 충전소 상세
    if st.session_state.get("clicked_station_id"):
        sid = st.session_state.clicked_station_id
        filtered = summary[summary['station_id'] == sid]
        if not filtered.empty:
            selected_row = filtered.iloc[0]
            use_time = get_use_time_by_station_id(sid)
            render_station_detail(selected_row, use_time)

    # 카드 및 페이지네이션
    st.markdown("### 📄 충전소 목록")
    render_station_cards(summary, start_idx, end_idx)
    render_pagination_controls(total_pages)

