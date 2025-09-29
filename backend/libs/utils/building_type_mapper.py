#!/usr/bin/env python3
"""
Building Type 코드 매핑 모듈
한글 라벨을 code_master 코드로 변환하는 기능을 제공합니다.
"""

import json
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path


class BuildingTypeMapper:
    """Building Type 코드 매핑 클래스"""
    
    def __init__(self, codes_file_path: str = None):
        """
        BuildingTypeMapper 초기화
        
        Args:
            codes_file_path: codes.json 파일 경로 (None이면 기본 경로 사용)
        """
        if codes_file_path is None:
            # 기본 경로 설정
            project_root = Path(__file__).parent.parent.parent.parent
            codes_file_path = project_root / "backend" / "data" / "normalized" / "codes.json"
        
        self.codes_file_path = Path(codes_file_path)
        self.building_type_mapping = {}
        self._load_codes()
    
    def _load_codes(self):
        """codes.json에서 building_type 매핑 로드"""
        try:
            with open(self.codes_file_path, 'r', encoding='utf-8') as f:
                codes = json.load(f)
            
            # building_type 관련 코드만 추출
            for code in codes:
                if code.get('upper_cd') == 'building_type':
                    cd = code.get('cd')
                    name = code.get('name', '')
                    description = code.get('description', '')
                    
                    # 한글 이름에서 매핑 키 추출
                    korean_name = self._extract_korean_name(name)
                    if korean_name:
                        self.building_type_mapping[korean_name] = {
                            'cd': cd,
                            'name': name,
                            'description': description
                        }
            
            print(f"✅ Building type 매핑 로드 완료: {len(self.building_type_mapping)}개")
            
        except Exception as e:
            print(f"❌ codes.json 로드 실패: {e}")
            self.building_type_mapping = {}
    
    def _extract_korean_name(self, name: str) -> Optional[str]:
        """영문 이름에서 한글 이름 추출"""
        if not name:
            return None
        
        # 괄호 안의 영문 제거하고 한글만 추출
        if '(' in name and ')' in name:
            korean_part = name.split('(')[0].strip()
            return korean_part if korean_part else None
        
        # 한글이 포함된 경우만 반환
        if any('\uac00' <= char <= '\ud7af' for char in name):
            return name.strip()
        
        return None
    
    def get_building_type_code(self, korean_name: str) -> Optional[str]:
        """
        한글 building_type 이름을 코드로 변환
        
        Args:
            korean_name: 한글 building_type 이름 (예: "다세대주택")
            
        Returns:
            코드 (예: "bt_02") 또는 None
        """
        if not korean_name:
            return None
        
        # 정확한 매칭 시도
        if korean_name in self.building_type_mapping:
            return self.building_type_mapping[korean_name]['cd']
        
        # 부분 매칭 시도
        for key, value in self.building_type_mapping.items():
            if key in korean_name or korean_name in key:
                return value['cd']
        
        return None
    
    def get_building_type_info(self, korean_name: str) -> Optional[Dict[str, str]]:
        """
        한글 building_type 이름의 전체 정보 반환
        
        Args:
            korean_name: 한글 building_type 이름
            
        Returns:
            {'cd': 'bt_02', 'name': '다세대주택 (Multi-household)', 'description': '...'} 또는 None
        """
        if not korean_name:
            return None
        
        # 정확한 매칭 시도
        if korean_name in self.building_type_mapping:
            return self.building_type_mapping[korean_name]
        
        # 부분 매칭 시도
        for key, value in self.building_type_mapping.items():
            if key in korean_name or korean_name in key:
                return value
        
        return None
    
    def map_notices_building_types(self, notices: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """
        notices 리스트의 building_type을 코드로 변환
        
        Args:
            notices: notices 데이터 리스트
            
        Returns:
            (변환된 notices 리스트, 통계 정보)
        """
        mapped_notices = []
        stats = {
            'total_notices': len(notices),
            'mapped_count': 0,
            'unmapped_count': 0,
            'unmapped_types': set(),
            'mapping_details': []
        }
        
        for notice in notices:
            mapped_notice = notice.copy()
            korean_name = notice.get('building_type', '')
            
            if korean_name:
                code = self.get_building_type_code(korean_name)
                if code:
                    mapped_notice['building_type'] = code
                    stats['mapped_count'] += 1
                    stats['mapping_details'].append({
                        'notice_id': notice.get('notice_id', 'N/A'),
                        'original': korean_name,
                        'mapped_to': code
                    })
                else:
                    stats['unmapped_count'] += 1
                    stats['unmapped_types'].add(korean_name)
                    stats['mapping_details'].append({
                        'notice_id': notice.get('notice_id', 'N/A'),
                        'original': korean_name,
                        'mapped_to': None
                    })
            else:
                stats['unmapped_count'] += 1
                stats['unmapped_types'].add('(empty)')
            
            mapped_notices.append(mapped_notice)
        
        # set을 list로 변환
        stats['unmapped_types'] = list(stats['unmapped_types'])
        
        return mapped_notices, stats
    
    def analyze_building_types(self, notices: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        notices에서 building_type 분포 분석
        
        Args:
            notices: notices 데이터 리스트
            
        Returns:
            분석 결과 딕셔너리
        """
        type_counts = {}
        unmapped_types = set()
        total_with_building_type = 0
        
        for notice in notices:
            building_type = notice.get('building_type', '')
            if building_type:
                type_counts[building_type] = type_counts.get(building_type, 0) + 1
                total_with_building_type += 1
                
                # 매핑 가능한지 확인
                if not self.get_building_type_code(building_type):
                    unmapped_types.add(building_type)
            else:
                # 빈 문자열도 매핑 불가능한 것으로 간주
                unmapped_types.add('(empty)')
                total_with_building_type += 1
        
        return {
            'total_notices': len(notices),
            'type_distribution': type_counts,
            'unmapped_types': list(unmapped_types),
            'mapping_coverage': (total_with_building_type - len(unmapped_types)) / total_with_building_type * 100 if total_with_building_type > 0 else 0
        }
    
    def get_available_mappings(self) -> Dict[str, Dict[str, str]]:
        """사용 가능한 매핑 목록 반환"""
        return self.building_type_mapping.copy()
    
    def add_custom_mapping(self, korean_name: str, code: str, name: str = None, description: str = None):
        """사용자 정의 매핑 추가"""
        self.building_type_mapping[korean_name] = {
            'cd': code,
            'name': name or korean_name,
            'description': description or f"사용자 정의: {korean_name}"
        }
    
    def save_mapping_to_file(self, output_path: str, notices: List[Dict[str, Any]]):
        """매핑된 notices를 파일로 저장"""
        mapped_notices, stats = self.map_notices_building_types(notices)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(mapped_notices, f, ensure_ascii=False, indent=2)
        
        print(f"✅ 매핑된 notices 저장 완료: {output_path}")
        print(f"📊 매핑 통계: {stats['mapped_count']}/{stats['total_notices']} 성공")
        
        if stats['unmapped_types']:
            print(f"⚠️  매핑 실패 타입들: {stats['unmapped_types']}")
        
        return stats


def main():
    """CLI 실행 함수"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Building Type 코드 매핑')
    parser.add_argument('input_file', help='입력 notices.json 파일 경로')
    parser.add_argument('--output', help='출력 파일 경로 (기본: input_file에 .mapped 추가)')
    parser.add_argument('--codes', help='codes.json 파일 경로')
    parser.add_argument('--analyze-only', action='store_true', help='분석만 수행하고 변환하지 않음')
    
    args = parser.parse_args()
    
    # Mapper 초기화
    mapper = BuildingTypeMapper(args.codes)
    
    # notices 로드
    with open(args.input_file, 'r', encoding='utf-8') as f:
        notices = json.load(f)
    
    # 분석
    analysis = mapper.analyze_building_types(notices)
    print(f"\n=== Building Type 분석 ===")
    print(f"총 notices: {analysis['total_notices']}개")
    print(f"매핑 커버리지: {analysis['mapping_coverage']:.1f}%")
    print(f"\n타입 분포:")
    for bt, count in sorted(analysis['type_distribution'].items(), key=lambda x: x[1], reverse=True):
        print(f"  {bt}: {count}개")
    
    if analysis['unmapped_types']:
        print(f"\n⚠️  매핑 불가능한 타입들:")
        for bt in analysis['unmapped_types']:
            print(f"  - {bt}")
    
    if not args.analyze_only:
        # 매핑 수행
        output_path = args.output or args.input_file.replace('.json', '.mapped.json')
        stats = mapper.save_mapping_to_file(output_path, notices)
        
        print(f"\n=== 매핑 완료 ===")
        print(f"출력 파일: {output_path}")
        print(f"성공: {stats['mapped_count']}개")
        print(f"실패: {stats['unmapped_count']}개")


if __name__ == "__main__":
    main()
