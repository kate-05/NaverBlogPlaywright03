"""
네이버 블로그 크롤러 메인 실행 파일
"""
import sys
from pathlib import Path

# 프로젝트 루트를 path에 추가
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.gui.main_window import main

if __name__ == "__main__":
    main()

