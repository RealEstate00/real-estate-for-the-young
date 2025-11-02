"""
Schema Loader - SQL 스키마 로더

데이터베이스 스키마 파일을 로드하고 관리합니다.
"""

import os
from pathlib import Path
from typing import Optional, Dict
import logging

logger = logging.getLogger(__name__)


def load_schema(schema_name: str, schema_dir: Optional[str] = None) -> str:
    """
    스키마 파일 로드
    
    Args:
        schema_name: 스키마 파일명 (확장자 포함)
        schema_dir: 스키마 디렉토리 경로 (기본값: backend/services/db/schema)
        
    Returns:
        스키마 내용 문자열
    """
    if schema_dir is None:
        # 기본 스키마 디렉토리
        current_dir = Path(__file__).parent
        project_root = current_dir.parent.parent.parent.parent
        schema_dir = project_root / "services" / "db" / "schema"
    else:
        schema_dir = Path(schema_dir)
    
    schema_path = schema_dir / schema_name
    
    try:
        with open(schema_path, 'r', encoding='utf-8') as f:
            content = f.read()
            logger.info(f"스키마 로드 성공: {schema_path}")
            return content
            
    except FileNotFoundError:
        logger.error(f"스키마 파일을 찾을 수 없습니다: {schema_path}")
        return ""
    except Exception as e:
        logger.error(f"스키마 로드 중 오류 발생: {e}")
        return ""


def load_housing_schema() -> str:
    """주택 스키마 로드"""
    return load_schema("housing_schema.sql")


def load_infra_schema() -> str:
    """인프라 스키마 로드"""
    return load_schema("infra_schema.sql")


def load_rtms_schema() -> str:
    """실거래가 스키마 로드"""
    return load_schema("rtms_schema.sql")


def get_schema_info(schema_content: str) -> Dict[str, str]:
    """
    스키마 내용에서 테이블 정보 추출
    
    Args:
        schema_content: 스키마 내용
        
    Returns:
        테이블별 정보 딕셔너리
    """
    # TODO: SQL 파싱하여 테이블 정보 추출
    # 현재는 기본 정보만 반환
    
    tables = {}
    
    # 간단한 테이블 추출 (CREATE TABLE 찾기)
    lines = schema_content.split('\n')
    current_table = None
    
    for line in lines:
        line = line.strip()
        if line.upper().startswith('CREATE TABLE'):
            # 테이블명 추출
            parts = line.split()
            if len(parts) >= 3:
                table_name = parts[2].replace('(', '').replace(';', '')
                current_table = table_name
                tables[current_table] = {
                    "name": table_name,
                    "columns": [],
                    "description": ""
                }
        elif current_table and line and not line.startswith('--'):
            # 컬럼 정보 추가 (간단한 파싱)
            if '(' in line and ')' in line:
                continue  # 테이블 정의 끝
            if line.endswith(',') or line.endswith(';'):
                tables[current_table]["columns"].append(line)
    
    return tables
