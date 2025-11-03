@echo off
REM 네이버 블로그 크롤러 실행 스크립트 (Windows)
REM 가상환경 활성화 후 실행

echo ====================================
echo 네이버 블로그 크롤러 실행
echo ====================================

REM 가상환경 활성화
call venv\Scripts\activate.bat

if errorlevel 1 (
    echo 오류: 가상환경 활성화 실패
    echo venv 폴더가 있는지 확인하세요.
    pause
    exit /b 1
)

REM Playwright 확인
python -c "import playwright" >nul 2>&1
if errorlevel 1 (
    echo Playwright가 설치되지 않았습니다.
    echo 설치 중...
    pip install -r requirements.txt
    playwright install chromium
)

REM GUI 실행
python main.py

pause

