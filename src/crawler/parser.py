"""
HTML 파싱 모듈
해시태그, 댓글, 본문, 메타데이터 추출
"""
import re
import time
from typing import List, Optional
from playwright.sync_api import Page

from src.models import PostMetadata, PostContent, Comment
from src.utils.exceptions import ParsingError


def extract_number(page: Page, selectors: List[str]) -> int:
    """숫자 추출 (조회수, 좋아요, 댓글 수 등)"""
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
    return 0


def extract_tags(page: Page) -> List[str]:
    """해시태그 추출 (확장 버튼 클릭 후)"""
    tags = []
    
    # 해시태그 확장 버튼 찾기
    expand_selectors = [
        'button.tag__tFC3j.expand_btn__oaNLH[data-click-area="pst.tagmore"]',
        'button.expand_btn__oaNLH[data-click-area="pst.tagmore"]',
        'button.expand_btn__oaNLH',
        'button[data-click-area="pst.tagmore"]'
    ]
    
    expand_button = None
    for selector in expand_selectors:
        try:
            element = page.locator(selector).first
            if element.count() > 0:
                expand_button = element
                break
        except Exception:
            continue
    
    # 확장 버튼 클릭
    if expand_button:
        try:
            expand_button.scroll_into_view_if_needed()
            time.sleep(0.5)
            expand_button.click(timeout=5000)
            time.sleep(2)  # 해시태그 로딩 대기
        except Exception as e:
            print(f"[경고] 해시태그 확장 버튼 클릭 실패: {e}")
    
    # 해시태그 요소 추출
    tag_selectors = [
        'a.tag__tFC3j[data-click-area="pst.tag"]',
        'a.tag__tFC3j',
        '.list_wrap__jKORt .list__yr1c8 .item__jRCnW a.tag__tFC3j',
        '.tag__tFC3j',
        '.tag-list .tag',
        '.area_tag a',
        '.se_tagList a',
        '.tag-item'
    ]
    
    for selector in tag_selectors:
        try:
            elements = page.locator(selector).all()
            if elements:
                for element in elements:
                    try:
                        text = element.text_content() or ""
                        tag_name = text.replace('#', '').strip()
                        if tag_name and tag_name not in tags:
                            tags.append(tag_name)
                    except Exception:
                        continue
                if tags:
                    break
        except Exception:
            continue
    
    # JavaScript Fallback
    if not tags:
        try:
            tags = page.evaluate("""() => {
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
            }""")
        except Exception as e:
            print(f"[경고] JavaScript Fallback 실패: {e}")
    
    return list(set(tags))  # 중복 제거


def extract_comments(page: Page, comment_count: Optional[int] = None) -> List[Comment]:
    """댓글 추출 (댓글 버튼 클릭 후)"""
    comments = []
    
    # 댓글 수가 0이면 버튼 클릭하지 않고 빈 리스트 반환 (크롤링 시간 단축)
    if comment_count is not None and comment_count == 0:
        return comments
    
    # 댓글 버튼 찾기
    comment_button_selectors = [
        'button.comment_btn__TUucZ[data-click-area="pst.re"]',
        'button.comment_btn__TUucZ',
        'button[data-click-area*="re"]'
    ]
    
    comment_button = None
    for selector in comment_button_selectors:
        try:
            element = page.locator(selector).first
            if element.count() > 0:
                comment_button = element
                break
        except Exception:
            continue
    
    if not comment_button:
        return comments
    
    # 댓글 버튼 클릭
    try:
        comment_button.click()
        time.sleep(3)  # 댓글 로딩 대기 (초기 로딩)
    except Exception:
        return comments
    
    # 비밀 댓글 확인 (모든 댓글이 비밀 댓글이면 빠르게 패스)
    try:
        is_secret_only = page.evaluate("""() => {
            // 댓글 영역 전체 텍스트 확인
            const commentArea = document.querySelector(
                '#naverComment_wai_u_cbox_content_wrap_tabpanel, [role="tabpanel"], .u_cbox_list'
            );
            if (!commentArea) {
                return false;
            }
            
            const areaText = commentArea.textContent || '';
            
            // "비밀 댓글입니다." 텍스트 확인
            if (!areaText.includes('비밀 댓글입니다.')) {
                return false;  // 비밀 댓글이 없으면 false
            }
            
            // 댓글 아이템 수 확인
            const commentItems = commentArea.querySelectorAll('li.u_cbox_comment, .u_cbox_comment');
            const commentCount = commentItems.length;
            
            if (commentCount === 0) {
                return false;
            }
            
            // 각 댓글 아이템 확인
            let secretCount = 0;
            let hasNormalComment = false;
            
            commentItems.forEach(item => {
                const itemText = item.textContent || '';
                // 비밀 댓글 확인
                if (itemText.includes('비밀 댓글입니다.')) {
                    secretCount++;
                } else {
                    // 일반 댓글 확인 (닉네임이나 내용이 있으면)
                    const hasNick = item.querySelector('span.u_cbox_nick');
                    const hasContent = item.querySelector('span.u_cbox_contents');
                    if (hasNick || hasContent) {
                        const nickText = hasNick ? (hasNick.textContent || '').trim() : '';
                        const contentText = hasContent ? (hasContent.textContent || '').trim() : '';
                        // 비밀 댓글 텍스트가 없고 내용이 있으면 일반 댓글
                        if (nickText || (contentText && !contentText.includes('비밀 댓글입니다.'))) {
                            hasNormalComment = true;
                        }
                    }
                }
            });
            
            // 모든 댓글이 비밀 댓글이면 true 반환
            // 일반 댓글이 하나도 없고, 모든 댓글이 비밀 댓글이면 건너뛰기
            if (secretCount === commentCount && commentCount > 0 && !hasNormalComment) {
                return true;
            }
            
            return false;
        }""")
        
        if is_secret_only:
            print("[단계] 모든 댓글이 비밀 댓글입니다. 댓글 수집 건너뛰기 (크롤링 시간 단축)")
            return comments
    except Exception as e:
        print(f"[경고] 비밀 댓글 확인 실패: {e}")
        pass  # 비밀 댓글 확인 실패 시 정상 진행
    
    # 추가 로딩 대기 (비밀 댓글이 아닌 경우에만)
    time.sleep(2)
    
    # JavaScript 기반 댓글 수집 (우선)
    try:
        comments_data = page.evaluate("""() => {
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
                // 비밀 댓글 확인
                const itemText = item.textContent || '';
                if (itemText.includes('비밀 댓글입니다.')) {
                    // 비밀 댓글은 건너뛰기
                    return;
                }
                
                // 닉네임 추출
                let author = '';
                const nickElem = item.querySelector('span.u_cbox_nick');
                if (nickElem) {
                    author = (nickElem.textContent || '').trim();
                } else {
                    const aElem = item.querySelector('a.u_cbox_name > span.u_cbox_nick');
                    if (aElem) {
                        author = (aElem.textContent || '').trim();
                    }
                }
                
                // 내용 추출
                let content = '';
                const contentElem = item.querySelector('span.u_cbox_contents');
                if (contentElem) {
                    content = (contentElem.textContent || '').trim();
                    // 비밀 댓글 내용 확인
                    if (content.includes('비밀 댓글입니다.')) {
                        return; // 비밀 댓글 건너뛰기
                    }
                }
                
                // 날짜 추출
                let dateText = '';
                const dateMatch = itemText.match(/\\d{4}\\.\\d{1,2}\\.\\d{1,2}\\.?\\s+\\d{1,2}:\\d{2}/);
                if (dateMatch) {
                    dateText = dateMatch[0];
                }
                
                // 좋아요 수 추출
                let likes = 0;
                const likesMatch = itemText.match(/공감\\s+(\\d+)/);
                if (likesMatch) {
                    likes = parseInt(likesMatch[1], 10);
                }
                
                if (author || content) {
                    comments.push({
                        author: author,
                        content: content,
                        date: dateText,
                        likes: likes
                    });
                }
            });
            
            return comments;
        }""")
        
        for data in comments_data:
            comments.append(Comment(
                author=data.get('author', ''),
                content=data.get('content', ''),
                date=data.get('date'),
                likes=data.get('likes', 0)
            ))
            
    except Exception as e:
        print(f"[경고] JavaScript 댓글 수집 실패: {e}")
        
        # Playwright Locator Fallback
        try:
            comment_items = page.locator('.u_cbox_list_item, .u_cbox_comment').all()
            for item in comment_items:
                try:
                    # 비밀 댓글 확인
                    item_text = item.text_content() or ''
                    if '비밀 댓글입니다.' in item_text:
                        continue  # 비밀 댓글 건너뛰기
                    
                    author_elem = item.locator('span.u_cbox_nick').first
                    author = author_elem.text_content().strip() if author_elem.count() > 0 else ''
                    
                    content_elem = item.locator('span.u_cbox_contents').first
                    content = content_elem.text_content().strip() if content_elem.count() > 0 else ''
                    
                    # 비밀 댓글 내용 확인
                    if '비밀 댓글입니다.' in content:
                        continue  # 비밀 댓글 건너뛰기
                    
                    if author or content:
                        comments.append(Comment(
                            author=author,
                            content=content,
                            date=None,
                            likes=0
                        ))
                except Exception:
                    continue
        except Exception:
            pass
    
    return comments


def extract_content(page: Page) -> PostContent:
    """본문 내용 추출 (모바일 네이버 블로그)"""
    content = PostContent()
    
    # 본문 컨테이너 찾기 (JavaScript로 더 정확하게)
    container_info = page.evaluate("""() => {
        // 본문 컨테이너 선택자 (우선순위 순)
        const selectors = [
            '.se-main-container',
            '.se-component-content',
            '#postViewArea',
            '.post-view-area',
            '.post-content',
            '.area_view',
            '.post-view',
            'article',
            '.post_body'
        ];
        
        for (const selector of selectors) {
            const elem = document.querySelector(selector);
            if (elem) {
                // 본문이 실제로 있는지 확인 (텍스트가 50자 이상)
                const text = (elem.textContent || '').trim();
                if (text.length > 50) {
                    return {
                        selector: selector,
                        found: true,
                        textLength: text.length
                    };
                }
            }
        }
        
        return { found: false };
    }""")
    
    container = None
    
    # JavaScript에서 찾은 선택자로 컨테이너 찾기
    if container_info.get('found'):
        try:
            container = page.locator(container_info['selector']).first
            if container.count() == 0:
                container = None
        except Exception:
            container = None
    
    # Fallback: 직접 선택자로 찾기
    if not container:
        content_selectors = [
            '.se-main-container',
            '.se-component-content',
            '#postViewArea',
            '.post-view-area',
            '.post-content',
            '.area_view',
            '.post-view',
            'article',
            '.post_body'
        ]
        
        for selector in content_selectors:
            try:
                element = page.locator(selector).first
                if element.count() > 0:
                    # 본문이 실제로 있는지 확인
                    text = element.text_content() or ""
                    if len(text.strip()) > 50:
                        container = element
                        break
            except Exception:
                continue
    
    # 최종 Fallback: body 사용 (하지만 본문 영역만 추출)
    if not container:
        container = page.locator('body')
    
    try:
        # HTML 추출
        content.html = container.inner_html()
        
        # 텍스트 추출 - 본문 영역만 추출 (헤더, 푸터, 댓글 제외)
        raw_text = page.evaluate("""(selector) => {
            let container = null;
            
            // 선택자가 있으면 해당 요소 사용
            if (selector) {
                container = document.querySelector(selector);
            }
            
            // 본문 컨테이너 찾기 (우선순위 순)
            if (!container) {
                const selectors = [
                    '.se-main-container',
                    '.se-component-content',
                    '#postViewArea',
                    '.post-view-area',
                    '.post-content',
                    '.area_view',
                    '.post-view',
                    'article',
                    '.post_body',
                    '.post_ct',
                    '.post-view-box'
                ];
                
                for (const sel of selectors) {
                    const elem = document.querySelector(sel);
                    if (elem) {
                        const text = (elem.textContent || '').trim();
                        // 본문이 실제로 있는지 확인 (50자 이상)
                        if (text.length > 50) {
                            container = elem;
                            break;
                        }
                    }
                }
            }
            
            // 본문 영역 직접 찾기 (특정 클래스나 구조로)
            if (!container || (container === document.body && container.textContent.length > 1000)) {
                // 방법 1: 제목 다음부터 본문 시작하는 경우
                const postSubject = document.querySelector('.post_subject, h1.post_subject');
                if (postSubject) {
                    // 제목 다음 형제 요소들에서 본문 찾기
                    let nextSibling = postSubject.nextElementSibling;
                    while (nextSibling) {
                        const text = (nextSibling.textContent || '').trim();
                        if (text.length > 50 && !text.includes('이웃추가') && !text.includes('공유하기') && !text.includes('로그인')) {
                            container = nextSibling;
                            break;
                        }
                        nextSibling = nextSibling.nextElementSibling;
                    }
                }
                
                // 방법 2: "신고하기" 버튼 다음 요소들 중 본문 찾기
                if (!container || container === document.body) {
                    const reportButtons = document.querySelectorAll('button, .btn, a');
                    for (const btn of reportButtons) {
                        const btnText = (btn.textContent || '').trim();
                        if (btnText.includes('신고하기')) {
                            // 신고하기 버튼 다음 형제 요소들 찾기
                            let nextSibling = btn.parentElement || btn;
                            while (nextSibling && nextSibling.nextElementSibling) {
                                nextSibling = nextSibling.nextElementSibling;
                                const text = (nextSibling.textContent || '').trim();
                                // 본문인지 확인 (50자 이상, 제외 텍스트 없음)
                                if (text.length > 50 && 
                                    !text.includes('이웃추가') && 
                                    !text.includes('공유하기') && 
                                    !text.includes('로그인') &&
                                    !text.includes('카테고리') &&
                                    !text.includes('PC버전')) {
                                    container = nextSibling;
                                    break;
                                }
                            }
                            if (container && container !== document.body) break;
                        }
                    }
                }
            }
            
            if (!container) {
                // body에서 본문 영역 찾기
                container = document.body;
            }
            
            // 제목, 헤더, 푸터, 댓글 영역 제외
            const excludeSelectors = [
                'header', '.header', '.post-header',
                'footer', '.footer', '.post-footer',
                '.post-title', '.post_subject', 'h1', 'h2',
                '.comment-area', '.u_cbox', '.comment',
                '.post-meta', '.meta-info', '.author-info',
                '.navigation', '.nav', '.menu',
                '.sidebar', '.side', '.widget',
                '.btn', '.button', 'button',
                '.link', '.menu-item',
                'script', 'style', 'noscript',
                '.Nservice_item', '.Nheader',  // 네이버 서비스 메뉴
                '.log_area', '.login',         // 로그인 영역
                '.bottom_area', '.footer_area' // 푸터 영역
            ];
            
            // 제외할 텍스트 패턴
            const excludeTexts = [
                '로그인이 필요합니다',
                '이웃추가',
                '공유하기',
                'URL 복사',
                '신고하기',
                '본문 폰트 크기',
                'PC버전으로 보기',
                '블로그 고객센터',
                '네이버 블로그',
                '카테고리 이동',
                '카테고리',
                '검색',
                'My Menu',
                '본문 바로가기',
                'Most important',
                '내소식',
                '이웃목록',
                '클립만들기',
                '글쓰기',
                '내 체크인',
                '최근 본 글',
                '내 동영상',
                '내 클립',
                '내 상품 관리',
                '마켓 플레이스',
                '장바구니',
                '마켓 구매내역',
                '블로그팀 공식블로그',
                '이달의 블로그',
                '공식 블로그',
                '블로그 앱',
                'NAVER Corp',
                'ⓒ'
            ];
            
            // 제외할 요소들 찾기
            const excludeElements = new Set();
            excludeSelectors.forEach(sel => {
                try {
                    document.querySelectorAll(sel).forEach(el => {
                        excludeElements.add(el);
                    });
                } catch (e) {}
            });
            
            // 본문 텍스트 추출 (제외 요소 제외)
            let text = '';
            const walker = document.createTreeWalker(
                container,
                NodeFilter.SHOW_TEXT,
                {
                    acceptNode: function(node) {
                        let parent = node.parentElement;
                        while (parent && parent !== container) {
                            if (excludeElements.has(parent)) {
                                return NodeFilter.FILTER_REJECT;
                            }
                            // 스크립트나 스타일 태그도 제외
                            if (parent.tagName === 'SCRIPT' || parent.tagName === 'STYLE') {
                                return NodeFilter.FILTER_REJECT;
                            }
                            parent = parent.parentElement;
                        }
                        return NodeFilter.FILTER_ACCEPT;
                    }
                }
            );
            
            let node;
            let collectedLines = [];
            while (node = walker.nextNode()) {
                const nodeText = node.textContent.trim();
                if (nodeText && nodeText.length > 0) {
                    // 제외할 텍스트 패턴 확인
                    let shouldExclude = false;
                    for (const excludeText of excludeTexts) {
                        if (nodeText.includes(excludeText)) {
                            shouldExclude = true;
                            break;
                        }
                    }
                    
                    // 추가 필터링: 불필요한 텍스트 패턴
                    if (!shouldExclude) {
                        // 날짜 형식 제외 (2016. 12. 18. 등)
                        if (/^\\d{4}\\.\\s*\\d{1,2}\\.\\s*\\d{1,2}/.test(nodeText)) {
                            shouldExclude = true;
                        }
                        // 숫자만 있는 줄 제외 (123 등)
                        if (/^\\d+$/.test(nodeText)) {
                            shouldExclude = true;
                        }
                        // JSON 데이터 제외
                        if (nodeText.trim().startsWith('{') && nodeText.includes('"title"')) {
                            shouldExclude = true;
                        }
                        // 블로그명/닉네임 패턴 제외
                        if (nodeText.includes('(skalekd77)') || nodeText.includes('투영') || nodeText.includes('Too_young')) {
                            shouldExclude = true;
                        }
                        // 영어만 있는 줄 (메뉴 항목 등) 제외
                        if (/^[A-Za-z\\s\\.]+$/.test(nodeText) && nodeText.length < 30 && !nodeText.includes('\\n')) {
                            shouldExclude = true;
                        }
                        // 특수 문자만 있는 줄 제외
                        if (/^[ⓒ\\(\\)\\[\\]\\{\\}]+$/.test(nodeText)) {
                            shouldExclude = true;
                        }
                        // 카테고리, 카테고리 이동 등 제외
                        if (nodeText.includes('카테고리')) {
                            shouldExclude = true;
                        }
                        // "블로그" 포함 텍스트 제외 (메뉴 등)
                        if (nodeText.includes('블로그')) {
                            shouldExclude = true;
                        }
                        // 한글과 숫자 조합이 아닌 짧은 텍스트 제외 (메뉴 등)
                        if (nodeText.length < 5 && !/[가-힣]/.test(nodeText)) {
                            shouldExclude = true;
                        }
                    }
                    
                    // 본문은 포함 (3자 이상, 한글이 포함된 경우 우선)
                    if (!shouldExclude && nodeText.length >= 3) {
                        // 한글이 포함된 텍스트는 우선 포함
                        // 하지만 제목과 같은 짧은 텍스트는 제외
                        const hasKorean = /[가-힣]/.test(nodeText);
                        if (hasKorean && nodeText.length > 5) {
                            // 제목 패턴 제외 (숫자로 시작하는 짧은 텍스트, 예: "161217 호떡 먹고싶다")
                            if (!(/^\\d{6}\\s/.test(nodeText) && nodeText.length < 30)) {
                                collectedLines.push(nodeText);
                            }
                        } else if (nodeText.length > 10 && !hasKorean) {
                            // 영어나 기타 텍스트도 10자 이상인 경우만 포함
                            collectedLines.push(nodeText);
                        }
                    }
                }
            }
            
            // 중복 제거 및 정리
            const uniqueLines = [];
            const seen = new Set();
            for (const line of collectedLines) {
                if (!seen.has(line) && line.length > 0) {
                    seen.add(line);
                    uniqueLines.push(line);
                }
            }
            
            // 수집된 줄들을 합치기
            text = uniqueLines.join('\\n');
            
            return text.trim();
        }""", container_info.get('selector') if container_info.get('found') else None)
        
        # 텍스트 정리 (가독성 향상)
        content.text = clean_text(raw_text)
        
        # 단어 수 계산 (정리된 텍스트 기준)
        content.word_count = len(content.text.split())
        
        # 이미지 URL 추출
        images = []
        img_selectors = [
            '.se-image img',
            '.post-content img',
            'img[src]'
        ]
        for selector in img_selectors:
            try:
                img_elements = container.locator(selector).all()
                for img in img_elements:
                    src = img.get_attribute('src') or img.get_attribute('data-src') or ''
                    if src and src not in images:
                        images.append(src)
            except Exception:
                continue
        content.images = images
        
        # 링크 URL 추출
        links = []
        try:
            link_elements = container.locator('a[href]').all()
            for link in link_elements:
                href = link.get_attribute('href') or ''
                if href:
                    # 상대 경로를 절대 경로로 변환
                    if href.startswith('/'):
                        href = f"https://m.blog.naver.com{href}"
                    elif not href.startswith('http'):
                        href = f"https://m.blog.naver.com/{href}"
                    if href not in links:
                        links.append(href)
        except Exception:
            pass
        content.links = links
        
        # 마크다운 변환 (간단한 버전)
        content.markdown = html_to_markdown(content.html)
        
    except Exception as e:
        print(f"[경고] 본문 추출 중 오류: {e}")
    
    return content


def clean_text(text: str) -> str:
    """텍스트 정리 - 가독성 향상"""
    if not text:
        return ""
    
    # 연속된 줄바꿈 정리 (3개 이상 -> 2개)
    text = re.sub(r'\n{3,}', '\n\n', text)
    
    # 각 줄의 앞뒤 공백 제거
    lines = text.split('\n')
    cleaned_lines = [line.strip() for line in lines]
    
    # 연속된 빈 줄 제거 (최대 2개까지만 유지)
    result_lines = []
    prev_empty = False
    for line in cleaned_lines:
        if not line:
            if not prev_empty:
                result_lines.append('')
                prev_empty = True
        else:
            result_lines.append(line)
            prev_empty = False
    
    # 연속된 공백 정리 (탭, 공백 여러 개 -> 하나의 공백)
    result = '\n'.join(result_lines)
    result = re.sub(r'[ \t]+', ' ', result)
    
    # 시작과 끝의 줄바꿈 제거
    result = result.strip()
    
    return result


def html_to_markdown(html: str) -> str:
    """HTML을 마크다운으로 간단 변환"""
    markdown = html
    
    # 제목 변환
    markdown = re.sub(r'<h1[^>]*>(.*?)</h1>', r'# \1', markdown, flags=re.DOTALL)
    markdown = re.sub(r'<h2[^>]*>(.*?)</h2>', r'## \1', markdown, flags=re.DOTALL)
    markdown = re.sub(r'<h3[^>]*>(.*?)</h3>', r'### \1', markdown, flags=re.DOTALL)
    
    # 강조 변환
    markdown = re.sub(r'<strong[^>]*>(.*?)</strong>', r'**\1**', markdown, flags=re.DOTALL)
    markdown = re.sub(r'<b[^>]*>(.*?)</b>', r'**\1**', markdown, flags=re.DOTALL)
    markdown = re.sub(r'<em[^>]*>(.*?)</em>', r'*\1*', markdown, flags=re.DOTALL)
    
    # 링크 변환
    markdown = re.sub(r'<a[^>]*href="([^"]*)"[^>]*>(.*?)</a>', r'[\2](\1)', markdown, flags=re.DOTALL)
    
    # 이미지 변환
    markdown = re.sub(r'<img[^>]*src="([^"]*)"[^>]*>', r'![](\1)', markdown)
    
    # 줄바꿈 변환
    markdown = re.sub(r'<br[^>]*>', '\n', markdown)
    markdown = re.sub(r'<p[^>]*>', '\n', markdown)
    markdown = re.sub(r'</p>', '\n', markdown)
    
    # HTML 태그 제거
    markdown = re.sub(r'<[^>]+>', '', markdown)
    
    # 공백 정리
    markdown = re.sub(r'\n\s*\n\s*\n', '\n\n', markdown)
    
    return markdown.strip()


def extract_metadata(page: Page) -> PostMetadata:
    """메타데이터 추출 (조회수, 좋아요, 댓글 수, 카테고리)"""
    metadata = PostMetadata()
    
    # 조회수 추출
    view_selectors = [
        '.view-count',
        '.area_viewcount',
        '[data-view-count]'
    ]
    metadata.views = extract_number(page, view_selectors)
    
    # 좋아요(공감) 수 추출
    like_selectors = [
        '.u_likeit_text._count.num',
        '.u_likeit_text',
        '.like-count',
        '.area_likecount',
        '[data-like-count]',
        '.meta_foot__I5IqM .like__vTXys'
    ]
    metadata.likes = extract_number(page, like_selectors)
    
    # 댓글 수 추출
    comment_count_selectors = [
        '.comment_btn__TUucZ .num__OVfhz',
        '.num__OVfhz',
        '.comment-count',
        '.area_commentcount',
        '[data-comment-count]',
        '.meta_foot__I5IqM .comment__bWHnT'
    ]
    metadata.comments = extract_number(page, comment_count_selectors)
    
    # 카테고리 추출
    category_selectors = [
        '.category',
        '.area_category',
        '.se_category'
    ]
    for selector in category_selectors:
        try:
            element = page.locator(selector).first
            if element.count() > 0:
                metadata.category = element.text_content().strip()
                break
        except Exception:
            continue
    
    # 태그는 extract_tags에서 별도로 추출
    metadata.tags = []
    
    return metadata

