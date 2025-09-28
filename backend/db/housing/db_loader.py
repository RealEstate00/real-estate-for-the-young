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
        self.building_type_map = {}  # building_type name -> code 매핑
        self.platform_code_map = {}  # platform code -> platform_code 매핑
    
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
            
            # codes.json 먼저 로드
            codes_file = normalized_dir / "codes.json"
            codes_data = []
            if codes_file.exists():
                logger.info("codes.json 파일 로드 중...")
                with open(codes_file, 'r', encoding='utf-8') as f:
                    codes_data = json.load(f)
                logger.info(f"codes.json 로드 완료: {len(codes_data)}개 코드")
            
            # 가장 최근 날짜 디렉토리 찾기
            date_dirs = [d for d in normalized_dir.iterdir() if d.is_dir() and not d.name.endswith('.json')]
            if not date_dirs:
                logger.warning("날짜 디렉토리를 찾을 수 없습니다")
                return False
            
            # 날짜별로 정렬하여 가장 최근 날짜 선택
            latest_date_dir = max(date_dirs, key=lambda x: x.name)
            logger.info(f"가장 최근 날짜 디렉토리 선택: {latest_date_dir.name}")
            
            # 선택된 날짜 디렉토리만 처리
            for platform_dir in latest_date_dir.iterdir():
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
                    
                    # codes.json 데이터 추가
                    if codes_data:
                        data['codes'] = codes_data
                    
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
                # 1. 코드 마스터 데이터 저장 (먼저 로드)
                self._load_code_master(normalized_data.get('codes', []))
                
                # 2. 플랫폼 데이터 저장
                self._load_platforms(normalized_data.get('platforms', []))
                
                # 3. 주소 데이터 저장
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
    
    def _execute_upsert(self, table_name: str, data: Dict, conflict_columns: List[str], update_columns: List[str] = None, return_id: bool = True) -> int:
        """공통 UPSERT 실행 메서드"""
        if update_columns is None:
            update_columns = [col for col in data.keys() if col not in conflict_columns]
        
        # CURRENT_TIMESTAMP 처리
        processed_data = {}
        columns = []
        values = []
        
        for col, val in data.items():
            if val == 'CURRENT_TIMESTAMP':
                columns.append(col)
                values.append('CURRENT_TIMESTAMP')
            else:
                columns.append(col)
                values.append(f":{col}")
                processed_data[col] = val
        
        update_clause = ", ".join([f"{col} = EXCLUDED.{col}" for col in update_columns])
        conflict_clause = ", ".join(conflict_columns)
        
        # RETURNING 절은 id 컬럼이 있는 경우에만 추가
        returning_clause = "RETURNING id" if return_id else ""
        
        query = f"""
        INSERT INTO {table_name} ({', '.join(columns)})
        VALUES ({', '.join(values)})
        ON CONFLICT ({conflict_clause}) DO UPDATE SET
            {update_clause}
        {returning_clause}
        """
        
        if return_id:
            result = self.connection.execute(text(query), processed_data).fetchone()
            return result[0] if result else None
        else:
            self.connection.execute(text(query), processed_data)
            return None

    def _load_code_master(self, codes: List[Dict]):
        """코드 마스터 데이터 저장"""
        if not codes:
            return
            
        logger.info(f"코드 마스터 데이터 저장: {len(codes)}개")
        
        for code in codes:
            code_data = {
                'cd': code.get('cd'),
                'name': code.get('name'),
                'description': code.get('description'),
                'upper_cd': code.get('upper_cd')
            }
            
            self._execute_upsert(
                'housing.code_master', 
                code_data, 
                ['cd'], 
                ['name', 'description', 'upper_cd'],
                return_id=False
            )
            
            # building_type 매핑 설정
            if code.get('upper_cd') == 'building_type':
                # 한국어 이름에서 코드 매핑 (예: "다세대주택" -> "bt_02")
                name = code.get('name', '')
                if '다세대주택' in name:
                    self.building_type_map['다세대주택'] = code.get('cd')
                elif '도시형생활주택' in name:
                    self.building_type_map['도시형생활주택'] = code.get('cd')
                elif '단독주택' in name:
                    self.building_type_map['단독주택'] = code.get('cd')
                elif '연립주택' in name:
                    self.building_type_map['연립주택'] = code.get('cd')
                elif '아파트' in name:
                    self.building_type_map['아파트'] = code.get('cd')
                elif '오피스텔' in name:
                    self.building_type_map['오피스텔'] = code.get('cd')
            
            # platform 매핑 설정
            if code.get('upper_cd') == 'platform':
                # 플랫폼 코드 매핑 (예: "cohouse" -> "platform_cohouse")
                cd = code.get('cd', '')
                if cd.startswith('platform_'):
                    platform_code = cd.replace('platform_', '')
                    self.platform_code_map[platform_code] = cd
    
    def _load_platforms(self, platforms: List[Dict]):
        """플랫폼 데이터 저장"""
        if not platforms:
            return
            
        logger.info(f"플랫폼 데이터 저장: {len(platforms)}개")
        
        for platform in platforms:
            # id 필드 제외하고 저장 (SERIAL로 자동 생성)
            platform_data = {k: v for k, v in platform.items() if k != 'id'}
            
            # base_url을 url로 매핑
            if 'base_url' in platform_data:
                platform_data['url'] = platform_data.pop('base_url')
            
            # 누락된 필드 기본값 설정
            if 'is_active' not in platform_data:
                platform_data['is_active'] = True
            
            # platform_code 매핑
            platform_code = None
            if 'code' in platform_data and platform_data['code'] in self.platform_code_map:
                platform_code = self.platform_code_map[platform_data['code']]
            
            # created_at, updated_at 추가
            platform_data['created_at'] = 'CURRENT_TIMESTAMP'
            platform_data['updated_at'] = 'CURRENT_TIMESTAMP'
            platform_data['platform_code'] = platform_code
            
            platform_id = self._execute_upsert(
                'housing.platforms', 
                platform_data, 
                ['code'], 
                ['name', 'url', 'platform_code', 'is_active', 'updated_at']
            )
            platform['db_id'] = platform_id
            
            # 매핑 테이블 업데이트
            if 'code' in platform:
                self.platform_id_map[platform['code']] = platform_id
    
    def _load_addresses(self, addresses: List[Dict]):
        """주소 데이터 저장"""
        if not addresses:
            return
            
        logger.info(f"주소 데이터 저장: {len(addresses)}개")
        
        for address in addresses:
            # id 필드 제외하고 저장
            address_data = {k: v for k, v in address.items() if k != 'id'}
            
            # 필드명 매핑
            if 'lat' in address_data:
                address_data['latitude'] = address_data.pop('lat')
            if 'lon' in address_data:
                address_data['longitude'] = address_data.pop('lon')
            
            # 빈 문자열을 NULL로 처리
            for key, value in address_data.items():
                if value == '' or value is None:
                    address_data[key] = None
            
            # INSERT 쿼리 (housing 스키마 사용) - 중복은 무시
            query = """
            INSERT INTO housing.addresses (address_raw, ctpv_nm, sgg_nm, emd_cd, emd_nm, road_name_full, jibun_name_full, building_name, building_main_no, building_sub_no, latitude, longitude, created_at)
            VALUES (:address_raw, :ctpv_nm, :sgg_nm, :emd_cd, :emd_nm, :road_name_full, :jibun_name_full, :building_name, :building_main_no, :building_sub_no, :latitude, :longitude, CURRENT_TIMESTAMP)
            ON CONFLICT DO NOTHING
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
            # platform_id 매핑 (정규화된 데이터의 platform_id를 DB의 실제 ID로 변환)
            platform_id = None
            notice_platform_id = notice.get('platform_id')
            if notice_platform_id:
                # platform_id_map의 키는 platform code이므로, 
                # 정규화된 데이터의 platform_id를 code로 변환해야 함
                # 현재는 cohouse=1, sohouse=2 등으로 가정
                platform_code_map = {1: 'cohouse', 2: 'sohouse', 3: 'youth', 4: 'sh', 5: 'lh'}
                platform_code = platform_code_map.get(notice_platform_id)
                if platform_code and platform_code in self.platform_id_map:
                    platform_id = self.platform_id_map[platform_code]
            
            # address_id 매핑
            address_id = None
            if 'address_id' in notice and notice['address_id'] in self.address_id_map:
                address_id = self.address_id_map[notice['address_id']]
            
            # building_type 매핑
            building_type_code = None
            if 'building_type' in notice and notice['building_type'] in self.building_type_map:
                building_type_code = self.building_type_map[notice['building_type']]
            
            # 공고 데이터 준비
            notice_data = {
                'platform_id': platform_id,
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
                'building_type': building_type_code,  # FK to code_master
                'notice_extra': json.dumps(notice.get('notice_extra', {})),
                'has_images': notice.get('has_images', False),
                'has_floorplan': notice.get('has_floorplan', False),
                'has_documents': notice.get('has_documents', False)
            }
            
            # UPSERT 쿼리 (housing 스키마 사용)
            query = """
            INSERT INTO housing.notices (
                platform_id, source_key, title, detail_url, list_url, status,
                posted_at, last_modified, apply_start_at, apply_end_at, address_raw, address_id,
                building_type, notice_extra, has_images, has_floorplan,
                has_documents, created_at, updated_at
            ) VALUES (
                :platform_id, :source_key, :title, :detail_url, :list_url, :status,
                :posted_at, :last_modified, :apply_start_at, :apply_end_at, :address_raw, :address_id,
                :building_type, :notice_extra, :has_images, :has_floorplan,
                :has_documents, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
            ) ON CONFLICT (platform_id, source_key) DO UPDATE SET
                title = EXCLUDED.title,
                detail_url = EXCLUDED.detail_url,
                status = EXCLUDED.status,
                posted_at = EXCLUDED.posted_at,
                last_modified = EXCLUDED.last_modified,
                address_raw = EXCLUDED.address_raw,
                address_id = EXCLUDED.address_id,
                building_type = EXCLUDED.building_type,
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
            # notice_id 매핑 (notice_id는 source_key와 동일)
            notice_id = None
            if 'notice_id' in unit and unit['notice_id'] in self.notice_id_map:
                notice_id = self.notice_id_map[unit['notice_id']]
            else:
                logger.warning(f"notice_id 매핑 실패: {unit.get('notice_id')}")
            
            # 유닛 데이터 준비
            unit_data = {
                'notice_id': notice_id,
                'unit_code': unit.get('unit_code'),
                'unit_type': unit.get('unit_type'),
                'deposit': unit.get('deposit'),
                'rent': unit.get('rent'),
                'maintenance_fee': unit.get('maintenance_fee'),
                'area_m2': unit.get('area_m2'),
                'floor': unit.get('floor'),
                'room_number': unit.get('room_number'),
                'occupancy_available': unit.get('occupancy_available'),
                'occupancy_available_at': unit.get('occupancy_available_at'),
                'capacity': unit.get('capacity')
            }
            
            # UPSERT 쿼리 (housing 스키마 사용)
            query = """
            INSERT INTO housing.units (
                notice_id, unit_code, unit_type, deposit, rent, maintenance_fee,
                area_m2, floor, room_number, occupancy_available, occupancy_available_at,
                capacity, created_at, updated_at
            ) VALUES (
                :notice_id, :unit_code, :unit_type, :deposit, :rent, :maintenance_fee,
                :area_m2, :floor, :room_number, :occupancy_available, :occupancy_available_at,
                :capacity, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
            ) ON CONFLICT (id) DO UPDATE SET
                notice_id = EXCLUDED.notice_id,
                unit_code = EXCLUDED.unit_code,
                unit_type = EXCLUDED.unit_type,
                deposit = EXCLUDED.deposit,
                rent = EXCLUDED.rent,
                maintenance_fee = EXCLUDED.maintenance_fee,
                area_m2 = EXCLUDED.area_m2,
                floor = EXCLUDED.floor,
                room_number = EXCLUDED.room_number,
                occupancy_available = EXCLUDED.occupancy_available,
                occupancy_available_at = EXCLUDED.occupancy_available_at,
                capacity = EXCLUDED.capacity,
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
            
            # unit_features 데이터 준비
            feature_data = {
                'unit_id': unit_id,
                'room_count': feature.get('room_count'),
                'bathroom_count': feature.get('bathroom_count'),
                'direction': feature.get('direction')
            }
            
            # INSERT 쿼리 (unit_features는 unit_id당 하나씩만 존재)
            query = """
            INSERT INTO housing.unit_features (
                unit_id, room_count, bathroom_count, direction, created_at, updated_at
            ) VALUES (
                :unit_id, :room_count, :bathroom_count, :direction, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
            )
            """
            self.connection.execute(text(query), feature_data)
    
    def _load_notice_tags(self, notice_tags: List[Dict]):
        """공고 태그 데이터 저장"""
        if not notice_tags:
            return
            
        logger.info(f"공고 태그 데이터 저장: {len(notice_tags)}개")
        
        for tag in notice_tags:
            # notice_id는 정규화된 데이터에서 직접 사용 (정수 ID)
            notice_id = tag.get('notice_id')
            
            if notice_id is None:
                continue
                
            tag_data = {
                'notice_id': notice_id,
                'tag': tag.get('tag')
            }
            
            # UPSERT 쿼리 (housing 스키마 사용)
            query = """
            INSERT INTO housing.notice_tags (notice_id, tag, created_at, updated_at)
            VALUES (:notice_id, :tag, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            ON CONFLICT (notice_id, tag) DO NOTHING
            """
            self.connection.execute(text(query), tag_data)
