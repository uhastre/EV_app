import streamlit as st
import pandas as pd
from db_utils import (
    get_station_data,
    get_region_list,
    get_region_center,         # ✅ 이게 실제 좌표 기반 조회 함수
    normalize_station_name
)

from utils import (
    get_sorted_district_list   # ✅ utils에 있는 함수만 이쪽에서 import
)
import os

from streamlit_folium import st_folium
import re

def init_session_state(keys_with_defaults):
    """
    세션 상태에서 지정된 키가 없으면 기본값으로 초기화
    """
    for key, default in keys_with_defaults.items():
        if key not in st.session_state:
            st.session_state[key] = default

def render_region_district_with_summary():
    default_region = "충청남도"
    default_district = "논산시 "

    region_list = get_region_list()

    # 세션 초기화
    if "last_region" not in st.session_state:
        st.session_state.last_region = default_region if default_region in region_list else region_list[0]

    # 기준 좌표로 시/도 선택 (col1)
    col1, col2, col3 = st.columns([1, 1, 1])
    with col1:
        region = st.selectbox(
            "📍 시/도 선택",
            region_list,
            index=region_list.index(st.session_state.last_region),
            key="region_selectbox_3col"
        )

    # 선택된 시/도의 중심 좌표
    region_lat, region_lon = get_region_center(region)
    
    # 기준 좌표로 가까운 구/군 정렬 리스트
    district_list = get_sorted_district_list(region, region_lat, region_lon)

    # 구/군 선택 (col2)
    with col2:
        if region == default_region and default_district in district_list:
            default_district_val = default_district
        else:
            default_district_val = district_list[0]

        district = st.selectbox(
            "🗺️ 구/군 선택",
            district_list,
            index=district_list.index(default_district_val),
            key="district_selectbox_3col"
        )

    # 데이터 로딩
    df = get_station_data(region, district)
    
    # 요약 출력 (col3)
    with col3:
        station_count = df['station_id'].nunique()
        charger_count = len(df)
        st.markdown(f'''
            #### 🔍 조회 결과  
            - 🏢 **충전소 수**: `{station_count}` 개  
            - ⚡ **충전기 수**: `{charger_count}` 기
        ''')

    # 마지막 선택값 저장
    st.session_state.last_region = region
    st.session_state.last_district = district

    return region, district, df




def render_station_detail(selected_row, use_time):
    subsidy_ev = selected_row.get('max_subsidy_ev')
    subsidy_mini = selected_row.get('max_subsidy_mini')
    with st.expander("📍 선택된 충전소 상세정보", expanded=True):
        st.markdown(f"""
        <div style="background-color:#f9f9f9; padding:16px; border-radius:8px; border:1px solid #ddd;">
            <h4 style="margin-top:0;">🔌 {selected_row['station_name']}</h4>
            <div style="display: flex; gap: 20px; flex-wrap: wrap;">
                <ul style="list-style:none; padding-left:0; font-size:15px; margin: 0; flex: 1;">
                    <li><b>🏢 지역:</b> {selected_row['region_name']} {selected_row['district_name']}</li>
                    <li><b>🗺️ 주소:</b> {selected_row['short_address']}</li>
                    <li><b>🔋 충전기 수:</b> {selected_row['charger_count']}기</li>
                    <li><b>⏰ 운영 시간:</b> <span style="color:#666;">{use_time if use_time else '정보 없음'}</span></li>
                </ul>
                <ul style="list-style:none; padding-left:0; font-size:15px; margin: 0; flex: 1;">
                    <li><b>⚡ 종류:</b> <span style="color:#0066cc">{selected_row['charger_types']}</span></li>
                    <li><b>🔌 용량:</b> <span style="color:#009900">{selected_row['capacities']}</span></li>
                    <li><b>💰 전기차 보조금:</b> 최대 <span style="color:#cc0000">{subsidy_ev if subsidy_ev else '정보 없음'}</span>만원</li>
                    <li><b>🚗 초소형 보조금:</b> 최대 <span style="color:#cc6600">{subsidy_mini if subsidy_mini else '정보 없음'}</span>만원</li>
                </ul>
            </div>
        </div>
        """, unsafe_allow_html=True)

def generate_summary(df):
    df = df.copy()
    df = df.dropna(subset=['latitude', 'longitude'])

    summary = (
        df.groupby('station_id')
        .agg({
            'station_name': 'first',
            'region_name': 'first',
            'district_name': 'first',
            'short_address': 'first',
            'latitude': 'first',
            'longitude': 'first',
            'max_subsidy_ev': 'first',
            'max_subsidy_mini': 'first',
            'charger_local_id': 'count',
            'charger_type': lambda x: ', '.join(sorted(set(x))),
            'capacity': lambda x: ', '.join(sorted(set(x)))
        }).reset_index().rename(columns={
            'charger_local_id': 'charger_count',
            'charger_type': 'charger_types',
            'capacity': 'capacities'
        })
    )
    summary['station_id'] = summary['station_id'].astype(int)
    return summary


def get_map_center(summary, clicked_station_id):
    if clicked_station_id:
        selected_row = summary[summary['station_id'] == clicked_station_id]
        if not selected_row.empty:
            return selected_row.iloc[0]['latitude'], selected_row.iloc[0]['longitude']
    return summary['latitude'].mean(), summary['longitude'].mean()

def render_station_cards(summary, start_idx, end_idx):
    visible_rows = summary.iloc[start_idx:end_idx].copy()
    cols = st.columns(3)
    for idx, row in enumerate(visible_rows.itertuples(index=False)):
        sid = row.station_id
        name = row.station_name
        district = row.district_name
        short_address = row.short_address
        count = row.charger_count
        types = row.charger_types
        caps = row.capacities

        cleaned_name = name.replace(" ", "")
        if not any(cleaned_name.endswith(suffix) for suffix in ["시청", "구청"]):
            for prefix in [district.replace(" ", ""), district.replace("시", "").replace("군", "").replace("구", "")]:
                if cleaned_name.startswith(prefix):
                    cleaned_name = cleaned_name[len(prefix):]
        cleaned_name = cleaned_name.strip()
        is_selected = sid == st.session_state.get("clicked_station_id")

        with cols[idx % 3]:
            with st.form(key=f"form_{sid}_{idx}_card"):
                background_color = '#fff0f0' if is_selected else '#fdfdfd'
                st.markdown(f'''
                <style>
                .card-box {{
                    border: 2px solid rgba(0, 0, 0, 0);
                    border-radius: 12px;
                    padding: 16px;
                    background-color: {background_color};
                    box-shadow: {'0 0 10px rgba(255,75,75,0.4)' if is_selected else '2px 2px 8px rgba(0,0,0,0.05)'};
                    font-size: 14px;
                    height: 200px;
                    text-align: left;
                    transition: box-shadow 0.3s ease;
                    cursor: default;
                }}
                </style>
                <div class="card-box">
                    📍 <b style="font-size: 16px;">{cleaned_name}</b><br>
                    🗺️ <b>주소:</b> <span style='color:#0066cc'>{short_address}</span><br>
                    🔌 <b>충전기 수:</b> {count}기<br>
                    ⚡ <b>종류:</b> <span style='color:#ff6600'>{types}</span><br>
                    🔋 <b>용량:</b> <span style='color:#009900'>{caps}</span>
                </div>
                ''', unsafe_allow_html=True)
                if st.form_submit_button("🔍 위치 보기", use_container_width=True):
                    st.session_state.clicked_station_id = sid
                    st.rerun()

def render_pagination_controls(total_pages):
    prev, mid, next = st.columns([1, 4, 1])
    with prev:
        if st.button("⬅ 이전") and st.session_state.page > 0:
            st.session_state.page -= 1
            st.session_state.clicked_station_id = None
            st.rerun()
    with next:
        if st.button("다음 ➡") and st.session_state.page < total_pages - 1:
            st.session_state.page += 1
            st.session_state.clicked_station_id = None
            st.rerun()
    with mid:
        st.markdown(f"<div style='text-align:center;'>📄 페이지 {st.session_state.page + 1} / {total_pages}</div>", unsafe_allow_html=True)


# 🔍 텍스트에서 숫자 추출 (kW 단위)
def extract_kw_from_text(text):
    try:
        match = re.search(r'(\d+(?:\.\d+)?)', str(text))
        return float(match.group(1)) if match else None
    except:
        return None

# 🔹 1. 충전기 종류 필터 함수
def render_type_filter(df):
    selected_types = []

    with st.expander("⚡ 충전기 종류 선택", expanded=True):
        # 🔍 데이터에서 실제 존재하는 charger_type 종류 추출
        available_types = set()
        for val in df['charger_type'].dropna():
            types = [t.strip() for t in str(val).split('+')]
            available_types.update(types)

        # 🏷️ 라벨 매핑 정의
        type_labels = {
            "DC콤보": "🔌 DC콤보",
            "AC완속": "🐢 AC완속",
            "DC차데모": "⚡ DC차데모",
            "AC3상": "🔋 AC3상",
            "NACS": "💥 NACS",
        }

        all_defined_types = list(type_labels.keys())

        for t in all_defined_types:
            label = type_labels[t]
            key = f"chk_{t}"
            if t in available_types:
                if st.checkbox(label, key=key, value=st.session_state.get(key, False)):
                    selected_types.append(t)
            else:
                st.markdown(
                    f"<span style='color:gray'>🔒 <s>{label}</s> (해당 지역에 없음)</span>",
                    unsafe_allow_html=True
                )

    return selected_types


# 🔹 2. 용량 필터 함수
def render_capacity_filter(df, selected_types):
    df = df.copy()

    # ⚡ 충전용량 추출
    if 'capacity_kw' not in df.columns:
        df['capacity_kw'] = df['capacity'].apply(extract_kw_from_text)

    # 🔍 충전기 종류 필터링
    if selected_types:
        types_str = ", ".join(selected_types)
        st.markdown(
            f"""<div style="font-size:17px;">
                ✅ 선택된 충전기 종류: <b>{types_str}</b>
                </div>""",
            unsafe_allow_html=True
        )
        df = df[df['charger_type'].apply(lambda s: any(t in str(s).split('+') for t in selected_types))]
    else:
        st.markdown("✅ 선택된 충전기 종류: *(전체)*")

    capacity_values = df['capacity_kw'].dropna()
    if capacity_values.empty:
        st.info("표시 가능한 충전용량 정보가 없습니다.")
        return []

    # 🔎 필터링된 용량 목록 미리보기 (👉 슬라이더보다 위에 표시)
    preview_kw_list = sorted(capacity_values.unique())
    if preview_kw_list:
        def get_color(kw):
            if kw < 50:
                return "#AED9E0"  # 파랑
            elif kw <= 100:
                return "#B9E3C6"  # 초록
            else:
                return "#F9D3A7"  # 주황

        styled_kw_html = " ".join([
            f"""<span style="background-color:{get_color(kw)}; padding:4px 8px; 
                   border-radius:6px; font-size:15px; margin:3px; display:inline-block;">
                   {kw:.0f}kW</span>"""
            for kw in preview_kw_list
        ])

        st.markdown(
            f"""<div style="font-size:17px; margin-top:10px; margin-bottom:5px;">
                    🔎 <b>적용 가능한 용량 목록 ({len(preview_kw_list)}개):</b>
                </div>""",
            unsafe_allow_html=True
        )
        st.markdown(styled_kw_html, unsafe_allow_html=True)
    else:
        st.info("선택된 충전기 종류에 해당하는 충전용량이 없습니다.")
        return []
    
    # ✅ 슬라이더 UI
    min_kw, max_kw = int(capacity_values.min()), int(capacity_values.max())
    if min_kw == max_kw:
        # 선택 가능한 값이 하나뿐일 때는 슬라이더 대신 안내만 표시
        st.markdown(
            f"""<div style="font-size:17px; color:gray; margin-top:10px;">
                    ⚡ 선택 가능한 충전용량이 <b>{min_kw} kW</b> 하나뿐입니다.
                </div>""",
            unsafe_allow_html=True
        )
        selected_min, selected_max = min_kw, max_kw
    else:
        selected_min, selected_max = st.slider(
            "⚡ 충전용량 (kW) 범위 선택",
            min_value=min_kw,
            max_value=max_kw,
            value=(min_kw, max_kw),
            step=5
        )
    st.markdown(
        f"""<div style="font-size:17px; margin-top:10px;">
                📁 <b>선택된 범위:</b> {selected_min} kW ~ {selected_max} kW
            </div>""",
        unsafe_allow_html=True
    )
    # 🔁 선택 범위로 최종 필터링
    filtered_kw_list = sorted(capacity_values[
        (capacity_values >= selected_min) & (capacity_values <= selected_max)
    ].unique())

    return filtered_kw_list


#필터링 -> starion_list 압축
def summarize_station_rows(df):
    if df.empty:
        return df

    df['capacity_kw'] = df['capacity'].apply(extract_kw_from_text)
    df['station_name'] = df['station_name'].apply(normalize_station_name)

    def summarize_group(group):
        name = group['station_name'].iloc[0]
        address = group['address'].iloc[0]
        lat = group['lat'].iloc[0] if 'lat' in group else None
        lon = group['lon'].iloc[0] if 'lon' in group else None
        station_id = group['station_id'].iloc[0] if 'station_id' in group else None

        # 충전기 종류별 카운트
        types = group['charger_type'].value_counts().to_dict()
        types_str = ", ".join([f"{k} ({v}기)" for k, v in types.items()])

        # 용량별 카운트
        caps = group['capacity_kw'].value_counts().to_dict()
        caps_str = ", ".join([f"{int(k)}kW ({v}기)" for k, v in sorted(caps.items())])

        return pd.Series({
            'station_name': name,
            'address': address,
            'charger_types': types_str,
            'capacities': caps_str,
            'latitude' :lat,
            'longitude':lon

        })
    
    grouped_df = df.groupby('station_name').apply(summarize_group).reset_index(drop=True)
    return grouped_df




def render_station_expanders(df):
    for _, row in df.iterrows():
        # 🔢 충전기 타입 목록 및 개수 추출
        type_list = re.findall(r"(.*?\([\d]+기\))", row['충전기 타입'])
        total_type_chargers = sum(int(re.search(r"\((\d+)기\)", t).group(1)) for t in type_list)
        type_count = len(type_list)

        # ⚡ 용량 목록 및 개수 추출
        cap_list = re.findall(r"(.*?\([\d]+기\))", row['용량'])
        total_cap_chargers = sum(int(re.search(r"\((\d+)기\)", c).group(1)) for c in cap_list)
        cap_count = len(cap_list)

        # 📍 제목 형식
        title = (
            f"📍 {row['장소']} "
            f"(타입 {type_count}종 {total_type_chargers}기, "
            f"용량 {cap_count}종 {total_cap_chargers}기)"
        )

        with st.expander(title):
            st.markdown(f"**📫 주소:** {row['주소']}")

            st.markdown("**🔌 충전기 타입 목록:**")
            for part in type_list:
                st.markdown(f"- {part.strip()}")

            st.markdown("**⚡ 용량 목록:**")
            for part in cap_list:
                st.markdown(f"- {part.strip()}")


def render_station_html_details_1(df):
    html_output = """
<style>
    details {
        background-color: #f9f9f9;
        border: 1px solid #ddd;
        border-radius: 8px;
        padding: 10px 14px;
        margin-bottom: 10px;
        font-size: 15px;
    }
    summary {
        font-weight: 600;
        cursor: pointer;
    }
    ul {
        margin: 8px 0 0 0;
        padding-left: 20px;
    }
</style>
"""

    for _, row in df.iterrows():
        # 충전기 개수 및 종류 수 계산
        type_list = re.findall(r"(.*?\([\d]+기\))", row['충전기 타입'])
        cap_list = re.findall(r"(.*?\([\d]+기\))", row['용량'])
        type_list = [t.strip().lstrip(',') for t in type_list]
        cap_list = [c.strip().lstrip(',') for c in cap_list]
        type_count = len(type_list)
        cap_count = len(cap_list)
        total_type_chargers = sum(int(re.search(r"\((\d+)기\)", t).group(1)) for t in type_list)
        total_cap_chargers = sum(int(re.search(r"\((\d+)기\)", c).group(1)) for c in cap_list)

        # 요약 제목
        summary_title = f"📍 {row['장소']} (타입 {type_count}종 {total_type_chargers}기, 용량 {cap_count}종 {total_cap_chargers}기)"

        # HTML details 블록 추가
        html_output += f"""
<details>
    <summary>{summary_title}</summary>
    <div><b>📫 주소:</b> {row['주소']}</div>
    <div><b>🔌 충전기 타입 목록:</b>
        <ul>{"".join(f"<li>{t.strip().lstrip(',')}</li>" for t in type_list)}</ul>
    </div>
    <div><b>⚡ 용량 목록:</b>
        <ul>{"".join(f"<li>{c.strip().lstrip(',')}</li>" for c in cap_list)}</ul>
    </div>
</details>
"""

    return html_output


def render_station_html_details(df):
    html_output = """
<style>
    details {
        background-color: #ffffff;
        border: 1px solid #ccc;
        border-radius: 10px;
        padding: 12px 16px;
        margin-bottom: 12px;
        font-size: 15px;
        box-shadow: 0 2px 6px rgba(0,0,0,0.05);
        transition: all 0.3s ease;
    }
    details:hover {
        border-color: #1976D2;
        box-shadow: 0 4px 12px rgba(25, 118, 210, 0.1);
    }
    summary {
        font-weight: 600;
        font-size: 16px;
        cursor: pointer;
        color: #333;
    }
    summary::marker {
        color: #1976D2;
    }
    ul {
        margin: 6px 0 0 0;
        padding-left: 20px;
    }
    li {
        margin-bottom: 4px;
    }
    .info-block {
        margin-top: 8px;
        margin-bottom: 6px;
    }
    .info-block b {
        color: #555;
    }
</style>
"""


    for _, row in df.iterrows():
        # 충전기 개수 및 종류 수 계산
        type_list = re.findall(r"(.*?\([\d]+기\))", row['충전기 타입'])
        cap_list = re.findall(r"(.*?\([\d]+기\))", row['용량'])
        type_list = [t.strip().lstrip(',') for t in type_list]
        cap_list = [c.strip().lstrip(',') for c in cap_list]
        type_count = len(type_list)
        cap_count = len(cap_list)
        total_type_chargers = sum(int(re.search(r"\((\d+)기\)", t).group(1)) for t in type_list)
        total_cap_chargers = sum(int(re.search(r"\((\d+)기\)", c).group(1)) for c in cap_list)
        summary_title = f"📍 <b>{row['장소']}</b> <span style='color:#888'>(타입 {type_count}종 {total_type_chargers}기, 용량 {cap_count}종 {total_cap_chargers}기)</span>"

        html_output += f"""
<details>
    <summary>{summary_title}</summary>
    <div class="info-block"><b>📫 주소:</b> {row['주소']}</div>
    <div class="info-block"><b>🔌 충전기 타입 목록:</b>
        <ul>{"".join(f"<li>{t}</li>" for t in type_list)}</ul>
    </div>
    <div class="info-block"><b>⚡ 용량 목록:</b>
        <ul>{"".join(f"<li>{c}</li>" for c in cap_list)}</ul>
    </div>
</details>
"""


    return html_output

import urllib.parse  # 주소 인코딩을 위해 필요

def render_station_html_details_g(df,force_collapse=True):
    html_output = """
<style>
    details {
        background-color: #ffffff;
        border: 1px solid #ccc;
        border-radius: 10px;
        padding: 12px 16px;
        margin-bottom: 12px;
        font-size: 15px;
        box-shadow: 0 2px 6px rgba(0,0,0,0.05);
        transition: all 0.3s ease;
    }
    details:hover {
        border-color: #1976D2;
        box-shadow: 0 4px 12px rgba(25, 118, 210, 0.1);
    }
    summary {
        font-weight: 600;
        font-size: 16px;
        cursor: pointer;
        color: #333;
    }
    summary::marker {
        color: #1976D2;
    }
    ul {
        margin: 6px 0 0 0;
        padding-left: 20px;
    }
    li {
        margin-bottom: 4px;
    }
    .info-block {
        margin-top: 8px;
        margin-bottom: 6px;
    }
    .info-block b {
        color: #555;
    }
</style>
"""

    for _, row in df.iterrows():
        type_list = re.findall(r"(.*?\([\d]+기\))", row['충전기 타입'])
        cap_list = re.findall(r"(.*?\([\d]+기\))", row['용량'])
        type_list = [t.strip().lstrip(',') for t in type_list]
        cap_list = [c.strip().lstrip(',') for c in cap_list]
        type_count = len(type_list)
        cap_count = len(cap_list)
        total_type_chargers = sum(int(re.search(r"\((\d+)기\)", t).group(1)) for t in type_list)
        total_cap_chargers = sum(int(re.search(r"\((\d+)기\)", c).group(1)) for c in cap_list)

        summary_title = f"📍 <b>{row['장소']}</b> <span style='color:#888'>(타입 {type_count}종 {total_type_chargers}기, 용량 {cap_count}종 {total_cap_chargers}기)</span>"

        # Google Maps iframe URL 생성
        encoded_address = urllib.parse.quote(row['주소'])
        map_url = f"https://www.google.com/maps?q={encoded_address}&output=embed"
        open_after="" if force_collapse else "open"
        html_output += f"""
<details {open_after}>
    <summary>{summary_title}</summary>
    <div class="info-block"><b>📫 주소:</b> {row['주소']}</div>
    <div class="info-block"><b>🔌 충전기 타입 목록:</b>
        <ul>{"".join(f"<li>{t}</li>" for t in type_list)}</ul>
    </div>
    <div class="info-block"><b>⚡ 용량 목록:</b>
        <ul>{"".join(f"<li>{c}</li>" for c in cap_list)}</ul>
    </div>
    <div class="info-block"><b>🗺️ 위치 지도:</b><br>
        <iframe src="{map_url}" width="100%" height="300" style="border:0;" allowfullscreen="" loading="lazy"></iframe>
    </div>
</details>
"""

    return html_output

def Legend_Customization():
    st.markdown("""
<div style="margin-top: 10px; padding: 10px; border: 1px solid #ccc; border-radius: 8px; background-color: #f9f9f9; font-size: 14px;">
<b>🎨 마커 색상 및 아이콘 범례</b>
<div style="display: flex; flex-wrap: wrap; gap: 40px; margin-top: 10px;">
    <ul style="list-style: none; padding-left: 0; margin: 0; flex: 1;">
        <li><span style="display:inline-block; width:12px; height:12px; background-color: rebeccapurple; border-radius: 50%; margin-right: 8px;"></span>7kW 단독 <i class="fas fa-battery-quarter"></i></li>
        <li><span style="display:inline-block; width:12px; height:12px; background-color: orange; border-radius: 50%; margin-right: 8px;"></span>7kW <i class="fas fa-battery-quarter"></i></li>
        <li><span style="display:inline-block; width:12px; height:12px; background-color: mediumseagreen; border-radius: 50%; margin-right: 8px;"></span>11kW 단독 <i class="fas fa-battery-half"></i></li>
        <li><span style="display:inline-block; width:12px; height:12px; background-color: lightblue; border-radius: 50%; margin-right: 8px;"></span>14kW 단독 <i class="fas fa-plug"></i></li>
        <li><span style="display:inline-block; width:12px; height:12px; background-color: cornflowerblue; border-radius: 50%; margin-right: 8px;"></span>50kW <i class="fas fa-car"></i></li>
    </ul>
    <ul style="list-style: none; padding-left: 0; margin: 0; flex: 1;">
        <li><span style="display:inline-block; width:12px; height:12px; background-color: deeppink; border-radius: 50%; margin-right: 8px;"></span>100kW 단독 <i class="fas fa-battery-full"></i></li>
        <li><span style="display:inline-block; width:12px; height:12px; background-color: darkred; border-radius: 50%; margin-right: 8px;"></span>100kW 동시 <i class="fas fa-bolt"></i></li>
        <li><span style="display:inline-block; width:12px; height:12px; background-color: cadetblue; border-radius: 50%; margin-right: 8px;"></span>200kW 동시 <i class="fas fa-charging-station"></i></li>
        <li><span style="display:inline-block; width:12px; height:12px; background-color: gray; border-radius: 50%; margin-right: 8px;"></span>기타 / 알 수 없음 <i class="fas fa-question"></i></li>
    </ul>
</div>
</div>
""", unsafe_allow_html=True)

@st.cache_data(ttl=3600)
def load_or_generate_summary(region, district):
    os.makedirs("cache", exist_ok=True)

    # ✅ 안전한 파일 이름 처리
    safe_region = region.replace(" ", "_")
    safe_district = district.replace(" ", "_")
    path = f"cache/summary_{safe_region}_{safe_district}.parquet"

    if os.path.exists(path):
        return pd.read_parquet(path)

    # → 요약 생성
    df = get_station_data(region, district)
    summary = generate_summary(df)

    summary.to_parquet(path)
    return summary
