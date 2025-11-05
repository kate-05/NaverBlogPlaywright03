"""
실제 재개 기능 테스트 (1개 포스트만)
"""
import sys
from pathlib import Path

# 프로젝트 루트를 path에 추가
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.utils.checkpoint_manager import CheckpointManager
from src.crawler.batch_crawler import resume_crawling

def test_resume_real():
    """실제 재개 기능 테스트 (1개 포스트만)"""
    print("=" * 60)
    print("실제 재개 기능 테스트 (1개 포스트만)")
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
    
    checkpoint_manager = CheckpointManager()
    
    # 재개 테스트 (1개 포스트만 크롤링)
    output_path = f"output/test_resume_{Path(checkpoint_path).stem}.json"
    
    print(f"\n🔄 재개 시작...")
    print(f"출력 파일: {output_path}")
    print(f"\n⚠️  주의: 1개 포스트만 크롤링하고 중단합니다.")
    
    try:
        # 재개 실행
        new_posts = resume_crawling(
            str(checkpoint_path),
            output_path,
            checkpoint_manager,
            delay=0.5,
            timeout=30
        )
        
        print(f"\n✅ 재개 완료: {len(new_posts)}개 새 포스트 크롤링됨")
        
    except KeyboardInterrupt:
        print("\n⚠️  사용자에 의해 중단되었습니다.")
    except Exception as e:
        import traceback
        print(f"\n❌ 오류 발생: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    test_resume_real()

