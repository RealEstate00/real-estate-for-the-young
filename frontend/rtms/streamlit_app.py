import streamlit as st
import pandas as pd
import requests
import ssl
import urllib.parse
import certifi
import xml.etree.ElementTree as ET
from requests.adapters import HTTPAdapter
from urllib3.util.ssl_ import create_urllib3_context
import time
from datetime import datetime
import os
from dotenv import load_dotenv

# .env 파일 로드
load_dotenv()

# 페이지 설정
st.set_page_config(
    page_title="부동산 면적별 통계 분석",
    page_icon="🏠",
    layout="wide"
)

# 통신 오류 해결
class Tls12Adapter(HTTPAdapter):
    def init_poolmanager(self, *args, **kwargs):
        ctx = create_urllib3_context(ciphers="DEFAULT:@SECLEVEL=1")
        ctx.minimum_version = ssl.TLSVersion.TLSv1_2
        ctx.maximum_version = ssl.TLSVersion.TLSv1_2
        kwargs["ssl_context"] = ctx
        return super().init_poolmanager(*args, **kwargs)

    def proxy_manager_for(self, *args, **kwargs):
        ctx = create_urllib3_context(ciphers="DEFAULT:@SECLEVEL=1")
        ctx.minimum_version = ssl.TLSVersion.TLSv1_2
        ctx.maximum_version = ssl.TLSVersion.TLSv1_2
        kwargs["ssl_context"] = ctx
        return super().proxy_manager_for(*args, **kwargs)

# API 설정 정보
API_CONFIGS = {
    '아파트': {
        '매매': {
            'url': 'http://apis.data.go.kr/1613000/RTMSDataSvcAptTradeDev/getRTMSDataSvcAptTradeDev',
            'service_id': '1613000'
        },
        '전월세': {
            'url': 'https://apis.data.go.kr/1613000/RTMSDataSvcAptRent/getRTMSDataSvcAptRent',
            'service_id': '1613000'
        }
    },
    '연립/다세대': {
        '매매': {
            'url': 'https://apis.data.go.kr/1613000/RTMSDataSvcRHTrade/getRTMSDataSvcRHTrade',
            'service_id': '1613000'
        },
        '전월세': {
            'url': 'https://apis.data.go.kr/1613000/RTMSDataSvcRHRent/getRTMSDataSvcRHRent',
            'service_id': '1613000'
        }
    },
    '단독/다가구': {
        '매매': {
            'url': 'http://apis.data.go.kr/1613000/RTMSDataSvcSHTrade/getRTMSDataSvcSHTrade',
            'service_id': '1613000'
        },
        '전월세': {
            'url': 'https://apis.data.go.kr/1613000/RTMSDataSvcSHRent/getRTMSDataSvcSHRent',
            'service_id': '1613000'
        }
    },
    '오피스텔': {
        '매매': {
            'url': 'https://apis.data.go.kr/1613000/RTMSDataSvcOffiTrade/getRTMSDataSvcOffiTrade',
            'service_id': '1613000'
        },
        '전월세': {  
            'url': 'https://apis.data.go.kr/1613000/RTMSDataSvcOffiRent/getRTMSDataSvcOffiRent',
            'service_id': '1613000'
        }
    }
}

@st.cache_data
def load_dong_codes():
    """법정동코드 로드 (캐시됨)"""
    code_file = "법정동코드 전체자료.txt"
    code = pd.read_csv(code_file, sep='\t')
    code.columns = ['code', 'name', 'is_exist']
    
    # 폐지여부 == '존재'인 경우만 필터링
    code = code[code['is_exist'] == '존재']
    code['code'] = code['code'].apply(str)
    
    # 시도, 시군구, 동 분리
    code['시도'] = code['name'].str.split(' ').str[0]
    code['시군구'] = code['name'].str.split(' ').str[1]
    code['동'] = code['name'].str.split(' ').str[2]
    
    return code

def get_sigungu_options(code_df, selected_sido):
    """선택된 시도에 따른 시군구 옵션 반환"""
    if selected_sido and selected_sido != "전체":
        sigungus = code_df[code_df['시도'] == selected_sido]['시군구'].dropna().unique()
        return sorted(sigungus)
    return []

def get_dong_options(code_df, selected_sido, selected_sigungu):
    """선택된 시도, 시군구에 따른 동 옵션 반환"""
    if selected_sido and selected_sido != "전체" and selected_sigungu and selected_sigungu != "전체":
        dongs = code_df[
            (code_df['시도'] == selected_sido) & 
            (code_df['시군구'] == selected_sigungu)
        ]['동'].dropna().unique()
        return sorted(dongs)
    return []

def categorize_area(area):
    """면적에 따라 구분"""
    try:
        area_num = float(area)
    except (ValueError, TypeError):
        return "데이터오류"
    
    if area_num <= 60:
        return "60㎡이하"
    elif area_num <= 85:
        return "60㎡초과~85㎡이하"
    elif area_num <= 102:
        return "85㎡초과~102㎡이하"
    elif area_num <= 135:
        return "102㎡초과~135㎡이하"
    else:
        return "135㎡초과"

def calculate_statistics(df, price_col):
    """통계 계산"""
    if len(df) == 0:
        return {
            '최저값': 0,
            '최대값': 0,
            '최빈값': 0,
            '중앙값': 0,
            '평균값': 0,
            '데이터수': 0
        }
    
    df[price_col] = df[price_col].astype(str).str.replace(',', '').astype(float)
    
    return {
        '최저값': df[price_col].min(),
        '최대값': df[price_col].max(),
        '최빈값': df[price_col].mode().iloc[0] if len(df[price_col].mode()) > 0 else 0,
        '중앙값': df[price_col].median(),
        '평균값': df[price_col].mean(),
        '데이터수': len(df)
    }

def calculate_area_statistics(df, price_col, area_col):
    """면적별 통계 계산"""
    if len(df) == 0:
        return pd.DataFrame()
    
    df['면적구분'] = df[area_col].apply(categorize_area)
    
    area_stats = []
    for area_type in ["60㎡이하", "60㎡초과~85㎡이하", "85㎡초과~102㎡이하", "102㎡초과~135㎡이하", "135㎡초과", "데이터오류"]:
        area_data = df[df['면적구분'] == area_type]
        
        if len(area_data) > 0:
            stats = calculate_statistics(area_data, price_col)
            stats['면적구분'] = area_type
            area_stats.append(stats)
        else:
            area_stats.append({
                '면적구분': area_type,
                '최저값': 0,
                '최대값': 0,
                '최빈값': 0,
                '중앙값': 0,
                '평균값': 0,
                '데이터수': 0
            })
    
    result_df = pd.DataFrame(area_stats)
    result_df = result_df[['면적구분', '데이터수', '최저값', '최빈값', '중앙값', '평균값']]
    
    return result_df

def get_items(response):
    """XML 파싱"""
    root = ET.fromstring(response.content)
    item_list = []
    for child in root.find('body').find('items'):
        elements = child.findall('*')
        data = {}
        for element in elements:
            tag = element.tag.strip()
            text = element.text.strip() if element.text else ""
            data[tag] = text
        item_list.append(data)  
    return item_list

def fetch_real_estate_data(property_type, deal_type, dong_code, start_date, end_date):
    """부동산 데이터 수집"""
    api_config = API_CONFIGS[property_type][deal_type]
    API_URL = api_config['url']
    raw_key = "3a064e9eda5a4eaa6392524affd2e3ef46a4d78bc199b388346b333825849dad"
    encoded_key = urllib.parse.quote(raw_key, safe="")
    
    session = requests.Session()
    session.mount("https://", Tls12Adapter())
    
    all_data = []
    
    # 날짜 범위 생성
    start_year = int(start_date[:4])
    start_month = int(start_date[4:])
    end_year = int(end_date[:4])
    end_month = int(end_date[4:])
    
    target_dates = []
    current_year = start_year
    current_month = start_month
    
    while (current_year < end_year) or (current_year == end_year and current_month <= end_month):
        target_dates.append(f"{current_year:04d}{current_month:02d}")
        current_month += 1
        if current_month > 12:
            current_month = 1
            current_year += 1
    
    for deal_ymd in target_dates:
        params = {
            "serviceKey": encoded_key,
            "LAWD_CD": dong_code,
            "DEAL_YMD": deal_ymd,
            "pageNo": 1,
            "numOfRows": 1000
        }
        
        try:
            response = session.get(API_URL, params=params, timeout=15, verify=certifi.where())
            response.raise_for_status()
            
            items_list = get_items(response)
            
            if items_list:
                items = pd.DataFrame(items_list)
                
                # 부동산 유형과 거래 유형에 따른 컬럼 선택
                if property_type == '아파트':
                    if deal_type == '매매':
                        required_columns = [
                            'buildYear', 'dealMonth', 'dealYear', 'price', 'excluUseAr', 
                            'floor', 'jibun', 'aptNm', 'sggCd', 'sggNm', 'umdNm'
                        ]
                    else:  # 전월세
                        required_columns = [
                            'umdNm', 'aptNm', 'jibun', 'excluUseAr', 'dealYear', 
                            'dealMonth', 'deposit', 'monthlyRent', 'floor', 'buildYear', 
                            'contractTerm', 'contractType'
                        ]
                elif property_type == '연립/다세대':
                    if deal_type == '매매':
                        required_columns = [
                            'buildYear', 'dealMonth', 'dealYear', 'price', 'excluUseAr', 
                            'floor', 'jibun', 'aptNm', 'sggCd', 'sggNm', 'umdNm'
                        ]
                    else:  # 전월세
                        required_columns = [
                            'umdNm', 'houseType', 'mhouseNm', 'jibun', 'buildYear', 'excluUseAr', 
                            'dealMonth', 'deposit', 'monthlyRent', 'floor', 'dealYear', 
                            'contractTerm', 'contractType'
                        ]
                elif property_type == '단독/다가구':
                    if deal_type == '매매':
                        required_columns = [
                            'umdNm', 'totalFloorAr', 'dealYear', 'dealMonth', 'price', 
                            'buildYear', 'houseType', 'jibun'
                        ]
                    else:  # 전월세
                        required_columns = [
                            'umdNm', 'totalFloorAr', 'dealYear', 'dealMonth', 
                            'deposit', 'monthlyRent', 'buildYear', 'contractTerm', 'contractType', 
                            'houseType', 'jibun'
                        ]
                elif property_type == '오피스텔':
                    if deal_type == '매매':
                        required_columns = [
                            'buildYear', 'dealMonth', 'dealYear', 'price', 'excluUseAr', 
                            'floor', 'jibun', 'offiNm', 'sggCd', 'sggNm', 'umdNm'
                        ]
                    else:  # 전월세
                        required_columns = [
                            'buildYear', 'contractType', 'contractTerm', 'dealMonth', 'dealYear', 
                            'deposit', 'excluUseAr', 'floor', 'jibun', 'monthlyRent', 
                            'offiNm', 'sggCd', 'sggNm', 'umdNm'
                        ]
                
                available_columns = [col for col in required_columns if col in items.columns]
                filtered_items = items[available_columns].copy()
                
                all_data.append(filtered_items)
            
            time.sleep(0.1)  # API 호출 간격
            
        except Exception as e:
            st.error(f"API 호출 오류: {str(e)[:50]}...")
            continue
    
    if all_data:
        final_df = pd.concat(all_data, ignore_index=True)
        
        # 계약기간 분리 (오피스텔, 단독/다가구 전월세)
        if deal_type == '전월세' and 'contractTerm' in final_df.columns:
            contract_terms = final_df['contractTerm'].str.split('~', expand=True)
            if len(contract_terms.columns) >= 2:
                final_df['con_start'] = contract_terms[0]
                final_df['con_end'] = contract_terms[1]
            else:
                final_df['con_start'] = ''
                final_df['con_end'] = ''
            final_df = final_df.drop('contractTerm', axis=1)
        
        # 면적 컬럼명 통일 (단독/다가구는 totalFloorAr, 나머지는 excluUseAr)
        if property_type == '단독/다가구' and 'totalFloorAr' in final_df.columns:
            final_df['excluUseAr'] = final_df['totalFloorAr']
        elif property_type == '단독/다가구' and 'excluUseAr' not in final_df.columns:
            # 단독/다가구에서 totalFloorAr가 없는 경우 다른 면적 컬럼 찾기
            area_columns = [col for col in final_df.columns if 'area' in col.lower() or '면적' in col]
            if area_columns:
                final_df['excluUseAr'] = final_df[area_columns[0]]
        
        # 직거래 필터링 (매매의 경우)
        if deal_type == '매매' and 'dealingGbn' in final_df.columns:
            final_df = final_df[final_df['dealingGbn'] != '직거래']
        
        # 단위면적당 환산금액 계산
        if deal_type == '전월세':
            final_df['단위면적당환산금액'] = (
                final_df['deposit'].astype(str).str.replace(',', '').astype(float) + 
                final_df['monthlyRent'].astype(str).str.replace(',', '').astype(float) * 100
            ) / final_df['excluUseAr'].astype(float)
        else:  # 매매
            # 거래금액 컬럼명 확인 (API 응답에 따라 다를 수 있음)
            price_col = None
            for col in ['dealamount', 'dealAmount', 'price', 'dealAmt']:
                if col in final_df.columns:
                    price_col = col
                    break
            
            if price_col:
                final_df['단위면적당환산금액'] = (
                    final_df[price_col].astype(str).str.replace(',', '').astype(float) / 
                    final_df['excluUseAr'].astype(float)
                )
            else:
                # 거래금액 컬럼이 없는 경우 기본값 설정
                final_df['단위면적당환산금액'] = 0
        
        return final_df
    
    return pd.DataFrame()

# 메인 앱
def main():
    st.title("🏠 부동산 면적별 통계 분석")
    st.markdown("---")
    
    # 법정동코드 로드
    code_df = load_dong_codes()
    
    # 메인페이지 - 검색 조건
    st.header("🔍 검색 조건")
    
    # 첫 번째 행: 시도, 시군구, 동 선택
    col1, col2, col3 = st.columns(3)
    with col1:
        sido_options = sorted(code_df['시도'].unique())
        selected_sido = st.selectbox("시도 선택", ["전체"] + sido_options)
    
    with col2:
        if selected_sido != "전체":
            sigungu_options = get_sigungu_options(code_df, selected_sido)
            selected_sigungu = st.selectbox("시군구 선택", ["전체"] + sigungu_options)
        else:
            selected_sigungu = "전체"
            st.selectbox("시군구 선택", ["시도를 먼저 선택하세요"], disabled=True)
    
    with col3:
        if selected_sido != "전체" and selected_sigungu != "전체":
            dong_options = get_dong_options(code_df, selected_sido, selected_sigungu)
            selected_dong = st.selectbox("동 선택", ["전체"] + dong_options)
        else:
            selected_dong = "전체"
            st.selectbox("동 선택", ["시군구를 먼저 선택하세요"], disabled=True)
    
    # 두 번째 행: 부동산 유형, 거래 유형, 기간 선택
    col4, col5, col6, col7 = st.columns(4)
    with col4:
        property_type = st.selectbox("부동산 유형", ["아파트", "연립/다세대", "단독/다가구", "오피스텔"])
    
    with col5:
        deal_type = st.selectbox("거래 유형", ["매매", "전월세"])
    
    with col6:
        # 시작일 드롭다운 생성 (2020년 1월 ~ 2025년 9월)
        start_date_options = []
        for year in range(2020, 2026):
            for month in range(1, 13):
                if year == 2025 and month > 9:  # 2025년 9월까지만
                    break
                start_date_options.append(f"{year:04d}{month:02d}")
        
        start_date = st.selectbox("시작일", start_date_options, index=len(start_date_options)-13)  # 기본값: 2024년 1월
    
    with col7:
        # 종료일 드롭다운 생성 (시작일 이후 ~ 2025년 9월)
        start_year = int(start_date[:4])
        start_month = int(start_date[4:])
        
        end_date_options = []
        for year in range(start_year, 2026):
            for month in range(1, 13):
                if year == start_year and month < start_month:
                    continue
                if year == 2025 and month > 9:  # 2025년 9월까지만
                    break
                end_date_options.append(f"{year:04d}{month:02d}")
        
        # 기본값: 시작일로부터 12개월 후 또는 2025년 9월 중 작은 값
        default_end_year = min(start_year + 1, 2025)
        default_end_month = min(start_month, 9) if default_end_year == 2025 else start_month
        default_end = f"{default_end_year:04d}{default_end_month:02d}"
        
        try:
            default_index = end_date_options.index(default_end)
        except ValueError:
            default_index = len(end_date_options) - 1
        
        end_date = st.selectbox("종료일", end_date_options, index=default_index)
    
    # 예상 로딩 시간 정보
    st.info("⏱️ **예상 로딩 시간**: 24개월치 데이터 조회 시 최대 10초")
    
    # 분석 버튼
    if st.button("📊 분석 시작", type="primary"):
        if selected_sido == "전체":
            st.error("시도를 선택해주세요.")
        elif selected_sigungu == "전체":
            st.error("시군구를 선택해주세요.")
        elif selected_dong == "전체":
            st.error("동을 선택해주세요.")
        else:
            # 선택된 동의 법정동코드 찾기
            dong_code = code_df[
                (code_df['시도'] == selected_sido) & 
                (code_df['시군구'] == selected_sigungu) & 
                (code_df['동'] == selected_dong)
            ]['code'].iloc[0][:5]
            
            # 진행 상황 표시
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            # 데이터 수집
            status_text.text("데이터 수집 중...")
            data = fetch_real_estate_data(property_type, deal_type, dong_code, start_date, end_date)
            
            if not data.empty:
                progress_bar.progress(100)
                status_text.text("분석 완료!")
                
                # 면적별 통계 계산
                area_stats_df = calculate_area_statistics(data, '단위면적당환산금액', 'excluUseAr')
                
                # 결과 표시
                st.header(f"📊 {selected_sido} {selected_sigungu} {selected_dong} 면적별 통계 분석")
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("부동산 유형", property_type)
                with col2:
                    st.metric("거래 유형", deal_type)
                with col3:
                    st.metric("총 데이터 수", f"{len(data):,}개")
                
                # 면적별 통계 테이블
                if property_type == '단독/다가구':
                    st.subheader("면적별 단위면적당 환산금액 통계 (단위면적: 연면적)")
                else:
                    st.subheader("면적별 단위면적당 환산금액 통계 (단위면적: 전용면적)")
                
                # 데이터 포맷팅
                display_df = area_stats_df.copy()
                for col in ['최저값', '최빈값', '중앙값', '평균값']:
                    display_df[col] = display_df[col].apply(lambda x: f"{x:,.0f}원/㎡" if x > 0 else "데이터없음")
                display_df['데이터수'] = display_df['데이터수'].apply(lambda x: f"{x:,}개")
                
                st.dataframe(display_df, use_container_width=True)
                
                # 차트
                st.subheader("면적별 데이터 분포")
                chart_data = area_stats_df[area_stats_df['데이터수'] > 0].copy()
                if not chart_data.empty:
                    # 면적구분 순서 정의 (작은 면적부터)
                    area_order = ["60㎡이하", "60㎡초과~85㎡이하", "85㎡초과~102㎡이하", "102㎡초과~135㎡이하", "135㎡초과", "데이터오류"]
                    
                    # 면적구분을 카테고리 타입으로 변환하여 정렬
                    chart_data['면적구분'] = pd.Categorical(chart_data['면적구분'], categories=area_order, ordered=True)
                    chart_data = chart_data.sort_values('면적구분')
                    
                    # 비율 계산
                    total_count = chart_data['데이터수'].sum()
                    chart_data['비율(%)'] = (chart_data['데이터수'] / total_count * 100).round(1)
                    
                    # 차트 표시 (비율과 함께)
                    import plotly.express as px
                    import plotly.graph_objects as go
                    
                    # Plotly 막대 차트 생성
                    fig = px.bar(
                        chart_data, 
                        x='면적구분', 
                        y='비율(%)',
                        title='면적별 데이터 분포',
                        text='비율(%)'
                    )
                    
                    # 막대 위에 비율 텍스트 표시
                    fig.update_traces(texttemplate='%{text:.1f}%', textposition='outside')
                    
                    # 레이아웃 설정
                    fig.update_layout(
                        xaxis_title="면적구분",
                        yaxis_title="비율 (%)",
                        showlegend=False,
                        height=400
                    )
                    
                    st.plotly_chart(fig, use_container_width=True)
                
                # 원본 데이터 표시 (모든 데이터)
                st.subheader(f"📋 원본 데이터 (총 {len(data)}건)")
                
                # 실제 데이터에서 사용 가능한 컬럼만 표시
                if deal_type == '매매':
                    # 매매의 경우 가능한 모든 컬럼을 시도
                    possible_columns = [
                        'umdCd', 'landCd', 'bonbun', 'bubun', 'roadNm', 
                        'roadNmBonbun', 'roadNmBubun', 'umdNm', 'aptNm', 'offiNm', 'mhouseNm', 'houseType', 'jibun', 
                        'excluUseAr', 'totalFloorAr', 'dealYear', 'dealMonth', 'floor',
                        'buildYear', 'cdealType', 'cdealDay', 'dealingGbn', 'rgstDate',
                        'aptDong', 'slerGbn', 'buyerGbn', 'landLeaseholdGbn',
                        'dealamount', 'dealAmount', 'price', 'dealAmt'  # 거래금액 관련 컬럼들
                    ]
                else:  # 전월세
                    possible_columns = [
                        'umdNm', 'aptNm', 'offiNm', 'mhouseNm', 'houseType', 'jibun', 
                        'excluUseAr', 'totalFloorAr', 'dealYear', 'dealMonth', 'floor', 'buildYear', 
                        'deposit', 'monthlyRent', 'contractTerm', 'contractType', 'con_start', 'con_end',
                        'sggCd', 'sggNm'
                    ]
                
                # 실제 존재하는 컬럼만 선택
                available_columns = [col for col in possible_columns if col in data.columns]
                all_data = data[available_columns].copy()
                
                # 데이터 포맷팅
                def safe_format_number(x, suffix=""):
                    """안전하게 숫자를 포맷팅하는 함수"""
                    if pd.isna(x):
                        return ""
                    try:
                        # 쉼표 제거 후 숫자 변환
                        clean_x = str(x).replace(',', '')
                        if clean_x.replace('.', '').isdigit():
                            return f"{float(clean_x):,.0f}{suffix}"
                        else:
                            return f"{x}{suffix}"
                    except:
                        return f"{x}{suffix}"
                
                # 모든 데이터에 포맷팅 적용
                if deal_type == '전월세':
                    if 'deposit' in all_data.columns:
                        all_data['deposit'] = all_data['deposit'].apply(lambda x: safe_format_number(x, "만원"))
                    if 'monthlyRent' in all_data.columns:
                        all_data['monthlyRent'] = all_data['monthlyRent'].apply(lambda x: safe_format_number(x, "만원"))
                else:  # 매매
                    # 거래금액 관련 컬럼 찾기
                    price_columns = ['dealamount', 'dealAmount', 'price', 'dealAmt']
                    for col in price_columns:
                        if col in all_data.columns:
                            all_data[col] = all_data[col].apply(lambda x: safe_format_number(x, "만원"))
                            break
                
                if 'excluUseAr' in all_data.columns:
                    all_data['excluUseAr'] = all_data['excluUseAr'].apply(lambda x: safe_format_number(x, "㎡").replace(',', ''))
                elif 'totalFloorAr' in all_data.columns:
                    all_data['totalFloorAr'] = all_data['totalFloorAr'].apply(lambda x: safe_format_number(x, "㎡").replace(',', ''))
                
                if '단위면적당환산금액' in all_data.columns:
                    all_data['단위면적당환산금액'] = all_data['단위면적당환산금액'].apply(lambda x: safe_format_number(x, "원/㎡"))
                
                # 컬럼명 한글화
                column_mapping = {
                    'umdNm': '동명',
                    'aptNm': '아파트명',
                    'offiNm': '오피스텔명',
                    'mhouseNm': '연립/다세대명',
                    'houseType': '주택유형',
                    'dealYear': '거래년도',
                    'dealMonth': '거래월',
                    'excluUseAr': '전용면적',
                    'totalFloorAr': '연면적',
                    'deposit': '보증금',
                    'monthlyRent': '월세',
                    'price': '매매가',
                    'dealamount': '거래금액',
                    'contractTerm': '계약기간',
                    'con_start': '계약시작',
                    'con_end': '계약종료',
                    'contractType': '계약유형',
                    'buildYear': '건축년도',
                    'floor': '층수',
                    'jibun': '지번',
                    'sggCd': '시군구코드',
                    'sggNm': '시군구명',
                    'umdCd': '동코드',
                    'landCd': '지번코드',
                    'bonbun': '본번',
                    'bubun': '부번',
                    'roadNm': '도로명',
                    'roadNmBonbun': '도로명본번',
                    'roadNmBubun': '도로명부번',
                    'cdealType': '계약유형',
                    'cdealDay': '계약일',
                    'dealingGbn': '거래구분',
                    'rgstDate': '등록일',
                    'aptDong': '아파트동',
                    'slerGbn': '매도자구분',
                    'buyerGbn': '매수자구분',
                    'landLeaseholdGbn': '지상권구분',
                    '단위면적당환산금액': '단위면적당환산금액'
                }
                
                all_data = all_data.rename(columns=column_mapping)
                
                # 데이터프레임 표시 (스크롤 가능)
                st.dataframe(all_data, use_container_width=True, height=600)
                
            else:
                st.error("데이터를 찾을 수 없습니다.")

if __name__ == "__main__":
    main()
