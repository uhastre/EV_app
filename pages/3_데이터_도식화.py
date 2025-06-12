import streamlit as st
import pandas as pd
import plotly.express as px
from db_utils import get_station_data, get_region_list, get_district_list
from utils import engine, load_or_create_nationwide_data

# -----------------------------
# ✅ Streamlit 설정 및 제목
# -----------------------------
st.set_page_config(page_title="데이터 도식화", layout="wide")
st.title("\U0001F4CA 전기차 충전소 데이터 도식화")

# -----------------------------
# ✅ 지역 선택 UI 구성
# -----------------------------
DEFAULT_REGION = "충청남도"
DEFAULT_DISTRICT = "논산시 "

col1, col2 = st.columns([1, 1])  # 두 컬럼 동일 비율로 나눔

with col1:
    region_list = get_region_list(include_all=True)
    default_region_index = region_list.index(DEFAULT_REGION) if DEFAULT_REGION in region_list else 0
    region = st.selectbox("📍 시/도 선택", region_list, index=default_region_index)

with col2:
    district_list = get_district_list(region)
    default_district_index = (
        district_list.index(DEFAULT_DISTRICT)
        if region == DEFAULT_REGION and DEFAULT_DISTRICT in district_list
        else 0
    )
    district = st.selectbox("🗺️ 구/군 선택", district_list, index=default_district_index)

# -----------------------------
# ✅ 데이터 불러오기 (전국 vs 지역 분기)
# -----------------------------
if region == "전국":
    df = load_or_create_nationwide_data()
else:
    df = get_station_data(region, None if district == "전체" else district)

district_display = district if district != "전체" else "전체"

# -----------------------------
# 🔹 col_a: 구/군 또는 시/도별 충전소 수
# -----------------------------
col_a, col_b = st.columns(2)
with col_a:
    if region == "전국":
        region_chart = (
            df.groupby('region_name')['station_id']
            .nunique()
            .reset_index()
            .rename(columns={'region_name': '시/도', 'station_id': '충전소 수'})
        )
        fig = px.bar(
            region_chart, x='시/도', y='충전소 수',
            title="📍 전국 시/도별 충전소 수",
            color='시/도', text='충전소 수',
            color_discrete_sequence=px.colors.qualitative.Set2
        )
    else:
        full_region_df = get_station_data(region=region)
        district_chart = (
            full_region_df.groupby('district_name')['station_id']
            .nunique()
            .reset_index()
            .rename(columns={'district_name': '구/군', 'station_id': '충전소 수'})
        )
        top_chart = district_chart.sort_values(by='충전소 수', ascending=False).head(10)
        if district not in top_chart['구/군'].values:
            selected_row = district_chart[district_chart['구/군'] == district]
            top_chart = pd.concat([top_chart, selected_row], ignore_index=True)

        fig = px.bar(
            top_chart, x='구/군', y='충전소 수',
            title=f"📍 '{region}' 내 구/군별 충전소 수 (선택: {district})",
            color='구/군', text='충전소 수',
            color_discrete_sequence=px.colors.qualitative.Set2
        )
    fig.update_layout(xaxis_tickangle=-45, height=350)
    st.plotly_chart(fig, use_container_width=True)

# -----------------------------
# 🔹 col_b: 용량별 충전기 분포
# -----------------------------
# with col_b:
#     capacity_chart = df.groupby("capacity")["charger_local_id"].count().reset_index()
#     capacity_chart.columns = ["용량", "충전기 수"]
#     fig = px.pie(
#         capacity_chart, names="용량", values="충전기 수",
#         title="⚡ 용량별 충전기 분포", hole=0.4,
#         color_discrete_sequence=px.colors.sequential.RdBu
#     )
#     fig.update_traces(textposition="inside", textinfo="percent+label")
#     fig.update_layout(height=350)
#     st.plotly_chart(fig, use_container_width=True)
with col_b:
    capacity_chart = df.groupby("capacity")["charger_local_id"].count().reset_index()
    capacity_chart.columns = ["용량", "충전기 수"]
    capacity_chart = capacity_chart.sort_values(by="충전기 수", ascending=False)

    # Top 6 + 기타 묶기
    top_n = 6
    if len(capacity_chart) > top_n:
        top = capacity_chart.head(top_n)
        other_sum = capacity_chart["충전기 수"][top_n:].sum()
        others = pd.DataFrame({"용량": ["기타"], "충전기 수": [other_sum]})
        capacity_chart = pd.concat([top, others], ignore_index=True)

    # 비율 계산
    capacity_chart["비율"] = (capacity_chart["충전기 수"] / capacity_chart["충전기 수"].sum() * 100).round(1)
    capacity_chart["레이블"] = capacity_chart.apply(lambda row: f"{row['용량']}<br>{row['비율']}%", axis=1)

    fig = px.pie(
        capacity_chart,
        names="레이블",
        values="충전기 수",
        title="⚡ 용량별 충전기 분포 (Top 6 + 기타)",
        hole=0.4,
        color_discrete_sequence=px.colors.qualitative.Bold 
    )
    fig.update_traces(textposition="inside", textinfo="percent+label")
    fig.update_layout(height=350)
    st.plotly_chart(fig, use_container_width=True)

# -----------------------------
# 🔹 col_c: 충전기 종류별 분포
# -----------------------------
col_c, col_d = st.columns(2)
with col_c:
    type_chart = df.groupby("charger_type")["charger_local_id"].count().reset_index()
    type_chart.columns = ["종류", "충전기 수"]
    type_chart = type_chart.sort_values(by="충전기 수", ascending=False)

    # Top 4 + 기타
    top_n = 5
    if len(type_chart) > top_n:
        top = type_chart.head(top_n)
        other_sum = type_chart["충전기 수"][top_n:].sum()
        others = pd.DataFrame({"종류": ["기타"], "충전기 수": [other_sum]})
        type_chart = pd.concat([top, others], ignore_index=True)

    type_chart["비율"] = (type_chart["충전기 수"] / type_chart["충전기 수"].sum() * 100).round(1)

    fig = px.bar(
        type_chart,
        x="종류",
        y="충전기 수",
        color="종류",
        text="비율",
        title="🔌 충전기 종류별 분포 (로그스케일)",
        color_discrete_sequence=px.colors.qualitative.Pastel,
    )
    fig.update_traces(texttemplate="%{y}기 (%{text}%)", textposition="outside")
    fig.update_layout(yaxis_type="log", xaxis_tickangle=-45, height=350)
    st.plotly_chart(fig, use_container_width=True)

# 🔹 col_d: 시설 유형별 충전기 수 (Top10)
# -----------------------------
with col_d:
    facility_chart = df.groupby("facility_major")["charger_local_id"].count().reset_index()
    facility_chart.columns = ["시설 유형", "충전기 수"]
    facility_chart = facility_chart.sort_values(by="충전기 수", ascending=False)

    # Top 8 + 기타
    top_n = 8
    if len(facility_chart) > top_n:
        top = facility_chart.head(top_n)
        other_sum = facility_chart["충전기 수"][top_n:].sum()
        others = pd.DataFrame({"시설 유형": ["기타"], "충전기 수": [other_sum]})
        facility_chart = pd.concat([top, others], ignore_index=True)

    facility_chart["비율"] = (facility_chart["충전기 수"] / facility_chart["충전기 수"].sum() * 100).round(1)

    fig = px.bar(
        facility_chart,
        x="시설 유형",
        y="충전기 수",
        color="시설 유형",
        text="비율",
        title="🏢 시설 유형별 충전기 수 (로그스케일)",
        color_discrete_sequence=px.colors.qualitative.Dark24,
    )
    fig.update_traces(texttemplate="%{y}기 (%{text}%)", textposition="outside")
    fig.update_layout(yaxis_type="log", xaxis_tickangle=-30, height=350)
    st.plotly_chart(fig, use_container_width=True)

# -----------------------------
# 🔹 col_e: 지역별 밀도 (시도 vs 용량)
# -----------------------------
col_e, col_f = st.columns(2)
import numpy as np

with col_e:
    if region == "전국":
        density_df = df.groupby(["region_name", "capacity"])["charger_local_id"].count().reset_index()
        density_df.columns = ["시도", "용량", "충전기 수"]

        # ⚠️ 로그 변환 (log(1+x)로 음수 방지)
        density_df["log_충전기 수"] = np.log1p(density_df["충전기 수"])

        fig = px.density_heatmap(
            density_df,
            x="시도", y="용량", z="log_충전기 수",  # log값을 z로 넣음
            title="📌 시도별 용량·충전기 밀도 (log)",
            color_continuous_scale="Turbo",
            text_auto=True,
        )
        fig.update_layout(height=450, xaxis_tickangle=-45)
        st.plotly_chart(fig, use_container_width=True)
    else:
        bar_df = df.groupby("capacity")["charger_local_id"].count().reset_index()
        bar_df.columns = ["용량", "충전기 수"]
        bar_df["log_충전기 수"] = np.log1p(bar_df["충전기 수"])

        fig = px.bar(
            bar_df,
            x="log_충전기 수", y="용량",
            orientation="h",
            title=f"📌 {region} {district_display} 내 용량별 충전기 수 (log)",
            color="용량",
            text="충전기 수",
            color_discrete_sequence=px.colors.qualitative.Set3,
        )
        fig.update_layout(height=450, yaxis=dict(categoryorder="total ascending"))
        st.plotly_chart(fig, use_container_width=True)


# -----------------------------
# 🔹 col_f: 충전기 수 vs 평균 보조금
# -----------------------------
with col_f:
    if region == "전국":
        subsidy_df = df.groupby("region_name").agg({
            "charger_local_id": "count",
            "max_subsidy_ev": "mean"
        }).reset_index()
        subsidy_df.columns = ["시도", "충전기 수", "평균 보조금"]

        avg_subsidy = subsidy_df["평균 보조금"].mean()

        fig = px.scatter(
            subsidy_df,
            x="충전기 수",
            y="평균 보조금",
            size="충전기 수",
            color="시도",
            hover_name="시도",
            title="💰 충전기 수 vs 평균 보조금",
            size_max=40,
            log_x=True,  # 🔍 충전기 수 차이 완화
            color_discrete_sequence=px.colors.qualitative.Bold
        )

        # ✅ 평균선 추가
        fig.add_hline(
            y=avg_subsidy,
            line_dash="dot",
            line_color="gray",
            annotation_text=f"평균 보조금 ≈ {int(avg_subsidy)}만원",
            annotation_position="top left"
        )

        # ✅ 레이아웃 개선
        fig.update_layout(
            height=500,
            xaxis_title="충전기 수 (log scale)",
            yaxis_title="평균 보조금 (만원)",
            xaxis=dict(
                showgrid=True, gridcolor="#f0f0f0",
                range=[4.2, np.log10(subsidy_df["충전기 수"].max() * 1.2)],  # ⬅️ 여기 조정!
            ),
            yaxis=dict(showgrid=True, gridcolor="#f0f0f0"),
            plot_bgcolor="white",
            title_font_size=20,
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5)
        )
        fig.update_traces(marker=dict(line=dict(width=1, color="DarkSlateGrey")))
        st.plotly_chart(fig, use_container_width=True)

    else:
        # ⚡ 시/도 단위 max/min 보조금 계산
        regional_df = df[df["region_name"] == region].copy()

        # 1. max_subsidy_ev를 숫자로 변환
        regional_df["max_subsidy_ev"] = pd.to_numeric(regional_df["max_subsidy_ev"], errors="coerce")
        regional_df["max_subsidy_mini"] = pd.to_numeric(regional_df["max_subsidy_mini"], errors="coerce")

        # 중복 제거 (충전소+보조금 조합만 남기기)
        unique_subsidy_df = regional_df.drop_duplicates(subset=["station_id", "max_subsidy_ev", "max_subsidy_mini"])

        max_subsidy = unique_subsidy_df["max_subsidy_ev"].max()
        min_subsidy = unique_subsidy_df["max_subsidy_mini"].min()
        
        with st.container():
            st.markdown(f"### 💸 '{region}' 보조금 요약")
            # 4. 출력
            col1, col2 = st.columns(2)
            with col1:
                st.metric("📈 승용차 최대 보조금 (만원)", f"{int(max_subsidy)}만원" if pd.notna(max_subsidy) else "정보 없음")
            with col2:
                st.metric("📉 소형차 최대 보조금 (만원)", f"{int(min_subsidy)}만원" if pd.notna(min_subsidy) else "정보 없음")
