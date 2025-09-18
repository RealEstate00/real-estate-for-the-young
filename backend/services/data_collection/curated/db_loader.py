#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
정규화된 데이터를 DB에 저장하는 로더
"""

import pandas as pd
import logging
from pathlib import Path
from typing import Dict, List, Any
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError

logger = logging.getLogger(__name__)

class NormalizedDataLoader:
    """정규화된 데이터를 DB에 저장하는 클래스"""
    
    def __init__(self, db_url: str):
        self.engine = create_engine(db_url)
        self.connection = None
    
    def __enter__(self):
        self.connection = self.engine.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.connection:
            self.connection.close()
    
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
                
                # 5. 유닛 특징 데이터 저장
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
            # UPSERT 쿼리
            query = """
            INSERT INTO platforms (id, code, name, base_url, is_active, created_at, updated_at)
            VALUES (:id, :code, :name, :base_url, :is_active, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            ON CONFLICT (code) DO UPDATE SET
                name = EXCLUDED.name,
                base_url = EXCLUDED.base_url,
                is_active = EXCLUDED.is_active,
                updated_at = CURRENT_TIMESTAMP
            """
            self.connection.execute(text(query), platform)
    
    def _load_addresses(self, addresses: List[Dict]):
        """주소 데이터 저장"""
        if not addresses:
            return
            
        logger.info(f"주소 데이터 저장: {len(addresses)}개")
        
        for address in addresses:
            query = """
            INSERT INTO addresses (id, address_raw, address_norm, si_do, si_gun_gu, road_name, zipcode, lat, lon, created_at)
            VALUES (:id, :address_raw, :address_norm, :si_do, :si_gun_gu, :road_name, :zipcode, :lat, :lon, CURRENT_TIMESTAMP)
            ON CONFLICT (id) DO NOTHING
            """
            self.connection.execute(text(query), address)
    
    def _load_notices(self, notices: List[Dict]):
        """공고 데이터 저장"""
        if not notices:
            return
            
        logger.info(f"공고 데이터 저장: {len(notices)}개")
        
        for notice in notices:
            query = """
            INSERT INTO notices (
                id, platform_id, source, source_key, title, detail_url, list_url, status,
                posted_at, last_modified, apply_start_at, apply_end_at, address_raw, address_id,
                deposit_min, deposit_max, rent_min, rent_max, area_min_m2, area_max_m2,
                floor_min, floor_max, description_raw, notice_extra, has_images, has_floorplan,
                has_documents, created_at, updated_at
            ) VALUES (
                :id, :platform_id, :source, :source_key, :title, :detail_url, :list_url, :status,
                :posted_at, :last_modified, :apply_start_at, :apply_end_at, :address_raw, :address_id,
                :deposit_min, :deposit_max, :rent_min, :rent_max, :area_min_m2, :area_max_m2,
                :floor_min, :floor_max, :description_raw, :notice_extra, :has_images, :has_floorplan,
                :has_documents, :created_at, :updated_at
            ) ON CONFLICT (source, source_key) DO UPDATE SET
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
                updated_at = EXCLUDED.updated_at
            """
            self.connection.execute(text(query), notice)
    
    def _load_units(self, units: List[Dict]):
        """유닛 데이터 저장"""
        if not units:
            return
            
        logger.info(f"유닛 데이터 저장: {len(units)}개")
        
        for unit in units:
            query = """
            INSERT INTO units (
                id, notice_id, unit_code, unit_type, tenure, deposit, rent, maintenance_fee,
                area_m2, room_count, bathroom_count, floor, direction, occupancy_available_at,
                unit_extra, created_at, updated_at
            ) VALUES (
                :id, :notice_id, :unit_code, :unit_type, :tenure, :deposit, :rent, :maintenance_fee,
                :area_m2, :room_count, :bathroom_count, :floor, :direction, :occupancy_available_at,
                :unit_extra, :created_at, :updated_at
            ) ON CONFLICT (id) DO UPDATE SET
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
                updated_at = EXCLUDED.updated_at
            """
            self.connection.execute(text(query), unit)
    
    def _load_unit_features(self, unit_features: List[Dict]):
        """유닛 특징 데이터 저장"""
        if not unit_features:
            return
            
        logger.info(f"유닛 특징 데이터 저장: {len(unit_features)}개")
        
        for feature in unit_features:
            query = """
            INSERT INTO unit_features (unit_id, feature, value)
            VALUES (:unit_id, :feature, :value)
            ON CONFLICT (unit_id, feature) DO UPDATE SET
                value = EXCLUDED.value
            """
            self.connection.execute(text(query), feature)
    
    def _load_notice_tags(self, notice_tags: List[Dict]):
        """공고 태그 데이터 저장"""
        if not notice_tags:
            return
            
        logger.info(f"공고 태그 데이터 저장: {len(notice_tags)}개")
        
        for tag in notice_tags:
            query = """
            INSERT INTO notice_tags (notice_id, tag)
            VALUES (:notice_id, :tag)
            ON CONFLICT (notice_id, tag) DO NOTHING
            """
            self.connection.execute(text(query), tag)
