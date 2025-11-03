# 네이버 블로그 크롤러 기능상세명세서
## 현재 완성된 버전 기준

**문서 버전**: 1.0  
**작성일**: 2025-01-03  
**최종 업데이트**: 2025-01-03

---

## 목차

1. [개요](#1-개요)
2. [블로그 ID 기반 크롤링](#2-블로그-id-기반-크롤링)
3. [링크 수집 (Phase 1)](#3-링크-수집-phase-1)
4. [상세 크롤링 (Phase 2)](#4-상세-크롤링-phase-2)
5. [데이터 파싱](#5-데이터-파싱)
6. [GUI 인터페이스](#6-gui-인터페이스)
7. [체크포인트 관리](#7-체크포인트-관리)
8. [배치 처리](#8-배치-처리)
9. [파일 출력](#9-파일-출력)
10. [에러 처리](#10-에러-처리)

---

## 1. 개요

### 1.1 문서 목적
이 문서는 네이버 블로그 크롤러의 각 기능에 대한 상세한 명세를 제공합니다. 각 기능의 동작 방식, 입력/출력, 알고리즘, 예외 처리 등을 기술합니다.

### 1.2 용어 정의
- **블로그 ID**: 네이버 블로그의 고유 식별자 (예: `koding2002`)
- **포스트 ID**: 블로그 내 개별 포스트의 고유 식별자 (예: `224048062846`)
- **체크포인트**: 크롤링 진행 상황을 저장한 JSON 파일
- **Phase 1**: 링크 수집 단계
- **Phase 2**: 상세 크롤링 단계

### 1.3 시스템 아키텍처
```
[GUI Layer]
    ↓
[Batch Crawler] → [Engine] → [Parser]
    ↓              ↓           ↓
[Checkpoint Manager]  [Playwright]  [Data Models]
    ↓
[File Exporter]
```

---
## 2. 블로그 ID 기반 크롤링

### 2.1 기능 개요
블로그 ID를 입력받아 해당 블로그의 모든 포스트를 수집하는 핵심 기능입니다.

### 2.2 함수 명세

#### 2.2.1 `crawl_by_blog_id()`

**함수 시그니처**
```python
def crawl_by_blog_id(
    blog_id: str,
    max_posts: Optional[int] = None,
    start_date: Optional[datetime] = None,
    delay: float = 0.5,
    timeout: int = 30,
    should_stop: Optional[Callable[[], bool]] = None
) -> Tuple[Dict, List[Post]]
```

**입력 파라미터**
- `blog_id` (str, 필수): 크롤링할 블로그 ID
  - 형식: 영문자, 숫자, 언더스코어, 하이픈 조합
  - 예시: `koding2002`, `redmin92`
- `max_posts` (Optional[int]): 최대 수집 포스트 수
  - 기본값: `None` (전체 수집)
  - 제한: 양수
- `start_date` (Optional[datetime]): 수집 시작 날짜
  - 기본값: `None` (전체 수집)
  - 필터링: 이 날짜 이후 포스트만 수집
- `delay` (float): 요청 간 딜레이 (초)
  - 기본값: `0.5`
  - 최소값: `0.5`
  - 목적: 서버 부하 방지
- `timeout` (int): 페이지 로딩 타임아웃 (초)
  - 기본값: `30`
  - 범위: 10~300
- `should_stop` (Optional[Callable]): 중단 확인 콜백 함수
  - 기본값: `None`
  - 반환값: `True`면 중단, `False`면 계속

**출력**
- `Tuple[Dict, List[Post]]`:
  - `Dict`: 블로그 메타데이터
    ```python
    {
        'blog_id': str,
        'blog_name': str,
        'blog_description': Optional[str],
        'author_nickname': str,
        'total_posts': Optional[int],
        'created_at': Optional[datetime]
    }
    ```
  - `List[Post]`: 수집된 포스트 목록

**동작 흐름**
```
1. 입력값 검증
   ├─ blog_id 형식 검증
   ├─ delay ≥ 0.5 확인
   └─ timeout 범위 확인

2. 브라우저 초기화
   ├─ Playwright 시작
   ├─ 모바일 디바이스 설정 (iPhone 12)
   └─ 브라우저 컨텍스트 생성

3. 블로그 메인 페이지 접속
   ├─ URL: https://m.blog.naver.com/{blog_id}
   ├─ 페이지 로딩 대기
   └─ 블로그 존재 여부 확인

4. 블로그 메타데이터 수집
   └─ extract_blog_info() 호출

5. 포스트 목록 페이지 접속
   ├─ URL: https://m.blog.naver.com/PostList.naver?blogId={blog_id}
   └─ 페이지 로딩 대기 (5초)

6. Phase 1: 링크 수집
   └─ _collect_all_post_links() 호출

7. should_stop 확인
   ├─ True → 브라우저 종료, 현재까지 결과 반환
   └─ False → 계속

8. Phase 2: 상세 크롤링
   └─ 각 링크에 대해 crawl_post_detail_mobile() 호출

9. 브라우저 종료 및 결과 반환
```

**예외 처리**
- `ValueError`: 잘못된 입력값
- `BlogNotFoundError`: 블로그를 찾을 수 없음
- `TimeoutError`: 페이지 로딩 타임아웃
- `NetworkError`: 네트워크 오류

**사용 예시**
```python
from src.crawler.engine import crawl_by_blog_id

# 전체 포스트 수집
blog_info, posts = crawl_by_blog_id(
    blog_id='koding2002',
    delay=0.5,
    timeout=30
)

# 최대 100개 포스트만 수집
blog_info, posts = crawl_by_blog_id(
    blog_id='koding2002',
    max_posts=100,
    delay=0.5
)

# 중단 콜백 사용
def should_stop():
    return user_requested_stop

blog_info, posts = crawl_by_blog_id(
    blog_id='koding2002',
    should_stop=should_stop
)
```

---## 3. 링크 수집 (Phase 1)

### 3.1 기능 개요
포스트 목록 페이지에서 모든 포스트 링크를 수집하는 단계입니다. 전체글 갯수를 확인하고, 스크롤을 통해 모든 링크를 수집합니다.

### 3.2 함수 명세

#### 3.2.1 `_collect_all_post_links()`

**함수 시그니처**
```python
def _collect_all_post_links(
    page: Page,
    blog_id: str,
    max_posts: Optional[int] = None,
    timeout: int = 30
) -> List[str]
```

**입력 파라미터**
- `page` (Page): Playwright Page 객체 (목록 페이지에 있어야 함)
- `blog_id` (str): 블로그 ID
- `max_posts` (Optional[int]): 최대 수집 포스트 수
- `timeout` (int): 타임아웃 (초)

**출력**
- `List[str]`: 수집된 포스트 URL 목록 (순서 보장)

**동작 흐름**

**단계 1: 전체글 갯수 확인**
```
1. 현재 페이지 URL 저장
   └─ 원래 페이지로 돌아오기 위해

2. 전체글 버튼 찾기
   ├─ 선택자 시도:
   │  ├─ button[data-click-area="pls.sort"]
   │  ├─ button.link__dkflP
   │  ├─ button:has-text("전체글")
   │  └─ button:has(span:text("전체글"))
   └─ 찾으면 클릭, 못 찾으면 경고 로그

3. 전체글 갯수 추출
   ├─ 요소: em.num_area__d8SvC
   ├─ 텍스트에서 숫자 추출 (정규식)
   └─ 저장: total_post_count

4. 닫기 버튼 클릭하여 원래 페이지로 복귀
   ├─ 선택자: button.btn__PPrNT[aria-label="닫기"]
   ├─ 클릭 후 2초 대기
   └─ 실패 시 URL로 복귀 시도
```

**단계 2: 스크롤 다운**
```
초기화:
- scroll_count = 0
- no_change_count = 0
- no_change_threshold = 3

while True:
    1. scroll_count 증가
    
    2. 스크롤 전 높이 측정
       └─ old_height = page.evaluate('document.body.scrollHeight')
    
    3. 맨 아래까지 스크롤
       └─ page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
    
    4. 최소 대기 (0.2초)
       └─ time.sleep(0.2)  # 콘텐츠 로딩 확보
    
    5. 스크롤 후 높이 측정
       └─ new_height = page.evaluate('document.body.scrollHeight')
    
    6. 높이 비교
       ├─ new_height == old_height:
       │  ├─ no_change_count 증가
       │  ├─ no_change_count >= 3:
       │  │  ├─ 최종 안정화 확인 (1초 대기)
       │  │  ├─ final_height 측정
       │  │  ├─ final_height == old_height:
       │  │  │  └─ break (스크롤 종료)
       │  │  └─ final_height != old_height:
       │  │     └─ no_change_count = 0 (리셋)
       │  └─ no_change_count < 3:
       │     └─ 0.3초 대기 후 계속
       └─ new_height != old_height:
          ├─ 높이 변화 감지 로그
          └─ no_change_count = 0 (리셋)
```

**단계 3: 링크 수집**
```
JavaScript 코드 실행:

1. 타겟 컨테이너 찾기
   ├─ XPath: /html/body/div[1]/div[5]/div[2]/div[3]
   └─ XPath: /html/body/div[1]/div[5]/div[4]

2. 각 컨테이너 내에서:
   ├─ ul 요소 찾기
   ├─ 각 ul 내 li 요소 찾기
   ├─ 각 li 내 div:nth-child(1), div:nth-child(2) 찾기
   └─ 각 div 내 a[href] 요소에서 링크 추출

3. 링크 필터링
   ├─ PostView 또는 logNo 포함 확인
   ├─ blog_id 매칭 확인
   └─ 상대 경로를 절대 경로로 변환

4. 중복 제거
   ├─ URL 기준 중복 제거
   └─ Post ID 기준 중복 제거

5. 목록 반환
```

**알고리즘 상세**

**스크롤 최적화 알고리즘**
```python
# 의사코드
no_change_count = 0
no_change_threshold = 3

while True:
    old_height = get_page_height()
    scroll_to_bottom()
    sleep(0.2)  # 최소 대기
    new_height = get_page_height()
    
    if new_height == old_height:
        no_change_count += 1
        if no_change_count >= threshold:
            sleep(1)  # 최종 안정화 확인
            final_height = get_page_height()
            if final_height == old_height:
                break  # 완전히 안정화됨
            else:
                no_change_count = 0  # 재변화 감지, 리셋
        else:
            sleep(0.3)  # 추가 확인
    else:
        no_change_count = 0  # 변화 있음, 리셋
```

**링크 수집 JavaScript 알고리즘**
```javascript
// 의사코드
function collectLinks(blogId) {
    const links = [];
    const blogIdPattern = new RegExp('blogId=' + blogId, 'i');
    
    // 컨테이너 찾기
    const containers = [
        '/html/body/div[1]/div[5]/div[2]/div[3]',
        '/html/body/div[1]/div[5]/div[4]'
    ];
    
    for (container of containers) {
        const element = document.evaluate(container, ...);
        if (element) {
            const ulElements = element.querySelectorAll('ul');
            for (ul of ulElements) {
                const listItems = ul.querySelectorAll('li');
                for (li of listItems) {
                    const div1 = li.querySelector('div:nth-child(1)');
                    const div2 = li.querySelector('div:nth-child(2)');
                    
                    for (div of [div1, div2]) {
                        if (div) {
                            const links_in_div = div.querySelectorAll('a[href]');
                            for (a of links_in_div) {
                                const href = a.getAttribute('href');
                                if (href && (href.includes('PostView') || href.includes('logNo'))) {
                                    const fullUrl = normalizeUrl(href);
                                    if (blogIdPattern.test(fullUrl)) {
                                        links.push(fullUrl);
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }
    
    return [...new Set(links)];  // 중복 제거
}
```

**성능 특성**
- **시간 복잡도**: O(n) where n = 포스트 수
- **공간 복잡도**: O(n) where n = 포스트 수
- **예상 시간**: 
  - 작은 블로그 (< 50 포스트): 약 10~20초
  - 중간 블로그 (50~200 포스트): 약 30~60초
  - 큰 블로그 (> 200 포스트): 약 1~3분

**예외 처리**
- 전체글 버튼을 찾지 못함: 경고 로그 후 계속 진행
- 전체글 갯수를 추출하지 못함: 경고 로그 후 계속 진행
- 닫기 버튼을 찾지 못함: URL로 복귀 시도
- 스크롤 중 높이 측정 실패: 예외 로그 후 재시도

**로깅**
```
[단계] === Phase 1: 링크 수집 시작 ===
[단계] === 1단계: 전체글 갯수 확인 (먼저) ===
[단계] 전체글 버튼 클릭하여 전체글 갯수 확인 중...
[단계] 전체글 갯수 확인: 187개
[단계] 닫기 버튼 클릭 완료 - 원래 페이지로 복귀
[단계] === 2단계: 스크롤 다운하여 전체 글 갯수와 링크 확인 ===
[단계] 목표: 187개 링크 수집
[단계] 스크롤을 빠르게 끝까지 진행 중... (높이 변화가 없을 때까지)
[단계] 스크롤 반복 1
[단계] 높이 변화 감지: 3000 → 4500px (+1500px) - 계속 스크롤
[단계] 스크롤 반복 2
[단계] 높이 변화 없음 (8000px) - 안정화 확인 중... (1/3)
[단계] 높이 변화 없음 (8000px) - 안정화 확인 중... (2/3)
[단계] 높이 변화 없음 (8000px) - 안정화 확인 중... (3/3)
[단계] 스크롤 완료: 높이 안정화됨 (8000px) - 링크 수집 단계로 진행
[단계] === 3단계: 스크롤 완료, 글 목록에서 링크 수집 ===
[단계] 페이지에서 187개 링크 발견
[단계] 새 링크 187개 추가 (총 187개)
[단계] ✓ 전체글 갯수(187개)와 링크 수(187개) 매칭!
[단계] === Phase 1 완료: 총 187개 링크 수집 ===
```

---## 4. 상세 크롤링 (Phase 2)

### 4.1 기능 개요
수집된 링크를 순회하며 각 포스트의 상세 정보를 수집하는 단계입니다.

### 4.2 함수 명세

#### 4.2.1 `crawl_post_detail_mobile()`

**함수 시그니처**
```python
def crawl_post_detail_mobile(
    page: Page,
    post_url: str,
    timeout: int = 30,
    blog_id: str = None
) -> Post
```

**입력 파라미터**
- `page` (Page): Playwright Page 객체
- `post_url` (str): 포스트 URL
- `timeout` (int): 타임아웃 (초)
- `blog_id` (str, 선택): 블로그 ID (없으면 URL에서 추출)

**출력**
- `Post`: 포스트 데이터 객체

**동작 흐름**
```
초기화:
- max_retries = 3

for attempt in range(max_retries):
    1. 페이지 상태 확인
       ├─ 페이지가 닫혔는지 확인
       └─ 닫혔으면 ValueError 발생
    
    2. 포스트 페이지 접속
       ├─ page.goto(post_url, wait_until='domcontentloaded')
       ├─ 실패 시 load 시도
       └─ 1초 추가 대기
    
    3. Post ID 추출
       └─ extract_post_id_from_url(post_url)
    
    4. 제목 추출 (최대 3회 시도)
       ├─ extract_title(page)
       ├─ 실패 시 기본값: "포스트 {post_id}"
       └─ 각 시도 간 0.5초 대기
    
    5. 작성자 정보 추출
       ├─ blog_id가 없으면 URL에서 추출
       └─ extract_author(page, blog_id)
    
    6. 날짜 정보 추출
       ├─ extract_published_date(page)
       └─ extract_modified_date(page)
    
    7. 메타데이터 추출
       └─ extract_metadata(page)
    
    8. 본문 내용 추출
       └─ extract_content(page)
    
    9. 해시태그 추출 (댓글보다 먼저)
       └─ extract_tags(page)
    
    10. 메타데이터에 해시태그 추가
        └─ metadata.tags = tags
    
    11. 댓글 추출
        ├─ extract_comments(page)
        ├─ 댓글 갯수가 0 이상인데 수집 실패 시:
        │  ├─ 2초 추가 대기
        │  └─ 재시도
        └─ 최종 댓글 목록
    
    12. Post 객체 생성 및 반환
    
    예외 발생 시:
    ├─ PlaywrightTimeout:
    │  ├─ attempt < max_retries - 1:
    │  │  ├─ 2초 대기
    │  │  └─ 재시도
    │  └─ attempt == max_retries - 1:
    │     └─ TimeoutError 발생
    └─ 기타 예외:
       ├─ attempt < max_retries - 1:
       │  ├─ 2초 대기
       │  └─ 재시도
       └─ attempt == max_retries - 1:
          └─ ParsingError 발생
```

**데이터 수집 순서**
1. 메타데이터 (조회수, 좋아요, 댓글 수)
2. 본문 내용
3. 해시태그 (확장 버튼 클릭 후)
4. 댓글 (댓글 버튼 클릭 후)

**재시도 로직**
```python
# 의사코드
max_retries = 3

for attempt in range(max_retries):
    try:
        # 크롤링 시도
        return crawl_post()
    except PlaywrightTimeout:
        if attempt < max_retries - 1:
            sleep(2)
            continue  # 재시도
        else:
            raise TimeoutError("최대 재시도 횟수 초과")
    except Exception as e:
        if attempt < max_retries - 1:
            sleep(2)
            continue  # 재시도
        else:
            raise ParsingError(f"파싱 실패: {e}")
```

**예외 처리**
- `ValueError`: 유효하지 않은 URL 또는 페이지가 닫힘
- `TimeoutError`: 페이지 로딩 타임아웃 (최대 3회 재시도)
- `ParsingError`: 데이터 파싱 실패 (최대 3회 재시도)

**성능 특성**
- **평균 시간**: 2~3초/포스트
- **최대 재시도**: 3회
- **총 최대 시간**: 약 10초/포스트 (재시도 포함)

---## 5. 데이터 파싱

### 5.1 해시태그 추출

#### 5.1.1 함수 명세

**함수 시그니처**
```python
def extract_tags(page: Page) -> List[str]
```

**입력**
- `page` (Page): Playwright Page 객체 (포스트 상세 페이지)

**출력**
- `List[str]`: 해시태그 목록 (중복 제거됨)

**동작 흐름**
```
1. 해시태그 확장 버튼 찾기
   ├─ 선택자 시도 (순차):
   │  ├─ button.tag__tFC3j.expand_btn__oaNLH[data-click-area="pst.tagmore"]
   │  ├─ button.expand_btn__oaNLH[data-click-area="pst.tagmore"]
   │  ├─ button.expand_btn__oaNLH
   │  └─ button[data-click-area="pst.tagmore"]
   │
   ├─ 찾으면:
   │  ├─ scroll_into_view_if_needed()
   │  ├─ 0.5초 대기
   │  ├─ 클릭 (timeout=5초)
   │  └─ 2초 대기 (해시태그 로딩)
   └─ 못 찾으면 경고 로그

2. 해시태그 요소 추출
   ├─ 선택자 시도 (순차):
   │  ├─ a.tag__tFC3j[data-click-area="pst.tag"]
   │  ├─ a.tag__tFC3j
   │  ├─ .list_wrap__jKORt .list__yr1c8 .item__jRCnW a.tag__tFC3j
   │  ├─ .tag__tFC3j
   │  ├─ .tag-list .tag
   │  ├─ .area_tag a
   │  ├─ .se_tagList a
   │  └─ .tag-item
   │
   ├─ 각 선택자로 elements 찾기
   ├─ 각 element의 text_content() 추출
   ├─ "#" 기호 제거
   └─ 공백 제거 및 중복 제거

3. JavaScript Fallback (Playwright Locator 실패 시)
   ├─ JavaScript 코드 실행:
   │  └─ document.querySelectorAll('a.tag__tFC3j[data-click-area="pst.tag"]')
   ├─ 각 링크의 textContent 추출
   ├─ "#" 기호 제거
   └─ 중복 제거

4. 결과 반환 (중복 제거)
   └─ return list(set(tags))
```

**알고리즘 상세**
```javascript
// JavaScript Fallback 코드
() => {
    const tags = [];
    const tagLinks = document.querySelectorAll(
        'a.tag__tFC3j[data-click-area="pst.tag"], a.tag__tFC3j'
    );
    
    tagLinks.forEach(link => {
        const text = (link.textContent || link.innerText || '').trim();
        if (text) {
            const tagName = text.replace(/^#+/, '').trim();
            if (tagName && !tags.includes(tagName)) {
                tags.push(tagName);
            }
        }
    });
    
    return tags;
}
```

**예외 처리**
- 확장 버튼을 찾지 못함: 경고 로그 후 계속 진행
- 해시태그 요소를 찾지 못함: 빈 리스트 반환
- JavaScript 실행 실패: 경고 로그 후 빈 리스트 반환

---

### 5.2 댓글 추출

#### 5.2.1 함수 명세

**함수 시그니처**
```python
def extract_comments(page: Page) -> List[Comment]
```

**입력**
- `page` (Page): Playwright Page 객체 (포스트 상세 페이지)

**출력**
- `List[Comment]`: 댓글 목록

**동작 흐름**
```
1. 댓글 버튼 찾기
   ├─ 선택자 시도 (순차):
   │  ├─ button.comment_btn__TUucZ[data-click-area="pst.re"]
   │  ├─ button.comment_btn__TUucZ
   │  └─ button[data-click-area*="re"]
   │
   ├─ 찾으면:
   │  ├─ 클릭
   │  ├─ 5초 대기 (댓글 로딩)
   │  ├─ 댓글 컨테이너 찾기: .u_cbox_list, .comment_list, tabpanel
   │  └─ 추가 2초 대기 (안정화)
   └─ 못 찾으면 빈 리스트 반환

2. JavaScript 기반 댓글 수집 (우선)
   ├─ 방법 1: tabpanel ID로 찾기
   │  ├─ #naverComment_wai_u_cbox_content_wrap_tabpanel
   │  ├─ [role="tabpanel"]
   │  ├─ ul.u_cbox_list 찾기
   │  └─ li.u_cbox_comment 찾기
   │
   ├─ 방법 2: 전체 페이지에서 u_cbox_comment 찾기
   ├─ 방법 3: u_cbox_list_item으로 찾기
   │
   └─ 각 댓글 아이템에서:
      ├─ 닉네임 추출:
      │  ├─ span.u_cbox_nick (우선)
      │  ├─ a.u_cbox_name > span.u_cbox_nick
      │  └─ a 요소에서 닉네임 추출 (대체)
      │
      ├─ 내용 추출:
      │  ├─ span.u_cbox_contents (우선)
      │  └─ div.u_cbox_text_wrap > span.u_cbox_contents
      │
      ├─ 날짜 추출:
      │  ├─ .u_cbox_date, time 요소 찾기
      │  ├─ 부모 요소에서 정규식 매칭
      │  └─ 형식: YYYY.MM.DD. HH:MM
      │
      └─ 좋아요 수 추출:
         ├─ 정규식: "공감 \d+"
         ├─ .u_cbox_recomm 요소 찾기
         └─ 기본값: 0

3. Playwright Locator Fallback (JavaScript 실패 시)
   ├─ 방법 1: .u_cbox_list_item, .u_cbox_comment 찾기
   ├─ 방법 2: tabpanel listitem 찾기
   ├─ 방법 3: [class*="cbox"], [class*="comment"] 찾기
   │
   └─ 방법 4: 직접 닉네임/내용 요소 찾기
      ├─ span.u_cbox_nick 요소들 찾기
      ├─ span.u_cbox_contents 요소들 찾기
      ├─ 같은 인덱스로 매칭
      └─ 각 댓글 생성

4. Comment 객체 생성
   └─ Comment(author, content, date, likes)

5. 결과 반환
```

**JavaScript 댓글 수집 알고리즘**
```javascript
// 의사코드
function extractComments() {
    const comments = [];
    
    // 방법 1: tabpanel로 찾기
    const tabpanel = document.querySelector(
        '#naverComment_wai_u_cbox_content_wrap_tabpanel, [role="tabpanel"]'
    );
    
    let commentItems = [];
    if (tabpanel) {
        const list = tabpanel.querySelector('ul.u_cbox_list');
        if (list) {
            commentItems = list.querySelectorAll('li.u_cbox_comment');
        } else {
            commentItems = tabpanel.querySelectorAll('li.u_cbox_comment');
        }
    }
    
    // 방법 2: 전체 페이지에서 찾기
    if (commentItems.length === 0) {
        commentItems = document.querySelectorAll('li.u_cbox_comment, .u_cbox_comment');
    }
    
    // 각 댓글 처리
    commentItems.forEach(item => {
        // 닉네임 추출
        let author = '';
        const nickElem = item.querySelector('span.u_cbox_nick');
        if (nickElem) {
            author = (nickElem.textContent || '').trim();
        }
        
        // 내용 추출
        let content = '';
        const contentElem = item.querySelector('span.u_cbox_contents');
        if (contentElem) {
            content = (contentElem.textContent || '').trim();
        }
        
        // 날짜 추출
        let dateText = '';
        const itemText = item.textContent || '';
        const dateMatch = itemText.match(/\d{4}\.\d{1,2}\.\d{1,2}\.?\s+\d{1,2}:\d{2}/);
        if (dateMatch) {
            dateText = dateMatch[0];
        }
        
        // 좋아요 수 추출
        let likes = 0;
        const likesMatch = itemText.match(/공감\s+(\d+)/);
        if (likesMatch) {
            likes = parseInt(likesMatch[1], 10);
        }
        
        if (author) {
            comments.push({
                author: author,
                content: content || '',
                date: dateText,
                likes: likes
            });
        }
    });
    
    return comments;
}
```

**예외 처리**
- 댓글 버튼을 찾지 못함: 빈 리스트 반환
- 댓글이 로드되지 않음: 빈 리스트 반환
- 파싱 오류: 해당 댓글 건너뛰고 계속 진행

---### 5.3 본문 추출

#### 5.3.1 함수 명세

**함수 시그니처**
```python
def extract_content(page: Page) -> PostContent
```

**입력**
- `page` (Page): Playwright Page 객체

**출력**
- `PostContent`: 본문 내용 객체
  ```python
  PostContent(
      html: str,
      text: str,
      markdown: str,
      word_count: int,
      images: List[str],
      links: List[str]
  )
  ```

**동작 흐름**
```
1. 본문 컨테이너 찾기
   ├─ 선택자 시도 (순차):
   │  ├─ .se-main-container
   │  ├─ .post-content
   │  ├─ .area_view
   │  ├─ .post-view
   │  ├─ #postViewArea
   │  ├─ .post-view-area
   │  ├─ .se-component-content
   │  ├─ article
   │  ├─ .post_body
   │  ├─ main
   │  └─ body (마지막 수단)
   │
   ├─ 찾으면:
   │  ├─ inner_html() 추출
   │  ├─ text_content() 추출
   │  └─ 텍스트 길이 >= 10자 확인
   └─ 못 찾거나 텍스트 < 10자:
      └─ Fallback: 전체 body에서 추출

2. 이미지 URL 추출
   ├─ 선택자:
   │  ├─ .se-image img
   │  ├─ .post-content img
   │  └─ img[src]
   │
   └─ 각 이미지에서:
      ├─ src 속성 추출
      ├─ data-src 속성 추출 (lazy loading)
      └─ 중복 제거

3. 링크 URL 추출
   ├─ 선택자:
   │  ├─ .post-content a
   │  └─ a[href]
   │
   └─ 각 링크에서:
      ├─ href 속성 추출
      ├─ 상대 경로를 절대 경로로 변환
      └─ 중복 제거

4. 마크다운 변환
   ├─ HTML → Markdown 변환 (간단한 버전)
   └─ 변환 규칙:
      ├─ h1 → #, h2 → ##, h3 → ###
      ├─ strong, b → **
      ├─ em → *
      ├─ a → [text](url)
      ├─ img → ![](url)
      └─ br, p → 줄바꿈

5. 단어 수 계산
   └─ text.split() 길이

6. PostContent 객체 생성 및 반환
```

**마크다운 변환 알고리즘**
```python
# 의사코드
def html_to_markdown(html: str) -> str:
    # 제목 변환
    html = re.sub(r'<h1[^>]*>(.*?)</h1>', r'# \1', html, flags=re.DOTALL)
    html = re.sub(r'<h2[^>]*>(.*?)</h2>', r'## \1', html, flags=re.DOTALL)
    html = re.sub(r'<h3[^>]*>(.*?)</h3>', r'### \1', html, flags=re.DOTALL)
    
    # 강조 변환
    html = re.sub(r'<strong[^>]*>(.*?)</strong>', r'**\1**', html, flags=re.DOTALL)
    html = re.sub(r'<b[^>]*>(.*?)</b>', r'**\1**', html, flags=re.DOTALL)
    html = re.sub(r'<em[^>]*>(.*?)</em>', r'*\1*', html, flags=re.DOTALL)
    
    # 링크 변환
    html = re.sub(r'<a[^>]*href="([^"]*)"[^>]*>(.*?)</a>', r'[\2](\1)', html, flags=re.DOTALL)
    
    # 이미지 변환
    html = re.sub(r'<img[^>]*src="([^"]*)"[^>]*>', r'![](\1)', html)
    
    # 줄바꿈 변환
    html = re.sub(r'<br[^>]*>', '\n', html)
    html = re.sub(r'<p[^>]*>', '\n', html)
    html = re.sub(r'</p>', '\n', html)
    
    # HTML 태그 제거
    html = re.sub(r'<[^>]+>', '', html)
    
    # 공백 정리
    html = re.sub(r'\n\s*\n\s*\n', '\n\n', html)
    
    return html.strip()
```

---

### 5.4 메타데이터 추출

#### 5.4.1 함수 명세

**함수 시그니처**
```python
def extract_metadata(page: Page) -> PostMetadata
```

**출력**
- `PostMetadata`: 메타데이터 객체
  ```python
  PostMetadata(
      views: int,
      likes: int,
      comments: int,
      category: Optional[str],
      tags: List[str]  # 빈 리스트 (extract_tags에서 별도 추출)
  )
  ```

**동작 흐름**
```
1. 조회수 추출
   ├─ 선택자:
   │  ├─ .view-count
   │  ├─ .area_viewcount
   │  └─ [data-view-count]
   │
   └─ extract_number() 호출

2. 좋아요(공감) 수 추출
   ├─ 선택자:
   │  ├─ .u_likeit_text._count.num
   │  ├─ .u_likeit_text
   │  ├─ .like-count
   │  ├─ .area_likecount
   │  └─ [data-like-count]
   │
   └─ extract_number() 호출

3. 댓글 수 추출
   ├─ 선택자:
   │  ├─ .comment_btn__TUucZ .num__OVfhz
   │  ├─ .num__OVfhz
   │  ├─ .comment-count
   │  ├─ .area_commentcount
   │  └─ [data-comment-count]
   │
   └─ extract_number() 호출

4. 카테고리 추출
   ├─ 선택자:
   │  ├─ .category
   │  ├─ .area_category
   │  └─ .se_category
   │
   └─ extract_text() 호출

5. 태그는 빈 리스트로 설정
   └─ extract_tags()에서 별도로 추출

6. PostMetadata 객체 생성 및 반환
```

**extract_number() 알고리즘**
```python
# 의사코드
def extract_number(page, selectors):
    for selector in selectors:
        try:
            element = page.locator(selector).first
            if element.count() > 0:
                text = element.text_content() or ""
                numbers = re.findall(r'\d+', text.replace(',', ''))
                if numbers:
                    return int(numbers[0])
        except Exception:
            continue
    
    return 0  # 기본값
```

---
## 6. GUI 인터페이스

### 6.1 메인 화면

#### 6.1.1 화면 구성
```
┌─────────────────────────────────────────┐
│  네이버 블로그 크롤러                  │
├─────────────────────────────────────────┤
│  입력 방법 선택                         │
│  ○ 단일 블로그 ID 입력                  │
│    [_________________________]          │
│                                         │
│  또는                                   │
│                                         │
│  ○ 파일로 여러 블로그 ID 업로드        │
│    [_________________] [찾기]          │
│                                         │
├─────────────────────────────────────────┤
│  재개 옵션                              │
│  ☐ 중단된 크롤링 재개                   │
│    [_________________________] [찾기]  │
│                                         │
├─────────────────────────────────────────┤
│  현재 설정 요약                         │
│  • 저장 간격: 10개 포스트마다           │
│  • 파일 분할: 사용 안 함                │
│  • 출력 형식: JSON                     │
│                    [설정 변경]          │
│                                         │
├─────────────────────────────────────────┤
│  [크롤링 시작] [설정] [도움말] [종료]   │
└─────────────────────────────────────────┘
```

#### 6.1.2 이벤트 처리

**입력 방법 변경**
```python
def on_input_method_change():
    if input_method == 'single':
        blog_id_entry.config(state='normal')
    else:
        blog_id_entry.config(state='disabled')
```

**재개 옵션 체크**
```python
def on_resume_check():
    if resume_var.get():
        blog_id_entry.config(state='disabled')
        file_path_var.set("")
    else:
        if input_method == 'single':
            blog_id_entry.config(state='normal')
```

**입력값 검증**
```python
def validate_inputs() -> tuple:
    if resume_var.get():
        if not checkpoint_path_var.get():
            return False, "체크포인트 파일을 선택해주세요."
        if not os.path.exists(checkpoint_path_var.get()):
            return False, "체크포인트 파일이 존재하지 않습니다."
    else:
        if input_method == 'single':
            blog_id = blog_id_entry.get().strip()
            if not blog_id:
                return False, "블로그 ID를 입력해주세요."
            try:
                validate_blog_id(blog_id)
            except ValueError as e:
                return False, f"유효하지 않은 블로그 ID: {e}"
        else:
            file_path = file_path_var.get()
            if not file_path:
                return False, "파일을 선택해주세요."
            if not os.path.exists(file_path):
                return False, "파일이 존재하지 않습니다."
            try:
                load_blog_ids(file_path)
            except Exception as e:
                return False, f"파일을 읽을 수 없습니다: {e}"
    
    return True, ""
```

---

### 6.2 진행 상황 화면

#### 6.2.1 화면 구성
```
┌─────────────────────────────────────────┐
│  전체 진행 상황                         │
│  [████████████░░░░░░░] 60%              │
│  예상 완료 시간: 약 5분 남음            │
│                                         │
├─────────────────────────────────────────┤
│  로그                                   │
│  ┌───────────────────────────────────┐ │
│  │ [12:00:01] 크롤링을 시작합니다... │ │
│  │ [12:00:05] 블로그 메인 페이지 접속│ │
│  │ [12:00:10] 전체글 갯수: 187개     │ │
│  │ [12:00:15] 스크롤 진행 중...      │ │
│  │ ...                               │ │
│  └───────────────────────────────────┘ │
│                                         │
├─────────────────────────────────────────┤
│  [중단]                         [메인으로]│
└─────────────────────────────────────────┘
```

#### 6.2.2 로그 메시지 처리
```python
def log_message(message: str, error: bool = False):
    timestamp = datetime.now().strftime("%H:%M:%S")
    log_message = f"[{timestamp}] {message}\n"
    
    # 로그 텍스트 영역에 추가
    log_text.insert(tk.END, log_message)
    
    # 에러 태그 추가
    if error:
        # 에러 색상 설정
        log_text.tag_add("error", ...)
        log_text.tag_config("error", foreground="red")
    
    # 자동 스크롤
    log_text.see(tk.END)
    
    # 상태 표시줄 업데이트
    status_bar.config(text=message)
```

---

### 6.3 결과 화면

#### 6.3.1 화면 구성
```
┌─────────────────────────────────────────┐
│  크롤링 결과 요약                       │
│  ✓ 크롤링이 성공적으로 완료되었습니다! │
│                                         │
│  • 수집된 포스트: 150개                 │
│  • 출력 파일: output_20250103_120000.json│
│                                         │
├─────────────────────────────────────────┤
│  결과 파일                              │
│  파일: C:\...\output_20250103_120000.json│
│  [폴더 열기]                            │
│                                         │
├─────────────────────────────────────────┤
│  [다시 크롤링]                   [종료] │
└─────────────────────────────────────────┘
```

#### 6.3.2 중단된 경우
```
┌─────────────────────────────────────────┐
│  크롤링 결과 요약                       │
│  ⚠ 크롤링이 중단되었습니다.             │
│                                         │
│  • 수집된 포스트: 75개                  │
│  • 출력 파일: output_20250103_120000.json│
│                                         │
│  중단된 크롤링은 체크포인트 파일로     │
│  재개할 수 있습니다.                    │
│                                         │
└─────────────────────────────────────────┘
```

---## 7. 체크포인트 관리

### 7.1 체크포인트 생성

#### 7.1.1 함수 명세

**함수 시그니처**
```python
def create_checkpoint(self, job: CrawlJob) -> Path
```

**동작 흐름**
```
1. 타임스탬프 생성
   └─ YYYYMMDD_HHMMSS 형식

2. 체크포인트 ID 생성
   └─ checkpoint_id = f"batch_{timestamp}"

3. 체크포인트 파일 경로 생성
   └─ checkpoint_dir / f"{checkpoint_id}.json"

4. 체크포인트 데이터 구성
   {
       "checkpoint_id": str,
       "created_at": str (ISO format),
       "last_updated": str (ISO format),
       "crawl_type": str,
       "input_file": Optional[str],
       "total_blog_ids": int,
       "processed_blog_ids": int,
       "failed_blog_ids": int,
       "total_posts_crawled": int,
       "status": str,
       "blog_progress": List[Dict],
       "posts": []  # 초기에는 빈 리스트
   }

5. JSON 파일로 저장
   └─ ensure_ascii=False, indent=2

6. 파일 경로 반환
```

**체크포인트 파일 구조**
```json
{
  "checkpoint_id": "batch_20250103_120000",
  "created_at": "2025-01-03T12:00:00",
  "last_updated": "2025-01-03T12:05:00",
  "crawl_type": "blog_id",
  "total_blog_ids": 5,
  "processed_blog_ids": 2,
  "failed_blog_ids": 0,
  "total_posts_crawled": 150,
  "status": "running",
  "blog_progress": [
    {
      "blog_id": "koding2002",
      "status": "completed",
      "posts_crawled": 100,
      "total_posts": 100,
      "last_post_id": "224048062846",
      "last_post_url": "https://...",
      "started_at": "2025-01-03T12:00:10",
      "completed_at": "2025-01-03T12:03:00"
    },
    {
      "blog_id": "redmin92",
      "status": "in_progress",
      "posts_crawled": 50,
      "total_posts": null,
      "started_at": "2025-01-03T12:03:05"
    }
  ],
  "posts": []  // 최근 100개만 저장
}
```

---

### 7.2 체크포인트 저장 (중간 저장)

#### 7.2.1 함수 명세

**함수 시그니처**
```python
def save_checkpoint(self, job: CrawlJob, posts: List[Post]) -> None
```

**동작 흐름**
```
1. posts_since_save 증가
   └─ posts_since_save += len(posts)

2. 저장 간격 체크
   ├─ posts_since_save >= save_interval:
   │  └─ 저장 진행
   └─ 그렇지 않으면:
      └─ return (저장 안 함)

3. 기존 체크포인트 파일 로드
   ├─ 파일이 있으면:
   │  └─ JSON 로드
   └─ 파일이 없으면:
      └─ 빈 딕셔너리 사용

4. 최근 포스트 추가
   ├─ posts[-save_interval:] 추출
   ├─ Post 객체를 dict로 변환 (to_dict())
   └─ 기존 posts에 추가

5. 중복 제거
   ├─ post_id 기준으로 중복 제거
   └─ 최근 100개만 유지

6. 체크포인트 데이터 업데이트
   ├─ last_updated 갱신
   ├─ job 정보 업데이트
   ├─ blog_progress 업데이트
   └─ posts 업데이트 (최근 100개)

7. JSON 파일로 저장
   └─ 기존 파일 덮어쓰기

8. posts_since_save 리셋
   └─ posts_since_save = 0
```

**저장 간격 로직**
```python
# 의사코드
save_interval = 10  # 기본값
posts_since_save = 0

def save_checkpoint(posts):
    posts_since_save += len(posts)
    
    if posts_since_save >= save_interval:
        # 저장 로직 실행
        actual_save()
        posts_since_save = 0  # 리셋
```

---

### 7.3 체크포인트 로드

#### 7.3.1 함수 명세

**함수 시그니처**
```python
def load_checkpoint(self, checkpoint_path: str) -> CrawlJob
```

**동작 흐름**
```
1. 파일 존재 확인
   ├─ 없으면 FileNotFoundError 발생
   └─ 있으면 계속

2. JSON 파일 로드
   └─ encoding='utf-8'

3. 데이터 검증 및 기본값 설정
   ├─ crawl_type: data.get('crawl_type', 'blog_id')
   ├─ created_at: ISO 형식 파싱
   ├─ last_updated: ISO 형식 파싱
   ├─ 기타 필드: .get()으로 안전하게 로드
   └─ 기본값 제공 (하위 호환성)

4. BlogProgress 객체 생성
   └─ 각 blog_progress 항목을 BlogProgress로 변환

5. CrawlJob 객체 생성
   └─ 모든 필드 포함

6. CrawlJob 반환
```

**하위 호환성 처리**
```python
# 기존 체크포인트 파일에 없을 수 있는 필드 처리
crawl_type = data.get('crawl_type', 'blog_id')  # 기본값
total_blog_ids = data.get('total_blog_ids', 0)  # 기본값
failed_blog_ids = data.get('failed_blog_ids', 0)  # 기본값
```

---
## 8. 배치 처리

### 8.1 다중 블로그 크롤링

#### 8.1.1 함수 명세

**함수 시그니처**
```python
def crawl_multiple_blog_ids(
    blog_ids: List[str],
    output_path: str,
    checkpoint_manager: CheckpointManager,
    max_posts_per_blog: Optional[int] = None,
    delay: float = 0.5,
    timeout: int = 30,
    should_stop: Optional[Callable[[], bool]] = None
) -> List[Post]
```

**동작 흐름**
```
1. 초기화
   ├─ all_posts = []  # 모든 블로그의 포스트 통합
   ├─ CrawlJob 객체 생성
   └─ 체크포인트 생성

2. 각 블로그 ID 순회
   for idx, blog_id in enumerate(blog_ids):
       a. should_stop 확인
          ├─ True:
          │  ├─ 현재까지 데이터 저장
          │  ├─ 체크포인트 저장
          │  └─ return all_posts
          └─ False: 계속
      
       b. 기존 진행 상황 확인
          ├─ 완료된 블로그:
          │  └─ 건너뛰기
          └─ 미완료 블로그:
             └─ 계속
      
       c. BlogProgress 초기화
          └─ status='in_progress'
      
       d. 블로그 크롤링 실행
          └─ crawl_by_blog_id(
               blog_id,
               max_posts=max_posts_per_blog,
               delay=delay,
               timeout=timeout,
               should_stop=should_stop
             )
      
       e. 중복 제거
          ├─ 기존 last_post_id와 일치하는 포스트 제거
          └─ 새 포스트만 추가
      
       f. all_posts에 추가
          └─ all_posts.extend(blog_posts)
      
       g. BlogProgress 업데이트
          ├─ status='completed'
          ├─ posts_crawled 업데이트
          └─ completed_at 설정
      
       h. should_stop 확인 (블로그 크롤링 후)
          ├─ True:
          │  ├─ 현재까지 데이터 저장
          │  ├─ 체크포인트 저장
          │  └─ return all_posts
          └─ False: 계속
      
       i. 체크포인트 중간 저장
          └─ checkpoint_manager.save_checkpoint(job, blog_posts)
      
       j. 예외 처리
          ├─ Exception 발생:
          │  ├─ status='failed'
          │  ├─ error 메시지 저장
          │  ├─ failed_blog_ids 증가
          │  └─ 다음 블로그로 계속
          └─ 정상 완료:
             └─ 계속

3. 최종 저장
   ├─ 모든 포스트를 JSON 파일로 저장
   └─ export_to_json(all_posts, output_path, crawl_info)

4. job.status = 'completed'

5. all_posts 반환
```

**중단 처리 흐름**
```python
# 의사코드
if should_stop and should_stop():
    logger.warning("크롤링이 중단되었습니다")
    
    # 현재까지 수집된 데이터 저장
    if all_posts:
        export_to_json(
            all_posts,
            output_path,
            {
                'crawl_type': 'blog_id',
                'total_blog_ids': job.total_blog_ids,
                'processed_blog_ids': job.processed_blog_ids,
                'total_posts': len(all_posts),
                'status': 'paused',
                'interrupted': True
            }
        )
    
    # 체크포인트 저장
    checkpoint_manager.save_checkpoint(job, recent_posts)
    
    return all_posts
```

---

### 8.2 크롤링 재개

#### 8.2.1 함수 명세

**함수 시그니처**
```python
def resume_crawling(
    checkpoint_path: str,
    output_path: str,
    delay: float = 0.5,
    timeout: int = 30
) -> List[Post]
```

**동작 흐름**
```
1. 체크포인트 로드
   └─ checkpoint_manager.load_checkpoint(checkpoint_path)

2. 미완료 블로그 찾기
   ├─ job.blog_progress에서 완료되지 않은 블로그 필터링
   └─ remaining_blog_ids = [
        blog_id for blog_id in job.blog_ids
        if not any(
            bp.blog_id == blog_id and bp.status == 'completed'
            for bp in job.blog_progress
        )
      ]

3. 미완료 블로그가 없으면
   └─ return []  # 이미 완료됨

4. 미완료 블로그 크롤링 실행
   └─ crawl_multiple_blog_ids(
        remaining_blog_ids,
        output_path,
        checkpoint_manager,
        delay=delay,
        timeout=timeout
      )

5. 기존 포스트와 병합
   ├─ output_path 파일이 있으면:
   │  ├─ 기존 JSON 파일 로드
   │  ├─ 기존 posts와 새 posts 병합
   │  └─ 중복 제거 (post_id 기준)
   └─ 없으면:
      └─ 새 posts만 사용

6. 최종 저장
   └─ export_to_json(merged_posts, output_path, ...)

7. 병합된 포스트 반환
```

---## 9. 파일 출력

### 9.1 JSON 출력

#### 9.1.1 함수 명세

**함수 시그니처**
```python
def export_to_json(
    posts: List,
    output_path: str,
    crawl_info: Dict,
    sort_by_date: bool = False
) -> Path
```

**출력 파일 구조**
```json
{
  "crawl_info": {
    "crawl_type": "blog_id",
    "total_blog_ids": 5,
    "processed_blog_ids": 5,
    "failed_blog_ids": 0,
    "total_posts": 150,
    "crawl_date": "2025-01-03T12:00:00",
    "sort_order": "crawl_order" | "date_desc"
  },
  "posts": [
    {
      "post_id": "224048062846",
      "title": "포스트 제목",
      "author": {
        "blog_id": "koding2002",
        "nickname": "작성자 닉네임"
      },
      "published_date": "2025-01-01T10:00:00",
      "modified_date": null,
      "url": "https://m.blog.naver.com/PostView.naver?blogId=...",
      "metadata": {
        "views": 100,
        "likes": 10,
        "comments": 5,
        "category": null,
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
          "date": "2025-01-01T11:00:00",
          "likes": 0
        }
      ]
    }
  ]
}
```

**동작 흐름**
```
1. 출력 경로 검증
   ├─ 없으면 ValueError 발생
   └─ 있으면 계속

2. 출력 디렉토리 생성
   └─ Path(output_path).parent.mkdir(parents=True, exist_ok=True)

3. 포스트 리스트 준비
   ├─ Post 객체를 dict로 변환 (to_dict())
   └─ 딕셔너리인 경우 그대로 사용

4. 날짜 기준 정렬 (옵션)
   ├─ sort_by_date=True:
   │  ├─ published_date 기준으로 내림차순 정렬
   │  └─ 최신순
   └─ sort_by_date=False:
      └─ 크롤링 순서 유지

5. 데이터 구조화
   {
       "crawl_info": {
           **crawl_info,
           "crawl_date": 현재 시간 (ISO 형식),
           "total_posts": len(post_list),
           "sort_order": "date_desc" | "crawl_order"
       },
       "posts": post_list
   }

6. JSON 파일로 저장
   ├─ encoding='utf-8'
   ├─ ensure_ascii=False (한글 지원)
   ├─ indent=2 (가독성)
   └─ default=str (datetime 등 직렬화)

7. 파일 경로 반환
```

**날짜 정렬 알고리즘**
```python
# 의사코드
if sort_by_date:
    try:
        post_list.sort(
            key=lambda p: (
                datetime.fromisoformat(
                    p.get('published_date', '').replace('Z', '+00:00')
                ) if p.get('published_date') else datetime.min
            ),
            reverse=True  # 내림차순 (최신순)
        )
    except Exception as e:
        logger.warning(f"날짜 기준 정렬 실패: {e}")
        # 원본 순서 유지
```

---

### 9.2 Post.to_dict() 변환

#### 9.2.1 변환 규칙

**포함되는 필드**
- 기본 정보: post_id, title, url
- 작성자 정보: author (blog_id, nickname)
- 날짜 정보: published_date, modified_date
- 메타데이터: metadata (views, likes, comments, category, tags)
- 본문: content (text, word_count, images, links)
- 댓글: comments (author, content, date, likes)

**제외되는 필드**
- `content.html`: HTML 원본은 제외
- `content.markdown`: Markdown 형식은 제외

**이유**
- JSON 파일 크기 최소화
- LLM에 전달할 때 불필요한 데이터 제거
- 텍스트만으로도 충분한 정보 제공

**변환 예시**
```python
# 입력: Post 객체
post = Post(
    post_id="123",
    title="제목",
    author=Author(blog_id="blog1", nickname="작성자"),
    published_date=datetime(2025, 1, 1),
    ...
)

# 출력: dict
{
    "post_id": "123",
    "title": "제목",
    "author": {
        "blog_id": "blog1",
        "nickname": "작성자"
    },
    "published_date": "2025-01-01T00:00:00",
    ...
}
```

---## 10. 에러 처리

### 10.1 네트워크 오류

#### 10.1.1 타임아웃 처리

**발생 위치**
- 페이지 로딩: `page.goto()`
- 요소 대기: `page.wait_for_selector()`

**처리 방식**
```python
# 의사코드
max_retries = 3

for attempt in range(max_retries):
    try:
        page.goto(url, timeout=timeout * 1000)
        break  # 성공
    except PlaywrightTimeout:
        if attempt < max_retries - 1:
            sleep(2)
            continue  # 재시도
        else:
            raise TimeoutError(f"최대 재시도 횟수 초과: {url}")
```

**로그 메시지**
```
[오류] 포스트 페이지 로딩 타임아웃: {url}
[경고] 재시도 {attempt+1}/{max_retries}: 페이지 로딩 타임아웃, 잠시 대기 후 재시도...
```

---

### 10.2 파싱 오류

#### 10.2.1 요소 찾기 실패

**처리 전략**
```
1. 다중 선택자 시도
   ├─ 기본 선택자 시도
   ├─ 실패 시 대체 선택자 시도
   └─ 모두 실패 시 기본값 사용

2. 기본값 설정
   ├─ 숫자 필드: 0
   ├─ 문자열 필드: "" 또는 "알 수 없음"
   └─ 리스트 필드: []

3. 로그 기록
   └─ DEBUG 레벨로 상세 정보 기록

4. 계속 진행
   └─ 부분 데이터라도 수집하여 진행
```

**예시: 제목 추출 실패**
```python
# 의사코드
title = None

for selector in selectors:
    try:
        element = page.locator(selector).first
        if element.count() > 0:
            title = element.text_content()
            if title and title.strip():
                break
    except Exception:
        continue

if not title:
    # 기본값 사용
    title = f"포스트 {post_id}"
    logger.warning(f"제목을 찾을 수 없어 기본값 사용: {post_url}")
```

---

### 10.3 블로그 오류

#### 10.3.1 블로그 없음

**감지 방법**
```python
# 의사코드
error_indicators = page.locator('.error, .not-found, .error-page').first
if error_indicators.count() > 0:
    raise BlogNotFoundError(f"블로그를 찾을 수 없습니다: {blog_id}")
```

**처리 방식**
- `BlogNotFoundError` 발생
- 해당 블로그 건너뛰기
- 다음 블로그로 진행
- 오류 로그 기록

#### 10.3.2 접근 불가

**처리 방식**
```python
try:
    blog_info, posts = crawl_by_blog_id(blog_id)
except BlogNotFoundError:
    logger.error(f"블로그를 찾을 수 없습니다: {blog_id}")
    # 건너뛰기
    continue
except Exception as e:
    logger.error(f"블로그 크롤링 실패: {blog_id}, 오류: {e}")
    # 건너뛰기
    continue
```

---

### 10.4 중단 처리

#### 10.4.1 사용자 중단

**처리 흐름**
```
1. 사용자가 중단 버튼 클릭
   └─ stop_requested = True

2. should_stop() 콜백이 True 반환
   └─ crawl_by_blog_id() 내부에서 확인

3. 중단 지점 감지
   ├─ Phase 1 후 확인
   ├─ Phase 2 루프 내 확인 (각 포스트 전)
   └─ 즉시 브라우저 종료

4. 현재까지 데이터 저장
   ├─ 결과 파일 저장
   ├─ 체크포인트 저장
   └─ 진행 상황 업데이트

5. 사용자에게 안내
   └─ "중단되었습니다. 체크포인트 파일로 재개 가능합니다."
```

**코드 예시**
```python
# engine.py
if should_stop and should_stop():
    log_step("크롤링이 중단되었습니다. 브라우저 종료 중...", "WARNING")
    browser.close()
    return blog_info, posts

# batch_crawler.py
if should_stop and should_stop():
    logger.warning("크롤링이 중단되었습니다")
    job.status = 'paused'
    
    if all_posts:
        export_to_json(all_posts, output_path, {...})
    
    checkpoint_manager.save_checkpoint(job, recent_posts)
    return all_posts
```

---

## 11. 성능 특성

### 11.1 시간 복잡도

**링크 수집 (Phase 1)**
- **시간 복잡도**: O(n) where n = 포스트 수
- **공간 복잡도**: O(n) where n = 포스트 수
- **실제 시간**: 
  - 스크롤: 평균 0.2초 * 스크롤 횟수
  - 링크 수집: O(n)

**상세 크롤링 (Phase 2)**
- **시간 복잡도**: O(n) where n = 포스트 수
- **공간 복잡도**: O(n) where n = 포스트 수
- **실제 시간**: 
  - 페이지 로딩: 약 1~2초
  - 데이터 파싱: 약 0.5~1초
  - 딜레이: 0.5초
  - **총 약 2~3초/포스트**

### 11.2 메모리 사용량

**브라우저 메모리**
- 기본: 약 200~300MB (Chromium)
- 페이지 로딩: 약 50~100MB 추가

**Python 메모리**
- Post 객체: 약 5~10KB/포스트
- 100개 포스트: 약 500KB~1MB
- 최근 100개만 메모리 유지

**총 메모리**
- 기본: 약 200~300MB
- 대량 크롤링: 최대 500MB

---

**문서 끝**
