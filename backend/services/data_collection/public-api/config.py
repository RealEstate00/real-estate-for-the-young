"""
API 설정 모듈
- 서울 열린데이터광장 (Path 방식 API)
- 로컬데이터 포털 (Query 방식 API)
"""

# dotenv는 그 .env 파일을 파이썬 코드에서 자동으로 불러와서 환경변수로 등록해주는 라이브러리
from dotenv import load_dotenv  
import os
from datetime import date, timedelta

load_dotenv()  # .env 파일 자동 로딩



# -------------------------------
# 🔑 API Key
# os.getenv(...)는 .env 값이 없으면 fallback을 허용하지만, os.environ[...]은 없으면 바로 에러를 내기 때문에 프로덕션에서는 더 안전
# 테스트 단계에서는 os.getenv()로 두고, 실제 운영 배포 시에는 os.environ[...] 쓰는 것이 좋음
#  -------------------------------
SEOUL_API_KEY = os.getenv("SEOUL_API_KEY")
LOCALDATA_API_KEY = os.getenv("LOCALDATA_API_KEY")

# -------------------------------
# ① 서울 열린데이터광장 (예: 지하철역 정보)
# URL 패턴: http://openapi.seoul.go.kr:8088/{KEY}/{TYPE}/{SERVICE}/{START}/{END}/
# -------------------------------
# SEOUL_SERVICE(여기 변수 명: service_name) 서비스 이름
# 노선별 지하철역 정보 : SearchSTNBySubwayLineInfo
# 서울시 약국 운영 정보 : TbPharmacyOperateInfo
# 서울시 어린이집 정보 : ChildCareInfo
# 서울시 유치원 일반현황 : childSchoolInfo
# 서울시 학교 정보(초중고) : neisSchoolInfo
# 서울시내대학 및 전문대학 DB : SebcCollegeInfoKor
# 서울시 주요 공원현황 : SearchParkInfoService
# --------------------------------
SEOUL_BASE_URL = "http://openapi.seoul.go.kr:8088"
# SEOUL_SERVICE = "SearchSTNBySubwayLineInfo"   # 🔁 사용할 서비스명 (데이터셋마다 다름)
SEOUL_RESPONSE_TYPE = "json"                  # "xml"도 가능
SEOUL_DEFAULT_START = 1
SEOUL_DEFAULT_END = 1000


def build_seoul_url(service_name: str = None, start: int = SEOUL_DEFAULT_START, end: int = SEOUL_DEFAULT_END) -> str:
    """
    서울 열린데이터광장 API 호출 URL 생성
    """
    if SEOUL_API_KEY is None:
        raise ValueError("환경변수 'SEOUL_API_KEY'를 .env 파일에 설정해주세요.")
    
    return f"{SEOUL_BASE_URL}/{SEOUL_API_KEY}/{SEOUL_RESPONSE_TYPE}/{service_name}/{start}/{end}/"



# ========== ② 로컬데이터(변동분 전용) ==========
LOCALDATA_BASE_URL = "http://www.localdata.go.kr/platform/rest"
LOCALDATA_API_TYPE = "TO0"      # 🔁 신청서/문서에 나온 API 유형코드(예: TO0, GR0 등)

def build_localdata_url(api_type: str = LOCALDATA_API_TYPE) -> str:
    """
    로컬데이터 호출 URL의 베이스 (Query 방식)
    """
    if LOCALDATA_API_KEY is None:
        raise ValueError("환겨변수 'LocalData_API_KEY'를 .env 파일에 설정해주세요.")

    return f"{LOCALDATA_BASE_URL}/{api_type}/openDataApi?authKey={LOCALDATA_API_KEY}="

def yyyymmdd(d: date) -> str:
    return d.strftime("%Y%m%d")

def default_delta_range(days: int = 1) -> tuple[str, str]:
    """
    변동분 기본 기간(전일 하루)을 YYYYMMDD 문자열로 반환
    """
    end = date.today() - timedelta(days=1)
    start = end - timedelta(days=days-1)
    return yyyymmdd(start), yyyymmdd(end)

def last_week_range() -> tuple[str, str]:
    """
    오늘 기준 7일 전 ~ 어제까지의 날짜 범위 (YYYYMMDD, YYYYMMDD)
    """
    end = date.today() - timedelta(days=1)       # 어제
    start = date.today() - timedelta(days=7)     # 7일 전
    return start.strftime("%Y%m%d"), end.strftime("%Y%m%d")

# 변동분 파라미터 키 이름은 데이터셋 문서에 맞춰야 함.
# 공식 예제(JSP) 기준 키명: bgnYmd / endYmd / localCode
LOCALDATA_DELTA_START_KEY = "bgnYmd"                   # 🔁 문서에 따라 바뀔 수 있음
LOCALDATA_DELTA_END_KEY = "endYmd"                     # 🔁 문서에 따라 바뀔 수 있음
LOCALDATA_LOCALCODE_KEY = "localCode"                  # 🔁 선택(지자체 코드)

# 페이지네이션 기본
LOCALDATA_DEFAULT_PAGE_SIZE = 100
LOCALDATA_DEFAULT_MAX_PAGES = 5



# ========== CSV 저장 경로 ==========
# 주의: 이 경로들은 db.py에서 절대 경로로 재정의됩니다
CSV_DIR_LOCALDATA = "backend/data/public-api/localdata"   # 로컬데이터 포털 결과 저장 폴더
CSV_DIR_OPENSEOUL = "backend/data/public-api/openseoul"   # 서울 열린데이터 결과 저장 폴더
CSV_ENCODING = "utf-8-sig"             # 엑셀 호환 인코딩


# ========== 네트워크/DB 공통 ==========
TIMEOUT = 15 #각 HTTP 요청에 대한 최대 대기 시간(초). 15초 지나면 실패로 간주하고 예외를 던짐
MAX_RETRY = 3 #요청 실패 시 재시도 횟수
RETRY_BACKOFF = 2.0 #재시도 간 대기시간을 2.0^(n-1)초로 두겠다

PG_DSN = os.getenv("PG_DSN", "postgresql+psycopg2://root:root1234@localhost:5432/postgres")
# 나중에 DB 쓰기를 켤 때 사용할 PostgreSQL 연결 문자열

TARGET_SCHEMA = None 
#나중에 DB 쓰기를 켤 때 사용할 스키마 이름
#None이면 DB의 기본 스키마(일반적으로 public)를 사용
#스키마를 따로 쓰려면 "~~" 같은 문자열로 바꾸면 됨

TARGET_TABLE = "external_api_raw"
#나중에 DB에 적재할 때 사용할 기본 테이블명
#여러 소스를 한 테이블에 모을 계획이면 source 컬럼을 추가해 출처 구분하면 됨