#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Real Estate for the Young - 환경 설정 스크립트
새로운 환경에서 원활하게 실행할 수 있도록 설정
"""

import os
import sys
import subprocess
from pathlib import Path

def main():
    """환경 설정 메인 함수"""
    print("🏠 Real Estate for the Young - 환경 설정")
    print("=" * 50)
    
    # 1. 환경 변수 파일 생성
    setup_env_file()
    
    # 2. Python 의존성 설치
    install_dependencies()
    
    # 3. Node.js 의존성 설치
    install_frontend_dependencies()
    
    # 4. 설정 완료 안내
    print_completion_guide()

def setup_env_file():
    """환경 변수 파일 설정"""
    print("\n📝 환경 변수 파일 설정 중...")
    
    env_file = Path(".env")
    env_example = Path("env.example")
    
    if not env_file.exists() and env_example.exists():
        # .env 파일이 없으면 env.example을 복사
        import shutil
        shutil.copy(env_example, env_file)
        print("✅ .env 파일이 생성되었습니다.")
        print("⚠️  .env 파일에서 API 키를 설정해주세요:")
        print("   - GROQ_API_KEY: Groq API 키")
        print("   - OPENAI_API_KEY: OpenAI API 키 (선택사항)")
    elif env_file.exists():
        print("✅ .env 파일이 이미 존재합니다.")
    else:
        print("❌ env.example 파일을 찾을 수 없습니다.")

def install_dependencies():
    """Python 의존성 설치"""
    print("\n🐍 Python 의존성 설치 중...")
    
    try:
        # uv를 사용하여 의존성 설치
        subprocess.run(["uv", "sync"], check=True)
        print("✅ Python 의존성 설치 완료")
    except subprocess.CalledProcessError:
        print("❌ uv 설치 실패, pip 사용 시도...")
        try:
            subprocess.run([sys.executable, "-m", "pip", "install", "-r", "backend/requirements.txt"], check=True)
            print("✅ Python 의존성 설치 완료 (pip)")
        except subprocess.CalledProcessError:
            print("❌ Python 의존성 설치 실패")
            print("수동으로 설치해주세요: pip install -r backend/requirements.txt")

def install_frontend_dependencies():
    """Node.js 의존성 설치"""
    print("\n📦 Frontend 의존성 설치 중...")
    
    frontend_dir = Path("frontend")
    if not frontend_dir.exists():
        print("❌ frontend 디렉토리를 찾을 수 없습니다.")
        return
    
    try:
        subprocess.run(["npm", "install"], cwd=frontend_dir, check=True)
        print("✅ Frontend 의존성 설치 완료")
    except subprocess.CalledProcessError:
        print("❌ Frontend 의존성 설치 실패")
        print("수동으로 설치해주세요: cd frontend && npm install")

def print_completion_guide():
    """설정 완료 안내"""
    print("\n🎉 환경 설정 완료!")
    print("=" * 50)
    print("\n📋 다음 단계:")
    print("1. .env 파일에서 API 키 설정:")
    print("   - GROQ_API_KEY: 필수")
    print("   - OPENAI_API_KEY: 선택사항")
    print("\n2. 데이터베이스 설정 (선택사항):")
    print("   python cli.py db create")
    print("\n3. 개발 서버 실행:")
    print("   python cli.py dev    # API + Frontend 동시 실행")
    print("   python cli.py api    # API만 실행")
    print("   python cli.py frontend  # Frontend만 실행")
    print("\n4. 접속 주소:")
    print("   - API: http://localhost:8000")
    print("   - Frontend: http://localhost:3000")
    print("   - API 문서: http://localhost:8000/docs")

if __name__ == "__main__":
    main()
