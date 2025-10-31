# db/db_utils_pg.py
# PostgreSQL SQLAlchemy engine. No emojis in comments.
import os
import json
from pathlib import Path
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from contextlib import contextmanager

ENV_PATH = Path(__file__).resolve().parent / ".env"
if ENV_PATH.exists():
    load_dotenv(ENV_PATH)

def get_engine():
    """PostgreSQL 엔진 생성"""
    host = os.getenv("PG_HOST", "localhost")
    port = int(os.getenv("PG_PORT", "55432"))
    user = os.getenv("PG_USER", "postgres")
    password = os.getenv("PG_PASSWORD", "post1234")
    db = os.getenv("PG_DB", "rey")
    # Optional schema search_path: add options if needed
    url = f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{db}"
    eng = create_engine(url, pool_pre_ping=True, pool_recycle=3600, future=True)
    return eng

def get_session():
    """세션 팩토리 생성"""
    engine = get_engine()
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return SessionLocal

@contextmanager
def get_db_session():
    """데이터베이스 세션 컨텍스트 매니저"""
    session = get_session()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()

def test_connection():
    """데이터베이스 연결 테스트"""
    try:
        engine = get_engine()
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            return True
    except Exception as e:
        print(f"Database connection failed: {e}")
        return False

def prepare_jsonb_data(data_dict):
    """JSONB 필드를 위한 데이터 준비"""
    if isinstance(data_dict, dict):
        return json.dumps(data_dict, ensure_ascii=False)
    return data_dict

def execute_sql_file(sql_file_path):
    """SQL 파일 실행"""
    engine = get_engine()
    with open(sql_file_path, 'r', encoding='utf-8') as f:
        sql_content = f.read()
    
    with engine.begin() as conn:
        conn.execute(text(sql_content))
    print(f"SQL file executed successfully: {sql_file_path}")

def upsert_notice(notice_data):
    """공고 데이터 upsert"""
    UPSERT_SQL = """
    INSERT INTO notices (
        platform_id, source, source_key, title, detail_url, posted_at, 
        apply_start_at, apply_end_at, address_raw, deposit_min, deposit_max,
        rent_min, rent_max, area_min_m2, area_max_m2, floor_min, floor_max,
        description_raw, notice_extra, has_images, has_floorplan, has_documents
    ) VALUES (
        :platform_id, :source, :source_key, :title, :detail_url, :posted_at,
        :apply_start_at, :apply_end_at, :address_raw, :deposit_min, :deposit_max,
        :rent_min, :rent_max, :area_min_m2, :area_max_m2, :floor_min, :floor_max,
        :description_raw, :notice_extra::jsonb, :has_images, :has_floorplan, :has_documents
    )
    ON CONFLICT (source, source_key)
    DO UPDATE SET
        title = EXCLUDED.title,
        detail_url = EXCLUDED.detail_url,
        posted_at = EXCLUDED.posted_at,
        apply_start_at = EXCLUDED.apply_start_at,
        apply_end_at = EXCLUDED.apply_end_at,
        address_raw = EXCLUDED.address_raw,
        deposit_min = EXCLUDED.deposit_min,
        deposit_max = EXCLUDED.deposit_max,
        rent_min = EXCLUDED.rent_min,
        rent_max = EXCLUDED.rent_max,
        area_min_m2 = EXCLUDED.area_min_m2,
        area_max_m2 = EXCLUDED.area_max_m2,
        floor_min = EXCLUDED.floor_min,
        floor_max = EXCLUDED.floor_max,
        description_raw = EXCLUDED.description_raw,
        notice_extra = notices.notice_extra || EXCLUDED.notice_extra,
        has_images = EXCLUDED.has_images,
        has_floorplan = EXCLUDED.has_floorplan,
        has_documents = EXCLUDED.has_documents,
        updated_at = now()
    RETURNING id;
    """
    
    engine = get_engine()
    with engine.begin() as conn:
        result = conn.execute(text(UPSERT_SQL), notice_data).fetchone()
        return result[0] if result else None

def upsert_unit(unit_data):
    """유닛 데이터 upsert"""
    UPSERT_SQL = """
    INSERT INTO units (
        notice_id, unit_code, unit_type, tenure, deposit, rent, maintenance_fee,
        area_m2, room_count, bathroom_count, floor, direction, 
        occupancy_available_at, unit_extra
    ) VALUES (
        :notice_id, :unit_code, :unit_type, :tenure, :deposit, :rent, :maintenance_fee,
        :area_m2, :room_count, :bathroom_count, :floor, :direction,
        :occupancy_available_at, :unit_extra::jsonb
    )
    ON CONFLICT (notice_id, unit_code) 
    DO UPDATE SET
        unit_type = EXCLUDED.unit_type,
        tenure = EXCLUDED.tenure,
        deposit = EXCLUDED.deposit,
        rent = EXCLUDED.rent,
        maintenance_fee = EXCLUDED.maintenance_fee,
        area_m2 = EXCLUDED.area_m2,
        room_count = EXCLUDED.room_count,
        bathroom_count = EXCLUDED.bathroom_count,
        floor = EXCLUDED.floor,
        direction = EXCLUDED.direction,
        occupancy_available_at = EXCLUDED.occupancy_available_at,
        unit_extra = units.unit_extra || EXCLUDED.unit_extra,
        updated_at = now()
    RETURNING id;
    """

    engine = get_engine()
    with engine.begin() as conn:
        result = conn.execute(text(UPSERT_SQL), unit_data).fetchone()
        return result[0] if result else None

def upsert_public_sports_facility(facility_data):
    """공공체육시설 데이터 upsert"""
    UPSERT_SQL = """
    INSERT INTO public_sports_facilities (
        facility_name, facility_type, address, lat, lon, phone, 
        homepage, operating_hours, facility_extra
    ) VALUES (
        :facility_name, :facility_type, :address, :lat, :lon, :phone,
        :homepage, :operating_hours, :facility_extra::jsonb
    )
    ON CONFLICT (facility_name, address)
    DO UPDATE SET
        facility_type = EXCLUDED.facility_type,
        lat = EXCLUDED.lat,
        lon = EXCLUDED.lon,
        phone = EXCLUDED.phone,
        homepage = EXCLUDED.homepage,
        operating_hours = EXCLUDED.operating_hours,
        facility_extra = public_sports_facilities.facility_extra || EXCLUDED.facility_extra,
        updated_at = now()
    RETURNING id;
    """

    engine = get_engine()
    with engine.begin() as conn:
        result = conn.execute(text(UPSERT_SQL), facility_data).fetchone()
        return result[0] if result else None

def upsert_subway_station(station_data):
    """지하철역 데이터 upsert"""
    UPSERT_SQL = """
    INSERT INTO subway_stations (
        station_name, line_name, station_code, address, lat, lon, station_extra
    ) VALUES (
        :station_name, :line_name, :station_code, :address, :lat, :lon, :station_extra::jsonb
    )
    ON CONFLICT (station_name, line_name)
    DO UPDATE SET
        station_code = EXCLUDED.station_code,
        address = EXCLUDED.address,
        lat = EXCLUDED.lat,
        lon = EXCLUDED.lon,
        station_extra = subway_stations.station_extra || EXCLUDED.station_extra,
        updated_at = now()
    RETURNING id;
    """

    engine = get_engine()
    with engine.begin() as conn:
        result = conn.execute(text(UPSERT_SQL), station_data).fetchone()
        return result[0] if result else None

def upsert_bus_stop(stop_data):
    """버스정류소 데이터 upsert"""
    # JSONB 필드 준비
    if 'stop_extra' in stop_data:
        stop_data['stop_extra'] = prepare_jsonb_data(stop_data['stop_extra'])
    
    UPSERT_SQL = """
    INSERT INTO bus_stops (
        stop_name, stop_id, address, lat, lon, stop_extra
    ) VALUES (
        :stop_name, :stop_id, :address, :lat, :lon, :stop_extra
    )
    RETURNING id;
    """

    engine = get_engine()
    with engine.begin() as conn:
        result = conn.execute(text(UPSERT_SQL), stop_data).fetchone()
        return result[0] if result else None

def upsert_convenience_store(store_data):
    """편의점 데이터 upsert"""
    # JSONB 필드 준비
    if 'store_extra' in store_data:
        store_data['store_extra'] = prepare_jsonb_data(store_data['store_extra'])
    
    UPSERT_SQL = """
    INSERT INTO convenience_stores (
        store_name, brand, address, lat, lon, phone, operating_hours, store_extra
    ) VALUES (
        :store_name, :brand, :address, :lat, :lon, :phone, :operating_hours, :store_extra
    )
    RETURNING id;
    """

    engine = get_engine()
    with engine.begin() as conn:
        result = conn.execute(text(UPSERT_SQL), store_data).fetchone()
        return result[0] if result else None

def upsert_hospital(hospital_data):
    """병원 데이터 upsert"""
    # JSONB 필드 준비
    if 'hospital_extra' in hospital_data:
        hospital_data['hospital_extra'] = prepare_jsonb_data(hospital_data['hospital_extra'])
    
    UPSERT_SQL = """
    INSERT INTO hospitals (
        hospital_name, hospital_type, address, lat, lon, phone, 
        homepage, operating_hours, hospital_extra
    ) VALUES (
        :hospital_name, :hospital_type, :address, :lat, :lon, :phone,
        :homepage, :operating_hours, :hospital_extra
    )
    RETURNING id;
    """

    engine = get_engine()
    with engine.begin() as conn:
        result = conn.execute(text(UPSERT_SQL), hospital_data).fetchone()
        return result[0] if result else None

def upsert_school(school_data):
    """학교 데이터 upsert"""
    # JSONB 필드 준비
    if 'school_extra' in school_data:
        school_data['school_extra'] = prepare_jsonb_data(school_data['school_extra'])
    
    UPSERT_SQL = """
    INSERT INTO schools (
        school_name, school_type, address, lat, lon, phone, homepage, school_extra
    ) VALUES (
        :school_name, :school_type, :address, :lat, :lon, :phone, :homepage, :school_extra
    )
    RETURNING id;
    """

    engine = get_engine()
    with engine.begin() as conn:
        result = conn.execute(text(UPSERT_SQL), school_data).fetchone()
        return result[0] if result else None

def log_data_collection(data_source, file_name, record_count, status, error_message=None):
    """데이터 수집 로그 기록"""
    LOG_SQL = """
    INSERT INTO public_data_collection_logs (
        data_source, file_name, record_count, status, error_message
    ) VALUES (
        :data_source, :file_name, :record_count, :status, :error_message
    );
    """

    engine = get_engine()
    with engine.begin() as conn:
        conn.execute(text(LOG_SQL), {
            'data_source': data_source,
            'file_name': file_name,
            'record_count': record_count,
            'status': status,
            'error_message': error_message
        })

def get_platform_id(platform_code):
    """플랫폼 코드로 플랫폼 ID 조회"""
    SELECT_SQL = "SELECT id FROM platforms WHERE code = :platform_code"
    
    engine = get_engine()
    with engine.connect() as conn:
        result = conn.execute(text(SELECT_SQL), {'platform_code': platform_code}).fetchone()
        return result[0] if result else None

def create_platform(platform_code, platform_name, base_url=None):
    """플랫폼 생성"""
    INSERT_SQL = """
    INSERT INTO platforms (code, name, base_url)
    VALUES (:code, :name, :base_url)
    ON CONFLICT (code) DO NOTHING
    RETURNING id;
    """
    
    engine = get_engine()
    with engine.begin() as conn:
        result = conn.execute(text(INSERT_SQL), {
            'code': platform_code,
            'name': platform_name,
            'base_url': base_url
        }).fetchone()
        return result[0] if result else get_platform_id(platform_code)
