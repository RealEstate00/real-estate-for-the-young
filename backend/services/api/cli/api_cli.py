#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
API 서버 CLI 스크립트 (도커 사용)
API와 Postgres를 docker-compose.dev.yml로 실행
Usage: 
  api          # API 서버 시작 (도커)
  api restart  # API 서버 재시작 (도커)
  api stop     # API 서버 중지 (도커)
"""

import os
import sys
import subprocess
import time
from pathlib import Path

def get_compose_file():
    """docker-compose.dev.yml 경로 반환"""
    project_root = Path(__file__).parent.parent.parent.parent.parent
    return project_root / "docker-compose.dev.yml"

def start_api_server():
    """API 서버 시작 (도커)"""
    compose_file = get_compose_file()
    
    if not compose_file.exists():
        print(f"❌ docker-compose.dev.yml 파일을 찾을 수 없습니다: {compose_file}")
        return False
    
    print("🚀 Starting API server (Docker)...")
    print("📍 API: http://localhost:8000")
    print("📚 API docs: http://localhost:8000/docs")
    print("🛑 중지하려면: api stop")
    print("-" * 50)
    
    try:
        # docker-compose로 API와 Postgres 시작
        result = subprocess.run(
            ["docker-compose", "-f", str(compose_file), "up", "-d"],
            check=False
        )
        
        if result.returncode == 0:
            print("✅ API 서버가 도커에서 시작되었습니다.")
            print("\n📋 유용한 명령어:")
            print("  api stop      - API 서버 중지")
            print("  api restart   - API 서버 재시작")
            print("  docker-compose -f docker-compose.dev.yml logs -f api  - 로그 확인")
            return True
        else:
            print("❌ API 서버 시작 실패")
            return False
            
    except FileNotFoundError:
        print("❌ docker-compose를 찾을 수 없습니다. Docker가 설치되어 있는지 확인해주세요.")
        return False
    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        return False

def stop_api_server():
    """API 서버 중지 (도커)"""
    compose_file = get_compose_file()
    
    if not compose_file.exists():
        print(f"❌ docker-compose.dev.yml 파일을 찾을 수 없습니다: {compose_file}")
        return False
    
    print("🛑 Stopping API server (Docker)...")
    
    try:
        # API만 중지 (Postgres는 유지)
        result = subprocess.run(
            ["docker-compose", "-f", str(compose_file), "stop", "api"],
            check=False
        )
        
        if result.returncode == 0:
            print("✅ API 서버가 중지되었습니다. (Postgres는 계속 실행 중)")
            return True
        else:
            print("⚠️ API 서버 중지 중 오류 발생 (이미 중지되었을 수 있음)")
            return False
            
    except FileNotFoundError:
        print("❌ docker-compose를 찾을 수 없습니다.")
        return False

def restart_api_server():
    """API 서버 재시작 (도커)"""
    compose_file = get_compose_file()
    
    if not compose_file.exists():
        print(f"❌ docker-compose.dev.yml 파일을 찾을 수 없습니다: {compose_file}")
        return False
    
    print("🔄 Restarting API server (Docker)...")
    
    try:
        # API만 재시작
        result = subprocess.run(
            ["docker-compose", "-f", str(compose_file), "restart", "api"],
            check=False
        )
        
        if result.returncode == 0:
            print("✅ API 서버가 재시작되었습니다.")
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
        command = sys.argv[1].lower()
        if command == "restart":
            restart_api_server()
        elif command == "stop":
            stop_api_server()
        else:
            print(f"❌ 알 수 없는 명령어: {command}")
            print("사용법: api [start|restart|stop]")
    else:
        start_api_server()

if __name__ == "__main__":
    main()
