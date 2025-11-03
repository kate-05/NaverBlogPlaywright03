@echo off
REM 현재 폴더 이름으로 GitHub 저장소를 자동 생성하고 연결하는 스크립트

echo ======================================
echo GitHub 저장소 자동 설정
echo ======================================

REM 현재 폴더 이름 가져오기
for %%F in (.) do set REPO_NAME=%%~nxF

echo 저장소 이름: %REPO_NAME%
echo.

REM GitHub CLI 로그인 확인
gh auth status >nul 2>&1
if errorlevel 1 (
    echo ⚠️  GitHub CLI에 로그인이 필요합니다.
    echo 로그인을 진행합니다...
    gh auth login
)

REM 저장소 생성
echo 📦 GitHub 저장소 생성 중...
gh repo create %REPO_NAME% --public --source=. --remote=origin --push

if errorlevel 1 (
    echo.
    echo ⚠️  저장소 생성 중 오류가 발생했습니다.
    echo 이미 존재하는 저장소일 수 있습니다.
) else (
    echo.
    echo ✅ 저장소가 성공적으로 생성되고 연결되었습니다!
)

pause

