# pages/2_충전기_필터.py
import streamlit as st
from db_utils import get_region_list, get_district_list, get_station_data,clean_address_from_station_name,normalize_station_name
from ev_ui_utils import (
    extract_kw_from_text,render_type_filter,render_capacity_filter,
    summarize_station_rows,render_station_expanders,
    render_station_html_details_g)
import pandas as pd
from ev_ui_utils import render_station_html_details


st.set_page_config(page_title="충전기 필터", layout="wide")
st.title("🔍 충전기 필터")

# 🔁 초기값 설정
DEFAULT_REGION = "충청남도"
DEFAULT_DISTRICT = "논산시 "

region_list = get_region_list()
default_region_index = region_list.index(DEFAULT_REGION) if DEFAULT_REGION in region_list else 0


# ✅ 전체 요약 출력
def show_summary_box(station_count, charger_count, filtered=False):
    if filtered:
        color = '#4CAF50'  # 초록색
        label = "📊 필터링 결과 요약"
    else:
        color = '#1976D2'  # 파란색
        label = "📊 선택 지역 전체 요약"

    st.markdown(f"### {label}")
    st.markdown(
        f"🏪 **충전소 수:** <span style='color:{color};font-weight:bold'>{station_count}</span> 개", 
        unsafe_allow_html=True
    )
    st.markdown(
        f"🔌 **충전기 수:** <span style='color:{color};font-weight:bold'>{charger_count}</span> 기", 
        unsafe_allow_html=True
    )



# 👉 수평 정렬
col_region, col_district = st.columns([1, 1])

with col_region:
    region = st.selectbox("📍 시/도 선택", region_list, index=default_region_index, key="filter_region")

district_list = get_district_list(region)
default_district_index = (
    district_list.index(DEFAULT_DISTRICT) if region == DEFAULT_REGION and DEFAULT_DISTRICT in district_list else 0
)

with col_district:
    district = st.selectbox("🗺️ 구/군 선택", district_list, index=default_district_index, key="filter_district")

# ✅ 지역 기반 데이터 가져오기
df = get_station_data(region, district if district != "전체" else None)

if df.empty:
    st.warning("선택된 지역에 충전소 데이터가 없습니다.")
    st.stop()

# ✅ 전체 수 요약 (초기값)
total_station_count = df['station_name'].nunique()
total_charger_count = len(df)

# 🔻 구분선
st.markdown('------')



if df.empty:
    st.warning("선택된 지역에 충전소 데이터가 없습니다.")
else:  
    col1, col2 = st.columns([1.2, 2])

    # ✅ 필터 선택 UI
    with col1:
        selected_types = render_type_filter(df)
        selected_caps = render_capacity_filter(df,selected_types)
    # 🔁 필터 초기화 버튼
        btn_cols = st.columns([3, 1.3])  # 왼쪽 공간 3, 오른쪽 버튼 1 비율
        with btn_cols[1]:
            if st.button("🔄 필터 초기화", key="filter_reset"):
                for key in list(st.session_state.keys()):
                    if key.startswith("chk_") or key.startswith("filter_cap_pills"):
                        del st.session_state[key]
                # _ = render_type_filter(df)
                # _ = render_capacity_filter(df)
                st.rerun()

    
        # ✅ 필터링 로직
    filtered_df = df.copy()

    if 'capacity_kw' not in filtered_df.columns:
        filtered_df['capacity_kw'] = filtered_df['capacity'].apply(extract_kw_from_text)

    if selected_types:
        filtered_df = filtered_df[
            filtered_df['charger_type'].apply(
                lambda s: any(t in str(s).split('+') for t in selected_types)
            )
        ]

    if selected_caps:
        filtered_df = filtered_df[filtered_df['capacity_kw'].isin(selected_caps)]

    # ✅ 주소 정리 및 요약
    filtered_df['address'] = filtered_df.apply(clean_address_from_station_name, axis=1)
    summarized_df = summarize_station_rows(filtered_df)
    with col1:
        filtered_station_count = len(summarized_df)
        total_charger_count = len(filtered_df)
        st.markdown("### 📊 필터링 결과 요약")
        st.markdown(f"🔎 **필터링된 충전소 수:** <span style='color:#4CAF50;font-weight:bold'>{filtered_station_count}</span> 개", unsafe_allow_html=True)
        st.markdown(f"🔋 **충전기 수 총합:** <span style='color:#4CAF50;font-weight:bold'>{total_charger_count}</span> 기", unsafe_allow_html=True)



    # ✅ 결과 출력
    # with col2:
        
    #     items_per_page = 10
    #     total_items = len(summarized_df)
    #     total_pages = (total_items - 1) // items_per_page + 1

    #     # 🔁 컬럼명 한글로 변경
    #     summarized_df = summarized_df.rename(columns={
    #         'station_name': '장소',
    #         'address': '주소',
    #         'charger_types': '충전기 타입',
    #         'capacities': '용량'
    #     })
        
    #     # 갯수검증..
    #     summarized_df = summarized_df.reset_index(drop=True)
    #     summarized_df['장소'] = summarized_df.index.map(lambda i: f"{i+1}. {summarized_df.loc[i, '장소']}")

    #     if 'current_page' not in st.session_state:
    #         st.session_state.current_page = 1
    #     start_idx = (st.session_state.current_page - 1) * items_per_page
    #     end_idx = start_idx + items_per_page
    #     paged_df = summarized_df.iloc[start_idx:end_idx]

    #     # st.subheader("📋충전소 리스트")
    #     # st.markdown(render_station_html_details(summarized_df), unsafe_allow_html=True)

    #     st.subheader("📋충전소 리스트")
    #     st.markdown(render_station_html_details_g(summarized_df), unsafe_allow_html=True)
        
    #     # 페이지네이션 UI
    #     col_prev, col_page, col_next = st.columns([1, 2, 1])
    #     with col_prev:
    #         if st.button("⬅️ 이전"):
    #             if st.session_state.current_page > 1:
    #                 st.session_state.current_page -= 1
    #                 st.rerun()
    #     with col_page:
    #         st.number_input("페이지", min_value=1, max_value=total_pages, key="current_page", format="%d")
    #     with col_next:
    #         if st.button("다음 ➡️"):
    #             if st.session_state.current_page < total_pages:
    #                 st.session_state.current_page += 1
    #                 st.rerun()

    with col2:
        
        if 'last_filter' not in st.session_state:
            st.session_state.last_filter = (selected_types, selected_caps)

        if (selected_types, selected_caps) != st.session_state.last_filter:
            st.session_state.current_page = 1
            st.session_state.last_filter = (selected_types, selected_caps)

        items_per_page = 10
        total_items = len(summarized_df)
        total_pages = (total_items - 1) // items_per_page + 1

        # 컬럼명 한글로 변경
        summarized_df = summarized_df.rename(columns={
            'station_name': '장소',
            'address': '주소',
            'charger_types': '충전기 타입',
            'capacities': '용량'
        }).reset_index(drop=True)

        # 번호 붙이기
        summarized_df['장소'] = summarized_df.index.map(lambda i: f"{i+1}. {summarized_df.loc[i, '장소']}")


        # 현재 페이지 상태
        if "current_page" not in st.session_state:
            st.session_state.current_page = 1
        current_page = st.session_state.current_page  # 로컬 변수 사용

        # 페이지별 데이터 추출
        start_idx = (current_page - 1) * items_per_page
        end_idx = start_idx + items_per_page
        paged_df = summarized_df.iloc[start_idx:end_idx]
        force_collapse = True
        # 리스트 출력
        st.subheader(f"📋 충전소 리스트 (총 {total_items}개 중 {start_idx+1}~{min(end_idx, total_items)}번)")
        # st.markdown(render_station_html_details_g(paged_df), unsafe_allow_html=True)
        st.markdown(render_station_html_details_g(paged_df, force_collapse=force_collapse), unsafe_allow_html=True)
        # # 페이지네이션 UI
        # col_prev, col_info, col_next = st.columns([1, 2, 0.4])
        # with col_prev:
        #     if st.button("⬅️ 이전", key="prev_page"):
        #         if current_page > 1:
        #             st.session_state.current_page = current_page - 1
        #             st.rerun()
        # with col_info:
        #     st.markdown(f"<div style='text-align: center; font-weight: bold; padding-top: 0.5rem;'>페이지 {current_page} / {total_pages}</div>", unsafe_allow_html=True)
        # with col_next:
        #     if st.button("다음 ➡️", key="next_page"):
        #         if current_page < total_pages:
        #             st.session_state.current_page = current_page + 1
        #             st.rerun()

        

        # 페이지네이션 UI
        col_prev, col_info, col_next = st.columns([1, 2, 0.6])

        with col_prev:
            if st.button("⬅️ 이전", key="prev_page"):
                if current_page > 1:
                    st.session_state.current_page = current_page - 1
                    st.rerun()

        with col_info:
            # 스타일을 적용한 number_input
            st.markdown(
                """
                <style>
                div[data-testid="stNumberInput"] {
                    width: 100px;
                    margin: 0 auto;
                }
                </style>
                """,
                unsafe_allow_html=True
            )

            page_input = st.number_input(
                " ",  # 라벨을 공백으로 해서 공간 절약
                min_value=1,
                max_value=total_pages,
                value=current_page,
                step=1,
                key="page_input"
            )

            if page_input != current_page:
                st.session_state.current_page = page_input
                st.rerun()

            st.markdown(
                f"<div style='text-align: center; font-weight: bold; padding-top: 0.5rem;'>페이지 {current_page} / {total_pages}</div>",
                unsafe_allow_html=True
            )

        with col_next:
            if st.button("다음 ➡️", key="next_page"):
                if current_page < total_pages:
                    st.session_state.current_page = current_page + 1
                    st.rerun()
