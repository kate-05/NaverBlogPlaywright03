# Naver Blog Playwright Test Project

Playwright를 사용한 Naver Blog 테스트 프로젝트입니다.

## 환경 설정

### 필요한 소프트웨어
- Node.js (v18 이상 권장)
- Google Chrome

### 설치 방법

1. 의존성 설치:
```bash
npm install
```

2. Playwright 브라우저 설치:
```bash
npx playwright install chromium
```

## 실행 방법

### 일반 테스트 (headful 모드)
```bash
npm test
```

### Headed 모드 (브라우저 창 표시)
```bash
npm run test:headed
```

### UI 모드
```bash
npm run test:ui
```

### 디버그 모드
```bash
npm run test:debug
```

## 프로젝트 구조

```
.
├── tests/              # 테스트 파일
│   └── example.spec.js
├── playwright.config.js # Playwright 설정
├── package.json        # 프로젝트 설정
└── README.md          # 프로젝트 문서
```

## 설정

현재 프로젝트는 Chrome 브라우저를 headful 모드(headless: false)로 실행하도록 설정되어 있습니다.
설정 파일: `playwright.config.js`

## 참고 사항

- 테스트는 Windows 11 환경에서 작성되었습니다.
- Chrome 브라우저를 기본으로 사용합니다.
- Playwright Test For VSCode 익스텐션과 호환됩니다.

