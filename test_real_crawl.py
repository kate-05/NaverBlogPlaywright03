"""
실제 크롤링 테스트 스크립트
블로그 ID: koding2002
"""
import sys
from pathlib import Path
from datetime import datetime

# 프로젝트 루트를 path에 추가
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.crawler.engine import crawl_by_blog_id
from src.utils.file_exporter import export_to_json


def test_crawl_koding2002():
    """koding2002 블로그 크롤링 테스트"""
    print("=" * 60)
    print("네이버 블로그 크롤러 - 실제 크롤링 테스트")
    print("=" * 60)
    print(f"블로그 ID: koding2002")
    print(f"최대 포스트 수: 5개 (테스트용)")
    print("=" * 60)
    print()
    
    try:
        # 크롤링 시작
        print("[시작] 크롤링을 시작합니다...")
        print()
        
        blog_info, posts = crawl_by_blog_id(
            blog_id="koding2002",
            max_posts=5,  # 테스트용으로 5개만 수집
            delay=0.5,
            timeout=30
        )
        
        print()
        print("=" * 60)
        print("크롤링 결과")
        print("=" * 60)
        print(f"블로그 ID: {blog_info.get('blog_id', 'N/A')}")
        print(f"블로그 이름: {blog_info.get('blog_name', 'N/A')}")
        print(f"수집된 포스트 수: {len(posts)}개")
        print()
        
        # 수집된 포스트 정보 출력
        for idx, post in enumerate(posts, 1):
            print(f"[{idx}] {post.title}")
            print(f"    - URL: {post.url}")
            print(f"    - 작성일: {post.published_date}")
            print(f"    - 조회수: {post.metadata.views}, 좋아요: {post.metadata.likes}, 댓글: {post.metadata.comments}")
            print(f"    - 해시태그: {len(post.metadata.tags)}개 {post.metadata.tags[:3] if post.metadata.tags else []}")
            print(f"    - 댓글 수: {len(post.comments)}개")
            print()
        
        # 결과 파일로 저장
        output_path = f"output/test_crawl_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        crawl_info = {
            "crawl_type": "blog_id",
            "blog_id": "koding2002",
            "total_posts": len(posts),
            "test_mode": True
        }
        
        export_path = export_to_json(posts, output_path, crawl_info)
        print(f"✓ 결과 파일 저장: {export_path}")
        print()
        print("=" * 60)
        print("✓ 크롤링 테스트 완료!")
        print("=" * 60)
        
        return True
        
    except Exception as e:
        print()
        print("=" * 60)
        print("✗ 크롤링 실패")
        print("=" * 60)
        print(f"오류: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_crawl_koding2002()
    exit(0 if success else 1)

