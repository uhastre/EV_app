#utils.py
from math import radians, cos, sin, sqrt, atan2
import pandas as pd
import streamlit as st
from db_utils import engine
from sqlalchemy import text
import folium
from folium.plugins import MarkerCluster
from db_utils import get_station_data
import os

# 🌍 위도/경도 기반 거리 계산 함수 (단위: km)
def haversine(lat1, lon1, lat2, lon2):
    R = 6371
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat/2)**2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon/2)**2
    return 2 * R * atan2(sqrt(a), sqrt(1 - a))



def get_marker_icon(charger_type):
    t = str(charger_type).lower().replace(" ", "")
    if "7kw단독" in t:
        return "battery-quarter"
    elif "7kw" in t:
        return "battery-quarter"
    elif "11kw단독" in t:
        return "battery-half"
    elif "14kw단독" in t:
        return "plug"
    elif "50kw" in t:
        return "car"
    elif "100kw단독" in t:
        return "battery-full"
    elif "100kw동시" in t:
        return "bolt"
    elif "200kw동시" in t:
        return "charging-station"
    else:
        return "question"
    

def display_debug_log():
    if "debug_log" not in st.session_state:
        return

    log = st.session_state.debug_log
    debug_html = f"""
    <div style="border: 2px dashed #666; border-radius: 10px; padding: 16px; margin-top: 20px; background-color: #f5f5f5;">
        <h4 style="color:#333;">🐞 클릭된 충전소 로그</h4>
        <ul style="list-style:none; padding-left:0; font-size:14px;">
            <li><b>ID:</b> {log['station_id']}</li>
            <li><b>이름:</b> {log['station_name']}</li>
            <li><b>지역:</b> {log['region']} {log['district']}</li>
            <li><b>주소:</b> {log['short_address']}</li>
            <li><b>위치:</b> {log['latitude']}, {log['longitude']}</li>
            <li><b>충전기 수:</b> {log['charger_count']}</li>
            <li><b>종류:</b> {log['types']}</li>
            <li><b>용량:</b> {log['capacities']}</li>
        </ul>
    </div>
    """
    st.markdown(debug_html, unsafe_allow_html=True)


# 전시
def display_clicked_station_info(df):
    if "clicked_station_id" not in st.session_state:
        return

    clicked_id = st.session_state.clicked_station_id
    row = df[df['station_id'] == clicked_id]

    if row.empty:
        return

    info = row.iloc[0]
    html = f"""
    <div style="border:2px solid #007BFF; border-radius:12px; padding:16px; background-color:#f9f9ff; margin-top:20px;">
        <h4 style="color:#007BFF;">📌 선택된 충전소 정보</h4>
        <ul style="list-style:none; font-size:14px; padding-left:0;">
            <li><b>🔋 충전소명:</b> {info['station_name']}</li>
            <li><b>📍 주소:</b> {info['short_address']}</li>
            <li><b>⚡ 충전기 종류:</b> {info['charger_type']}</li>
            <li><b>🔌 용량:</b> {info['capacity']} kW</li>
            <li><b>🧭 위치:</b> ({info['latitude']}, {info['longitude']})</li>
        </ul>
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)

@st.cache_data(ttl=3600)
def get_region_center(region_name):
    query = text("""
    SELECT latitude, longitude
    FROM region_centers
    WHERE region = :region
    """)
    df = pd.read_sql(query, engine, params={"region": region_name})
    if df.empty:
        return None, None
    return df.iloc[0]['latitude'], df.iloc[0]['longitude']

@st.cache_data(ttl=3600)
def get_sorted_district_list(region_name, lat, lon):
    query = text("""
    SELECT d.district_name, dc.latitude, dc.longitude
    FROM districts d
    JOIN regions r ON d.region_id = r.region_id
    JOIN district_centers dc ON d.district_id = dc.district_id
    WHERE r.region = :region
    """)
    df = pd.read_sql(query, engine, params={"region": region_name})
    df['distance'] = df.apply(lambda row: haversine(lat, lon, row['latitude'], row['longitude']), axis=1)
    return df.sort_values('distance')['district_name'].tolist()


# 🎨 사용자 색상 선택 UI 생성
def get_user_color_map():
    default_colors = {
        "7kW 단독": "#663399",
        "7kW": "#FFA500",
        "11kW 단독": "#3CB371",
        "14kW 단독": "#ADD8E6",
        "50kW": "#6495ED",
        "100kW 단독": "#FF1493",
        "100kW 동시": "#8B0000",
        "200kW 동시": "#5F9EA0",
        "기타": "#808080"
    }
    st.markdown("### 🎨 마커 색상 선택")
    user_colors = {}
    for label, default in default_colors.items():
        user_colors[label] = st.color_picker(f"{label} 색상", default)
    return user_colors

# 🎨 충전기 타입 → 마커 색상 매핑
def get_marker_color(charger_type, color_map=None):
    # 기본 색상 정의
    default_colors = {
        "7kW 단독": "darkpurple",
        "7kW": "orange",
        "11kW 단독": "green",
        "14kW 단독": "lightblue",
        "50kW": "blue",
        "100kW 단독": "pink",
        "100kW 동시": "darkred",
        "200kW 동시": "cadetblue",
        "기타": "gray"
    }

    # color_map이 없으면 기본값 사용
    color_map = color_map or default_colors

    if charger_type is None:
        return color_map.get("기타")

    t = str(charger_type).lower().replace(" ", "")

    if "7kw단독" in t:
        return color_map.get("7kW 단독")
    elif "7kw" in t:
        return color_map.get("7kW")
    elif "11kw단독" in t:
        return color_map.get("11kW 단독")
    elif "14kw단독" in t:
        return color_map.get("14kW 단독")
    elif "50kw" in t:
        return color_map.get("50kW")
    elif "100kw단독" in t:
        return color_map.get("100kW 단독")
    elif "100kw동시" in t:
        return color_map.get("100kW 동시")
    elif "200kw동시" in t:
        return color_map.get("200kW 동시")

    return color_map.get("기타")



@st.cache_data(ttl=60)
def generate_map(df, center_lat, center_lon, clicked_station_id):
    m = folium.Map(location=[center_lat, center_lon], zoom_start=17)
    cluster = MarkerCluster().add_to(m)

    for station_id in df['station_id'].unique():
        row = df[df['station_id'] == station_id].iloc[0]

        # ⛔ NaN 좌표 무시
        if pd.isna(row['latitude']) or pd.isna(row['longitude']):
            continue

        is_selected = station_id == clicked_station_id
        type_string = f"{row['charger_type']}({row['capacity']}kW)"
        color = get_marker_color(type_string)
        icon = "star" if is_selected else get_marker_icon(type_string)

        popup_html = f"""
        <div style='width:250px;'>
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

    return m

@st.cache_data(ttl=600)
def load_or_create_nationwide_data():
    """
    전국 데이터 Parquet 파일이 없으면 생성하고, 있으면 불러온다.
    """
    file_path = "nationwide_charger_data.parquet"
    if os.path.exists(file_path):
        return pd.read_parquet(file_path)
    else:
        df = get_station_data()  # 지역/구군 조건 없이 전체 조회
        df.to_parquet(file_path)
        return df
    
