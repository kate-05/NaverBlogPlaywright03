"""
크롤링 엔진
2단계 크롤링 전략 구현
"""
import time
import re
from typing import List, Optional, Tuple, Callable
from playwright.sync_api import Page, Browser, sync_playwright, TimeoutError as PlaywrightTimeout

from src.models import Post, Author, PostMetadata, PostContent, Comment
from src.crawler.parser import extract_tags, extract_comments, extract_content, extract_metadata
from src.utils.exceptions import BlogNotFoundError, TimeoutError, ParsingError, NetworkError


def extract_post_id_from_url(url: str) -> str:
    """URL에서 포스트 ID 추출"""
    # logNo 파라미터에서 추출 시도
    match = re.search(r'logNo=(\d+)', url)
    if match:
        return match.group(1)
    # URL 경로에서 추출 시도
    match = re.search(r'/(\d+)(?:\?|$)', url)
    if match:
        return match.group(1)
    return ''


def extract_blog_id_from_url(url: str) -> str:
    """URL에서 블로그 ID 추출"""
    match = re.search(r'/PostView\.naver\?blogId=([^&]+)', url)
    if match:
        return match.group(1)
    match = re.search(r'blogId=([^&/]+)', url)
    if match:
        return match.group(1)
    return ''


def extract_title(page: Page) -> str:
    """제목 추출"""
    title_selectors = [
        '.se-title-text',
        '.post-title',
        'h1',
        '.title',
        'title'
    ]
    
    for selector in title_selectors:
        try:
            element = page.locator(selector).first
            if element.count() > 0:
                title = element.text_content() or ''
                if title.strip():
                    return title.strip()
        except Exception:
            continue
    
    # Fallback: page title에서 추출
    try:
        page_title = page.title()
        if page_title:
            return page_title
    except Exception:
        pass
    
    return ''


def extract_author(page: Page, blog_id: str = '') -> Author:
    """작성자 정보 추출"""
    nickname = ''
    
    nickname_selectors = [
        '.nickname',
        '.author-name',
        '.blog-author',
        '.blog_info .nickname'
    ]
    
    for selector in nickname_selectors:
        try:
            element = page.locator(selector).first
            if element.count() > 0:
                nickname = element.text_content().strip()
                if nickname:
                    break
        except Exception:
            continue
    
    if not nickname:
        nickname = blog_id  # 기본값
    
    if not blog_id:
        blog_id = extract_blog_id_from_url(page.url)
    
    return Author(blog_id=blog_id, nickname=nickname)


def extract_published_date(page: Page) -> str:
    """작성일 추출"""
    date_selectors = [
        '.se_publishDate',
        '.publish-date',
        '.date',
        '.time__SNGFu',
        '.desc__k5fQT .time__SNGFu'
    ]
    
    for selector in date_selectors:
        try:
            element = page.locator(selector).first
            if element.count() > 0:
                date_text = element.text_content() or ''
                if date_text.strip():
                    return date_text.strip()
        except Exception:
            continue
    
    return ''


def extract_modified_date(page: Page) -> Optional[str]:
    """수정일 추출"""
    modified_selectors = [
        '.se_modifyDate',
        '.modified-date',
        '.modify-date'
    ]
    
    for selector in modified_selectors:
        try:
            element = page.locator(selector).first
            if element.count() > 0:
                date_text = element.text_content() or ''
                if date_text.strip():
                    return date_text.strip()
        except Exception:
            continue
    
    return None


def _collect_all_post_links(
    page: Page,
    blog_id: str,
    max_posts: Optional[int] = None,
    timeout: int = 30
) -> List[str]:
    """
    Phase 1: 링크 수집
    1. 전체글 갯수 확인
    2. 스크롤 다운하여 모든 링크 수집
    3. JavaScript로 DOM 순서대로 모든 포스트 링크 추출
    """
    print("[단계] === Phase 1: 링크 수집 시작 ===")
    
    # 1단계: 전체글 갯수 확인
    print("[단계] === 1단계: 전체글 갯수 확인 (먼저) ===")
    total_post_count = None
    current_url = page.url
    
    # 전체글 버튼 찾기 및 클릭
    sort_selectors = [
        'button[data-click-area="pls.sort"]',
        'button.link__dkflP',
        'button:has-text("전체글")',
        'button:has(span:text("전체글"))'
    ]
    
    sort_button = None
    for selector in sort_selectors:
        try:
            element = page.locator(selector).first
            if element.count() > 0:
                sort_button = element
                break
        except Exception:
            continue
    
    if sort_button:
        try:
            print("[단계] 전체글 버튼 클릭하여 전체글 갯수 확인 중...")
            sort_button.click()
            time.sleep(2)
            
            # 전체글 갯수 추출
            count_elem = page.locator('em.num_area__d8SvC').first
            if count_elem.count() > 0:
                count_text = count_elem.text_content() or ''
                numbers = re.findall(r'\d+', count_text.replace(',', ''))
                if numbers:
                    total_post_count = int(numbers[0])
                    print(f"[단계] 전체글 갯수 확인: {total_post_count}개")
            
            # 닫기 버튼 클릭하여 원래 페이지로 복귀
            close_button = page.locator('button.btn__PPrNT[aria-label="닫기"]').first
            if close_button.count() > 0:
                close_button.click()
                time.sleep(2)
                print("[단계] 닫기 버튼 클릭 완료 - 원래 페이지로 복귀")
            else:
                # URL로 복귀 시도
                page.goto(current_url, wait_until='domcontentloaded')
                time.sleep(2)
        except Exception as e:
            print(f"[경고] 전체글 갯수 확인 실패: {e}")
            # URL로 복귀 시도
            try:
                page.goto(current_url, wait_until='domcontentloaded')
                time.sleep(2)
            except Exception:
                pass
    
    # 2단계: 스크롤 다운
    print("[단계] === 2단계: 스크롤 다운하여 전체 글 갯수와 링크 확인 ===")
    if total_post_count:
        print(f"[단계] 목표: {total_post_count}개 링크 수집")
    
    print("[단계] 스크롤을 빠르게 끝까지 진행 중... (높이 변화가 없을 때까지)")
    
    scroll_count = 0
    no_change_count = 0
    no_change_threshold = 3
    
    while True:
        scroll_count += 1
        if scroll_count % 10 == 0:
            print(f"[단계] 스크롤 반복 {scroll_count}")
        
        # 스크롤 전 높이 측정
        old_height = page.evaluate('document.body.scrollHeight')
        
        # 맨 아래까지 스크롤
        page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
        
        # 최소 대기 (0.2초)
        time.sleep(0.2)
        
        # 스크롤 후 높이 측정
        new_height = page.evaluate('document.body.scrollHeight')
        
        # 높이 비교
        if new_height == old_height:
            no_change_count += 1
            if no_change_count >= no_change_threshold:
                # 최종 안정화 확인 (1초 대기)
                time.sleep(1)
                final_height = page.evaluate('document.body.scrollHeight')
                if final_height == old_height:
                    print(f"[단계] 스크롤 완료: 높이 안정화됨 ({old_height}px) - 링크 수집 단계로 진행")
                    break
                else:
                    no_change_count = 0  # 재변화 감지, 리셋
            else:
                print(f"[단계] 높이 변화 없음 ({old_height}px) - 안정화 확인 중... ({no_change_count}/{no_change_threshold})")
                time.sleep(0.3)
        else:
            print(f"[단계] 높이 변화 감지: {old_height} → {new_height}px (+{new_height - old_height}px) - 계속 스크롤")
            no_change_count = 0  # 리셋
    
    # 3단계: 링크 수집
    print("[단계] === 3단계: 스크롤 완료, 글 목록에서 링크 수집 ===")
    
    # JavaScript로 링크 수집
    links = page.evaluate("""(blogId) => {
        const links = [];
        const blogIdPattern = new RegExp('blogId=' + blogId, 'i');
        
        // 컨테이너 찾기
        const containers = [
            document.evaluate('/html/body/div[1]/div[5]/div[2]/div[3]', document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue,
            document.evaluate('/html/body/div[1]/div[5]/div[4]', document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue
        ];
        
        containers.forEach(container => {
            if (!container) return;
            
            const ulElements = container.querySelectorAll('ul');
            ulElements.forEach(ul => {
                const listItems = ul.querySelectorAll('li');
                listItems.forEach(li => {
                    const div1 = li.querySelector('div:nth-child(1)');
                    const div2 = li.querySelector('div:nth-child(2)');
                    
                    [div1, div2].forEach(div => {
                        if (!div) return;
                        const linksInDiv = div.querySelectorAll('a[href]');
                        linksInDiv.forEach(a => {
                            let href = a.getAttribute('href');
                            if (href) {
                                // 상대 경로를 절대 경로로 변환
                                if (href.startsWith('/')) {
                                    href = 'https://m.blog.naver.com' + href;
                                } else if (!href.startsWith('http')) {
                                    href = 'https://m.blog.naver.com/' + href;
                                }
                                
                                // PostView 또는 logNo 포함 확인
                                if ((href.includes('PostView') || href.includes('logNo')) && 
                                    blogIdPattern.test(href)) {
                                    if (!links.includes(href)) {
                                        links.push(href);
                                    }
                                }
                            }
                        });
                    });
                });
            });
        });
        
        return [...new Set(links)];  // 중복 제거
    }""", blog_id)
    
    print(f"[단계] 페이지에서 {len(links)}개 링크 발견")
    
    if max_posts:
        links = links[:max_posts]
    
    print(f"[단계] === Phase 1 완료: 총 {len(links)}개 링크 수집 ===")
    if total_post_count and len(links) == total_post_count:
        print(f"[단계] ✓ 전체글 갯수({total_post_count}개)와 링크 수({len(links)}개) 매칭!")
    elif total_post_count:
        print(f"[경고] 전체글 갯수({total_post_count}개)와 링크 수({len(links)}개) 불일치")
    
    return links


def crawl_post_detail_mobile(
    page: Page,
    post_url: str,
    timeout: int = 30,
    blog_id: str = None
) -> Post:
    """
    Phase 2: 상세 크롤링
    각 포스트의 상세 정보를 수집
    """
    max_retries = 3
    
    for attempt in range(max_retries):
        try:
            # 페이지 상태 확인
            if page.is_closed():
                raise ValueError("페이지가 닫혔습니다")
            
            # 포스트 페이지 접속
            try:
                page.goto(post_url, wait_until='domcontentloaded', timeout=timeout * 1000)
            except PlaywrightTimeout:
                try:
                    page.goto(post_url, wait_until='load', timeout=timeout * 1000)
                except PlaywrightTimeout:
                    if attempt < max_retries - 1:
                        time.sleep(2)
                        continue
                    raise TimeoutError(f"페이지 로딩 타임아웃: {post_url}")
            
            time.sleep(1)  # 추가 대기
            
            # Post ID 추출
            post_id = extract_post_id_from_url(post_url)
            if not post_id:
                post_id = str(int(time.time()))
            
            # 제목 추출
            title = extract_title(page)
            if not title:
                title = f"포스트 {post_id}"
            
            # 작성자 정보 추출
            if not blog_id:
                blog_id = extract_blog_id_from_url(post_url)
            author = extract_author(page, blog_id)
            
            # 날짜 정보 추출
            published_date = extract_published_date(page)
            modified_date = extract_modified_date(page)
            
            # 메타데이터 추출
            metadata = extract_metadata(page)
            
            # 본문 내용 추출
            content = extract_content(page)
            
            # 해시태그 추출 (댓글보다 먼저)
            tags = extract_tags(page)
            metadata.tags = tags
            
            # 댓글 추출
            comment_count = metadata.comments
            comments = extract_comments(page)
            
            # 댓글 수가 0 이상인데 수집 실패한 경우 재시도
            if comment_count > 0 and len(comments) == 0:
                time.sleep(2)
                comments = extract_comments(page)
            
            # Post 객체 생성
            post = Post(
                post_id=post_id,
                title=title,
                author=author,
                published_date=published_date,
                modified_date=modified_date,
                url=post_url,
                metadata=metadata,
                content=content,
                comments=comments
            )
            
            return post
            
        except PlaywrightTimeout:
            if attempt < max_retries - 1:
                print(f"[경고] 재시도 {attempt+1}/{max_retries}: 페이지 로딩 타임아웃, 잠시 대기 후 재시도...")
                time.sleep(2)
                continue
            raise TimeoutError(f"최대 재시도 횟수 초과: {post_url}")
        except Exception as e:
            if attempt < max_retries - 1:
                print(f"[경고] 재시도 {attempt+1}/{max_retries}: {e}, 잠시 대기 후 재시도...")
                time.sleep(2)
                continue
            raise ParsingError(f"파싱 실패: {e}")


def crawl_by_blog_id(
    blog_id: str,
    max_posts: Optional[int] = None,
    start_date: Optional[str] = None,
    delay: float = 0.5,
    timeout: int = 30,
    should_stop: Optional[Callable[[], bool]] = None
) -> Tuple[dict, List[Post]]:
    """
    블로그 ID 기반 크롤링
    
    Args:
        blog_id: 크롤링할 블로그 ID
        max_posts: 최대 수집 포스트 수
        start_date: 수집 시작 날짜 (미구현)
        delay: 요청 간 딜레이 (초)
        timeout: 페이지 로딩 타임아웃 (초)
        should_stop: 중단 확인 콜백 함수
    
    Returns:
        Tuple[블로그 메타데이터, 포스트 목록]
    """
    # 입력값 검증
    if not blog_id or not blog_id.strip():
        raise ValueError("블로그 ID가 필요합니다")
    
    blog_id = blog_id.strip()
    if delay < 0.5:
        delay = 0.5
    if timeout < 10:
        timeout = 10
    if timeout > 300:
        timeout = 300
    
    # 브라우저 초기화
    playwright = sync_playwright().start()
    browser = playwright.chromium.launch(headless=False)  # headful 모드
    
    # 모바일 디바이스 설정 (iPhone 12)
    device = playwright.devices['iPhone 12']
    context = browser.new_context(**device)
    page = context.new_page()
    
    try:
        # 블로그 메인 페이지 접속
        blog_main_url = f"https://m.blog.naver.com/{blog_id}"
        print(f"[단계] 블로그 메인 페이지 접속: {blog_main_url}")
        page.goto(blog_main_url, wait_until='domcontentloaded', timeout=timeout * 1000)
        time.sleep(2)
        
        # 블로그 존재 여부 확인
        error_indicators = page.locator('.error, .not-found, .error-page').first
        if error_indicators.count() > 0:
            raise BlogNotFoundError(f"블로그를 찾을 수 없습니다: {blog_id}")
        
        # 블로그 메타데이터 수집
        blog_info = {
            'blog_id': blog_id,
            'blog_name': blog_id,
            'author_nickname': blog_id,
            'total_posts': None,
            'created_at': None
        }
        
        # 포스트 목록 페이지 접속 (빠른 스크롤을 위한 링크 타입 사용)
        post_list_url = f"https://m.blog.naver.com/{blog_id}?categoryNo=0&listStyle=post&tab=1"
        print(f"[단계] 포스트 목록 페이지 접속: {post_list_url}")
        page.goto(post_list_url, wait_until='domcontentloaded', timeout=timeout * 1000)
        time.sleep(5)  # 페이지 로딩 대기
        
        # Phase 1: 링크 수집
        post_urls = _collect_all_post_links(page, blog_id, max_posts, timeout)
        
        if not post_urls:
            print("[경고] 수집된 링크가 없습니다")
            return blog_info, []
        
        # should_stop 확인
        if should_stop and should_stop():
            print("[경고] 크롤링이 중단되었습니다. 브라우저 종료 중...")
            browser.close()
            playwright.stop()
            return blog_info, []
        
        # Phase 2: 상세 크롤링
        posts = []
        total_urls = len(post_urls)
        
        for idx, post_url in enumerate(post_urls, 1):
            # should_stop 확인
            if should_stop and should_stop():
                print(f"[경고] 크롤링이 중단되었습니다. ({idx}/{total_urls})")
                break
            
            try:
                print(f"[단계] [{idx}/{total_urls}] 포스트 크롤링 중...")
                post = crawl_post_detail_mobile(page, post_url, timeout, blog_id)
                posts.append(post)
                
                # 딜레이
                if idx < total_urls:
                    time.sleep(delay)
                    
            except Exception as e:
                print(f"[오류] 포스트 크롤링 실패: {post_url}, 오류: {e}")
                continue
        
        browser.close()
        playwright.stop()
        
        blog_info['total_posts'] = len(posts)
        print(f"[단계] === 크롤링 완료: 총 {len(posts)}개 포스트 수집 ===")
        
        return blog_info, posts
        
    except Exception as e:
        browser.close()
        playwright.stop()
        raise

