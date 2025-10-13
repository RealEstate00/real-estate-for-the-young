#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
API 서버 CLI 스크립트
Usage: 
  python -m backend.services.api.cli          # API 서버 시작
  python -m backend.services.api.cli restart  # API 서버 재시작
"""

import os
import sys
import subprocess
import signal
import time
from pathlib import Path
from dotenv import load_dotenv

def kill_api_processes():
    """기존 API 프로세스들을 종료"""
    print("🔄 기존 API 프로세스 종료 중...")
    
    try:
        # 포트 8000을 사용하는 프로세스 찾기
        result = subprocess.run(['lsof', '-ti:8000'], capture_output=True, text=True)
        if result.stdout.strip():
            pids = result.stdout.strip().split('\n')
            for pid in pids:
                if pid:
                    print(f"  - PID {pid} 종료 중...")
                    os.kill(int(pid), signal.SIGTERM)
                    time.sleep(1)
                    # 강제 종료가 필요한 경우
                    try:
                        os.kill(int(pid), signal.SIGKILL)
                    except ProcessLookupError:
                        pass  # 이미 종료됨
        
        # python -m backend.services.api.cli 프로세스 찾기
        result = subprocess.run(['pgrep', '-f', 'python -m backend.services.api.cli'], capture_output=True, text=True)
        if result.stdout.strip():
            pids = result.stdout.strip().split('\n')
            for pid in pids:
                if pid:
                    print(f"  - API CLI PID {pid} 종료 중...")
                    os.kill(int(pid), signal.SIGTERM)
                    time.sleep(1)
                    try:
                        os.kill(int(pid), signal.SIGKILL)
                    except ProcessLookupError:
                        pass
        
        print("✅ 기존 프로세스 종료 완료")
        time.sleep(2)
        
    except Exception as e:
        print(f"⚠️ 프로세스 종료 중 오류: {e}")

def start_api_server():
    """API 서버 시작"""
    # 프로젝트 루트로 이동
    project_root = Path(__file__).parent.parent.parent.parent.parent
    os.chdir(project_root)
    
    # 환경 변수 로드
    load_dotenv()
    
    print("🚀 Starting API server...")
    print("📍 API: http://localhost:8000")
    print("📚 API docs: http://localhost:8000/docs")
    print("🛑 Press Ctrl+C to stop")
    print("-" * 50)
    
    try:
        subprocess.run([
            sys.executable, "-m", "uvicorn", 
            "backend.services.api.app:app", 
            "--reload", 
            "--host", "0.0.0.0", 
            "--port", "8000"
        ])
    except KeyboardInterrupt:
        print("\n🛑 API server stopped")

def restart_api_server():
    """API 서버 재시작"""
    print("=" * 50)
    print("🔄 API 서버 재시작")
    print("=" * 50)
    
    # 1. 기존 프로세스 종료
    kill_api_processes()
    
    # 2. 새로운 API 서버 시작
    start_api_server()

def main():
    """메인 함수"""
    if len(sys.argv) > 1 and sys.argv[1] == "restart":
        restart_api_server()
    else:
        start_api_server()

if __name__ == "__main__":
    main()
