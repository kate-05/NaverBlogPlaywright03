"""
재개 기능 테스트 스크립트
"""
import sys
from pathlib import Path

# 프로젝트 루트를 path에 추가
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.utils.checkpoint_manager import CheckpointManager
from src.crawler.batch_crawler import resume_crawling

def test_resume():
    """재개 기능 테스트"""
    print("=" * 60)
    print("재개 기능 테스트 시작")
    print("=" * 60)
    
    # 체크포인트 파일 찾기
    checkpoint_dir = Path("checkpoints")
    checkpoint_files = sorted(checkpoint_dir.glob("*.json"), key=lambda x: x.stat().st_mtime, reverse=True)
    
    if not checkpoint_files:
        print("❌ 체크포인트 파일이 없습니다.")
        return
    
    # 가장 최근 체크포인트 파일 사용
    checkpoint_path = checkpoint_files[0]
    print(f"\n📁 체크포인트 파일: {checkpoint_path}")
    
    # 체크포인트 내용 확인
    checkpoint_manager = CheckpointManager()
    checkpoint_data = checkpoint_manager.load_checkpoint(str(checkpoint_path))
    
    print(f"\n📊 체크포인트 정보:")
    print(f"  - 블로그 ID 수: {len(checkpoint_data.get('blog_ids', []))}")
    print(f"  - 처리된 블로그: {checkpoint_data.get('processed_blog_ids', 0)}")
    print(f"  - 상태: {checkpoint_data.get('status', 'unknown')}")
    
    blog_progress = checkpoint_data.get('blog_progress', [])
    print(f"\n📋 블로그 진행 상황:")
    for bp in blog_progress:
        blog_id = bp.get('blog_id', 'unknown')
        status = bp.get('status', 'unknown')
        posts_crawled = bp.get('posts_crawled', 0)
        all_urls = bp.get('all_post_urls', [])
        crawled_urls = bp.get('crawled_urls', [])
        
        print(f"  - {blog_id}:")
        print(f"    상태: {status}")
        print(f"    크롤링된 포스트: {posts_crawled}개")
        print(f"    전체 링크: {len(all_urls) if all_urls else 0}개")
        print(f"    크롤링된 URL: {len(crawled_urls)}개")
        if all_urls and crawled_urls:
            remaining = len(all_urls) - len(crawled_urls)
            print(f"    남은 포스트: {remaining}개")
    
    # 재개 테스트 (실제 크롤링은 하지 않고 정보만 확인)
    print(f"\n🔄 재개 테스트 (정보 확인만)")
    
    # 미완료 블로그 찾기 (수정된 로직 적용)
    blog_ids = checkpoint_data.get("blog_ids", [])
    
    # 완료된 블로그 찾기 (실제로 모든 포스트를 크롤링했는지 확인)
    completed_blog_ids = set()
    for bp in blog_progress:
        if bp.get("status") == "completed":
            blog_id = bp.get("blog_id")
            all_urls = bp.get("all_post_urls", [])
            crawled_urls = bp.get("crawled_urls", [])
            
            # 전체 링크가 있고, 크롤링된 URL 수가 전체 링크 수와 같으면 완료
            if all_urls and len(crawled_urls) >= len(all_urls):
                completed_blog_ids.add(blog_id)
            # 전체 링크가 없거나 크롤링된 URL이 더 적으면 미완료
            else:
                print(f"  ⚠️  블로그 {blog_id}: 상태가 'completed'이지만 미완료 포스트가 있습니다.")
                print(f"     전체 링크: {len(all_urls) if all_urls else 0}개, 크롤링됨: {len(crawled_urls)}개")
    
    remaining_blog_ids = [
        blog_id for blog_id in blog_ids 
        if blog_id not in completed_blog_ids
    ]
    
    print(f"  - 미완료 블로그: {len(remaining_blog_ids)}개")
    for blog_id in remaining_blog_ids:
        blog_prog = next((bp for bp in blog_progress if bp.get("blog_id") == blog_id), None)
        if blog_prog:
            all_urls = blog_prog.get("all_post_urls", [])
            crawled = blog_prog.get("crawled_urls", [])
            remaining = len(all_urls) - len(crawled) if all_urls else 0
            print(f"    {blog_id}: 전체 링크 {len(all_urls) if all_urls else 0}개, 크롤링됨 {len(crawled)}개, 남은 포스트 {remaining}개")
        else:
            print(f"    {blog_id}: 진행 상황 정보 없음")
    
    print("\n" + "=" * 60)
    print("테스트 완료")
    print("=" * 60)

if __name__ == "__main__":
    test_resume()

