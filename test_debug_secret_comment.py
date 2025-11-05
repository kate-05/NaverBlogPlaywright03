"""
비밀 댓글 디버깅 테스트
"""
import sys
from pathlib import Path
import time

# 프로젝트 루트를 path에 추가
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from playwright.sync_api import sync_playwright

def debug_secret_comment():
    """비밀 댓글 구조 디버깅"""
    print("=" * 60)
    print("비밀 댓글 구조 디버깅")
    print("=" * 60)
    
    test_url = "https://m.blog.naver.com/skalekd77/220544641966"
    
    playwright = sync_playwright().start()
    browser = playwright.chromium.launch(headless=False)
    device = playwright.devices['iPhone 12']
    context = browser.new_context(**device)
    page = context.new_page()
    
    try:
        print(f"\n📄 테스트 포스트: {test_url}")
        
        # 포스트 페이지 접속
        page.goto(test_url, wait_until='domcontentloaded', timeout=30000)
        time.sleep(3)  # 페이지 로딩 대기
        
        # 댓글 버튼 찾기 및 클릭
        comment_button = None
        selectors = [
            'button.comment_btn__TUucZ[data-click-area="pst.re"]',
            'button.comment_btn__TUucZ',
            'button[data-click-area*="re"]'
        ]
        
        for selector in selectors:
            try:
                element = page.locator(selector).first
                if element.count() > 0:
                    comment_button = element
                    break
            except Exception:
                continue
        
        if comment_button:
            print("✅ 댓글 버튼 찾음")
            comment_button.click()
            time.sleep(1)  # 댓글 영역 로딩 대기
            
            # 페이지 구조 확인
            page_structure = page.evaluate("""() => {
                const result = {
                    pageText: document.body.textContent || '',
                    hasSecretComment: document.body.textContent.includes('비밀 댓글입니다.'),
                    commentAreas: [],
                    commentItems: []
                };
                
                // 댓글 영역 찾기
                const selectors = [
                    '#naverComment_wai_u_cbox_content_wrap_tabpanel',
                    '[role="tabpanel"]',
                    '.u_cbox_list',
                    '.u_cbox_content_wrap',
                    '#cbox_module',
                    '.u_cbox',
                    '[id*="comment"]',
                    '[class*="comment"]'
                ];
                
                selectors.forEach(selector => {
                    const elem = document.querySelector(selector);
                    if (elem) {
                        result.commentAreas.push({
                            selector: selector,
                            text: elem.textContent || '',
                            hasSecret: (elem.textContent || '').includes('비밀 댓글입니다.')
                        });
                    }
                });
                
                // 댓글 아이템 찾기
                const commentItems = document.querySelectorAll('li.u_cbox_comment, .u_cbox_comment, .u_cbox_list_item, li');
                commentItems.forEach((item, index) => {
                    if (index < 10) {  // 처음 10개만
                        const text = item.textContent || '';
                        result.commentItems.push({
                            index: index,
                            text: text.substring(0, 100),  // 처음 100자만
                            hasSecret: text.includes('비밀 댓글입니다.')
                        });
                    }
                });
                
                return result;
            }""")
            
            print(f"\n📊 페이지 구조 분석:")
            print(f"  - 페이지에 '비밀 댓글입니다' 포함: {page_structure['hasSecretComment']}")
            print(f"  - 댓글 영역 수: {len(page_structure['commentAreas'])}")
            for area in page_structure['commentAreas']:
                print(f"    * {area['selector']}: '비밀 댓글입니다' 포함 = {area['hasSecret']}")
                print(f"      텍스트: {area['text'][:100]}...")
            
            print(f"\n  - 댓글 아이템 수: {len(page_structure['commentItems'])}")
            for item in page_structure['commentItems']:
                print(f"    * 아이템 {item['index']}: '비밀 댓글입니다' 포함 = {item['hasSecret']}")
                print(f"      텍스트: {item['text']}")
            
            # 페이지 텍스트 샘플
            page_text = page_structure['pageText']
            if '비밀 댓글입니다' in page_text:
                print(f"\n✅ 페이지에 '비밀 댓글입니다' 발견!")
                # 주변 텍스트 확인
                idx = page_text.find('비밀 댓글입니다')
                start = max(0, idx - 50)
                end = min(len(page_text), idx + 100)
                print(f"  주변 텍스트: ...{page_text[start:end]}...")
            
        else:
            print("❌ 댓글 버튼을 찾을 수 없습니다.")
        
    except Exception as e:
        import traceback
        print(f"\n❌ 오류 발생: {e}")
        traceback.print_exc()
    
    finally:
        input("\nEnter를 누르면 브라우저를 닫습니다...")
        browser.close()
        playwright.stop()
    
    print("\n" + "=" * 60)
    print("디버깅 완료")
    print("=" * 60)

if __name__ == "__main__":
    debug_secret_comment()

