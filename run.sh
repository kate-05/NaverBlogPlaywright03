#!/bin/bash
# 네이버 블로그 크롤러 실행 스크립트 (Linux/Mac/Git Bash)
# 가상환경 활성화 후 실행

echo "===================================="
echo "네이버 블로그 크롤러 실행"
echo "===================================="

# 가상환경 활성화
source venv/Scripts/activate

if [ $? -ne 0 ]; then
    echo "오류: 가상환경 활성화 실패"
    echo "venv 폴더가 있는지 확인하세요."
    exit 1
fi

# Playwright 확인
python -c "import playwright" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "Playwright가 설치되지 않았습니다."
    echo "설치 중..."
    pip install -r requirements.txt
    playwright install chromium
fi

# GUI 실행
python main.py

