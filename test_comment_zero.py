"""
댓글 수가 0인 경우 댓글 수집 건너뛰기 기능 테스트
"""
import sys
from pathlib import Path

# 프로젝트 루트를 path에 추가
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from playwright.sync_api import sync_playwright
from src.crawler.parser import extract_metadata, extract_comments
import time

def test_comment_zero():
    """댓글 수가 0인 포스트 테스트"""
    print("=" * 60)
    print("댓글 수가 0인 경우 댓글 수집 건너뛰기 테스트")
    print("=" * 60)
    
    # 테스트할 포스트 URL (다양한 포스트 테스트)
    test_urls = [
        "https://m.blog.naver.com/PostView.naver?blogId=skalekd77&logNo=224054238709",  # 댓글 있음
        "https://m.blog.naver.com/PostView.naver?blogId=skalekd77&logNo=220888708277",  # 댓글 있음
        # 댓글이 없는 포스트를 찾기 위해 여러 포스트 테스트
    ]
    
    playwright = sync_playwright().start()
    browser = playwright.chromium.launch(headless=False)
    device = playwright.devices['iPhone 12']
    context = browser.new_context(**device)
    page = context.new_page()
    
    try:
        for test_url in test_urls:
            print(f"\n📄 테스트 포스트: {test_url}")
            
            # 포스트 페이지 접속
            page.goto(test_url, wait_until='domcontentloaded', timeout=30000)
            time.sleep(3)
            
            # 메타데이터 추출 (댓글 수 확인)
            metadata = extract_metadata(page)
            comment_count = metadata.comments
            
            print(f"  - 댓글 수: {comment_count}")
            
            # 댓글 수집 시도 (comment_count 파라미터 전달)
            start_time = time.time()
            comments = extract_comments(page, comment_count=comment_count)
            elapsed_time = time.time() - start_time
            
            print(f"  - 수집된 댓글 수: {len(comments)}")
            print(f"  - 소요 시간: {elapsed_time:.2f}초")
            
            if comment_count == 0:
                if len(comments) == 0 and elapsed_time < 2.0:
                    print("  ✅ 테스트 통과: 댓글 수가 0이므로 댓글 수집을 건너뛰고 빠르게 반환됨")
                else:
                    print(f"  ❌ 테스트 실패: 댓글 수집을 건너뛰지 않았거나 시간이 오래 걸림 (시간: {elapsed_time:.2f}초)")
            else:
                if len(comments) > 0 or elapsed_time > 5.0:
                    print(f"  ✅ 댓글 수집 정상 (댓글 수: {comment_count}, 수집: {len(comments)})")
                else:
                    print(f"  ⚠️  댓글 수집 확인 필요 (댓글 수: {comment_count}, 수집: {len(comments)})")
            
            print("-" * 60)
        
        # 댓글 수가 0인 경우 직접 테스트 (시뮬레이션)
        print("\n🧪 댓글 수가 0인 경우 직접 테스트 (시뮬레이션)")
        test_url = "https://m.blog.naver.com/PostView.naver?blogId=skalekd77&logNo=224054238709"
        page.goto(test_url, wait_until='domcontentloaded', timeout=30000)
        time.sleep(3)
        
        # comment_count를 0으로 강제 설정하여 테스트
        start_time = time.time()
        comments = extract_comments(page, comment_count=0)
        elapsed_time = time.time() - start_time
        
        print(f"  - 댓글 수: 0 (시뮬레이션)")
        print(f"  - 수집된 댓글 수: {len(comments)}")
        print(f"  - 소요 시간: {elapsed_time:.2f}초")
        
        if len(comments) == 0 and elapsed_time < 2.0:
            print("  ✅ 테스트 통과: comment_count=0일 때 댓글 수집을 건너뛰고 빠르게 반환됨")
        else:
            print(f"  ❌ 테스트 실패: 댓글 수집을 건너뛰지 않았거나 시간이 오래 걸림")
            
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
    test_comment_zero()
