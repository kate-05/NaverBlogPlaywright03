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
    """제목 추출 (모바일 네이버 블로그)"""
    # 우선: 페이지 title에서 추출 (가장 정확)
    try:
        page_title = page.title()
        if page_title:
            # " : " 구분자로 제목 추출 (네이버 블로그 형식: "제목 : 네이버 블로그")
            if ' : ' in page_title:
                parts = page_title.split(' : ')
                if len(parts) > 0:
                    title = parts[0].strip()
                    if title and len(title) < 200:
                        return title
            # " - " 구분자로 제목 추출
            if ' - ' in page_title:
                parts = page_title.split(' - ')
                if len(parts) > 0:
                    title = parts[0].strip()
                    if title and len(title) < 200:
                        return title
    except Exception:
        pass
    
    # JavaScript로 제목 추출 (Fallback)
    try:
        title = page.evaluate("""() => {
            // 방법 1: 본문 제목 요소 직접 찾기
            const titleSelectors = [
                'h1.post_subject',
                'h1.se-title-text',
                '.post-title h1',
                '.post_subject',
                '.se-title-text',
                'h1.title',
                'h1',
                '.title',
                '[class*="title"]'
            ];
            
            for (const selector of titleSelectors) {
                const elem = document.querySelector(selector);
                if (elem) {
                    const text = (elem.textContent || elem.innerText || '').trim();
                    if (text && text.length > 0 && text.length < 200) {
                        return text;
                    }
                }
            }
            
            // 방법 2: 페이지 title에서 추출
            const pageTitle = document.title;
            if (pageTitle) {
                // " : " 구분자로 제목 추출
                if (pageTitle.includes(' : ')) {
                    const parts = pageTitle.split(' : ');
                    if (parts.length > 0) {
                        return parts[0].trim();
                    }
                }
                // " - " 구분자로 제목 추출
                if (pageTitle.includes(' - ')) {
                    const parts = pageTitle.split(' - ');
                    if (parts.length > 0) {
                        return parts[0].trim();
                    }
                }
                return pageTitle.trim();
            }
            
            return '';
        }""")
        
        if title and title.strip():
            return title.strip()
    except Exception as e:
        print(f"[경고] JavaScript 제목 추출 실패: {e}")
    
    # Fallback: Playwright Locator 사용
    title_selectors = [
        'h1.post_subject',
        'h1.se-title-text',
        '.post_subject',
        '.se-title-text',
        '.post-title',
        'h1.title',
        'h1',
        '.title'
    ]
    
    for selector in title_selectors:
        try:
            element = page.locator(selector).first
            if element.count() > 0:
                title = element.text_content() or ''
                title = title.strip()
                if title and len(title) < 200:  # 제목이 너무 길면 제외
                    return title
        except Exception:
            continue
    
    # 최종 Fallback: page title에서 추출
    try:
        page_title = page.title()
        if page_title:
            # " : " 구분자로 제목 추출 (네이버 블로그 형식)
            if ' : ' in page_title:
                parts = page_title.split(' : ')
                if len(parts) > 0:
                    return parts[0].strip()
            # " - " 구분자로 제목 추출
            if ' - ' in page_title:
                parts = page_title.split(' - ')
                if len(parts) > 0:
                    return parts[0].strip()
            return page_title.strip()
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
    
    # 2단계: 스크롤 다운 (문서: '맨 위로' 버튼이 나타날 때까지)
    print("[단계] === 2단계: 스크롤 다운하여 전체 글 갯수와 링크 확인 ===")
    if total_post_count:
        print(f"[단계] 목표: {total_post_count}개 링크 수집")
    
    print("[단계] 스크롤을 빠르게 끝까지 진행 중... ('맨 위로' 버튼이 나타날 때까지)")
    
    scroll_count = 0
    no_change_count = 0
    no_change_threshold = 3
    max_scrolls = 200  # 최대 스크롤 횟수 제한
    
    while scroll_count < max_scrolls:
        scroll_count += 1
        if scroll_count % 10 == 0:
            print(f"[단계] 스크롤 반복 {scroll_count}")
        
        # '맨 위로' 버튼 확인 (문서 기준)
        scroll_top_button = page.locator('button.scroll_top_button__uyAEr[data-click-area="pls.backtotop"]').first
        if scroll_top_button.count() > 0:
            # '맨 위로' 버튼이 보이면 스크롤 완료
            print("[단계] '맨 위로' 버튼 감지 - 스크롤 완료")
            time.sleep(1)  # 최종 로딩 대기
            break
        
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
    
    # 링크 수집 전 추가 대기
    time.sleep(2)
    
    # 3단계: 링크 수집
    print("[단계] === 3단계: 스크롤 완료, 글 목록에서 링크 수집 ===")
    
    # 디버깅: 페이지 구조 확인
    debug_info = page.evaluate("""() => {
        const info = {
            containers: [],
            allLinks: 0,
            postLinks: 0
        };
        
        // 모든 가능한 컨테이너 확인
        for (let i = 1; i <= 10; i++) {
            for (let j = 1; j <= 10; j++) {
                const xpath = `/html/body/div[1]/div[${i}]/div[${j}]`;
                const container = document.evaluate(xpath, document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue;
                if (container) {
                    const linkCount = container.querySelectorAll('a[href]').length;
                    if (linkCount > 0) {
                        info.containers.push({xpath: xpath, links: linkCount});
                    }
                }
            }
        }
        
        // 전체 페이지 링크 수
        info.allLinks = document.querySelectorAll('a[href]').length;
        info.postLinks = document.querySelectorAll('a[href*="/' + location.pathname.split('/')[1] + '/"], a[href*="PostView"], a[href*="logNo"]').length;
        
        return info;
    }""")
    
    print(f"[디버깅] 페이지 구조 확인:")
    print(f"  - 전체 링크 수: {debug_info['allLinks']}")
    print(f"  - 포스트 링크 수: {debug_info['postLinks']}")
    if debug_info['containers']:
        print(f"  - 링크가 있는 컨테이너: {len(debug_info['containers'])}개")
        for container in debug_info['containers'][:5]:  # 처음 5개만 출력
            print(f"    * {container['xpath']}: {container['links']}개 링크")
    
    # JavaScript로 링크 수집 (문서 기준: /html/body/div[1]/div[5]/div[4])
    links = page.evaluate("""(blogId) => {
        const links = [];
        
        // 컨테이너 찾기 (문서 기준 XPath: /html/body/div[1]/div[5]/div[4])
        const mainContainer = document.evaluate(
            '/html/body/div[1]/div[5]/div[4]', 
            document, 
            null, 
            XPathResult.FIRST_ORDERED_NODE_TYPE, 
            null
        ).singleNodeValue;
        
        // Fallback 컨테이너들
        const fallbackContainers = [
            document.evaluate('/html/body/div[1]/div[5]/div[2]/div[3]', document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue,
            mainContainer
        ].filter(c => c !== null);
        
        const containers = mainContainer ? [mainContainer] : fallbackContainers;
        
        // 방법 1: 문서에 명시된 선택자 사용 (a.link__A4O1D, a[data-click-area="pls.textpost"])
        containers.forEach(container => {
            if (!container) return;
            
            // div.postlist__qxOgF 안의 링크 찾기 (문서 기준)
            const postListDivs = container.querySelectorAll('div.postlist__qxOgF');
            postListDivs.forEach(postDiv => {
                const linkElements = postDiv.querySelectorAll('a.link__A4O1D, a[data-click-area="pls.textpost"]');
                linkElements.forEach(a => {
                    let href = a.getAttribute('href');
                    if (href) {
                        // 상대 경로를 절대 경로로 변환
                        if (href.startsWith('/')) {
                            href = 'https://m.blog.naver.com' + href;
                        } else if (!href.startsWith('http')) {
                            href = 'https://m.blog.naver.com/' + href;
                        }
                        
                        // 블로그 ID와 포스트 번호 포함 확인
                        // 형식: /blog_id/숫자 또는 ?blogId=...&logNo=...
                        const blogIdPattern = new RegExp(blogId, 'i');
                        const postNumberPattern = /\/(\d+)|logNo=(\d+)/;
                        
                        if (blogIdPattern.test(href) && postNumberPattern.test(href)) {
                            // PostView URL로 변환 (표준 형식)
                            const postNumMatch = href.match(/\/(\d+)/) || href.match(/logNo=(\d+)/);
                            if (postNumMatch) {
                                const postNum = postNumMatch[1] || postNumMatch[2];
                                const standardUrl = `https://m.blog.naver.com/PostView.naver?blogId=${blogId}&logNo=${postNum}`;
                                if (!links.includes(standardUrl)) {
                                    links.push(standardUrl);
                                }
                            }
                        }
                    }
                });
            });
        });
        
        // 방법 2: Fallback - 직접 선택자로 찾기
        if (links.length === 0) {
            containers.forEach(container => {
                if (!container) return;
                
                // 전체 링크 찾기
                const linkElements = container.querySelectorAll('a.link__A4O1D, a[data-click-area="pls.textpost"]');
                linkElements.forEach(a => {
                    let href = a.getAttribute('href');
                    if (href) {
                        if (href.startsWith('/')) {
                            href = 'https://m.blog.naver.com' + href;
                        } else if (!href.startsWith('http')) {
                            href = 'https://m.blog.naver.com/' + href;
                        }
                        
                        const blogIdPattern = new RegExp(blogId, 'i');
                        const postNumberPattern = /\/(\d+)|logNo=(\d+)/;
                        
                        if (blogIdPattern.test(href) && postNumberPattern.test(href)) {
                            const postNumMatch = href.match(/\/(\d+)/) || href.match(/logNo=(\d+)/);
                            if (postNumMatch) {
                                const postNum = postNumMatch[1] || postNumMatch[2];
                                const standardUrl = `https://m.blog.naver.com/PostView.naver?blogId=${blogId}&logNo=${postNum}`;
                                if (!links.includes(standardUrl)) {
                                    links.push(standardUrl);
                                }
                            }
                        }
                    }
                });
            });
        }
        
        // 방법 3: 최종 Fallback - ul/li 구조에서 찾기
        if (links.length === 0) {
            containers.forEach(container => {
                if (!container) return;
                
                const ulElements = container.querySelectorAll('ul');
                ulElements.forEach(ul => {
                    const listItems = ul.querySelectorAll('li');
                    listItems.forEach(li => {
                        const allLinks = li.querySelectorAll('a[href]');
                        allLinks.forEach(a => {
                            let href = a.getAttribute('href');
                            if (href) {
                                if (href.startsWith('/')) {
                                    href = 'https://m.blog.naver.com' + href;
                                } else if (!href.startsWith('http')) {
                                    href = 'https://m.blog.naver.com/' + href;
                                }
                                
                                const blogIdPattern = new RegExp(blogId, 'i');
                                const postNumberPattern = /\/(\d+)|logNo=(\d+)|PostView/;
                                
                                if (blogIdPattern.test(href) && postNumberPattern.test(href)) {
                                    const postNumMatch = href.match(/\/(\d+)/) || href.match(/logNo=(\d+)/);
                                    if (postNumMatch) {
                                        const postNum = postNumMatch[1] || postNumMatch[2];
                                        const standardUrl = `https://m.blog.naver.com/PostView.naver?blogId=${blogId}&logNo=${postNum}`;
                                        if (!links.includes(standardUrl)) {
                                            links.push(standardUrl);
                                        }
                                    }
                                }
                            }
                        });
                    });
                });
            });
        }
        
        // 방법 4: 최종 Fallback - 페이지 전체에서 블로그 ID와 포스트 번호가 있는 링크 찾기
        if (links.length === 0) {
            const allLinks = document.querySelectorAll('a[href]');
            allLinks.forEach(a => {
                let href = a.getAttribute('href');
                if (href) {
                    if (href.startsWith('/')) {
                        href = 'https://m.blog.naver.com' + href;
                    } else if (!href.startsWith('http')) {
                        href = 'https://m.blog.naver.com/' + href;
                    }
                    
                    const blogIdPattern = new RegExp(blogId, 'i');
                    const postNumberPattern = /\/(\d{8,})|logNo=(\d{8,})/;  // 8자리 이상 숫자 (포스트 ID)
                    
                    if (blogIdPattern.test(href) && postNumberPattern.test(href)) {
                        const postNumMatch = href.match(/\/(\d{8,})/) || href.match(/logNo=(\d{8,})/);
                        if (postNumMatch) {
                            const postNum = postNumMatch[1] || postNumMatch[2];
                            const standardUrl = `https://m.blog.naver.com/PostView.naver?blogId=${blogId}&logNo=${postNum}`;
                            if (!links.includes(standardUrl)) {
                                links.push(standardUrl);
                            }
                        }
                    }
                }
            });
        }
        
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
            
            # 본문 로딩 대기 (중요: 네이버 블로그는 동적 로딩)
            time.sleep(2)  # 초기 로딩 대기
            
            # 본문이 로드될 때까지 대기
            try:
                # 본문 컨테이너가 나타날 때까지 대기
                page.wait_for_selector('.se-main-container, .se-component-content, #postViewArea, .post-view-area, .post-content', timeout=10000)
            except Exception:
                # 선택자가 없어도 계속 진행
                pass
            
            time.sleep(1)  # 추가 안정화 대기
            
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
    should_stop: Optional[Callable[[], bool]] = None,
    all_post_urls: Optional[List[str]] = None,
    crawled_urls: Optional[List[str]] = None
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
        all_post_urls: 전체 포스트 링크 목록 (재개 모드에서 사용)
        crawled_urls: 이미 크롤링된 포스트 URL 목록 (재개 모드에서 사용)
    
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
    
    # 블로그 메타데이터 수집
    blog_info = {
        'blog_id': blog_id,
        'blog_name': blog_id,
        'author_nickname': blog_id,
        'total_posts': None,
        'created_at': None
    }
    
    # 재개 모드: 전체 링크 목록이 이미 있는 경우
    if all_post_urls:
        post_urls = all_post_urls
        print(f"[단계] 재개 모드: 체크포인트에서 전체 링크 목록 {len(post_urls)}개 로드")
        # 재개 모드에서는 브라우저 초기화를 나중에 (Phase 2에서)
        browser = None
        playwright = None
        page = None
    else:
        # 브라우저 초기화
        playwright = sync_playwright().start()
        browser = playwright.chromium.launch(headless=False)  # headful 모드
        
        # 모바일 디바이스 설정 (iPhone 12)
        device = playwright.devices['iPhone 12']
        context = browser.new_context(**device)
        page = context.new_page()
    
    try:
        # 재개 모드가 아닐 때만 블로그 존재 여부 확인
        if not all_post_urls:
            # 블로그 메인 페이지 접속
            blog_main_url = f"https://m.blog.naver.com/{blog_id}"
            print(f"[단계] 블로그 메인 페이지 접속: {blog_main_url}")
            page.goto(blog_main_url, wait_until='domcontentloaded', timeout=timeout * 1000)
            time.sleep(2)
            
            # 블로그 존재 여부 확인
            error_indicators = page.locator('.error, .not-found, .error-page').first
            if error_indicators.count() > 0:
                raise BlogNotFoundError(f"블로그를 찾을 수 없습니다: {blog_id}")
        
        if not all_post_urls:
            # Phase 1: 링크 수집
            post_list_url = f"https://m.blog.naver.com/{blog_id}?categoryNo=0&listStyle=post&tab=1"
            print(f"[단계] 포스트 목록 페이지 접속: {post_list_url}")
            page.goto(post_list_url, wait_until='domcontentloaded', timeout=timeout * 1000)
            time.sleep(5)  # 페이지 로딩 대기
            
            post_urls = _collect_all_post_links(page, blog_id, max_posts, timeout)
            
            if not post_urls:
                print("[경고] 수집된 링크가 없습니다")
                return blog_info, []
        
        # 전체 링크 목록을 blog_info에 저장 (재개 시 사용)
        blog_info['all_post_urls'] = post_urls
        blog_info['total_post_urls'] = len(post_urls)
        
        # should_stop 확인
        if should_stop and should_stop():
            print("[경고] 크롤링이 중단되었습니다. 브라우저 종료 중...")
            if browser:
                browser.close()
            if playwright:
                playwright.stop()
            return blog_info, []
        
        # Phase 2: 상세 크롤링
        # 재개 모드인 경우 브라우저 초기화 (이제 필요함)
        if all_post_urls and (browser is None or page is None):
            playwright = sync_playwright().start()
            browser = playwright.chromium.launch(headless=False)  # headful 모드
            device = playwright.devices['iPhone 12']
            context = browser.new_context(**device)
            page = context.new_page()
            print(f"[단계] 재개 모드: 브라우저 초기화 완료")
        
        # 이미 크롤링된 포스트 URL 목록이 있으면 제외
        crawled_urls_list = crawled_urls or []
        if crawled_urls_list:
            crawled_urls_set = set(crawled_urls_list)
            post_urls = [url for url in post_urls if url not in crawled_urls_set]
            skipped_count = len(crawled_urls_list)
            print(f"[단계] 이미 크롤링된 포스트 {skipped_count}개 건너뛰기 (재개 모드)")
            print(f"[단계] 남은 포스트 {len(post_urls)}개 크롤링 시작")
        
        if not post_urls:
            print("[경고] 크롤링할 남은 포스트가 없습니다")
            if browser:
                browser.close()
            if playwright:
                playwright.stop()
            blog_info['total_posts'] = 0
            return blog_info, []
        
        posts = []
        total_urls = blog_info['total_post_urls']  # 전체 링크 수 (원래 순서 표시용)
        crawled_count = len(crawled_urls_list)
        
        for idx, post_url in enumerate(post_urls, 1):
            # should_stop 확인
            if should_stop and should_stop():
                current_idx = crawled_count + idx
                print(f"[경고] 크롤링이 중단되었습니다. ({current_idx}/{total_urls})")
                break
            
            try:
                current_idx = crawled_count + idx
                print(f"[단계] [{current_idx}/{total_urls}] 포스트 크롤링 중...")
                post = crawl_post_detail_mobile(page, post_url, timeout, blog_id)
                posts.append(post)
                
                # 딜레이
                if idx < len(post_urls):
                    time.sleep(delay)
                    
            except Exception as e:
                print(f"[오류] 포스트 크롤링 실패: {post_url}, 오류: {e}")
                continue
        
        if browser:
            browser.close()
        if playwright:
            playwright.stop()
        
        blog_info['total_posts'] = len(posts)
        print(f"[단계] === 크롤링 완료: 총 {len(posts)}개 포스트 수집 ===")
        
        return blog_info, posts
        
    except Exception as e:
        if browser:
            browser.close()
        if playwright:
            playwright.stop()
        raise

