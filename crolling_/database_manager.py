import json
import sqlite3
import pandas as pd
from datetime import datetime
import re

class HousingDatabaseManager:
    """서울시 사회주택 데이터베이스 관리자"""
    
    def __init__(self, db_path="seoul_housing.db"):
        self.db_path = db_path
        self.conn = None
        
    def connect(self):
        """데이터베이스 연결"""
        self.conn = sqlite3.connect(self.db_path)
        self.conn.execute("PRAGMA foreign_keys = ON")  # 외래키 제약조건 활성화
        return self.conn
    
    def close(self):
        """데이터베이스 연결 종료"""
        if self.conn:
            self.conn.close()
    
    def create_tables(self):
        """테이블 생성 (SQLite 버전)"""
        cursor = self.conn.cursor()
        
        # 1. 주택 기본 정보 테이블
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS housing (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                house_name TEXT NOT NULL,
                address TEXT NOT NULL,
                target_residents TEXT,
                housing_type TEXT,
                area_info TEXT,
                total_residents TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # 2. 사업자 정보 테이블
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS business_info (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                housing_id INTEGER NOT NULL,
                company_name TEXT,
                ceo_name TEXT,
                phone TEXT,
                email TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (housing_id) REFERENCES housing(id) ON DELETE CASCADE
            )
        """)
        
        # 3. 평면도 이미지 테이블
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS floor_plan_images (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                housing_id INTEGER NOT NULL,
                image_url TEXT NOT NULL,
                alt_text TEXT,
                image_order INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (housing_id) REFERENCES housing(id) ON DELETE CASCADE
            )
        """)
        
        # 4. 입주현황 테이블
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS occupancy_status (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                housing_id INTEGER NOT NULL,
                room_name TEXT NOT NULL,
                occupancy_type TEXT,
                area TEXT,
                deposit REAL,
                monthly_rent REAL,
                management_fee REAL,
                floor_number INTEGER,
                room_number INTEGER,
                capacity INTEGER,
                available_date DATE,
                is_available BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (housing_id) REFERENCES housing(id) ON DELETE CASCADE
            )
        """)
        
        # 5. 교통 정보 테이블
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS transportation (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                housing_id INTEGER NOT NULL,
                transport_type TEXT NOT NULL CHECK(transport_type IN ('subway', 'bus')),
                line_info TEXT NOT NULL,
                station_name TEXT,
                distance_meters INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (housing_id) REFERENCES housing(id) ON DELETE CASCADE
            )
        """)
        
        # 6. 편의시설 테이블
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS facilities (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                housing_id INTEGER NOT NULL,
                facility_name TEXT NOT NULL,
                facility_type TEXT,
                distance_meters INTEGER,
                description TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (housing_id) REFERENCES housing(id) ON DELETE CASCADE
            )
        """)
        
        # 7. 크롤링 로그 테이블
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS crawling_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                housing_id INTEGER,
                crawl_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                status TEXT NOT NULL CHECK(status IN ('success', 'partial', 'failed')),
                images_collected INTEGER DEFAULT 0,
                rooms_collected INTEGER DEFAULT 0,
                transport_collected INTEGER DEFAULT 0,
                facilities_collected INTEGER DEFAULT 0,
                error_message TEXT,
                FOREIGN KEY (housing_id) REFERENCES housing(id) ON DELETE SET NULL
            )
        """)
        
        self.conn.commit()
        print("데이터베이스 테이블 생성 완료")
    
    def parse_currency(self, currency_str):
        """통화 문자열을 숫자로 변환"""
        if not currency_str or currency_str == "정보 없음":
            return 0
        
        # 숫자와 쉼표만 추출
        numbers = re.findall(r'[\d,]+', str(currency_str))
        if numbers:
            return float(numbers[0].replace(',', ''))
        return 0
    
    def parse_integer(self, int_str):
        """정수 문자열을 숫자로 변환"""
        if not int_str or int_str == "정보 없음":
            return None
        
        numbers = re.findall(r'\d+', str(int_str))
        if numbers:
            return int(numbers[0])
        return None
    
    def insert_housing_data(self, json_file_path):
        """JSON 파일에서 주택 데이터를 데이터베이스에 삽입"""
        cursor = self.conn.cursor()
        
        # JSON 파일 읽기
        with open(json_file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        try:
            # 1. 주택 기본 정보 삽입
            cursor.execute("""
                INSERT INTO housing (house_name, address, target_residents, housing_type, area_info, total_residents)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                data.get("주택명", ""),
                data.get("주소", ""),
                data.get("입주대상", ""),
                data.get("주거형태", ""),
                data.get("면적", ""),
                data.get("총 주거인원", "")
            ))
            
            housing_id = cursor.lastrowid
            print(f"주택 정보 삽입 완료 (ID: {housing_id})")
            
            # 2. 사업자 정보 삽입
            cursor.execute("""
                INSERT INTO business_info (housing_id, company_name, ceo_name, phone, email)
                VALUES (?, ?, ?, ?, ?)
            """, (
                housing_id,
                data.get("상호", ""),
                data.get("대표자", ""),
                data.get("대표전화", ""),
                data.get("이메일", "")
            ))
            
            # 3. 평면도 이미지 삽입
            images = data.get("평면도_이미지", [])
            for i, image in enumerate(images):
                cursor.execute("""
                    INSERT INTO floor_plan_images (housing_id, image_url, alt_text, image_order)
                    VALUES (?, ?, ?, ?)
                """, (
                    housing_id,
                    image.get("url", ""),
                    image.get("alt", ""),
                    i + 1
                ))
            print(f"평면도 이미지 {len(images)}개 삽입 완료")
            
            # 4. 입주현황 삽입
            occupancy_list = data.get("입주현황", [])
            for room in occupancy_list:
                cursor.execute("""
                    INSERT INTO occupancy_status 
                    (housing_id, room_name, occupancy_type, area, deposit, monthly_rent, 
                     management_fee, floor_number, room_number, capacity, is_available)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    housing_id,
                    room.get("방이름", ""),
                    room.get("입주타입", ""),
                    room.get("면적", ""),
                    self.parse_currency(room.get("보증금", "")),
                    self.parse_currency(room.get("월임대료", "")),
                    self.parse_currency(room.get("관리비", "")),
                    self.parse_integer(room.get("층", "")),
                    self.parse_integer(room.get("호", "")),
                    self.parse_integer(room.get("인원", "")),
                    1 if room.get("입주가능", "").strip() != "X" else 0
                ))
            print(f"입주현황 {len(occupancy_list)}개 방 정보 삽입 완료")
            
            # 5. 교통 정보 삽입 (dashline에서 추출된 정보 사용)
            # 지하철 정보
            subway_info = data.get("지하철", "")
            if subway_info and subway_info != "정보 없음":
                # 1호선, 7호선 등 분리
                subway_lines = re.findall(r'\d+호선', subway_info)
                for line in subway_lines:
                    cursor.execute("""
                        INSERT INTO transportation (housing_id, transport_type, line_info, station_name)
                        VALUES (?, ?, ?, ?)
                    """, (housing_id, 'subway', line, '도봉산역'))
            
            # 버스 정보
            bus_info = data.get("버스", "")
            if bus_info and bus_info != "정보 없음":
                cursor.execute("""
                    INSERT INTO transportation (housing_id, transport_type, line_info)
                    VALUES (?, ?, ?)
                """, (housing_id, 'bus', bus_info))
            
            # 6. 편의시설 삽입
            facilities_list = data.get("편의시설", [])
            for facility in facilities_list:
                cursor.execute("""
                    INSERT INTO facilities (housing_id, facility_name)
                    VALUES (?, ?)
                """, (housing_id, facility))
            print(f"편의시설 {len(facilities_list)}개 삽입 완료")
            
            # 7. 크롤링 로그 삽입
            cursor.execute("""
                INSERT INTO crawling_logs 
                (housing_id, status, images_collected, rooms_collected, transport_collected, facilities_collected)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                housing_id,
                'success',
                len(images),
                len(occupancy_list),
                (1 if subway_info != "정보 없음" else 0) + (1 if bus_info != "정보 없음" else 0),
                len(facilities_list)
            ))
            
            self.conn.commit()
            print(f"✅ 모든 데이터 삽입 완료! (주택 ID: {housing_id})")
            return housing_id
            
        except Exception as e:
            self.conn.rollback()
            print(f"❌ 데이터 삽입 중 오류: {e}")
            return None
    
    def export_to_csv(self, output_dir="crolling_/"):
        """데이터베이스 데이터를 CSV로 내보내기"""
        cursor = self.conn.cursor()
        
        # 각 테이블을 CSV로 내보내기
        tables = [
            'housing', 'business_info', 'floor_plan_images', 
            'occupancy_status', 'transportation', 'facilities', 'crawling_logs'
        ]
        
        for table in tables:
            cursor.execute(f"SELECT * FROM {table}")
            data = cursor.fetchall()
            
            # 컬럼명 가져오기
            cursor.execute(f"PRAGMA table_info({table})")
            columns = [col[1] for col in cursor.fetchall()]
            
            # DataFrame 생성 및 CSV 저장
            df = pd.DataFrame(data, columns=columns)
            df.to_csv(f"{output_dir}{table}.csv", index=False, encoding='utf-8-sig')
            print(f"📊 {table}.csv 내보내기 완료 ({len(data)}개 레코드)")
    
    def get_summary(self):
        """데이터베이스 요약 정보"""
        cursor = self.conn.cursor()
        
        summary = {}
        tables = [
            'housing', 'business_info', 'floor_plan_images', 
            'occupancy_status', 'transportation', 'facilities'
        ]
        
        for table in tables:
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            count = cursor.fetchone()[0]
            summary[table] = count
        
        return summary

def main():
    """메인 실행 함수"""
    print("🏠 서울시 사회주택 데이터베이스 관리자 시작")
    
    # 데이터베이스 관리자 초기화
    db_manager = HousingDatabaseManager("crolling_/seoul_housing.db")
    db_manager.connect()
    
    try:
        # 테이블 생성
        db_manager.create_tables()
        
        # JSON 데이터 삽입
        json_file = "crolling_/seoul_housing_complete.json"
        housing_id = db_manager.insert_housing_data(json_file)
        
        if housing_id:
            # 요약 정보 출력
            summary = db_manager.get_summary()
            print("\n📊 데이터베이스 요약:")
            for table, count in summary.items():
                print(f"  - {table}: {count}개")
            
            # CSV 내보내기
            print("\n📁 CSV 파일 내보내기...")
            db_manager.export_to_csv()
            
            print("\n✅ 모든 작업 완료!")
            print(f"📍 데이터베이스 위치: seoul_housing.db")
            print(f"📍 DBeaver에서 SQLite 연결하여 확인 가능")
        
    except Exception as e:
        print(f"❌ 오류 발생: {e}")
    
    finally:
        db_manager.close()

if __name__ == "__main__":
    main()
