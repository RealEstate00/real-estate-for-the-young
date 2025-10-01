"""
RTMS 데이터 정규화 CLI
"""

import logging
from pathlib import Path
from typing import Optional

from backend.services.data_collection.rtms.normalized.rent_normalizer import RentDataNormalizer


class RTMSNormalizedCLI:
    """RTMS 데이터 정규화 CLI"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
    def process_all(self, building_type: Optional[str] = None, verbose: bool = False):
        """모든 RTMS 데이터 정규화 처리"""
        # 로깅 설정
        level = logging.DEBUG if verbose else logging.INFO
        logging.basicConfig(
            level=level,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        
        # 프로젝트 루트 경로 설정 (현재 작업 디렉토리 기준)
        project_root = Path.cwd()
        raw_data_dir = project_root / 'backend' / 'data' / 'raw' / 'rtms'
        normalized_data_dir = project_root / 'backend' / 'data' / 'normalized' / 'rtms'
        bjdong_code_file = raw_data_dir / '법정동코드 전체자료.txt'
        
        self.logger.info("RTMS 데이터 정규화 시작")
        self.logger.info(f"원본 데이터 디렉토리: {raw_data_dir}")
        self.logger.info(f"정규화 데이터 디렉토리: {normalized_data_dir}")
        self.logger.info(f"법정동 코드 파일: {bjdong_code_file}")
        
        # 필수 파일 확인
        if not raw_data_dir.exists():
            raise FileNotFoundError(f"원본 데이터 디렉토리를 찾을 수 없습니다: {raw_data_dir}")
        
        if not bjdong_code_file.exists():
            raise FileNotFoundError(f"법정동 코드 파일을 찾을 수 없습니다: {bjdong_code_file}")
        
        # 출력 디렉토리 생성
        normalized_data_dir.mkdir(parents=True, exist_ok=True)
        
        try:
            # 정규화 실행
            normalizer = RentDataNormalizer(
                raw_data_dir=raw_data_dir,
                normalized_dir=normalized_data_dir,
                bjdong_code_file=bjdong_code_file
            )
            
            # 정규화 실행 (현재는 모든 파일 처리만 지원)
            if building_type:
                self.logger.warning(f"특정 주택유형({building_type}) 선택 기능은 현재 지원되지 않습니다. 모든 주택유형을 처리합니다.")
            
            self.logger.info("=== 모든 주택유형 데이터 정규화 ===")
            normalizer.process_all_files()
            
            self.logger.info("RTMS 데이터 정규화 완료")
            
        except Exception as e:
            self.logger.error(f"RTMS 데이터 정규화 실패: {e}")
            raise
