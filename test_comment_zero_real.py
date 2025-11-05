"""
실제 댓글 수가 0인 포스트로 테스트
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

def test_comment_zero_real():
    """실제 댓글 수가 0인 포스트로 테스트"""
    print("=" * 60)
    print("실제 댓글 수가 0인 포스트 테스트")
    print("=" * 60)
    
    playwright = sync_playwright().start()
    browser = playwright.chromium.launch(headless=False)
    device = playwright.devices['iPhone 12']
    context = browser.new_context(**device)
    page = context.new_page()
    
    try:
        # 여러 포스트를 확인하여 댓글이 없는 포스트 찾기
        test_urls = [
            "https://m.blog.naver.com/PostView.naver?blogId=skalekd77&logNo=224054244544",
            "https://m.blog.naver.com/PostView.naver?blogId=skalekd77&logNo=224054257169",
            "https://m.blog.naver.com/PostView.naver?blogId=skalekd77&logNo=223924349009",
        ]
        
        zero_comment_url = None
        
        # 댓글이 없는 포스트 찾기
        for test_url in test_urls:
            print(f"\n🔍 포스트 확인: {test_url}")
            page.goto(test_url, wait_until='domcontentloaded', timeout=30000)
            time.sleep(3)
            
            metadata = extract_metadata(page)
            comment_count = metadata.comments
            print(f"  - 댓글 수: {comment_count}")
            
            if comment_count == 0:
                zero_comment_url = test_url
                print("  ✅ 댓글이 없는 포스트 발견!")
                break
        
        if zero_comment_url:
            print(f"\n📄 댓글 수가 0인 포스트 테스트: {zero_comment_url}")
            
            # 1. extract_comments 직접 테스트
            print("\n1️⃣ extract_comments 함수 직접 테스트")
            page.goto(zero_comment_url, wait_until='domcontentloaded', timeout=30000)
            time.sleep(3)
            
            metadata = extract_metadata(page)
            comment_count = metadata.comments
            print(f"  - 댓글 수: {comment_count}")
            
            start_time = time.time()
            comments = extract_comments(page, comment_count=comment_count)
            elapsed_time = time.time() - start_time
            
            print(f"  - 수집된 댓글 수: {len(comments)}")
            print(f"  - 소요 시간: {elapsed_time:.2f}초")
            
            if len(comments) == 0 and elapsed_time < 2.0:
                print("  ✅ 테스트 통과: 댓글 수집을 건너뛰고 빠르게 반환됨")
            else:
                print(f"  ❌ 테스트 실패: 댓글 수집을 건너뛰지 않았거나 시간이 오래 걸림")
            
            # 2. crawl_post_detail_mobile 전체 테스트
            print("\n2️⃣ crawl_post_detail_mobile 전체 테스트")
            start_time = time.time()
            post = crawl_post_detail_mobile(page, zero_comment_url, timeout=30, blog_id="skalekd77")
            elapsed_time = time.time() - start_time
            
            print(f"  - 포스트 제목: {post.title[:50] if post.title else 'N/A'}...")
            print(f"  - 댓글 수: {len(post.comments)}")
            print(f"  - 소요 시간: {elapsed_time:.2f}초")
            
            if len(post.comments) == 0 and elapsed_time < 10.0:
                print("  ✅ 테스트 통과: 댓글 수가 0인 경우 댓글 수집을 건너뛰고 빠르게 완료됨")
            else:
                print(f"  ⚠️  확인 필요: 댓글 수집 시간 또는 결과 확인 필요")
        else:
            print("\n⚠️  댓글이 없는 포스트를 찾지 못했습니다.")
            print("   테스트를 위해 댓글이 없는 포스트가 필요합니다.")
    
    except Exception as e:
        import traceback
        print(f"\n❌ 오류 발생: {e}")
        traceback.print_exc()
    
    finally:
        browser.close()
        playwright.stop()
    
    print("\n" + "=" * 60)
    print("테스트 완료")
    print("=" * 60)

if __name__ == "__main__":
    test_comment_zero_real()

