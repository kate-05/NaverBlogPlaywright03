"""
댓글 수 추출 정확도 테스트
"""
import sys
from pathlib import Path

# 프로젝트 루트를 path에 추가
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from playwright.sync_api import sync_playwright
from src.crawler.parser import extract_metadata, extract_comments
import time

def test_comment_extraction():
    """댓글 수 추출 정확도 테스트"""
    print("=" * 60)
    print("댓글 수 추출 정확도 테스트")
    print("=" * 60)
    
    playwright = sync_playwright().start()
    browser = playwright.chromium.launch(headless=False)
    device = playwright.devices['iPhone 12']
    context = browser.new_context(**device)
    page = context.new_page()
    
    try:
        # 다양한 댓글 수를 가진 포스트 테스트
        test_cases = [
            {
                "url": "https://m.blog.naver.com/PostView.naver?blogId=skalekd77&logNo=224054244544",
                "expected_comments": 0,
                "description": "댓글 없음"
            },
            {
                "url": "https://m.blog.naver.com/PostView.naver?blogId=skalekd77&logNo=224054238709",
                "expected_comments": 1,
                "description": "댓글 1개"
            },
            {
                "url": "https://m.blog.naver.com/PostView.naver?blogId=skalekd77&logNo=220888708277",
                "expected_comments": 49,
                "description": "댓글 49개"
            }
        ]
        
        for i, test_case in enumerate(test_cases, 1):
            print(f"\n📄 테스트 케이스 {i}: {test_case['description']}")
            print(f"   URL: {test_case['url']}")
            
            page.goto(test_case['url'], wait_until='domcontentloaded', timeout=30000)
            time.sleep(3)
            
            # 댓글 수 추출
            metadata = extract_metadata(page)
            extracted_count = metadata.comments
            
            print(f"  - 추출된 댓글 수: {extracted_count}")
            print(f"  - 예상 댓글 수: {test_case['expected_comments']}")
            
            # 댓글 수가 0인 경우 댓글 수집 건너뛰기 테스트
            if extracted_count == 0:
                start_time = time.time()
                comments = extract_comments(page, comment_count=extracted_count)
                elapsed_time = time.time() - start_time
                
                print(f"  - 수집된 댓글 수: {len(comments)}")
                print(f"  - 소요 시간: {elapsed_time:.2f}초")
                
                if elapsed_time < 2.0:
                    print("  ✅ 댓글 수가 0이므로 댓글 수집을 건너뛰고 빠르게 반환됨")
                else:
                    print(f"  ❌ 댓글 수집을 건너뛰지 않았거나 시간이 오래 걸림")
            else:
                print(f"  - 댓글 수가 {extracted_count}개이므로 댓글 수집 진행")
                
                # 댓글 수 추출 정확도 확인
                if extracted_count == test_case['expected_comments']:
                    print("  ✅ 댓글 수 추출 정확")
                else:
                    print(f"  ⚠️  댓글 수 추출 차이 (예상: {test_case['expected_comments']}, 추출: {extracted_count})")
            
            print("-" * 60)
    
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
    test_comment_extraction()

