#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
React 개발 서버 CLI 메인 엔트리 포인트
Usage: python -m frontend.react.cli
"""

import sys
from pathlib import Path

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent.parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from frontend.react.cli.react_cli import main

if __name__ == "__main__":
    main()
