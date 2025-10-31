"""
JSONL 파일을 PostgreSQL DB에 로드하는 모듈
infra_schema.sql의 테이블 구조에 맞춰 데이터를 삽입
"""
import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError
from dotenv import load_dotenv
import os
import pandas as pd
from datetime import datetime

logger = logging.getLogger(__name__)

class JSONLDBLoader:
    """JSONL 파일을 DB에 로드하는 클래스"""
    
    def __init__(self, db_url: str = None):
        load_dotenv()
        
        if db_url:
            self.db_url = db_url
        else:
            # .env 파일에서 DB 연결 정보 가져오기
            db_host = os.getenv('PG_HOST', 'localhost')
            db_port = os.getenv('PG_PORT', '55432')
            db_name = os.getenv('PG_DB', 'rey')
            db_user = os.getenv('PG_USER', 'postgres')
            db_password = os.getenv('PG_PASSWORD', 'post1234')
            
            if db_password:
                self.db_url = f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
            else:
                self.db_url = f"postgresql://{db_user}@{db_host}:{db_port}/{db_name}"
        
        self.engine = create_engine(self.db_url)
        self.connection = self.engine.connect()
        logger.info("JSONL DB Loader 초기화 완료")
    
    def _safe_int(self, value) -> Optional[int]:
        """안전하게 정수로 변환"""
        if pd.isna(value) or value == '' or value is None:
            return None
        try:
            return int(float(str(value)))
        except (ValueError, TypeError):
            return None
    
    def _safe_float(self, value) -> Optional[float]:
        """안전하게 실수로 변환"""
        if pd.isna(value) or value == '' or value is None:
            return None
        try:
            return float(str(value))
        except (ValueError, TypeError):
            return None
    
    def _safe_str(self, value, max_length: int = None) -> Optional[str]:
        """안전하게 문자열로 변환"""
        if pd.isna(value) or value == '' or value is None:
            return None
        str_value = str(value).strip()
        if max_length and len(str_value) > max_length:
            str_value = str_value[:max_length]
        return str_value
    
    def _clean_json_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """JSON 데이터에서 NaN 값을 None으로 변환"""
        if not isinstance(data, dict):
            return data
        
        cleaned = {}
        for key, value in data.items():
            if pd.isna(value):
                cleaned[key] = None
            elif isinstance(value, dict):
                cleaned[key] = self._clean_json_data(value)
            else:
                cleaned[key] = value
        return cleaned
    
    
    def load_jsonl_file(self, jsonl_file_path: Path, batch_size: int = 1000) -> Dict[str, int]:
        """JSONL 파일을 읽어서 적절한 테이블에 삽입"""
        if not jsonl_file_path.exists():
            logger.error(f"JSONL 파일이 존재하지 않습니다: {jsonl_file_path}")
            return {"success": 0, "failed": 0}
        
        results = {"success": 0, "failed": 0}
        batch = []
        
        try:
            with open(jsonl_file_path, 'r', encoding='utf-8') as f:
                for line_num, line in enumerate(f, 1):
                    try:
                        data = json.loads(line.strip())
                        batch.append(data)
                        
                        # 배치 크기 도달 시 처리
                        if len(batch) >= batch_size:
                            batch_results = self._process_batch(batch, jsonl_file_path.name)
                            results["success"] += batch_results["success"]
                            results["failed"] += batch_results["failed"]
                            batch = []
                            
                    except json.JSONDecodeError as e:
                        logger.error(f"JSON 파싱 오류 (라인 {line_num}): {e}")
                        results["failed"] += 1
                    except Exception as e:
                        logger.error(f"라인 {line_num} 처리 오류: {e}")
                        results["failed"] += 1
            
            # 남은 배치 처리
            if batch:
                batch_results = self._process_batch(batch, jsonl_file_path.name)
                results["success"] += batch_results["success"]
                results["failed"] += batch_results["failed"]
                
        except Exception as e:
            logger.error(f"JSONL 파일 읽기 오류: {e}")
            return {"success": 0, "failed": 0}
        
        logger.info(f"JSONL 로딩 완료: {jsonl_file_path.name} - 성공: {results['success']}, 실패: {results['failed']}")
        return results
    
    def _process_batch(self, batch: List[Dict], filename: str) -> Dict[str, int]:
        """배치 데이터를 적절한 테이블에 삽입"""
        results = {"success": 0, "failed": 0}
        
        # 로그 파일은 DB 적재하지 않음
        if "failed_addresses" in filename or "progress" in filename:
            logger.info(f"로그 파일은 DB 적재하지 않음: {filename}")
            return results
        
        # 파일명으로 테이블 타입 결정
        if "transport_points" in filename or "subway" in filename or "bus" in filename:
            # 교통 시설 테이블
            for data in batch:
                try:
                    # 트랜잭션 롤백 후 재시작
                    try:
                        self.connection.rollback()
                    except:
                        pass
                    
                    self._insert_transport_point(data)
                    self.connection.commit()
                    results["success"] += 1
                except Exception as e:
                    logger.error(f"교통 시설 삽입 오류: {e}")
                    logger.error(f"실패한 데이터: {data.get('name', 'Unknown')} (ID: {data.get('id', 'Unknown')})")
                    try:
                        self.connection.rollback()
                    except:
                        pass
                    results["failed"] += 1
        else:
            # 일반 시설 테이블
            for data in batch:
                try:
                    # 트랜잭션 롤백 후 재시작
                    try:
                        self.connection.rollback()
                    except:
                        pass
                    
                    self._insert_facility_info(data)
                    self.connection.commit()
                    results["success"] += 1
                except Exception as e:
                    logger.error(f"시설 정보 삽입 오류: {e}")
                    logger.error(f"실패한 데이터: {data.get('name', 'Unknown')} (ID: {data.get('facility_id', 'Unknown')}, CD: {data.get('cd', 'Unknown')})")
                    try:
                        self.connection.rollback()
                    except:
                        pass
                    results["failed"] += 1
        
        return results
    
    def _insert_facility_info(self, data: Dict[str, Any]):
        """facility_info 테이블에 데이터 삽입"""
        # address_id가 있으면 addresses 테이블에 먼저 삽입
        if data.get('address_id') and data.get('address_nm'):
            self._insert_address(data['address_id'], data['address_nm'])
        
        # facility_info 테이블에 삽입
        insert_sql = text("""
            INSERT INTO infra.facility_info (
                facility_id, cd, name, address_raw, address_id, lat, lon,
                tel, website, operating_hours, is_24h, is_emergency,
                capacity, grade_level, facility_extra, data_source,
                last_updated, created_at
            ) VALUES (
                :facility_id, :cd, :name, :address_raw, :address_id, :lat, :lon,
                :tel, :website, :operating_hours, :is_24h, :is_emergency,
                :capacity, :grade_level, :facility_extra, :data_source,
                :last_updated, :created_at
            )
            ON CONFLICT (facility_id) DO UPDATE SET
                cd = EXCLUDED.cd,
                name = EXCLUDED.name,
                address_raw = EXCLUDED.address_raw,
                address_id = EXCLUDED.address_id,
                lat = EXCLUDED.lat,
                lon = EXCLUDED.lon,
                tel = EXCLUDED.tel,
                website = EXCLUDED.website,
                operating_hours = EXCLUDED.operating_hours,
                is_24h = EXCLUDED.is_24h,
                is_emergency = EXCLUDED.is_emergency,
                capacity = EXCLUDED.capacity,
                grade_level = EXCLUDED.grade_level,
                facility_extra = EXCLUDED.facility_extra,
                data_source = EXCLUDED.data_source,
                last_updated = EXCLUDED.last_updated
        """)
        
        params = {
            'facility_id': self._safe_str(data.get('facility_id'), 50),
            'cd': self._safe_str(data.get('cd'), 20),
            'name': self._safe_str(data.get('name'), 200),
            'address_raw': self._safe_str(data.get('address_raw')),
            'address_id': self._safe_str(data.get('address_id'), 10),
            'lat': self._safe_float(data.get('lat')),
            'lon': self._safe_float(data.get('lon')),
            'tel': self._safe_str(data.get('phone'), 50),
            'website': self._safe_str(data.get('website')),
            'operating_hours': self._safe_str(data.get('operating_hours')),
            'is_24h': data.get('is_24h', False),
            'is_emergency': data.get('is_emergency', False),
            'capacity': self._safe_int(data.get('capacity')),
            'grade_level': self._safe_str(data.get('grade_level')),
            'facility_extra': json.dumps(self._clean_json_data(data.get('facility_extra', {})), ensure_ascii=False),
            'data_source': self._safe_str(data.get('data_source')),
            'last_updated': datetime.now(),
            'created_at': datetime.now()
        }
        
        self.connection.execute(insert_sql, params)
        self.connection.commit()
    
    def _insert_transport_point(self, data: Dict[str, Any]):
        """transport_points 테이블에 데이터 삽입"""
        # address_id가 있으면 addresses 테이블에 먼저 삽입
        if data.get('address_id') and data.get('address_nm'):
            self._insert_address(data['address_id'], data['address_nm'])
        
        # transport_type 결정 (새로운 데이터 형식만 지원)
        transport_type = data.get('transport_type')
        if not transport_type:
            logger.warning(f"transport_type이 없는 데이터 건너뛰기: {data}")
            return
        
        insert_sql = text("""
            INSERT INTO infra.transport_points (
                id, transport_type, name, official_code, line_name, stop_type, is_transfer,
                lat, lon, extra_info, created_at
            ) VALUES (
                :id, :transport_type, :name, :official_code, :line_name, :stop_type, :is_transfer,
                :lat, :lon, :extra_info, :created_at
            )
            ON CONFLICT (id) DO NOTHING
        """)
        
        # 새로운 데이터 형식만 처리
        params = {
            'id': data.get('id'),
            'transport_type': transport_type,
            'name': self._safe_str(data.get('name'), 200),
            'official_code': self._safe_str(data.get('official_code')),
            'line_name': self._safe_str(data.get('line_name')),
            'stop_type': self._safe_str(data.get('stop_type')),
            'is_transfer': data.get('is_transfer', False),
            'lat': self._safe_float(data.get('lat')),
            'lon': self._safe_float(data.get('lon')),
            'extra_info': json.dumps(data.get('extra_info', {}), ensure_ascii=False),
            'created_at': datetime.now()
        }
        
        self.connection.execute(insert_sql, params)
    
    def _insert_address(self, address_id: str, address_nm: str):
        """addresses 테이블에 주소 정보 삽입"""
        if not address_id or not address_nm:
            return
        
        # address_nm을 파싱해서 시도, 시군구, 읍면동 추출
        parts = address_nm.split()
        ctpv_nm = parts[0] if len(parts) > 0 else None
        sgg_nm = parts[1] if len(parts) > 1 else None
        emd_nm = parts[2] if len(parts) > 2 else None
        
        insert_sql = text("""
            INSERT INTO infra.addresses (id, name, ctpv_nm, sgg_nm, emd_nm, created_at)
            VALUES (:id, :name, :ctpv_nm, :sgg_nm, :emd_nm, :created_at)
            ON CONFLICT (id) DO NOTHING
        """)
        
        params = {
            'id': self._safe_str(address_id, 10),
            'name': self._safe_str(address_nm, 100),
            'ctpv_nm': self._safe_str(ctpv_nm, 50),
            'sgg_nm': self._safe_str(sgg_nm, 50),
            'emd_nm': self._safe_str(emd_nm, 50),
            'created_at': datetime.now()
        }
        
        self.connection.execute(insert_sql, params)
        self.connection.commit()
    
    def load_all_jsonl_files(self, jsonl_dir: Path) -> Dict[str, Dict[str, int]]:
        """디렉토리 내 모든 JSONL 파일을 로드"""
        results = {}
        
        if not jsonl_dir.exists():
            logger.error(f"JSONL 디렉토리가 존재하지 않습니다: {jsonl_dir}")
            return results
        
        jsonl_files = list(jsonl_dir.glob("*.jsonl"))
        logger.info(f"발견된 JSONL 파일: {len(jsonl_files)}개")
        
        for jsonl_file in jsonl_files:
            logger.info(f"로딩 시작: {jsonl_file.name}")
            file_results = self.load_jsonl_file(jsonl_file)
            results[jsonl_file.name] = file_results
        
        return results
    
    def clear_all_data(self):
        """모든 infra 데이터 삭제"""
        try:
            logger.info("🗑️ infra 스키마 데이터 삭제 시작...")
            
            # 외래키 참조 때문에 순서대로 삭제 (infra_code는 유지)
            delete_queries = [
                "DELETE FROM infra.housing_facility_distances",
                "DELETE FROM infra.transport_points", 
                "DELETE FROM infra.facility_info",
                "DELETE FROM infra.addresses"
            ]
            
            for query in delete_queries:
                result = self.connection.execute(text(query))
                logger.info(f"삭제 완료: {query} - {result.rowcount}개 행")
                self.connection.commit()
            
            logger.info("✅ 모든 infra 데이터 삭제 완료!")
            
        except Exception as e:
            logger.error(f"❌ 데이터 삭제 중 오류: {e}")
            self.connection.rollback()
            raise
    
    def clear_transport_data(self):
        """교통 데이터만 삭제"""
        try:
            logger.info("🗑️ 교통 데이터 삭제 시작...")
            
            # transport_points 테이블만 삭제
            result = self.connection.execute(text("DELETE FROM infra.transport_points"))
            self.connection.commit()
            
            logger.info(f"✅ 교통 데이터 삭제 완료: {result.rowcount}개 행")
            
        except Exception as e:
            logger.error(f"❌ 교통 데이터 삭제 중 오류: {e}")
            self.connection.rollback()
            raise
    
    def clear_facility_data(self):
        """시설 데이터만 삭제"""
        try:
            logger.info("🗑️ 시설 데이터 삭제 시작...")
            
            # 시설 관련 테이블 삭제
            delete_queries = [
                "DELETE FROM infra.housing_facility_distances",
                "DELETE FROM infra.facility_info"
            ]
            
            for query in delete_queries:
                result = self.connection.execute(text(query))
                logger.info(f"삭제 완료: {query} - {result.rowcount}개 행")
                self.connection.commit()
            
            logger.info("✅ 시설 데이터 삭제 완료!")
            
        except Exception as e:
            logger.error(f"❌ 시설 데이터 삭제 중 오류: {e}")
            self.connection.rollback()
            raise
    
    def load_legal_dong_codes(self, file_path: Path = None):
        """법정동코드 전체자료.txt를 addresses 테이블에 로드"""
        try:
            if file_path is None:
                # 기본 경로 설정
                file_path = Path(__file__).resolve().parents[4] / "backend" / "data" / "rtms" / "법정동코드 전체자료.txt"
            
            if not file_path.exists():
                logger.error(f"법정동코드 파일이 존재하지 않습니다: {file_path}")
                return False
            
            logger.info(f"📂 법정동코드 파일 로딩 시작: {file_path}")
            
            # 기존 addresses 데이터 삭제
            self.connection.execute(text("DELETE FROM infra.addresses"))
            self.connection.commit()
            logger.info("🗑️ 기존 주소 데이터 삭제 완료")
            
            loaded_count = 0
            
            with open(file_path, 'r', encoding='utf-8') as f:
                # 헤더 스킵
                next(f)
                
                for line_num, line in enumerate(f, 2):
                    try:
                        parts = line.strip().split('\t')
                        if len(parts) < 3:
                            continue
                        
                        legal_code = parts[0].strip()
                        legal_name = parts[1].strip()
                        status = parts[2].strip()
                        
                        # 폐지여부가 '존재'인 데이터만 로드
                        if status != '존재':
                            continue
                        
                        # 주소명을 파싱해서 시도, 시군구, 읍면동 추출
                        address_parts = legal_name.split()
                        ctpv_nm = address_parts[0] if len(address_parts) > 0 else None
                        sgg_nm = address_parts[1] if len(address_parts) > 1 else None
                        emd_nm = address_parts[2] if len(address_parts) > 2 else None
                        
                        # addresses 테이블에 삽입
                        insert_sql = text("""
                            INSERT INTO infra.addresses (id, name, ctpv_nm, sgg_nm, emd_nm, created_at)
                            VALUES (:id, :name, :ctpv_nm, :sgg_nm, :emd_nm, :created_at)
                        """)
                        
                        params = {
                            'id': legal_code,
                            'name': legal_name,
                            'ctpv_nm': ctpv_nm,
                            'sgg_nm': sgg_nm,
                            'emd_nm': emd_nm,
                            'created_at': datetime.now()
                        }
                        
                        self.connection.execute(insert_sql, params)
                        loaded_count += 1
                        
                        # 1000개마다 커밋
                        if loaded_count % 1000 == 0:
                            self.connection.commit()
                            logger.info(f"📊 진행 상황: {loaded_count}개 로드 완료")
                        
                    except Exception as e:
                        logger.warning(f"라인 {line_num} 처리 오류: {e}")
                        continue
            
            # 마지막 커밋
            self.connection.commit()
            logger.info(f"✅ 법정동코드 로딩 완료: {loaded_count}개")
            return True
            
        except Exception as e:
            logger.error(f"❌ 법정동코드 로딩 중 오류: {e}")
            self.connection.rollback()
            return False

    def close(self):
        """연결 종료"""
        if self.connection:
            self.connection.close()
        logger.info("JSONL DB Loader 연결 종료")


def main():
    """메인 실행 함수"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="JSONL 파일을 PostgreSQL DB에 로드하는 도구",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
사용 예시:
  python ...경로설정.../infra_jsonl_db_loader.py                    # JSONL 데이터 로드
  python ...경로설정.../infra_jsonl_db_loader.py --clear-all        # 모든 infra 데이터 삭제
  python ...경로설정.../infra_jsonl_db_loader.py --clear-transport  # 교통 데이터만 삭제
  python ...경로설정.../infra_jsonl_db_loader.py --clear-facility   # 시설 데이터만 삭제
  python ...경로설정.../infra_jsonl_db_loader.py --help             # 도움말 표시
        """
    )
    
    parser.add_argument(
        '--clear-all', 
        action='store_true',
        help='모든 infra 데이터 삭제'
    )
    
    parser.add_argument(
        '--clear-transport', 
        action='store_true',
        help='교통 데이터만 삭제'
    )
    
    parser.add_argument(
        '--clear-facility',
        action='store_true',
        help='시설 데이터만 삭제'
    )
    
    parser.add_argument(
        '--load-addresses',
        action='store_true',
        help='법정동코드 전체자료.txt를 addresses 테이블에 로드'
    )
    
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='상세 로그 출력'
    )
    
    args = parser.parse_args()
    
    # 로깅 레벨 설정
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    try:
        loader = JSONLDBLoader()
        
        # 명령 실행
        if args.clear_all:
            print("🗑️ 모든 infra 데이터 삭제 중...")
            loader.clear_all_data()
            print("✅ 모든 infra 데이터 삭제 완료!")
            
        elif args.clear_transport:
            print("🗑️ 교통 데이터 삭제 중...")
            loader.clear_transport_data()
            print("✅ 교통 데이터 삭제 완료!")
            
        elif args.clear_facility:
            print("🗑️ 시설 데이터 삭제 중...")
            loader.clear_facility_data()
            print("✅ 시설 데이터 삭제 완료!")
            
        elif args.load_addresses:
            print("📂 법정동코드 데이터 로딩 중...")
            success = loader.load_legal_dong_codes()
            if success:
                print("✅ 법정동코드 데이터 로딩 완료!")
            else:
                print("❌ 법정동코드 데이터 로딩 실패!")
                return 1
            
        else:
            # 기본 동작: 기존 데이터 삭제 후 법정동코드 + JSONL 데이터 로드
            print("🗑️ 기존 인프라 데이터 삭제 중...")
            loader.clear_all_data()
            print("✅ 기존 데이터 삭제 완료!")
            
            print("📂 법정동코드 데이터 로딩 중...")
            success = loader.load_legal_dong_codes()
            if success:
                print("✅ 법정동코드 데이터 로딩 완료!")
            else:
                print("❌ 법정동코드 데이터 로딩 실패!")
                return 1
            
            print("📂 JSONL 데이터 로딩 시작...")
            jsonl_dir = Path(__file__).resolve().parents[4] / "backend" / "data" / "normalized" / "infra"
            results = loader.load_all_jsonl_files(jsonl_dir)
            
            print("\n=== JSONL 로딩 결과 ===")
            total_success = 0
            total_failed = 0
            
            for filename, result in results.items():
                success = result.get('success', 0)
                failed = result.get('failed', 0)
                total_success += success
                total_failed += failed
                status = "✅" if failed == 0 else "⚠️" if success > 0 else "❌"
                print(f"{status} {filename}: 성공 {success}개, 실패 {failed}개")
            
            print(f"\n📊 전체 결과: 성공 {total_success}개, 실패 {total_failed}개")
            
            if total_failed > 0:
                print(f"\n💡 실패한 데이터를 확인하려면 --verbose 옵션을 사용하세요.")
        
    except Exception as e:
        logger.error(f"작업 중 오류: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
    finally:
        if 'loader' in locals():
            loader.close()


if __name__ == "__main__":
    main()
