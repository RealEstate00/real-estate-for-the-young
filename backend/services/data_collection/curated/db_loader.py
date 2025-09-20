#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
정규화된 데이터를 DB에 저장하는 로더
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError
from psycopg import Connection

logger = logging.getLogger(__name__)

class NormalizedDataLoader:
    """정규화된 데이터를 DB에 저장하는 클래스"""
    
    def __init__(self, db_url: str):
        self.engine = create_engine(db_url)
        self.connection = None
        self.platform_id_map = {}  # source -> platform_id 매핑
        self.address_id_map = {}   # address_id -> db_id 매핑
        self.notice_id_map = {}    # source_key -> notice_id 매핑
        self.units_cache = []      # units 데이터 캐시 (unit_features 매핑용)
    
    def __enter__(self):
        self.connection = self.engine.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.connection:
            self.connection.close()
    
    def load_from_directory(self, normalized_dir: Path) -> bool:
        """
        정규화된 데이터 디렉토리에서 파일들을 읽어서 DB에 저장
        
        Args:
            normalized_dir: 정규화된 데이터가 있는 디렉토리 경로
            
        Returns:
            성공 여부
        """
        try:
            logger.info(f"정규화된 데이터 디렉토리 스캔: {normalized_dir}")
            # 각 날짜별 디렉토리 처리
            for date_dir in normalized_dir.iterdir():
                logger.info(f"날짜 디렉토리 발견: {date_dir.name} (is_dir: {date_dir.is_dir()})")
                if date_dir.is_dir():
                    # 각 플랫폼별로 처리
                    for platform_dir in date_dir.iterdir():
                        logger.info(f"플랫폼 디렉토리 발견: {platform_dir.name} (is_dir: {platform_dir.is_dir()})")
                        if platform_dir.is_dir():
                            logger.info(f"플랫폼 데이터 처리: {platform_dir.name}")
                            
                            # JSON 파일들 읽기
                            data = {}
                            json_files = list(platform_dir.glob("*.json"))
                            logger.info(f"  - JSON 파일 {len(json_files)}개 발견")
                            for json_file in json_files:
                                table_name = json_file.stem
                                with open(json_file, 'r', encoding='utf-8') as f:
                                    data[table_name] = json.load(f)
                                logger.info(f"  - {table_name}: {len(data[table_name])}개 레코드 로드")
                            
                            # DB에 저장
                            success = self.load_normalized_data(data)
                            if not success:
                                logger.error(f"플랫폼 {platform_dir.name} 데이터 저장 실패")
                                return False
                        
            logger.info("모든 정규화된 데이터 저장 완료")
            return True
            
        except Exception as e:
            logger.error(f"디렉토리에서 데이터 로드 실패: {e}")
            return False
    
    def load_normalized_data(self, normalized_data: Dict[str, List[Dict]]) -> bool:
        """
        정규화된 데이터를 DB에 저장
        
        Args:
            normalized_data: 정규화된 테이블 데이터
            
        Returns:
            성공 여부
        """
        try:
            # 트랜잭션 시작
            trans = self.connection.begin()
            
            try:
                # 1. 플랫폼 데이터 저장
                self._load_platforms(normalized_data.get('platforms', []))
                
                # 2. 주소 데이터 저장
                self._load_addresses(normalized_data.get('addresses', []))
                
                # 3. 공고 데이터 저장
                self._load_notices(normalized_data.get('notices', []))
                
                # 4. 유닛 데이터 저장
                self._load_units(normalized_data.get('units', []))
                
                # 5. 유닛 특징 데이터 저장 (units 캐시 사용)
                self._load_unit_features(normalized_data.get('unit_features', []))
                
                # 6. 공고 태그 데이터 저장
                self._load_notice_tags(normalized_data.get('notice_tags', []))
                
                # 트랜잭션 커밋
                trans.commit()
                logger.info("정규화된 데이터 저장 완료")
                return True
                
            except Exception as e:
                trans.rollback()
                logger.error(f"데이터 저장 실패: {e}")
                return False
                
        except Exception as e:
            logger.error(f"DB 연결 실패: {e}")
            return False
    
    def _load_platforms(self, platforms: List[Dict]):
        """플랫폼 데이터 저장"""
        if not platforms:
            return
            
        logger.info(f"플랫폼 데이터 저장: {len(platforms)}개")
        
        for platform in platforms:
            # id 필드 제외하고 저장 (SERIAL로 자동 생성)
            platform_data = {k: v for k, v in platform.items() if k != 'id'}
            
            # 누락된 필드 기본값 설정
            if 'platform_extra' not in platform_data:
                platform_data['platform_extra'] = None
            
            # UPSERT 쿼리 (housing 스키마 사용)
            query = """
            INSERT INTO housing.platforms (code, name, base_url, is_active, platform_extra, created_at, updated_at)
            VALUES (:code, :name, :base_url, :is_active, :platform_extra, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            ON CONFLICT (code) DO UPDATE SET
                name = EXCLUDED.name,
                base_url = EXCLUDED.base_url,
                is_active = EXCLUDED.is_active,
                platform_extra = EXCLUDED.platform_extra,
                updated_at = CURRENT_TIMESTAMP
            RETURNING id
            """
            result = self.connection.execute(text(query), platform_data).fetchone()
            platform['db_id'] = result[0] if result else None
            
            # 매핑 테이블 업데이트
            if 'source' in platform:
                self.platform_id_map[platform['source']] = platform['db_id']
    
    def _load_addresses(self, addresses: List[Dict]):
        """주소 데이터 저장"""
        if not addresses:
            return
            
        logger.info(f"주소 데이터 저장: {len(addresses)}개")
        
        for address in addresses:
            # id 필드 제외하고 저장
            address_data = {k: v for k, v in address.items() if k != 'id'}
            
            # INSERT 쿼리 (housing 스키마 사용)
            query = """
            INSERT INTO housing.addresses (address_raw, ctpv_nm, sgg_nm, emd_cd, emd_nm, road_name_full, jibun_name_full, main_jibun, sub_jibun, building_name, building_main_no, building_sub_no, lat, lon, created_at)
            VALUES (:address_raw, :ctpv_nm, :sgg_nm, :emd_cd, :emd_nm, :road_name_full, :jibun_name_full, :main_jibun, :sub_jibun, :building_name, :building_main_no, :building_sub_no, :lat, :lon, CURRENT_TIMESTAMP)
            RETURNING id
            """
            result = self.connection.execute(text(query), address_data).fetchone()
            address['db_id'] = result[0] if result else None
            
            # 매핑 테이블 업데이트
            if 'id' in address:
                self.address_id_map[address['id']] = address['db_id']
    
    def _load_notices(self, notices: List[Dict]):
        """공고 데이터 저장"""
        if not notices:
            return
            
        logger.info(f"공고 데이터 저장: {len(notices)}개")
        
        for notice in notices:
            # platform_id 매핑
            platform_id = None
            if 'source' in notice and notice['source'] in self.platform_id_map:
                platform_id = self.platform_id_map[notice['source']]
            
            # address_id 매핑
            address_id = None
            if 'address_id' in notice and notice['address_id'] in self.address_id_map:
                address_id = self.address_id_map[notice['address_id']]
            
            # 공고 데이터 준비
            notice_data = {
                'platform_id': platform_id,
                'source': notice.get('source'),
                'source_key': notice.get('source_key'),
                'title': notice.get('title'),
                'detail_url': notice.get('detail_url'),
                'list_url': notice.get('list_url'),
                'status': notice.get('status'),
                'posted_at': notice.get('posted_at'),
                'last_modified': notice.get('last_modified'),
                'apply_start_at': notice.get('apply_start_at'),
                'apply_end_at': notice.get('apply_end_at'),
                'address_raw': notice.get('address_raw'),
                'address_id': address_id,
                'deposit_min': notice.get('deposit_min'),
                'deposit_max': notice.get('deposit_max'),
                'rent_min': notice.get('rent_min'),
                'rent_max': notice.get('rent_max'),
                'area_min_m2': notice.get('area_min_m2'),
                'area_max_m2': notice.get('area_max_m2'),
                'floor_min': notice.get('floor_min'),
                'floor_max': notice.get('floor_max'),
                'description_raw': notice.get('description_raw'),
                'notice_extra': json.dumps(notice.get('notice_extra', {})),
                'has_images': notice.get('has_images', False),
                'has_floorplan': notice.get('has_floorplan', False),
                'has_documents': notice.get('has_documents', False)
            }
            
            # UPSERT 쿼리 (housing 스키마 사용)
            query = """
            INSERT INTO housing.notices (
                platform_id, source, source_key, title, detail_url, list_url, status,
                posted_at, last_modified, apply_start_at, apply_end_at, address_raw, address_id,
                deposit_min, deposit_max, rent_min, rent_max, area_min_m2, area_max_m2,
                floor_min, floor_max, description_raw, notice_extra, has_images, has_floorplan,
                has_documents, created_at, updated_at
            ) VALUES (
                :platform_id, :source, :source_key, :title, :detail_url, :list_url, :status,
                :posted_at, :last_modified, :apply_start_at, :apply_end_at, :address_raw, :address_id,
                :deposit_min, :deposit_max, :rent_min, :rent_max, :area_min_m2, :area_max_m2,
                :floor_min, :floor_max, :description_raw, :notice_extra, :has_images, :has_floorplan,
                :has_documents, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
            ) ON CONFLICT (source, source_key) DO UPDATE SET
                platform_id = EXCLUDED.platform_id,
                title = EXCLUDED.title,
                detail_url = EXCLUDED.detail_url,
                status = EXCLUDED.status,
                posted_at = EXCLUDED.posted_at,
                last_modified = EXCLUDED.last_modified,
                address_raw = EXCLUDED.address_raw,
                address_id = EXCLUDED.address_id,
                deposit_min = EXCLUDED.deposit_min,
                deposit_max = EXCLUDED.deposit_max,
                rent_min = EXCLUDED.rent_min,
                rent_max = EXCLUDED.rent_max,
                area_min_m2 = EXCLUDED.area_min_m2,
                area_max_m2 = EXCLUDED.area_max_m2,
                floor_min = EXCLUDED.floor_min,
                floor_max = EXCLUDED.floor_max,
                description_raw = EXCLUDED.description_raw,
                notice_extra = EXCLUDED.notice_extra,
                has_images = EXCLUDED.has_images,
                has_floorplan = EXCLUDED.has_floorplan,
                has_documents = EXCLUDED.has_documents,
                updated_at = CURRENT_TIMESTAMP
            RETURNING id
            """
            result = self.connection.execute(text(query), notice_data).fetchone()
            notice['db_id'] = result[0] if result else None
            
            # 매핑 테이블 업데이트
            if 'source_key' in notice:
                self.notice_id_map[notice['source_key']] = notice['db_id']
    
    def _load_units(self, units: List[Dict]):
        """유닛 데이터 저장"""
        if not units:
            return
            
        logger.info(f"유닛 데이터 저장: {len(units)}개")
        
        for unit in units:
            # notice_id 매핑
            notice_id = None
            if 'notice_id' in unit and unit['notice_id'] in self.notice_id_map:
                notice_id = self.notice_id_map[unit['notice_id']]
            
            # 유닛 데이터 준비
            unit_data = {
                'notice_id': notice_id,
                'unit_code': unit.get('unit_code'),
                'unit_type': unit.get('unit_type'),
                'tenure': unit.get('tenure'),
                'deposit': unit.get('deposit'),
                'rent': unit.get('rent'),
                'maintenance_fee': unit.get('maintenance_fee'),
                'area_m2': unit.get('area_m2'),
                'room_count': unit.get('room_count'),
                'bathroom_count': unit.get('bathroom_count'),
                'floor': unit.get('floor'),
                'direction': unit.get('direction'),
                'occupancy_available_at': unit.get('occupancy_available_at'),
                'unit_extra': json.dumps(unit.get('unit_extra', {}))
            }
            
            # UPSERT 쿼리 (housing 스키마 사용)
            query = """
            INSERT INTO housing.units (
                notice_id, unit_code, unit_type, tenure, deposit, rent, maintenance_fee,
                area_m2, room_count, bathroom_count, floor, direction, occupancy_available_at,
                unit_extra, created_at, updated_at
            ) VALUES (
                :notice_id, :unit_code, :unit_type, :tenure, :deposit, :rent, :maintenance_fee,
                :area_m2, :room_count, :bathroom_count, :floor, :direction, :occupancy_available_at,
                :unit_extra, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
            ) ON CONFLICT (id) DO UPDATE SET
                notice_id = EXCLUDED.notice_id,
                unit_code = EXCLUDED.unit_code,
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
                unit_extra = EXCLUDED.unit_extra,
                updated_at = CURRENT_TIMESTAMP
            RETURNING id
            """
            result = self.connection.execute(text(query), unit_data).fetchone()
            unit['db_id'] = result[0] if result else None
            
            # units 캐시에 추가 (unit_features 매핑용)
            self.units_cache.append(unit)
    
    def _load_unit_features(self, unit_features: List[Dict]):
        """유닛 특징 데이터 저장"""
        if not unit_features:
            return
            
        logger.info(f"유닛 특징 데이터 저장: {len(unit_features)}개")
        
        for feature in unit_features:
            # unit_id 매핑 (unit의 db_id 사용)
            unit_id = None
            if 'unit_id' in feature:
                # unit_features의 unit_id는 units 테이블의 원본 id
                # 이를 units의 db_id로 매핑해야 함
                for unit in self.units_cache:
                    if unit.get('id') == feature['unit_id']:
                        unit_id = unit.get('db_id')
                        break
            
            if unit_id is None:
                continue
                
            feature_data = {
                'unit_id': unit_id,
                'feature': feature.get('feature'),
                'value': feature.get('value')
            }
            
            # UPSERT 쿼리 (housing 스키마 사용)
            query = """
            INSERT INTO housing.unit_features (unit_id, feature, value)
            VALUES (:unit_id, :feature, :value)
            ON CONFLICT (unit_id, feature, value) DO NOTHING
            """
            self.connection.execute(text(query), feature_data)
    
    def _load_notice_tags(self, notice_tags: List[Dict]):
        """공고 태그 데이터 저장"""
        if not notice_tags:
            return
            
        logger.info(f"공고 태그 데이터 저장: {len(notice_tags)}개")
        
        for tag in notice_tags:
            # notice_id 매핑
            notice_id = None
            if 'notice_id' in tag and tag['notice_id'] in self.notice_id_map:
                notice_id = self.notice_id_map[tag['notice_id']]
            
            if notice_id is None:
                continue
                
            tag_data = {
                'notice_id': notice_id,
                'tag': tag.get('tag')
            }
            
            # UPSERT 쿼리 (housing 스키마 사용)
            query = """
            INSERT INTO housing.notice_tags (notice_id, tag)
            VALUES (:notice_id, :tag)
            ON CONFLICT (notice_id, tag) DO NOTHING
            """
            self.connection.execute(text(query), tag_data)