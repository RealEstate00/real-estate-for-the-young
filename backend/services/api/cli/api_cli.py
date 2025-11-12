#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
API 서버 CLI 스크립트 (도커 사용)
Usage: 
  api          # API 서버 시작 (개발 모드, docker-compose.dev.yml)
  api restart  # API 서버 재시작 (개발 모드)
  api stop     # API 서버 중지 (개발 모드)
  api prod     # API 서버 시작 (프로덕션 모드, docker-compose.prod.yml, Docker Hub 이미지)
  api prod restart  # API 서버 재시작 (프로덕션 모드)
  api prod stop     # API 서버 중지 (프로덕션 모드)
"""

import os
import sys
import subprocess
import time
from pathlib import Path

def get_compose_file(production=False):
    """docker-compose 파일 경로 반환"""
    project_root = Path(__file__).parent.parent.parent.parent.parent
    if production:
        return project_root / "docker-compose.prod.yml"
    else:
        return project_root / "docker-compose.dev.yml"

def start_api_server(production=False):
    """API 서버 시작 (도커)"""
    compose_file = get_compose_file(production)
    mode = "프로덕션" if production else "개발"
    compose_name = "docker-compose.prod.yml" if production else "docker-compose.dev.yml"
    
    if not compose_file.exists():
        print(f"❌ {compose_name} 파일을 찾을 수 없습니다: {compose_file}")
        return False
    
    if production:
        print("🚀 Starting API server (프로덕션 모드 - Docker Hub 이미지)...")
        print("📦 이미지: jina1003/seoul-housing-api:latest")
    else:
        print("🚀 Starting API server (개발 모드 - 로컬 빌드)...")
    
    print("📍 API: http://localhost:8000")
    print("📚 API docs: http://localhost:8000/docs")
    print(f"🛑 중지하려면: {'api prod stop' if production else 'api stop'}")
    print("-" * 50)
    
    try:
        # docker-compose로 API와 Postgres 시작
        result = subprocess.run(
            ["docker-compose", "-f", str(compose_file), "up", "-d"],
            check=False
        )
        
        if result.returncode == 0:
            print(f"✅ API 서버가 {mode} 모드로 도커에서 시작되었습니다.")
            print("\n📋 유용한 명령어:")
            if production:
                print("  api prod stop      - API 서버 중지")
                print("  api prod restart   - API 서버 재시작")
                print(f"  docker-compose -f {compose_name} logs -f api  - 로그 확인")
            else:
                print("  api stop      - API 서버 중지")
                print("  api restart   - API 서버 재시작")
                print(f"  docker-compose -f {compose_name} logs -f api  - 로그 확인")
            return True
        else:
            print(f"❌ API 서버 시작 실패")
            return False
            
    except FileNotFoundError:
        print("❌ docker-compose를 찾을 수 없습니다. Docker가 설치되어 있는지 확인해주세요.")
        return False
    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        return False

def stop_api_server(production=False):
    """API 서버 중지 (도커)"""
    compose_file = get_compose_file(production)
    mode = "프로덕션" if production else "개발"
    compose_name = "docker-compose.prod.yml" if production else "docker-compose.dev.yml"
    
    if not compose_file.exists():
        print(f"❌ {compose_name} 파일을 찾을 수 없습니다: {compose_file}")
        return False
    
    print(f"🛑 Stopping API server ({mode} 모드)...")
    
    try:
        # API만 중지 (Postgres는 유지)
        result = subprocess.run(
            ["docker-compose", "-f", str(compose_file), "stop", "api"],
            check=False
        )
        
        if result.returncode == 0:
            print(f"✅ API 서버가 중지되었습니다. (Postgres는 계속 실행 중)")
            return True
        else:
            print("⚠️ API 서버 중지 중 오류 발생 (이미 중지되었을 수 있음)")
            return False
            
    except FileNotFoundError:
        print("❌ docker-compose를 찾을 수 없습니다.")
        return False

def restart_api_server(production=False):
    """API 서버 재시작 (도커)"""
    compose_file = get_compose_file(production)
    mode = "프로덕션" if production else "개발"
    compose_name = "docker-compose.prod.yml" if production else "docker-compose.dev.yml"
    
    if not compose_file.exists():
        print(f"❌ {compose_name} 파일을 찾을 수 없습니다: {compose_file}")
        return False
    
    print(f"🔄 Restarting API server ({mode} 모드)...")
    
    try:
        # API만 재시작
        result = subprocess.run(
            ["docker-compose", "-f", str(compose_file), "restart", "api"],
            check=False
        )
        
        if result.returncode == 0:
            print(f"✅ API 서버가 재시작되었습니다.")
            return True
        else:
            print("❌ API 서버 재시작 실패")
            return False
            
    except FileNotFoundError:
        print("❌ docker-compose를 찾을 수 없습니다.")
        return False

def main():
    """메인 함수"""
    if len(sys.argv) > 1:
        first_arg = sys.argv[1].lower()
        
        # 프로덕션 모드 체크
        if first_arg == "prod":
            production = True
            if len(sys.argv) > 2:
                command = sys.argv[2].lower()
                if command == "restart":
                    restart_api_server(production=True)
                elif command == "stop":
                    stop_api_server(production=True)
                elif command == "start":
                    start_api_server(production=True)
                else:
                    print(f"❌ 알 수 없는 명령어: {command}")
                    print("사용법: api prod [start|restart|stop]")
            else:
                # api prod만 입력한 경우 시작
                start_api_server(production=True)
        else:
            # 개발 모드
            production = False
            command = first_arg
            if command == "restart":
                restart_api_server(production=False)
            elif command == "stop":
                stop_api_server(production=False)
            elif command == "start":
                start_api_server(production=False)
            else:
                print(f"❌ 알 수 없는 명령어: {command}")
                print("사용법:")
                print("  api [start|restart|stop]        # 개발 모드 (로컬 빌드)")
                print("  api prod [start|restart|stop]   # 프로덕션 모드 (Docker Hub 이미지)")
    else:
        # 인자 없이 실행한 경우 개발 모드로 시작
        start_api_server(production=False)

if __name__ == "__main__":
    main()
