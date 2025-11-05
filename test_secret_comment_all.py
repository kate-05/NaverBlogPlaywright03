"""
모든 댓글이 비밀 댓글인 경우 테스트
"""
import sys
from pathlib import Path

# 프로젝트 루트를 path에 추가
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from playwright.sync_api import sync_playwright
from src.crawler.parser import extract_metadata, extract_comments
from src.crawler.engine import crawl_post_detail_mobile
import time

def test_secret_comment_all():
    """모든 댓글이 비밀 댓글인 경우 테스트"""
    print("=" * 60)
    print("모든 댓글이 비밀 댓글인 경우 테스트")
    print("=" * 60)
    
    # 이미지에서 확인된 댓글 6개 모두 비밀 댓글인 포스트 찾기
    # 실제 URL은 사용자가 제공하거나, 여러 포스트를 확인해야 함
    test_urls = [
        "https://m.blog.naver.com/PostView.naver?blogId=skalekd77&logNo=220888708277",
        # 추가 URL 필요
    ]
    
    playwright = sync_playwright().start()
    browser = playwright.chromium.launch(headless=False)
    device = playwright.devices['iPhone 12']
    context = browser.new_context(**device)
    page = context.new_page()
    
    try:
        for test_url in test_urls:
            print(f"\n📄 테스트 포스트: {test_url}")
            
            page.goto(test_url, wait_until='domcontentloaded', timeout=30000)
            time.sleep(3)
            
            # 메타데이터 추출
            metadata = extract_metadata(page)
            comment_count = metadata.comments
            
            print(f"  - 댓글 수: {comment_count}")
            
            if comment_count > 0:
                # 댓글 버튼 클릭하여 비밀 댓글 확인
                comment_button = page.locator('button.comment_btn__TUucZ[data-click-area="pst.re"]').first
                if comment_button.count() > 0:
                    comment_button.click()
                    time.sleep(3)
                    
                    # 댓글 영역 텍스트 확인
                    comment_area = page.locator('#naverComment_wai_u_cbox_content_wrap_tabpanel, [role="tabpanel"], .u_cbox_list').first
                    if comment_area.count() > 0:
                        area_text = comment_area.text_content() or ''
                        secret_count = area_text.count('비밀 댓글입니다.')
                        comment_items = page.locator('li.u_cbox_comment, .u_cbox_comment')
                        item_count = comment_items.count()
                        
                        print(f"  - 댓글 아이템 수: {item_count}")
                        print(f"  - '비밀 댓글입니다.' 텍스트 개수: {secret_count}")
                        
                        if item_count > 0 and secret_count >= item_count:
                            print(f"  ✅ 모든 댓글이 비밀 댓글입니다!")
                            
                            # extract_comments 테스트
                            print(f"\n🧪 extract_comments 함수 테스트")
                            start_time = time.time()
                            comments = extract_comments(page, comment_count=comment_count)
                            elapsed_time = time.time() - start_time
                            
                            print(f"  - 수집된 댓글 수: {len(comments)}")
                            print(f"  - 소요 시간: {elapsed_time:.2f}초")
                            
                            if len(comments) == 0 and elapsed_time < 5.0:
                                print("  ✅ 테스트 통과: 모든 댓글이 비밀 댓글이므로 빠르게 건너뛰기")
                            else:
                                print(f"  ⚠️  확인 필요: 시간이 오래 걸리거나 댓글이 수집됨")
                            
                            # 전체 크롤링 테스트
                            print(f"\n🧪 전체 크롤링 테스트")
                            page.goto(test_url, wait_until='domcontentloaded', timeout=30000)
                            time.sleep(3)
                            
                            start_time = time.time()
                            post = crawl_post_detail_mobile(page, test_url, timeout=30, blog_id="skalekd77")
                            elapsed_time = time.time() - start_time
                            
                            print(f"  - 수집된 댓글 수: {len(post.comments)}")
                            print(f"  - 소요 시간: {elapsed_time:.2f}초")
                            
                            if len(post.comments) == 0:
                                print("  ✅ 테스트 통과: 모든 댓글이 비밀 댓글이므로 수집하지 않음")
                            else:
                                print(f"  ⚠️  댓글이 수집됨: {len(post.comments)}개")
                            
                            break  # 첫 번째 모든 댓글이 비밀 댓글인 포스트를 찾으면 종료
        
        print("\n" + "=" * 60)
        print("테스트 완료")
        print("=" * 60)
        
    except Exception as e:
        import traceback
        print(f"\n❌ 오류 발생: {e}")
        traceback.print_exc()
    
    finally:
        browser.close()
        playwright.stop()

if __name__ == "__main__":
    test_secret_comment_all()

