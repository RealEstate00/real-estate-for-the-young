"""
RTMS 전월세 데이터 정규화 및 JSONL 변환

CSV 파일을 읽어서 스키마에 맞게 정규화한 후 JSONL 형식으로 저장합니다.
"""

import os
import json
import pandas as pd
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class RentDataNormalizer:
    """전월세 데이터 정규화 클래스"""
    
    # CSV 컬럼명 매핑 (실제 CSV 컬럼명 기준)
    COLUMN_MAPPING = {
        '단독다가구': {
            '시군구': 'sigungu',
            '계약면적(㎡)': 'area_m2',  # 단독다가구만 "계약면적"임!
            '전월세구분': 'contract_type',
            '계약년월': 'contract_year_month',
            '보증금(만원)': 'deposit_amount',
            '월세금(만원)': 'monthly_rent',
            '건축년도': 'construction_year',
            '도로명': 'road_name',
            '전용구분': 'use_type',
            '주택유형': 'housing_type',
            '계약기간시작': 'contract_start_ym',
            '계약기간끝': 'contract_end_ym',
        },
        '아파트': {
            '시군구': 'sigungu',
            '단지명': 'building_name',
            '전월세구분': 'contract_type',
            '전용면적(㎡)': 'area_m2',
            '계약년월': 'contract_year_month',
            '보증금(만원)': 'deposit_amount',
            '월세금(만원)': 'monthly_rent',
            '층': 'floor',
            '건축년도': 'construction_year',
            '도로명': 'road_name',
            '계약구분': 'contract_status',
            '주택유형': 'housing_type',
            '계약기간시작': 'contract_start_ym',
            '계약기간끝': 'contract_end_ym',
        },
        '연립다세대': {
            '시군구': 'sigungu',
            '법정동': 'dong_csv',
            '전월세구분': 'contract_type',
            '전용면적(㎡)': 'area_m2',
            '계약년월': 'contract_year_month',
            '보증금(만원)': 'deposit_amount',
            '월세금(만원)': 'monthly_rent',
            '층': 'floor',
            '건축년도': 'construction_year',
            '도로명': 'road_name',
            '계약구분': 'contract_status',
            '주택유형': 'housing_type',
            '계약기간시작': 'contract_start_ym',
            '계약기간끝': 'contract_end_ym',
        },
        '오피스텔': {
            '시군구': 'sigungu',
            '단지명': 'building_name',
            '전월세구분': 'contract_type',
            '전용면적(㎡)': 'area_m2',
            '계약년월': 'contract_year_month',
            '보증금(만원)': 'deposit_amount',
            '월세금(만원)': 'monthly_rent',
            '층': 'floor',
            '건축년도': 'construction_year',
            '도로명': 'road_name',
            '계약구분': 'contract_status',
            '주택유형': 'housing_type',
            '계약기간시작': 'contract_start_ym',
            '계약기간끝': 'contract_end_ym',
        }
    }
    
    def __init__(self, raw_data_dir: Path, normalized_dir: Path, bjdong_code_file: Path):
        """
        Args:
            raw_data_dir: 원본 CSV 파일 디렉토리
            normalized_dir: 정규화된 JSONL 파일 저장 디렉토리
            bjdong_code_file: 법정동 코드 파일 경로
        """
        self.raw_data_dir = raw_data_dir
        self.normalized_dir = normalized_dir
        self.bjdong_code_file = bjdong_code_file
        
        # 출력 디렉토리 생성
        self.normalized_dir.mkdir(parents=True, exist_ok=True)
        
        # 법정동 코드 로드
        self.bjdong_codes = self._load_bjdong_codes()
        
        # 파일 경로
        self.progress_file = self.normalized_dir / 'progress.jsonl'
        self.failed_file = self.normalized_dir / 'failed.jsonl'
        
    def _load_bjdong_codes(self) -> Dict[str, str]:
        """법정동 코드 파일 로드 - 전체 법정동명(시군구+동) → 10자리 코드"""
        logger.info(f"법정동 코드 로드 중: {self.bjdong_code_file}")
        
        bjdong_map = {}
        
        # 여러 인코딩 시도
        encodings = ['utf-8', 'cp949', 'euc-kr']
        
        for encoding in encodings:
            try:
                with open(self.bjdong_code_file, 'r', encoding=encoding) as f:
                    next(f)  # 헤더 스킵
                    for line in f:
                        parts = line.strip().split('\t')
                        if len(parts) >= 3:
                            code, name, status = parts[0], parts[1], parts[2]
                            if status == '존재':
                                # 전체 법정동명 → 10자리 코드로 매핑
                                # 예: "서울특별시 강동구 암사동" → "1174010100"
                                bjdong_map[name] = code
                
                logger.info(f"법정동 코드 {len(bjdong_map):,}개 로드 완료 (인코딩: {encoding})")
                return bjdong_map
                
            except UnicodeDecodeError:
                if encoding == encodings[-1]:  # 마지막 인코딩도 실패
                    logger.error(f"모든 인코딩 시도 실패: {encodings}")
                    raise
                continue
            except Exception as e:
                logger.error(f"법정동 코드 로드 실패: {e}")
                raise
    
    def _get_emd_code(self, sigungu_full: str) -> Optional[str]:
        """전체 법정동명(시군구+동)으로 10자리 법정동 코드 조회"""
        if pd.isna(sigungu_full):
            return None
        
        address = str(sigungu_full).strip()
        
        # 1. 정확히 일치하는 법정동명 찾기
        if address in self.bjdong_codes:
            return self.bjdong_codes[address]
        
        # 2. 부분 매칭 (공백 차이 등)
        for key, code in self.bjdong_codes.items():
            if key == address or key.replace(' ', '') == address.replace(' ', ''):
                return code
        
        # 3. 유사 매칭 (포함 관계)
        for key, code in self.bjdong_codes.items():
            if address in key or key in address:
                return code
        
        return None
    
    def _load_progress(self) -> Dict[str, Dict]:
        """진행 상황 로드"""
        progress = {}
        
        if self.progress_file.exists():
            try:
                with open(self.progress_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        record = json.loads(line.strip())
                        progress[record['file_name']] = record
                logger.info(f"진행 상황 로드: {len(progress)}개 파일")
            except Exception as e:
                logger.warning(f"진행 상황 로드 실패 (새로 시작): {e}")
        
        return progress
    
    def _save_progress(self, file_name: str, building_type: str, processed_rows: int, 
                      total_rows: int, status: str, error: Optional[str] = None):
        """진행 상황 저장"""
        progress_record = {
            'file_name': file_name,
            'building_type': building_type,
            'processed_rows': processed_rows,
            'total_rows': total_rows,
            'status': status,
            'timestamp': datetime.now().isoformat(),
            'error': error
        }
        
        with open(self.progress_file, 'a', encoding='utf-8') as f:
            f.write(json.dumps(progress_record, ensure_ascii=False) + '\n')
    
    def _save_failed_record(self, file_name: str, row_index: int, raw_data: Dict, error: str):
        """실패한 레코드 저장"""
        failed_record = {
            'file_name': file_name,
            'row_index': row_index,
            'raw_data': raw_data,
            'error': error,
            'timestamp': datetime.now().isoformat()
        }
        
        with open(self.failed_file, 'a', encoding='utf-8') as f:
            f.write(json.dumps(failed_record, ensure_ascii=False) + '\n')
    
    def _normalize_record(self, row: pd.Series, building_type: str, row_idx: int, 
                         file_name: str) -> Optional[Dict]:
        """단일 레코드 정규화"""
        try:
            # 기본 필드 추출
            record = {
                'building_type': building_type,
                # 단독다가구는 계약면적, 나머지는 전용면적
                'area_type': '계약면적' if building_type == '단독다가구' else '전용면적',
            }
            
            # 시군구+동 (CSV 원본 그대로 - 법정동 포함)
            sigungu_full = row.get('sigungu')
            if pd.notna(sigungu_full):
                # 원본 그대로 저장: "서울특별시 강동구 암사동"
                record['sigungudong'] = str(sigungu_full).strip()
                
                # 10자리 법정동 코드 조회 (전체 주소로 매칭)
                record['emd_code'] = self._get_emd_code(record['sigungudong'])
            else:
                record['sigungudong'] = None
                record['emd_code'] = None
            
            # 도로명 주소
            road = row.get('road_name')
            record['road_address'] = str(road).strip() if pd.notna(road) else None
            
            # 건물명
            building_name = row.get('building_name')
            record['building_name'] = str(building_name).strip() if pd.notna(building_name) else None
            
            # 면적
            area_m2 = row.get('area_m2')
            if pd.notna(area_m2):
                record['area_m2'] = float(area_m2)
            else:
                raise ValueError("면적 정보 누락")
            
            # 층
            floor = row.get('floor')
            if pd.notna(floor):
                try:
                    record['floor'] = int(floor)
                except:
                    record['floor'] = None
            else:
                record['floor'] = None
            
            # 계약 정보
            contract_type = row.get('contract_type')
            record['contract_type'] = str(contract_type).strip() if pd.notna(contract_type) else None
            
            contract_ym = row.get('contract_year_month')
            if pd.notna(contract_ym):
                try:
                    record['contract_year_month'] = int(contract_ym)
                except:
                    raise ValueError(f"계약년월 형식 오류: {contract_ym}")
            else:
                raise ValueError("계약년월 누락")
            
            # 보증금 / 월세 (쉼표 제거 후 만원 → 원 단위로 변환)
            deposit = row.get('deposit_amount')
            if pd.notna(deposit):
                try:
                    # 문자열이면 쉼표 제거
                    if isinstance(deposit, str):
                        deposit = deposit.replace(',', '').strip()
                    # 만원 단위를 원 단위로 변환 (10000 곱하기)
                    record['deposit_amount'] = int(float(deposit) * 10000)
                except (ValueError, TypeError):
                    record['deposit_amount'] = 0
            else:
                record['deposit_amount'] = 0
            
            monthly_rent = row.get('monthly_rent')
            if pd.notna(monthly_rent):
                try:
                    if isinstance(monthly_rent, str):
                        monthly_rent = monthly_rent.replace(',', '').strip()
                    # 만원 단위를 원 단위로 변환 (10000 곱하기)
                    record['monthly_rent'] = int(float(monthly_rent) * 10000)
                except (ValueError, TypeError):
                    record['monthly_rent'] = 0
            else:
                record['monthly_rent'] = 0
            
            # 건축년도
            const_year = row.get('construction_year')
            if pd.notna(const_year):
                try:
                    record['construction_year'] = int(const_year)
                except:
                    record['construction_year'] = None
            else:
                record['construction_year'] = None
            
            # 계약 상태 (계약구분: 신규/갱신)
            contract_status = row.get('contract_status')
            if pd.notna(contract_status):
                record['contract_status'] = str(contract_status).strip()
            else:
                record['contract_status'] = None
            
            # 계약기간
            start_ym = row.get('contract_start_ym')
            if pd.notna(start_ym) and str(start_ym).strip() != '-':
                try:
                    record['contract_start_ym'] = int(start_ym)
                except:
                    record['contract_start_ym'] = None
            else:
                record['contract_start_ym'] = None
            
            end_ym = row.get('contract_end_ym')
            if pd.notna(end_ym) and str(end_ym).strip() != '-':
                try:
                    record['contract_end_ym'] = int(end_ym)
                except:
                    record['contract_end_ym'] = None
            else:
                record['contract_end_ym'] = None
            
            # 면적구간 계산 (DB 트리거와 동일 로직)
            if record['area_m2'] <= 60:
                record['area_range'] = '~60이하'
            elif record['area_m2'] <= 85:
                record['area_range'] = '60초과~85이하'
            elif record['area_m2'] <= 102:
                record['area_range'] = '85초과~102이하'
            elif record['area_m2'] <= 135:
                record['area_range'] = '102초과~135이하'
            else:
                record['area_range'] = '135초과~'
            
            # 환산가액 계산 (DB 트리거와 동일 로직)
            # 환산가액 = (보증금 + 월세*100) / 면적 (원/㎡)
            if record['area_m2'] > 0:
                record['converted_price'] = round(
                    (record['deposit_amount'] + record['monthly_rent'] * 100.0) / record['area_m2'],
                    2
                )
            else:
                record['converted_price'] = None
            
            return record
            
        except Exception as e:
            error_msg = f"레코드 정규화 실패: {str(e)}"
            logger.debug(f"Row {row_idx}: {error_msg}")
            self._save_failed_record(file_name, row_idx, row.to_dict(), error_msg)
            return None
    
    def normalize_csv_to_jsonl(self, csv_path: Path, building_type: str, 
                               batch_size: int = 10000) -> Tuple[int, int]:
        """
        CSV 파일을 JSONL로 변환
        
        Args:
            csv_path: CSV 파일 경로
            building_type: 주택유형
            batch_size: 배치 크기
            
        Returns:
            (성공 건수, 실패 건수)
        """
        file_name = csv_path.name
        logger.info(f"파일 처리 시작: {file_name}")
        
        # 진행 상황 확인
        progress = self._load_progress()
        if file_name in progress and progress[file_name]['status'] == 'completed':
            logger.info(f"이미 완료된 파일: {file_name}")
            return progress[file_name]['processed_rows'], 0
        
        # 출력 파일
        output_file = self.normalized_dir / f"{building_type}_rent.jsonl"
        
        try:
            # CSV 읽기
            logger.info(f"CSV 파일 읽는 중: {csv_path}")
            df = pd.read_csv(csv_path, encoding='utf-8')
            total_rows = len(df)
            logger.info(f"총 {total_rows:,}개 행 읽음")
            
            # 컬럼명 매핑
            column_map = self.COLUMN_MAPPING[building_type]
            df = df.rename(columns=column_map)
            
            # 배치 처리
            success_count = 0
            fail_count = 0
            
            with open(output_file, 'a', encoding='utf-8') as f:
                for i in range(0, total_rows, batch_size):
                    batch_df = df.iloc[i:i + batch_size]
                    
                    for idx, row in batch_df.iterrows():
                        normalized = self._normalize_record(row, building_type, idx, file_name)
                        
                        if normalized:
                            f.write(json.dumps(normalized, ensure_ascii=False) + '\n')
                            success_count += 1
                        else:
                            fail_count += 1
                    
                    # 진행 상황 로그
                    processed = min(i + batch_size, total_rows)
                    logger.info(f"{file_name}: {processed:,} / {total_rows:,} "
                              f"({processed/total_rows*100:.1f}%) - "
                              f"성공: {success_count:,}, 실패: {fail_count:,}")
                    
                    # 중간 진행 상황 저장
                    self._save_progress(file_name, building_type, processed, 
                                      total_rows, 'processing')
            
            # 완료 상태 저장
            self._save_progress(file_name, building_type, total_rows, 
                              total_rows, 'completed')
            
            logger.info(f"파일 처리 완료: {file_name} - "
                       f"성공: {success_count:,}, 실패: {fail_count:,}")
            
            return success_count, fail_count
            
        except Exception as e:
            error_msg = f"파일 처리 실패: {str(e)}"
            logger.error(error_msg)
            self._save_progress(file_name, building_type, 0, 0, 'failed', error_msg)
            raise
    
    def process_all_files(self, batch_size: int = 10000):
        """모든 전월세 CSV 파일 처리"""
        file_mapping = {
            '단독다가구(전월세)_202009중순~202509중순.csv': '단독다가구',
            '아파트(전월세)_202009중순~202509중순.csv': '아파트',
            '연립다세대(전월세)_202009중순~202509중순.csv': '연립다세대',
            '오피스텔(전월세)_202009중순~202509중순.csv': '오피스텔',
        }
        
        total_success = 0
        total_fail = 0
        
        for filename, building_type in file_mapping.items():
            csv_path = self.raw_data_dir / filename
            
            if not csv_path.exists():
                logger.warning(f"파일을 찾을 수 없습니다: {csv_path}")
                continue
            
            try:
                success, fail = self.normalize_csv_to_jsonl(csv_path, building_type, batch_size)
                total_success += success
                total_fail += fail
            except Exception as e:
                logger.error(f"{filename} 처리 중 오류: {e}")
                continue
        
        logger.info(f"\n{'='*80}")
        logger.info(f"전체 처리 완료")
        logger.info(f"총 성공: {total_success:,}건")
        logger.info(f"총 실패: {total_fail:,}건")
        logger.info(f"{'='*80}\n")


def main():
    """메인 실행 함수"""
    # 경로 설정
    base_dir = Path(__file__).parent.parent.parent.parent.parent
    raw_data_dir = base_dir / 'data' / 'raw' / 'rtms'
    normalized_dir = base_dir / 'data' / 'normalized' / 'rtms'
    bjdong_code_file = raw_data_dir / '법정동코드 전체자료.txt'
    
    # 정규화 실행
    normalizer = RentDataNormalizer(raw_data_dir, normalized_dir, bjdong_code_file)
    normalizer.process_all_files(batch_size=10000)


if __name__ == '__main__':
    main()
