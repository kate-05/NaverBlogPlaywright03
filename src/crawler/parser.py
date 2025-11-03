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


def extract_comments(page: Page) -> List[Comment]:
    """댓글 추출 (댓글 버튼 클릭 후)"""
    comments = []
    
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
        time.sleep(5)  # 댓글 로딩 대기
        time.sleep(2)  # 추가 안정화 대기
    except Exception:
        return comments
    
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
                }
                
                // 날짜 추출
                let dateText = '';
                const itemText = item.textContent || '';
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
                    author_elem = item.locator('span.u_cbox_nick').first
                    author = author_elem.text_content().strip() if author_elem.count() > 0 else ''
                    
                    content_elem = item.locator('span.u_cbox_contents').first
                    content = content_elem.text_content().strip() if content_elem.count() > 0 else ''
                    
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
    """본문 내용 추출"""
    content = PostContent()
    
    # 본문 컨테이너 찾기
    content_selectors = [
        '.se-main-container',
        '.post-content',
        '.area_view',
        '.post-view',
        '#postViewArea',
        '.post-view-area',
        '.se-component-content',
        'article',
        '.post_body',
        'main',
        'body'
    ]
    
    container = None
    for selector in content_selectors:
        try:
            element = page.locator(selector).first
            if element.count() > 0:
                container = element
                break
        except Exception:
            continue
    
    if not container:
        container = page.locator('body')
    
    try:
        # HTML 추출
        content.html = container.inner_html()
        
        # 텍스트 추출
        content.text = container.text_content() or ""
        
        # 단어 수 계산
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

