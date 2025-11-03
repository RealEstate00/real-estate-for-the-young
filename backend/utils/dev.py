#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
개발/프로덕션 모드 실행 스크립트
- 개발 모드: API/Postgres는 도커, Frontend는 로컬 (코드 수정 즉시 반영)
- 프로덕션 모드: 모든 서비스를 도커에서 실행 (Docker Hub 이미지 사용)
Usage: 
  dev [--model e5_small|e5_base|e5_large|kakao]          # 개발 모드
  dev --prod [--model e5_small|e5_base|e5_large|kakao]  # 프로덕션 모드
"""

import os
import sys
import subprocess
import time
import argparse
from pathlib import Path

def get_compose_file(prod: bool = False):
    """docker-compose 파일 경로 반환"""
    project_root = Path(__file__).parent.parent.parent
    if prod:
        return project_root / "docker-compose.prod.yml"
    else:
        return project_root / "docker-compose.dev.yml"

def start_docker_services(model_name: str = None, prod: bool = False):
    """도커에서 서비스 시작"""
    compose_file = get_compose_file(prod=prod)
    compose_name = "docker-compose.prod.yml" if prod else "docker-compose.dev.yml"
    
    if not compose_file.exists():
        print(f"❌ {compose_name} 파일을 찾을 수 없습니다: {compose_file}")
        return False
    
    if prod:
        print("🐳 Starting Docker services (프로덕션 모드: API + Postgres + Frontend)...")
    else:
        print("🐳 Starting Docker services (개발 모드: API + Postgres)...")
    
    # 모델 환경 변수 설정 (docker-compose에서 사용할 수 있도록)
    env = os.environ.copy()
    if model_name:
        env['RAG_EMBEDDING_MODEL'] = model_name.upper()
        print(f"📌 Embedding Model: {model_name.upper()}")
    
    try:
        # docker-compose로 서비스 시작
        if prod:
            # 프로덕션: 모든 서비스 시작
            result = subprocess.run(
                ["docker-compose", "-f", str(compose_file), "up", "-d"],
                env=env,
                check=False
            )
        else:
            # 개발: API와 Postgres만 시작
            result = subprocess.run(
                ["docker-compose", "-f", str(compose_file), "up", "-d"],
                env=env,
                check=False
            )
        
        if result.returncode == 0:
            print("✅ Docker services started")
            # 서비스 시작 대기
            time.sleep(3)
            return True
        else:
            print("❌ Docker services 시작 실패")
            return False
            
    except FileNotFoundError:
        print("❌ docker-compose를 찾을 수 없습니다. Docker가 설치되어 있는지 확인해주세요.")
        return False
    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        return False

def run_react():
    """React 개발 서버 실행"""
    project_root = Path(__file__).parent.parent.parent
    react_dir = project_root / "frontend" / "react"
    
    # React 디렉토리로 이동하여 실행
    os.chdir(react_dir)
    
    try:
        # npm run dev 직접 실행 (충돌 방지)
        subprocess.run(["npm", "run", "dev"])
    except KeyboardInterrupt:
        print("\n🛑 React server stopped")
    except FileNotFoundError:
        print("❌ npm을 찾을 수 없습니다. Node.js가 설치되어 있는지 확인해주세요.")
        print("설치 방법: https://nodejs.org/")
    finally:
        # 원래 디렉토리로 복귀
        os.chdir(project_root)

def main():
    """개발/프로덕션 모드 실행"""
    parser = argparse.ArgumentParser(
        description="개발/프로덕션 모드 실행",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
사용 가능한 임베딩 모델:
  e5_small   - Multilingual E5 Small (384차원, 가장 빠름, 기본값)
  e5_base    - Multilingual E5 Base (768차원, 균형잡힌 성능)
  e5_large   - Multilingual E5 Large (1024차원, 가장 정확)
  kakao      - KakaoBank DeBERTa (768차원, 한국어 특화)

예시:
  dev --model e5_large              # 개발 모드
  dev --prod --model e5_large       # 프로덕션 모드
        """
    )
    parser.add_argument(
        "--model",
        type=str,
        default=None,
        choices=["e5_small", "e5_base", "e5_large", "kakao", "E5_SMALL", "E5_BASE", "E5_LARGE", "KAKAO"],
        help="사용할 임베딩 모델 (기본값: e5_small)"
    )
    parser.add_argument(
        "--prod",
        action="store_true",
        help="프로덕션 모드 실행 (모든 서비스 Docker에서 실행)"
    )
    
    args = parser.parse_args()
    
    # 모델 이름 정규화 (대소문자 통일)
    model_name = None
    if args.model:
        model_upper = args.model.upper()
        if model_upper in ["E5_SMALL", "E5_BASE", "E5_LARGE", "KAKAO"]:
            model_name = model_upper
        elif model_upper == "KAKAO":
            model_name = "KAKAO"
        elif "SMALL" in model_upper:
            model_name = "E5_SMALL"
        elif "BASE" in model_upper:
            model_name = "E5_BASE"
        elif "LARGE" in model_upper:
            model_name = "E5_LARGE"
    
    if args.prod:
        # 프로덕션 모드
        print("🚀 Starting Production Mode...")
        print("🐳 모든 서비스: Docker (docker-compose.prod.yml)")
        print("📍 API: http://localhost:8000")
        print("📍 Frontend: http://localhost:3000")
        if model_name:
            print(f"📌 Embedding Model: {model_name}")
        print("🛑 중지하려면: docker-compose -f docker-compose.prod.yml down")
        print("-" * 50)
        
        try:
            # 프로덕션: 모든 서비스를 Docker에서 실행
            if not start_docker_services(model_name, prod=True):
                print("❌ Docker services 시작 실패. 종료합니다.")
                return
            
            print("✅ 모든 서비스가 Docker에서 실행 중입니다.")
            print("💡 로그 확인: docker-compose -f docker-compose.prod.yml logs -f")
            print("💡 중지: docker-compose -f docker-compose.prod.yml down")
            
        except KeyboardInterrupt:
            print("\n🛑 중지되었습니다")
    else:
        # 개발 모드
        print("🚀 Starting Development Mode...")
        print("🐳 API + Postgres: Docker (docker-compose.dev.yml)")
        print("💻 Frontend: Local (npm run dev)")
        print("📍 API: http://localhost:8000")
        print("📍 Frontend: http://localhost:3000")
        if model_name:
            print(f"📌 Embedding Model: {model_name}")
        print("🛑 Press Ctrl+C to stop Frontend (Docker는 계속 실행)")
        print("-" * 50)
        
        try:
            # 1. 도커에서 API와 Postgres 시작
            if not start_docker_services(model_name, prod=False):
                print("❌ Docker services 시작 실패. 종료합니다.")
                return
            
            print("✅ Docker services (API + Postgres) running")
            print("⏳ Starting Frontend (local)...")
            print("-" * 50)
            
            # 2. 로컬에서 Frontend 개발 서버 실행
            run_react()
            
        except KeyboardInterrupt:
            print("\n🛑 Frontend stopped (Docker services are still running)")
            print("💡 Docker를 중지하려면: docker-compose -f docker-compose.dev.yml down")

if __name__ == "__main__":
    main()

