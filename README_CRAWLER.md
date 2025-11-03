# 네이버 블로그 크롤러

네이버 블로그의 모바일 버전을 활용하여 특정 블로그의 모든 포스트를 체계적으로 수집하는 자동화 크롤러입니다.

## 주요 기능

### ✅ 2단계 크롤링 전략
- **Phase 1: 링크 수집**: 전체글 갯수 확인 → 스크롤 → 모든 링크 추출
- **Phase 2: 상세 크롤링**: 각 링크 순회 → 상세 데이터 수집

### ✅ 데이터 수집
- **기본 정보**: post_id, title, url, author, published_date
- **메타데이터**: views, likes, comments, category, tags
- **본문 내용**: html, text, markdown, word_count, images, links
- **해시태그**: 확장 버튼 클릭 후 모든 해시태그 수집
- **댓글**: 댓글 버튼 클릭 후 모든 댓글 수집

### ✅ GUI 인터페이스
- 메인 화면: 입력 방법 선택, 재개 옵션, 설정 요약
- 진행 상황 화면: 프로그레스 바, 실시간 로그, 중단 버튼
- 결과 화면: 결과 요약, 파일 경로, 폴더 열기

### ✅ 중단 및 재개 기능
- 사용자 중단 처리 (현재까지 데이터 저장)
- 체크포인트 자동 저장 (N개 포스트마다, 기본값: 10개)
- 체크포인트 파일로 재개

### ✅ 배치 처리
- 다중 블로그 ID 처리
- 통합 결과 파일 생성
- 중복 제거 (URL, Post ID 기준)

## 설치 방법

### 1. Python 가상환경 활성화
```bash
# Windows
venv\Scripts\activate

# Linux/Mac
source venv/bin/activate
```

### 2. Python 패키지 설치
```bash
pip install -r requirements.txt
```

### 3. Playwright 브라우저 설치
```bash
playwright install chromium
```

## 실행 방법

### GUI 모드로 실행
```bash
python main.py
```

## 사용 방법

### 1. 단일 블로그 크롤링
1. "단일 블로그 ID 입력" 선택
2. 블로그 ID 입력 (예: `koding2002`)
3. "크롤링 시작" 버튼 클릭

### 2. 다중 블로그 크롤링
1. "파일로 여러 블로그 ID 업로드" 선택
2. 블로그 ID가 한 줄에 하나씩 있는 텍스트 파일 선택
3. "크롤링 시작" 버튼 클릭

### 3. 중단된 크롤링 재개
1. "중단된 크롤링 재개" 체크
2. 체크포인트 파일 선택 (`checkpoints/` 폴더)
3. "크롤링 시작" 버튼 클릭

## 출력 형식

결과는 JSON 형식으로 `output/` 디렉토리에 저장됩니다.

```json
{
  "crawl_info": {
    "crawl_type": "blog_id",
    "total_blog_ids": 1,
    "processed_blog_ids": 1,
    "total_posts": 150,
    "crawl_date": "2025-01-03T12:00:00"
  },
  "posts": [
    {
      "post_id": "224048062846",
      "title": "포스트 제목",
      "author": {
        "blog_id": "koding2002",
        "nickname": "작성자 닉네임"
      },
      "published_date": "2025. 01. 01.",
      "url": "https://m.blog.naver.com/...",
      "metadata": {
        "views": 100,
        "likes": 10,
        "comments": 5,
        "tags": ["태그1", "태그2"]
      },
      "content": {
        "text": "본문 텍스트...",
        "word_count": 500,
        "images": ["url1", "url2"],
        "links": ["url1", "url2"]
      },
      "comments": [
        {
          "author": "댓글 작성자",
          "content": "댓글 내용",
          "date": "2025. 01. 01. 12:00",
          "likes": 0
        }
      ]
    }
  ]
}
```

## 프로젝트 구조

```
NaverBlogPlaywright03/
├── src/
│   ├── crawler/
│   │   ├── engine.py          # 크롤링 엔진 (2단계 크롤링)
│   │   ├── parser.py          # HTML 파싱 (해시태그, 댓글, 본문)
│   │   └── batch_crawler.py   # 배치 처리
│   ├── gui/
│   │   └── main_window.py     # GUI 메인 윈도우
│   ├── utils/
│   │   ├── checkpoint_manager.py  # 체크포인트 관리
│   │   ├── file_exporter.py       # 파일 출력
│   │   └── exceptions.py          # 예외 처리
│   └── models.py              # 데이터 모델
├── output/                    # 결과 파일 출력 디렉토리
├── checkpoints/               # 체크포인트 파일 저장 디렉토리
├── logs/                      # 로그 파일 디렉토리
├── main.py                    # 메인 실행 파일
└── requirements.txt           # Python 의존성
```

## 설정

### 저장 간격 변경
- 메인 화면에서 "설정 변경" 버튼 클릭
- 저장 간격 조정 (1~100개 포스트마다, 기본값: 10개)

## 주의사항

1. **이용약관 준수**: 네이버 블로그 이용약관을 준수하세요
2. **요청 간 딜레이**: 기본 0.5초 딜레이를 유지하세요 (서버 부하 방지)
3. **개인정보 보호**: 수집된 데이터의 개인정보 보호 책임은 사용자에게 있습니다

## 참고 문서

- `Documents/PRD_NaverBlogCrawler_Current.md`: 제품 요구사항 문서
- `Documents/DETAILED_FUNCTIONAL_SPEC_Current.md`: 기능상세명세서
- `Documents/UI_UX_SPEC_Current.md`: UI/UX 명세서
- `Documents/DEVELOPMENT_PLAN_Current.md`: 개발 계획서

## 라이선스

ISC

