#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
RAW 크롤링 데이터 분석기
"""

import json
import pandas as pd
from pathlib import Path
from typing import Dict, Any, List
from datetime import datetime

class RawDataAnalyzer:
    """RAW 크롤링 데이터 분석기"""
    
    def __init__(self, data_root: str = None):
        if data_root is None:
            # backend 루트 기준으로 data/raw 경로 설정 (분석할 데이터 위치)
            # data_analyzer.py -> parsers -> services -> ingestion -> backend
            self.data_root = Path(__file__).parent.parent.parent.parent.parent / "data" / "raw"
        else:
            self.data_root = Path(data_root)
        self.platforms = []
        self.analysis_results = {}
    
    def analyze_all_platforms(self) -> Dict[str, Any]:
        """모든 플랫폼의 RAW 데이터 분석"""
        print(f"📁 분석 대상 디렉토리: {self.data_root}")
        
        if not self.data_root.exists():
            print("❌ 분석할 데이터 디렉토리가 존재하지 않습니다.")
            return {}
        
        # 플랫폼별 디렉토리 찾기
        platform_dirs = [d for d in self.data_root.iterdir() if d.is_dir()]
        
        if not platform_dirs:
            print("❌ 분석할 플랫폼 데이터가 없습니다.")
            return {}
        
        print(f"🔍 발견된 플랫폼: {[d.name for d in platform_dirs]}")
        
        for platform_dir in platform_dirs:
            platform_name = platform_dir.name
            print(f"\n📊 {platform_name} 플랫폼 분석 중...")
            
            # 날짜별 디렉토리 찾기
            date_dirs = [d for d in platform_dir.iterdir() if d.is_dir()]
            
            if not date_dirs:
                print(f"  ⚠️ {platform_name}에 날짜별 데이터가 없습니다.")
                continue
            
            # 가장 최근 날짜 선택
            latest_date_dir = max(date_dirs, key=lambda x: x.name)
            print(f"  📅 최신 데이터: {latest_date_dir.name}")
            
            # CSV 파일 분석
            csv_path = latest_date_dir / "raw.csv"
            if csv_path.exists():
                self.analyze_platform_csv(platform_name, csv_path, latest_date_dir)
            else:
                print(f"  ❌ {platform_name}에 raw.csv 파일이 없습니다.")
        
        return self.analysis_results
    
    def analyze_platform_csv(self, platform_name: str, csv_path: Path, data_dir: Path):
        """플랫폼별 CSV 데이터 분석"""
        try:
            df = pd.read_csv(csv_path)
            print(f"  📈 총 {len(df)}개 주택 데이터")
            
            # 기본 통계
            stats = {
                'platform': platform_name,
                'total_houses': len(df),
                'crawl_date': data_dir.name,
                'data_quality': {}
            }
            
            # 데이터 품질 분석
            stats['data_quality'] = self.analyze_data_quality(df, data_dir)
            
            # 주소 분석
            stats['address_analysis'] = self.analyze_addresses(df)
            
            # 이미지 분석
            stats['image_analysis'] = self.analyze_images(df, data_dir)
            
            # 텍스트 분석
            stats['text_analysis'] = self.analyze_texts(df, data_dir)
            
            self.analysis_results[platform_name] = stats
            
            print(f"  ✅ {platform_name} 분석 완료")
            
        except Exception as e:
            print(f"  ❌ {platform_name} 분석 중 오류: {e}")
    
    def analyze_data_quality(self, df: pd.DataFrame, data_dir: Path) -> Dict[str, Any]:
        """데이터 품질 분석"""
        quality = {
            'missing_data': {},
            'completeness_score': 0
        }
        
        # 필수 필드 누락 분석
        essential_fields = ['house_name', 'address', 'detail_url']
        for field in essential_fields:
            if field in df.columns:
                missing_count = df[field].isna().sum()
                quality['missing_data'][field] = {
                    'count': int(missing_count),
                    'percentage': round(missing_count / len(df) * 100, 2)
                }
        
        # 완성도 점수 계산
        total_fields = len(essential_fields)
        complete_fields = sum(1 for field in essential_fields 
                            if field in df.columns and df[field].isna().sum() == 0)
        quality['completeness_score'] = round(complete_fields / total_fields * 100, 2)
        
        return quality
    
    def analyze_addresses(self, df: pd.DataFrame) -> Dict[str, Any]:
        """주소 정보 분석"""
        if 'address' not in df.columns:
            return {'error': '주소 필드가 없습니다.'}
        
        addresses = df['address'].dropna()
        
        analysis = {
            'total_addresses': len(addresses),
            'seoul_addresses': 0,
            'gu_distribution': {}
        }
        
        # 서울시 주소 분석
        seoul_count = addresses.str.contains('서울', na=False).sum()
        analysis['seoul_addresses'] = int(seoul_count)
        
        # 구별 분포 분석
        for address in addresses:
            if '서울' in str(address):
                # 구 추출 (간단한 패턴 매칭)
                for gu in ['강남구', '강동구', '강북구', '강서구', '관악구', '광진구', '구로구', 
                          '금천구', '노원구', '도봉구', '동대문구', '동작구', '마포구', 
                          '서대문구', '서초구', '성동구', '성북구', '송파구', '양천구', 
                          '영등포구', '용산구', '은평구', '종로구', '중구', '중랑구']:
                    if gu in str(address):
                        analysis['gu_distribution'][gu] = analysis['gu_distribution'].get(gu, 0) + 1
                        break
        
        return analysis
    
    def analyze_images(self, df: pd.DataFrame, data_dir: Path) -> Dict[str, Any]:
        """이미지 파일 분석"""
        if 'image_paths' not in df.columns:
            return {'error': '이미지 경로 필드가 없습니다.'}
        
        image_dir = data_dir / 'images'
        total_images = 0
        image_sizes = []
        
        if image_dir.exists():
            # 실제 이미지 파일 개수
            image_files = list(image_dir.glob('*.jpg')) + list(image_dir.glob('*.png'))
            total_images = len(image_files)
            
            # 이미지 크기 분석
            for img_file in image_files[:10]:  # 샘플 10개만
                try:
                    size = img_file.stat().st_size
                    image_sizes.append(size)
                except:
                    pass
        
        # CSV에서 이미지 경로 개수
        image_path_counts = []
        for paths in df['image_paths'].dropna():
            if isinstance(paths, str) and paths.strip():
                count = len([p for p in paths.split(';') if p.strip()])
                image_path_counts.append(count)
        
        return {
            'total_image_files': total_images,
            'avg_images_per_house': round(sum(image_path_counts) / len(image_path_counts), 2) if image_path_counts else 0,
            'max_images_per_house': max(image_path_counts) if image_path_counts else 0,
            'avg_image_size_kb': round(sum(image_sizes) / len(image_sizes) / 1024, 2) if image_sizes else 0
        }
    
    def analyze_texts(self, df: pd.DataFrame, data_dir: Path) -> Dict[str, Any]:
        """텍스트 파일 분석"""
        text_dir = data_dir / 'texts'
        
        if not text_dir.exists():
            return {'error': '텍스트 디렉토리가 없습니다.'}
        
        text_files = list(text_dir.glob('*.txt'))
        text_lengths = []
        
        for txt_file in text_files:
            try:
                content = txt_file.read_text(encoding='utf-8')
                text_lengths.append(len(content))
            except:
                pass
        
        return {
            'total_text_files': len(text_files),
            'avg_text_length': round(sum(text_lengths) / len(text_lengths), 2) if text_lengths else 0,
            'max_text_length': max(text_lengths) if text_lengths else 0
        }
    
    def print_summary(self):
        """분석 결과 요약 출력"""
        print("\n" + "="*60)
        print("📊 RAW 데이터 분석 결과 요약")
        print("="*60)
        
        total_houses = 0
        for platform, stats in self.analysis_results.items():
            print(f"\n🏠 {platform.upper()}")
            print(f"  📈 총 주택 수: {stats['total_houses']}개")
            print(f"  📅 크롤링 날짜: {stats['crawl_date']}")
            
            # 데이터 품질
            quality = stats.get('data_quality', {})
            print(f"  🎯 완성도 점수: {quality.get('completeness_score', 0)}%")
            
            # 주소 분석
            addr = stats.get('address_analysis', {})
            if 'seoul_addresses' in addr:
                print(f"  🏙️ 서울시 주소: {addr['seoul_addresses']}개")
            
            # 이미지 분석
            img = stats.get('image_analysis', {})
            if 'total_image_files' in img:
                print(f"  🖼️ 이미지 파일: {img['total_image_files']}개")
                print(f"  📊 주택당 평균 이미지: {img.get('avg_images_per_house', 0)}개")
            
            # 텍스트 분석
            txt = stats.get('text_analysis', {})
            if 'total_text_files' in txt:
                print(f"  📝 텍스트 파일: {txt['total_text_files']}개")
                print(f"  📏 평균 텍스트 길이: {txt.get('avg_text_length', 0)}자")
            
            total_houses += stats['total_houses']
        
        print(f"\n🎉 전체 요약: {len(self.analysis_results)}개 플랫폼, 총 {total_houses}개 주택")
        print("="*60)
    
    def save_analysis_report(self):
        """분석 보고서를 JSON 파일로 저장"""
        report_path = Path("data_analysis_report.json")
        
        report = {
            'analysis_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'data_root': str(self.data_root),
            'platforms_analyzed': list(self.analysis_results.keys()),
            'total_houses': sum(stats['total_houses'] for stats in self.analysis_results.values()),
            'detailed_results': self.analysis_results
        }
        
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        
        print(f"📄 상세 보고서 저장: {report_path.absolute()}")
