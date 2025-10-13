#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
개발 모드 실행 스크립트 (API + React 동시 실행)
Usage: python dev.py
"""

import os
import sys
import subprocess
import threading
import time
from pathlib import Path
from dotenv import load_dotenv

def run_api():
    """API 서버 실행"""
    project_root = Path(__file__).parent
    os.chdir(project_root)
    load_dotenv()
    
    subprocess.run([
        sys.executable, "-m", "backend.services.api.cli"
    ])

def run_react():
    """React 개발 서버 실행"""
    project_root = Path(__file__).parent
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
    """개발 모드 실행"""
    print("🚀 Starting Development Mode...")
    print("📍 API: http://localhost:8000")
    print("📍 Frontend: http://localhost:3000")
    print("🛑 Press Ctrl+C to stop both")
    print("-" * 50)
    
    try:
        # API 서버를 백그라운드에서 실행
        api_thread = threading.Thread(target=run_api, daemon=True)
        api_thread.start()
        
        # 잠시 대기 후 React 실행
        print("⏳ Starting API server...")
        time.sleep(3)
        print("⏳ Starting React server...")
        run_react()
    except KeyboardInterrupt:
        print("\n🛑 Development mode stopped")

if __name__ == "__main__":
    main()
