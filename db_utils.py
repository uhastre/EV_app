# db_utils.py
from sqlalchemy import create_engine, text
import pandas as pd
import re
import streamlit as st




# SQLAlchemy 엔진 생성
engine = create_engine("mysql+mysqlconnector://root:1234@localhost:3306/evcar", echo=False)

# 시/도 리스트
def get_region_list(include_all=False):
    query = text("SELECT DISTINCT region_name FROM station_charger_view ORDER BY region_name")
    df = pd.read_sql(query, engine)
    region_list = df['region_name'].tolist()
    if include_all:
        return ["전국"] + region_list
    return region_list

# 구/군 리스트
def get_district_list(region):
    query = text("""
        SELECT DISTINCT district_name
        FROM station_charger_view
        WHERE region_name = :region
        ORDER BY district_name
    """)
    df = pd.read_sql(query, engine, params={"region": region})
    district_list = df['district_name'].tolist()
    return ["전체"] + district_list  # ✅ "전체" 옵션 맨 앞에 추가


@st.cache_data(ttl=600)
def get_station_data(region=None, district=None):
    import os

    os.makedirs("cache", exist_ok=True)
    safe_region = region.replace(" ", "_") if region else "전체"
    safe_district = district.replace(" ", "_") if district else "전체"
    cache_path = f"cache/station_{safe_region}_{safe_district}.parquet"

    # ✅ 파일이 있으면 바로 불러오기
    if os.path.exists(cache_path):
        return pd.read_parquet(cache_path)

    # ✅ 없으면 DB에서 가져오기
    base_query = "SELECT * FROM station_charger_with_subsidy"
    filters = []
    params = {}

    if region and region != "전국":
        filters.append("region_name = :region")
        params["region"] = region
    if district and district != "전체":
        filters.append("district_name = :district")
        params["district"] = district

    if filters:
        base_query += " WHERE " + " AND ".join(filters)

    query = text(base_query)
    df = pd.read_sql(query, engine, params=params)

    # ✅ 캐시 저장
    df.to_parquet(cache_path, index=False)
    return df




def get_use_time_by_station_id(station_id):
    query = text("""
        SELECT DISTINCT available_time
        FROM chargers_generated
        WHERE station_id = :station_id
        LIMIT 1
    """)
    df = pd.read_sql(query, engine, params={"station_id": station_id})
    return df['available_time'].iloc[0] if not df.empty else "정보 없음"

def get_region_center(region_name):
    query = """
    SELECT latitude, longitude
    FROM region_centers
    WHERE region = %s
    """
    df = pd.read_sql(query, engine, params=(region_name,))
    if df.empty:
        return None, None
    return df.iloc[0]['latitude'], df.iloc[0]['longitude']


def clean_address_from_station_name(row):
    address = str(row['address']).strip()
    station = str(row['station_name']).strip()

    if address.endswith(station):
        return address[: -len(station)].strip()
    return address

def normalize_station_name(name: str) -> str:
    if not isinstance(name, str):
        return name

    # 괄호 앞뒤 공백 통일: '(대전) 휴게소' → '(대전)휴게소'
    name = re.sub(r'\(\s*', '(', name)
    name = re.sub(r'\s*\)', ')', name)

    # 괄호와 문자 사이 공백 제거: '(대전) 휴게소' → '(대전)휴게소'
    name = re.sub(r'\)\s+', ')', name)
    name = re.sub(r'\s+\(', '(', name)

    # 연속 공백 하나로 줄이기
    name = re.sub(r'\s+', ' ', name)

    return name.strip()

def get_nationwide_summary():
    query = "SELECT * FROM station_charger_nationwide_summary"
    return pd.read_sql(query, engine)

