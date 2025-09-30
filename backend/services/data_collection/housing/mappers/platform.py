#!/usr/bin/env python3
"""
Platform 키 통일 모듈
platform_id와 code 필드 불일치 문제를 해결합니다.
"""

import json
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path


class PlatformMapper:
    """Platform 키 통일 클래스"""
    
    def __init__(self):
        """PlatformMapper 초기화"""
        # 플랫폼 코드 매핑 (notices의 platform_id -> platforms의 code)
        self.platform_mapping = {
            'co': 'cohouse',
            'so': 'sohouse', 
            'youth': 'youth',
            'sh': 'sh',
            'lh': 'lh'
        }
        
        # 역매핑 (platforms의 code -> notices의 platform_id)
        self.reverse_mapping = {v: k for k, v in self.platform_mapping.items()}
    
    def normalize_platforms(self, platforms: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        platforms 데이터 정규화
        platform_id를 code로 변경하고 구조 통일
        
        Args:
            platforms: platforms 데이터 리스트
            
        Returns:
            정규화된 platforms 리스트
        """
        normalized_platforms = []
        
        for platform in platforms:
            normalized_platform = platform.copy()
            
            # platform_id가 있으면 code로 변경
            if 'platform_id' in normalized_platform:
                normalized_platform['code'] = normalized_platform.pop('platform_id')
            
            # 기본 필드 확인 및 설정
            if 'name' not in normalized_platform:
                normalized_platform['name'] = normalized_platform.get('code', 'Unknown')
            
            if 'url' not in normalized_platform:
                normalized_platform['url'] = self._get_default_url(normalized_platform.get('code', ''))
            
            if 'is_active' not in normalized_platform:
                normalized_platform['is_active'] = True
            
            normalized_platforms.append(normalized_platform)
        
        return normalized_platforms
    
    def normalize_notices_platform_ids(self, notices: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        notices의 platform_id를 통일된 코드로 변경
        
        Args:
            notices: notices 데이터 리스트
            
        Returns:
            정규화된 notices 리스트
        """
        normalized_notices = []
        
        for notice in notices:
            normalized_notice = notice.copy()
            platform_id = notice.get('platform_id', '')
            
            # platform_id 매핑
            if platform_id in self.platform_mapping:
                normalized_notice['platform_id'] = self.platform_mapping[platform_id]
            elif platform_id in self.reverse_mapping:
                # 이미 올바른 형태인 경우 그대로 유지
                pass
            else:
                # 매핑되지 않은 경우 경고
                print(f"⚠️  알 수 없는 platform_id: {platform_id}")
            
            normalized_notices.append(normalized_notice)
        
        return normalized_notices
    
    def _get_default_url(self, code: str) -> str:
        """플랫폼 코드에 따른 기본 URL 반환"""
        url_map = {
            'cohouse': 'https://soco.seoul.go.kr/coHouse',
            'sohouse': 'https://soco.seoul.go.kr/soHouse',
            'youth': 'https://soco.seoul.go.kr/youth',
            'sh': 'https://www.sh.co.kr',
            'lh': 'https://www.lh.or.kr'
        }
        return url_map.get(code, '')
    
    def analyze_platform_consistency(self, platforms: List[Dict[str, Any]], 
                                   notices: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        플랫폼 일관성 분석
        
        Args:
            platforms: platforms 데이터 리스트
            notices: notices 데이터 리스트
            
        Returns:
            분석 결과 딕셔너리
        """
        # platforms에서 사용되는 코드들
        platform_codes = set()
        for platform in platforms:
            code = platform.get('code') or platform.get('platform_id')
            if code:
                platform_codes.add(code)
        
        # notices에서 사용되는 platform_id들
        notice_platform_ids = set()
        for notice in notices:
            platform_id = notice.get('platform_id', '')
            if platform_id:
                notice_platform_ids.add(platform_id)
        
        # 매핑된 platform_id들
        mapped_platform_ids = set()
        for platform_id in notice_platform_ids:
            if platform_id in self.platform_mapping:
                mapped_platform_ids.add(self.platform_mapping[platform_id])
            elif platform_id in self.reverse_mapping:
                mapped_platform_ids.add(platform_id)
        
        # 일치하지 않는 코드들
        mismatched_platforms = platform_codes - mapped_platform_ids
        mismatched_notices = notice_platform_ids - set(self.platform_mapping.keys()) - set(self.reverse_mapping.keys())
        
        return {
            'platform_codes': list(platform_codes),
            'notice_platform_ids': list(notice_platform_ids),
            'mapped_platform_ids': list(mapped_platform_ids),
            'mismatched_platforms': list(mismatched_platforms),
            'mismatched_notices': list(mismatched_notices),
            'consistency_score': len(mapped_platform_ids) / len(platform_codes) * 100 if platform_codes else 0
        }
    
    def process_platform_files(self, platforms_file: str, notices_file: str, 
                             output_platforms_file: str = None, 
                             output_notices_file: str = None) -> Dict[str, Any]:
        """
        플랫폼 파일들 일괄 처리
        
        Args:
            platforms_file: platforms.json 파일 경로
            notices_file: notices.json 파일 경로
            output_platforms_file: 출력 platforms 파일 경로 (None이면 원본 덮어쓰기)
            output_notices_file: 출력 notices 파일 경로 (None이면 원본 덮어쓰기)
            
        Returns:
            처리 결과 통계
        """
        # 파일 읽기
        with open(platforms_file, 'r', encoding='utf-8') as f:
            platforms = json.load(f)
        
        with open(notices_file, 'r', encoding='utf-8') as f:
            notices = json.load(f)
        
        # 분석
        analysis = self.analyze_platform_consistency(platforms, notices)
        
        # 정규화
        normalized_platforms = self.normalize_platforms(platforms)
        normalized_notices = self.normalize_notices_platform_ids(notices)
        
        # 파일 저장
        output_platforms = output_platforms_file or platforms_file
        output_notices = output_notices_file or notices_file
        
        with open(output_platforms, 'w', encoding='utf-8') as f:
            json.dump(normalized_platforms, f, ensure_ascii=False, indent=2)
        
        with open(output_notices, 'w', encoding='utf-8') as f:
            json.dump(normalized_notices, f, ensure_ascii=False, indent=2)
        
        return {
            'analysis': analysis,
            'platforms_file': output_platforms,
            'notices_file': output_notices,
            'platforms_count': len(normalized_platforms),
            'notices_count': len(normalized_notices)
        }
    
    def add_platform_mapping(self, notice_platform_id: str, platform_code: str):
        """사용자 정의 플랫폼 매핑 추가"""
        self.platform_mapping[notice_platform_id] = platform_code
        self.reverse_mapping[platform_code] = notice_platform_id
    
    def get_platform_mappings(self) -> Dict[str, str]:
        """현재 플랫폼 매핑 반환"""
        return self.platform_mapping.copy()


def main():
    """CLI 실행 함수"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Platform 키 통일')
    parser.add_argument('--platforms', required=True, help='platforms.json 파일 경로')
    parser.add_argument('--notices', required=True, help='notices.json 파일 경로')
    parser.add_argument('--output-platforms', help='출력 platforms 파일 경로')
    parser.add_argument('--output-notices', help='출력 notices 파일 경로')
    parser.add_argument('--analyze-only', action='store_true', help='분석만 수행하고 변환하지 않음')
    
    args = parser.parse_args()
    
    mapper = PlatformMapper()
    
    if args.analyze_only:
        # 분석만 수행
        with open(args.platforms, 'r', encoding='utf-8') as f:
            platforms = json.load(f)
        
        with open(args.notices, 'r', encoding='utf-8') as f:
            notices = json.load(f)
        
        analysis = mapper.analyze_platform_consistency(platforms, notices)
        
        print(f"=== Platform 일관성 분석 ===")
        print(f"Platforms 코드: {analysis['platform_codes']}")
        print(f"Notices platform_id: {analysis['notice_platform_ids']}")
        print(f"일관성 점수: {analysis['consistency_score']:.1f}%")
        
        if analysis['mismatched_platforms']:
            print(f"불일치 platforms: {analysis['mismatched_platforms']}")
        
        if analysis['mismatched_notices']:
            print(f"불일치 notices: {analysis['mismatched_notices']}")
    
    else:
        # 변환 수행
        result = mapper.process_platform_files(
            args.platforms, 
            args.notices,
            args.output_platforms,
            args.output_notices
        )
        
        print(f"=== Platform 키 통일 완료 ===")
        print(f"Platforms: {result['platforms_file']}")
        print(f"Notices: {result['notices_file']}")
        print(f"일관성 점수: {result['analysis']['consistency_score']:.1f}%")


if __name__ == "__main__":
    main()
