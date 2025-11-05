"""
비밀 댓글 처리 속도 테스트
"""
import sys
from pathlib import Path
import time

# 프로젝트 루트를 path에 추가
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from playwright.sync_api import sync_playwright
from src.crawler.parser import extract_metadata, extract_comments
from src.crawler.engine import crawl_post_detail_mobile

def test_secret_comment_speed():
    """비밀 댓글 처리 속도 테스트"""
    print("=" * 60)
    print("비밀 댓글 처리 속도 테스트")
    print("=" * 60)
    
    # 비밀 댓글이 있는 포스트 URL
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
        time.sleep(2)
        
        # 메타데이터 추출
        metadata = extract_metadata(page)
        comment_count = metadata.comments
        
        print(f"  - 댓글 수: {comment_count}")
        
        if comment_count > 0:
            print(f"\n🧪 댓글 수집 속도 테스트")
            
            # 댓글 수집 시도 및 시간 측정
            start_time = time.time()
            comments, is_secret_only = extract_comments(page, comment_count=comment_count)
            elapsed_time = time.time() - start_time
            
            print(f"  - 수집된 댓글 수: {len(comments)}")
            print(f"  - 비밀 댓글 여부: {is_secret_only}")
            print(f"  - 소요 시간: {elapsed_time:.2f}초")
            
            if is_secret_only:
                if elapsed_time < 1.0:
                    print(f"  ✅ 테스트 통과: 비밀 댓글 확인 후 빠르게 건너뛰기 ({elapsed_time:.2f}초)")
                else:
                    print(f"  ⚠️  속도 개선 필요: 비밀 댓글 확인 후 {elapsed_time:.2f}초 소요 (1초 이상)")
            else:
                print(f"  ℹ️  일반 댓글이 포함되어 있습니다.")
            
            # 전체 크롤링 속도 테스트
            print(f"\n🧪 전체 크롤링 속도 테스트")
            page.goto(test_url, wait_until='domcontentloaded', timeout=30000)
            time.sleep(2)
            
            start_time = time.time()
            post = crawl_post_detail_mobile(page, test_url, timeout=30, blog_id="skalekd77")
            elapsed_time = time.time() - start_time
            
            print(f"  - 포스트 제목: {post.title[:50] if post.title else 'N/A'}...")
            print(f"  - 수집된 댓글 수: {len(post.comments)}")
            print(f"  - 소요 시간: {elapsed_time:.2f}초")
            
            if elapsed_time < 5.0:
                print(f"  ✅ 테스트 통과: 전체 크롤링이 빠르게 완료됨 ({elapsed_time:.2f}초)")
            else:
                print(f"  ⚠️  속도 개선 필요: 전체 크롤링에 {elapsed_time:.2f}초 소요")
        else:
            print("  ⚠️  댓글이 없는 포스트입니다.")
            
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
    test_secret_comment_speed()

