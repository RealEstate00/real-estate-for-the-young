#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
서울 열린데이터광장 API 정규화된 데이터를 DB에 적재
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError

logger = logging.getLogger(__name__)

class SeoulDataLoader:
    """서울 API 정규화된 데이터를 DB에 저장하는 클래스"""
    
    def __init__(self, db_url: str):
        self.engine = create_engine(db_url)
        self.connection = None
    
    def __enter__(self):
        self.connection = self.engine.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.connection:
            self.connection.close()
    
    def load_from_directory(self, normalized_dir: Path) -> bool:
        """정규화된 데이터 디렉토리에서 파일들을 읽어서 DB에 저장"""
        try:
            logger.info(f"서울 API 정규화된 데이터 디렉토리 스캔: {normalized_dir}")
            
            if not normalized_dir.exists():
                logger.error(f"디렉토리가 존재하지 않습니다: {normalized_dir}")
                return False
            
            # JSON 파일들 처리
            json_files = list(normalized_dir.glob("*.json"))
            logger.info(f"JSON 파일 {len(json_files)}개 발견")
            
            for json_file in json_files:
                service_name = json_file.stem
                logger.info(f"서비스 처리: {service_name}")
                
                with open(json_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                logger.info(f"  - {service_name}: {len(data)}개 레코드 로드")
                
                # DB에 저장
                success = self._load_service_data(service_name, data)
                if not success:
                    logger.error(f"서비스 {service_name} 데이터 저장 실패")
                    return False
            
            logger.info("모든 서울 API 데이터 저장 완료")
            return True
            
        except Exception as e:
            logger.error(f"디렉토리에서 데이터 로드 실패: {e}")
            return False
    
    def _load_service_data(self, service_name: str, data: List[Dict]) -> bool:
        """개별 서비스 데이터를 DB에 저장"""
        try:
            # 트랜잭션 시작
            trans = self.connection.begin()
            
            try:
                if service_name == "ChildCareInfo":
                    self._load_childcare(data)
                elif service_name == "childSchoolInfo":
                    self._load_school(data, "child_school")
                elif service_name == "neisSchoolInfo":
                    self._load_school(data, "neis_school")
                elif service_name == "SearchSTNBySubwayLineInfo":
                    self._load_subway_station(data)
                elif service_name == "SearchParkInfoService":
                    self._load_park(data)
                elif service_name == "SebcCollegeInfoKor":
                    self._load_school(data, "college")
                elif service_name == "TbPharmacyOperateInfo":
                    self._load_pharmacy(data)
                else:
                    logger.error(f"알 수 없는 서비스: {service_name}")
                    return False
                
                # 트랜잭션 커밋
                trans.commit()
                logger.info(f"{service_name} 데이터 저장 완료")
                return True
                
            except Exception as e:
                trans.rollback()
                logger.error(f"{service_name} 데이터 저장 실패: {e}")
                return False
                
        except Exception as e:
            logger.error(f"DB 연결 실패: {e}")
            return False
    
    def _load_childcare(self, data: List[Dict]):
        """어린이집 데이터 저장"""
        if not data:
            return
        
        logger.info(f"어린이집 데이터 저장: {len(data)}개")
        
        for record in data:
            # 어린이집 테이블에 저장
            query = """
            INSERT INTO infra.childcare (
                source, source_key, name, type, status, address_raw, address_norm,
                zipcode, phone, fax, homepage, room_count, room_size, capacity,
                child_count, lat, lon, si_do, si_gun_gu, created_at
            ) VALUES (
                :source, :source_key, :name, :type, :status, :address_raw, :address_norm,
                :zipcode, :phone, :fax, :homepage, :room_count, :room_size, :capacity,
                :child_count, :lat, :lon, :si_do, :si_gun_gu, :created_at
            ) ON CONFLICT (source, source_key) DO UPDATE SET
                name = EXCLUDED.name,
                type = EXCLUDED.type,
                status = EXCLUDED.status,
                address_raw = EXCLUDED.address_raw,
                address_norm = EXCLUDED.address_norm,
                zipcode = EXCLUDED.zipcode,
                phone = EXCLUDED.phone,
                fax = EXCLUDED.fax,
                homepage = EXCLUDED.homepage,
                room_count = EXCLUDED.room_count,
                room_size = EXCLUDED.room_size,
                capacity = EXCLUDED.capacity,
                child_count = EXCLUDED.child_count,
                lat = EXCLUDED.lat,
                lon = EXCLUDED.lon,
                si_do = EXCLUDED.si_do,
                si_gun_gu = EXCLUDED.si_gun_gu,
                updated_at = CURRENT_TIMESTAMP
            """
            self.connection.execute(text(query), record)
    
    def _load_school(self, data: List[Dict], school_type: str):
        """학교 데이터 저장 (어린이학교, NEIS학교, 대학)"""
        if not data:
            return
        
        logger.info(f"{school_type} 데이터 저장: {len(data)}개")
        
        for record in data:
            # 학교 테이블에 저장
            query = """
            INSERT INTO infra.schools (
                source, source_key, name, type, level, address_raw, address_norm,
                phone, homepage, lat, lon, si_do, si_gun_gu, created_at
            ) VALUES (
                :source, :source_key, :name, :type, :level, :address_raw, :address_norm,
                :phone, :homepage, :lat, :lon, :si_do, :si_gun_gu, :created_at
            ) ON CONFLICT (source, source_key) DO UPDATE SET
                name = EXCLUDED.name,
                type = EXCLUDED.type,
                level = EXCLUDED.level,
                address_raw = EXCLUDED.address_raw,
                address_norm = EXCLUDED.address_norm,
                phone = EXCLUDED.phone,
                homepage = EXCLUDED.homepage,
                lat = EXCLUDED.lat,
                lon = EXCLUDED.lon,
                si_do = EXCLUDED.si_do,
                si_gun_gu = EXCLUDED.si_gun_gu,
                updated_at = CURRENT_TIMESTAMP
            """
            self.connection.execute(text(query), record)
    
    def _load_subway_station(self, data: List[Dict]):
        """지하철역 데이터 저장"""
        if not data:
            return
        
        logger.info(f"지하철역 데이터 저장: {len(data)}개")
        
        for record in data:
            # 지하철역 테이블에 저장
            query = """
            INSERT INTO infra.subway_stations (
                source, source_key, name, name_eng, name_chn, name_jpn,
                line_num, fr_code, si_do, created_at
            ) VALUES (
                :source, :source_key, :name, :name_eng, :name_chn, :name_jpn,
                :line_num, :fr_code, :si_do, :created_at
            ) ON CONFLICT (source, source_key) DO UPDATE SET
                name = EXCLUDED.name,
                name_eng = EXCLUDED.name_eng,
                name_chn = EXCLUDED.name_chn,
                name_jpn = EXCLUDED.name_jpn,
                line_num = EXCLUDED.line_num,
                fr_code = EXCLUDED.fr_code,
                si_do = EXCLUDED.si_do,
                updated_at = CURRENT_TIMESTAMP
            """
            self.connection.execute(text(query), record)
    
    def _load_park(self, data: List[Dict]):
        """공원 데이터 저장"""
        if not data:
            return
        
        logger.info(f"공원 데이터 저장: {len(data)}개")
        
        for record in data:
            # 공원 테이블에 저장
            query = """
            INSERT INTO infra.parks (
                source, source_key, name, description, area, open_date,
                main_equipment, main_plants, guidance, visit_road, use_refer,
                address_raw, address_norm, phone, lat, lon, si_do, si_gun_gu, created_at
            ) VALUES (
                :source, :source_key, :name, :description, :area, :open_date,
                :main_equipment, :main_plants, :guidance, :visit_road, :use_refer,
                :address_raw, :address_norm, :phone, :lat, :lon, :si_do, :si_gun_gu, :created_at
            ) ON CONFLICT (source, source_key) DO UPDATE SET
                name = EXCLUDED.name,
                description = EXCLUDED.description,
                area = EXCLUDED.area,
                open_date = EXCLUDED.open_date,
                main_equipment = EXCLUDED.main_equipment,
                main_plants = EXCLUDED.main_plants,
                guidance = EXCLUDED.guidance,
                visit_road = EXCLUDED.visit_road,
                use_refer = EXCLUDED.use_refer,
                address_raw = EXCLUDED.address_raw,
                address_norm = EXCLUDED.address_norm,
                phone = EXCLUDED.phone,
                lat = EXCLUDED.lat,
                lon = EXCLUDED.lon,
                si_do = EXCLUDED.si_do,
                si_gun_gu = EXCLUDED.si_gun_gu,
                updated_at = CURRENT_TIMESTAMP
            """
            self.connection.execute(text(query), record)
    
    def _load_pharmacy(self, data: List[Dict]):
        """약국 데이터 저장"""
        if not data:
            return
        
        logger.info(f"약국 데이터 저장: {len(data)}개")
        
        for record in data:
            # 약국 테이블에 저장
            query = """
            INSERT INTO infra.pharmacies (
                source, source_key, name, type, address_raw, address_norm,
                phone, lat, lon, si_do, si_gun_gu, created_at
            ) VALUES (
                :source, :source_key, :name, :type, :address_raw, :address_norm,
                :phone, :lat, :lon, :si_do, :si_gun_gu, :created_at
            ) ON CONFLICT (source, source_key) DO UPDATE SET
                name = EXCLUDED.name,
                type = EXCLUDED.type,
                address_raw = EXCLUDED.address_raw,
                address_norm = EXCLUDED.address_norm,
                phone = EXCLUDED.phone,
                lat = EXCLUDED.lat,
                lon = EXCLUDED.lon,
                si_do = EXCLUDED.si_do,
                si_gun_gu = EXCLUDED.si_gun_gu,
                updated_at = CURRENT_TIMESTAMP
            """
            self.connection.execute(text(query), record)


def main():
    """메인 함수"""
    import argparse
    import os
    
    parser = argparse.ArgumentParser(description="서울 API 데이터 DB 적재")
    parser.add_argument("--data-dir", default="backend/data/normalized/seoul", help="정규화된 데이터 디렉토리")
    parser.add_argument("--db-url", help="데이터베이스 URL")
    
    args = parser.parse_args()
    
    # 로깅 설정
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    
    # DB URL 설정
    db_url = args.db_url or os.getenv('DATABASE_URL')
    if not db_url:
        logger.error("DATABASE_URL이 설정되지 않았습니다.")
        return
    
    # 데이터 로드 실행
    data_dir = Path(args.data_dir)
    if not data_dir.exists():
        logger.error(f"데이터 디렉토리가 존재하지 않습니다: {data_dir}")
        return
    
    with SeoulDataLoader(db_url) as loader:
        success = loader.load_from_directory(data_dir)
        
        if success:
            logger.info("서울 API 데이터 적재 완료")
        else:
            logger.error("서울 API 데이터 적재 실패")


if __name__ == "__main__":
    main()



