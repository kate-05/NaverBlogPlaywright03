"""
단일 포스트 테스트 스크립트
"""
import sys
from pathlib import Path

project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from playwright.sync_api import sync_playwright
from src.crawler.engine import extract_title, extract_post_id_from_url
from src.crawler.parser import extract_content


def test_single_post():
    """단일 포스트 테스트"""
    url = "https://m.blog.naver.com/PostView.naver?blogId=skalekd77&logNo=220888708277"
    
    print("=" * 60)
    print("단일 포스트 테스트")
    print("=" * 60)
    print(f"URL: {url}")
    print()
    
    playwright = sync_playwright().start()
    browser = playwright.chromium.launch(headless=False)
    page = browser.new_page()
    
    try:
        # 페이지 접속
        page.goto(url, wait_until='domcontentloaded', timeout=30000)
        import time
        time.sleep(3)  # 로딩 대기
        
        # 페이지 구조 디버깅
        print("=== 페이지 구조 확인 ===")
        page_info = page.evaluate("""() => {
            const info = {
                title: document.title,
                h1Elements: [],
                postSubjectElements: [],
                contentElements: []
            };
            
            // H1 요소들
            document.querySelectorAll('h1').forEach((h, i) => {
                info.h1Elements.push({
                    index: i,
                    text: h.textContent.trim(),
                    className: h.className,
                    id: h.id
                });
            });
            
            // .post_subject 요소들
            document.querySelectorAll('.post_subject').forEach((el, i) => {
                info.postSubjectElements.push({
                    index: i,
                    text: el.textContent.trim(),
                    className: el.className
                });
            });
            
            // 본문 컨테이너들
            const contentSelectors = [
                '.se-main-container',
                '.se-component-content',
                '#postViewArea',
                '.post-view-area',
                '.post-content',
                '.area_view'
            ];
            
            contentSelectors.forEach(selector => {
                const elem = document.querySelector(selector);
                if (elem) {
                    const text = elem.textContent.trim();
                    info.contentElements.push({
                        selector: selector,
                        textLength: text.length,
                        textPreview: text.substring(0, 100)
                    });
                }
            });
            
            return info;
        }""")
        
        print(f"페이지 제목: {page_info['title']}")
        print(f"\nH1 요소들:")
        for h1 in page_info['h1Elements']:
            print(f"  [{h1['index']}] {h1['text']} (class: {h1['className']}, id: {h1['id']})")
        
        print(f"\n.post_subject 요소들:")
        for subj in page_info['postSubjectElements']:
            print(f"  [{subj['index']}] {subj['text']}")
        
        print(f"\n본문 컨테이너들:")
        for cont in page_info['contentElements']:
            print(f"  [{cont['selector']}] 길이: {cont['textLength']}, 미리보기: {cont['textPreview']}")
        
        print()
        print("=== 추출 테스트 ===")
        
        # 제목 추출
        title = extract_title(page)
        print(f"\n제목: '{title}'")
        print(f"제목 길이: {len(title)}")
        
        # 본문 추출
        content = extract_content(page)
        print(f"\n본문 길이: {len(content.text)}자")
        print(f"\n본문 전체:")
        print("-" * 60)
        print(content.text)
        print("-" * 60)
        
    finally:
        browser.close()
        playwright.stop()


if __name__ == "__main__":
    test_single_post()

