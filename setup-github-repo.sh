#!/bin/bash
# 현재 폴더 이름으로 GitHub 저장소를 자동 생성하고 연결하는 스크립트

# 현재 폴더 이름 가져오기
REPO_NAME=$(basename "$PWD")

echo "======================================"
echo "GitHub 저장소 자동 설정"
echo "======================================"
echo "저장소 이름: $REPO_NAME"
echo ""

# GitHub CLI 로그인 확인
if ! gh auth status &> /dev/null; then
    echo "⚠️  GitHub CLI에 로그인이 필요합니다."
    echo "로그인을 진행합니다..."
    gh auth login
fi

# 저장소 생성
echo "📦 GitHub 저장소 생성 중..."
gh repo create "$REPO_NAME" --public --source=. --remote=origin --push 2>&1

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ 저장소가 성공적으로 생성되고 연결되었습니다!"
    echo "🔗 저장소 URL: https://github.com/$(gh api user --jq .login)/$REPO_NAME"
else
    echo ""
    echo "⚠️  저장소 생성 중 오류가 발생했습니다."
    echo "이미 존재하는 저장소일 수 있습니다."
    echo ""
    echo "원격 저장소를 수동으로 연결하려면:"
    echo "  git remote add origin https://github.com/$(gh api user --jq .login)/$REPO_NAME.git"
    echo "  git branch -M main"
    echo "  git push -u origin main"
fi

