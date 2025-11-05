"""
비밀 댓글 처리 기능 테스트
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

def test_secret_comment():
    """비밀 댓글 처리 기능 테스트"""
    print("=" * 60)
    print("비밀 댓글 처리 기능 테스트")
    print("=" * 60)
    
    # 비밀 댓글이 있는 포스트 URL (이미지에서 확인된 6개 댓글 모두 비밀 댓글)
    # 실제 URL은 사용자가 제공해야 함
    test_url = "https://m.blog.naver.com/PostView.naver?blogId=skalekd77&logNo=220888708277"
    
    playwright = sync_playwright().start()
    browser = playwright.chromium.launch(headless=False)
    device = playwright.devices['iPhone 12']
    context = browser.new_context(**device)
    page = context.new_page()
    
    try:
        print(f"\n📄 테스트 포스트: {test_url}")
        
        # 포스트 페이지 접속
        page.goto(test_url, wait_until='domcontentloaded', timeout=30000)
        time.sleep(3)
        
        # 메타데이터 추출 (댓글 수 확인)
        metadata = extract_metadata(page)
        comment_count = metadata.comments
        
        print(f"  - 댓글 수: {comment_count}")
        
        if comment_count > 0:
            print(f"\n🧪 댓글 수집 테스트 (비밀 댓글 확인)")
            
            # 댓글 수집 시도
            start_time = time.time()
            comments = extract_comments(page, comment_count=comment_count)
            elapsed_time = time.time() - start_time
            
            print(f"  - 수집된 댓글 수: {len(comments)}")
            print(f"  - 소요 시간: {elapsed_time:.2f}초")
            
            # 비밀 댓글 확인
            secret_count = sum(1 for c in comments if '비밀 댓글입니다.' in (c.content or ''))
            normal_count = len(comments) - secret_count
            
            print(f"  - 비밀 댓글 수: {secret_count}")
            print(f"  - 일반 댓글 수: {normal_count}")
            
            if secret_count == 0 and comment_count > 0:
                print("  ✅ 테스트 통과: 비밀 댓글을 건너뛰고 일반 댓글만 수집")
            elif len(comments) == 0 and comment_count > 0:
                print("  ✅ 테스트 통과: 모든 댓글이 비밀 댓글이므로 수집 건너뛰기")
            else:
                print(f"  ⚠️  확인 필요: 비밀 댓글 처리 상태 확인")
            
            # 전체 크롤링 테스트
            print(f"\n🧪 전체 크롤링 테스트")
            page.goto(test_url, wait_until='domcontentloaded', timeout=30000)
            time.sleep(3)
            
            start_time = time.time()
            post = crawl_post_detail_mobile(page, test_url, timeout=30, blog_id="skalekd77")
            elapsed_time = time.time() - start_time
            
            print(f"  - 포스트 제목: {post.title[:50] if post.title else 'N/A'}...")
            print(f"  - 수집된 댓글 수: {len(post.comments)}")
            print(f"  - 소요 시간: {elapsed_time:.2f}초")
            
            secret_in_post = sum(1 for c in post.comments if '비밀 댓글입니다.' in (c.content or ''))
            print(f"  - 비밀 댓글 수: {secret_in_post}")
            
            if secret_in_post == 0:
                print("  ✅ 테스트 통과: 비밀 댓글을 건너뛰고 일반 댓글만 수집")
            else:
                print(f"  ⚠️  비밀 댓글이 수집됨: {secret_in_post}개")
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
    test_secret_comment()

