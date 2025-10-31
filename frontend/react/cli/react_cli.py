#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
React 개발 서버 CLI 스크립트
Usage: python -m frontend.react.cli
"""

import os
import sys
import subprocess
from pathlib import Path

def main():
    """React 개발 서버 실행"""
    # frontend/react 디렉토리로 이동
    react_dir = Path(__file__).parent.parent
    os.chdir(react_dir)
    
    print("🚀 Starting React development server...")
    print("📍 Frontend: http://localhost:3000")
    print("🛑 Press Ctrl+C to stop")
    print("-" * 50)
    
    try:
        # Windows에서 npm이 PowerShell 스크립트인 경우를 위해 shell=True 사용
        subprocess.run(["npm", "run", "dev"], shell=True)
    except KeyboardInterrupt:
        print("\n🛑 React server stopped")
    except FileNotFoundError:
        print("❌ npm을 찾을 수 없습니다. Node.js가 설치되어 있는지 확인해주세요.")
        print("설치 방법: https://nodejs.org/")

if __name__ == "__main__":
    main()
