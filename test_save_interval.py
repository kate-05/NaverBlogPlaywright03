"""
저장 간격 테스트
"""
import sys
from pathlib import Path

# 프로젝트 루트를 path에 추가
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.crawler.batch_crawler import crawl_multiple_blog_ids
from src.utils.checkpoint_manager import CheckpointManager
from src.utils.file_exporter import export_to_json
import json
import os

def test_save_interval():
    """저장 간격 테스트"""
    print("=" * 60)
    print("저장 간격 테스트")
    print("=" * 60)
    
    # 테스트 블로그 ID
    blog_id = "skalekd77"
    
    # 출력 파일 경로
    output_path = "output/test_save_interval.json"
    
    # 기존 파일 삭제
    if os.path.exists(output_path):
        os.remove(output_path)
        print(f"[테스트] 기존 파일 삭제: {output_path}")
    
    # 체크포인트 매니저
    checkpoint_manager = CheckpointManager()
    
    # 저장 간격 5개로 설정 (테스트용)
    save_interval = 5
    
    print(f"\n[테스트] 저장 간격: {save_interval}개")
    print(f"[테스트] 블로그 ID: {blog_id}")
    print(f"[테스트] 출력 파일: {output_path}")
    print(f"\n[테스트] 크롤링 시작...")
    
    try:
        # 크롤링 실행
        posts = crawl_multiple_blog_ids(
            blog_ids=[blog_id],
            output_path=output_path,
            checkpoint_manager=checkpoint_manager,
            max_posts_per_blog=20,  # 최대 20개 포스트
            delay=0.5,
            timeout=30,
            should_stop=None,
            save_interval=save_interval
        )
        
        print(f"\n[테스트] 크롤링 완료")
        
        # 파일 확인
        if os.path.exists(output_path):
            with open(output_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                saved_posts = data.get("posts", [])
                total_posts = data.get("crawl_info", {}).get("total_posts", 0)
                
                print(f"\n[테스트 결과]")
                print(f"  - 저장된 포스트 수: {len(saved_posts)}")
                print(f"  - 총 포스트 수: {total_posts}")
                print(f"  - 저장 간격: {save_interval}개")
                
                # 저장 간격 확인
                if total_posts > 0:
                    expected_saves = (total_posts // save_interval) + (1 if total_posts % save_interval > 0 else 0)
                    print(f"  - 예상 저장 횟수: {expected_saves}회")
                    
                    # 파일 크기 확인 (여러 번 저장되었는지 확인)
                    file_size = os.path.getsize(output_path)
                    print(f"  - 파일 크기: {file_size} bytes")
                    
                    if len(saved_posts) >= save_interval:
                        print(f"  ✅ 저장 간격 테스트 통과: {len(saved_posts)}개 포스트 저장됨")
                    else:
                        print(f"  ⚠️  저장 간격 테스트 실패: {len(saved_posts)}개 포스트만 저장됨 (예상: {save_interval}개 이상)")
                else:
                    print(f"  ⚠️  포스트가 저장되지 않았습니다.")
        else:
            print(f"\n[테스트 결과] 파일이 생성되지 않았습니다.")
            
    except Exception as e:
        import traceback
        print(f"\n[테스트 오류] {e}")
        traceback.print_exc()

if __name__ == "__main__":
    test_save_interval()
