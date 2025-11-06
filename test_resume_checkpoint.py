"""
재개 모드 체크포인트 갱신 테스트
5개 크롤링 → 중단 → 재개(4개) → 중단 → 재개(10번째부터) 시나리오
"""
import sys
import time
import json
from pathlib import Path

# 프로젝트 루트를 path에 추가
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.utils.checkpoint_manager import CheckpointManager
from src.crawler.batch_crawler import crawl_multiple_blog_ids, resume_crawling
from src.models import Post


class StopController:
    """중단 제어 클래스"""
    def __init__(self, stop_after: int = None, checkpoint_path: Path = None, blog_id: str = None):
        self.stop_after = stop_after
        self.count = 0
        self.stopped = False
        self.checkpoint_path = checkpoint_path
        self.blog_id = blog_id
    
    def should_stop(self) -> bool:
        """중단 여부 확인"""
        if self.stopped:
            return True
        
        # progress_callback에서 설정한 count 확인 (가장 빠른 방법)
        if self.stop_after and self.count >= self.stop_after:
            self.stopped = True
            return True
        
        # 체크포인트에서 현재 크롤링된 포스트 수 확인 (백업 방법)
        if self.checkpoint_path and self.checkpoint_path.exists() and self.blog_id:
            try:
                with open(self.checkpoint_path, 'r', encoding='utf-8') as f:
                    checkpoint_data = json.load(f)
                
                blog_progress = checkpoint_data.get('blog_progress', [])
                blog_prog = next((bp for bp in blog_progress if bp.get('blog_id') == self.blog_id), None)
                
                if blog_prog:
                    crawled_urls = blog_prog.get('crawled_urls', [])
                    current_count = len(crawled_urls)
                    # count가 업데이트되지 않았으면 체크포인트에서 가져온 값 사용
                    if self.count == 0 or current_count > self.count:
                        self.count = current_count
                    
                    if self.stop_after and current_count >= self.stop_after:
                        self.stopped = True
                        return True
            except Exception:
                pass  # 체크포인트 읽기 실패 시 무시
        
        return False
    
    def increment(self):
        """카운트 증가"""
        self.count += 1


def verify_checkpoint(checkpoint_path: Path, expected_crawled: int, blog_id: str):
    """체크포인트 검증"""
    print(f"\n{'='*60}")
    print(f"체크포인트 검증: {checkpoint_path.name}")
    print(f"{'='*60}")
    
    with open(checkpoint_path, 'r', encoding='utf-8') as f:
        checkpoint_data = json.load(f)
    
    blog_progress = checkpoint_data.get('blog_progress', [])
    blog_prog = next((bp for bp in blog_progress if bp.get('blog_id') == blog_id), None)
    
    if not blog_prog:
        print(f"[오류] 블로그 {blog_id}의 진행 상황을 찾을 수 없습니다.")
        return False
    
    crawled_urls = blog_prog.get('crawled_urls', [])
    all_urls = blog_prog.get('all_post_urls', [])
    posts_crawled = blog_prog.get('posts_crawled', 0)
    
    print(f"[정보] 체크포인트 정보:")
    print(f"  - 전체 링크 수: {len(all_urls) if all_urls else 0}개")
    print(f"  - 크롤링된 URL 수: {len(crawled_urls)}개")
    print(f"  - posts_crawled: {posts_crawled}개")
    print(f"  - 예상 크롤링 수: {expected_crawled}개")
    
    success = len(crawled_urls) == expected_crawled
    if success:
        print(f"[성공] 체크포인트 검증 성공: {len(crawled_urls)}개 == {expected_crawled}개")
    else:
        print(f"[실패] 체크포인트 검증 실패: {len(crawled_urls)}개 != {expected_crawled}개")
    
    return success


def test_resume_checkpoint():
    """재개 모드 체크포인트 갱신 테스트"""
    print("=" * 60)
    print("재개 모드 체크포인트 갱신 테스트")
    print("=" * 60)
    
    # 테스트 블로그 ID (실제 블로그 ID로 변경 필요)
    blog_id = "skalekd77"  # 테스트용 블로그 ID
    
    # 테스트 출력 파일
    output_path = "test_output/resume_checkpoint_test.json"
    Path("test_output").mkdir(exist_ok=True)
    
    checkpoint_manager = CheckpointManager(checkpoint_dir="test_checkpoints")
    
    # ===== 1단계: 초기 크롤링 (5개 포스트 후 중단) =====
    print(f"\n{'='*60}")
    print("1단계: 초기 크롤링 (5개 포스트 후 중단)")
    print(f"{'='*60}")
    
    stop_controller_1 = StopController(stop_after=5, blog_id=blog_id)
    
    def should_stop_1():
        # 체크포인트 파일이 생성된 후에만 확인
        if checkpoint_manager.current_checkpoint_path and checkpoint_manager.current_checkpoint_path.exists():
            stop_controller_1.checkpoint_path = checkpoint_manager.current_checkpoint_path
        return stop_controller_1.should_stop()
    
    def progress_callback_1(current, total):
        # current는 블로그 진행률 (0~1 사이)
        # 체크포인트에서 현재 크롤링된 포스트 수를 확인
        if checkpoint_manager.current_checkpoint_path and checkpoint_manager.current_checkpoint_path.exists():
            try:
                with open(checkpoint_manager.current_checkpoint_path, 'r', encoding='utf-8') as f:
                    checkpoint_data = json.load(f)
                blog_progress = checkpoint_data.get('blog_progress', [])
                blog_prog = next((bp for bp in blog_progress if bp.get('blog_id') == stop_controller_1.blog_id), None)
                if blog_prog:
                    crawled_urls = blog_prog.get('crawled_urls', [])
                    stop_controller_1.count = len(crawled_urls)
                    print(f"[테스트] progress_callback_1: crawled={stop_controller_1.count}, stop_after={stop_controller_1.stop_after}")
                    # 목표에 도달하면 즉시 중단 플래그 설정
                    if stop_controller_1.stop_after and stop_controller_1.count >= stop_controller_1.stop_after:
                        stop_controller_1.stopped = True
                        print(f"[테스트] 목표 도달: {stop_controller_1.count}개 >= {stop_controller_1.stop_after}개, 중단 플래그 설정")
            except Exception as e:
                pass  # 체크포인트 읽기 실패 시 무시
    
    try:
        posts_1 = crawl_multiple_blog_ids(
            blog_ids=[blog_id],
            output_path=output_path,
            checkpoint_manager=checkpoint_manager,
            max_posts_per_blog=10,  # 최대 10개로 제한
            delay=0.5,
            timeout=30,
            should_stop=should_stop_1,
            save_interval=1,  # 1개마다 저장
            progress_callback=progress_callback_1
        )
        
        print(f"\n[완료] 1단계 완료: {stop_controller_1.count}개 포스트 크롤링 후 중단")
        
        # 체크포인트 파일 확인
        checkpoint_files = sorted(
            checkpoint_manager.checkpoint_dir.glob("*.json"),
            key=lambda x: x.stat().st_mtime,
            reverse=True
        )
        
        if not checkpoint_files:
            print("[오류] 체크포인트 파일이 생성되지 않았습니다.")
            return False
        
        checkpoint_1 = checkpoint_files[0]
        print(f"📁 체크포인트 파일: {checkpoint_1.name}")
        
        # 체크포인트 검증
        if not verify_checkpoint(checkpoint_1, 5, blog_id):
            return False
        
        time.sleep(2)  # 파일 시스템 동기화 대기
        
        # ===== 2단계: 첫 번째 재개 (4개 포스트 추가 크롤링 후 중단) =====
        print(f"\n{'='*60}")
        print("2단계: 첫 번째 재개 (4개 포스트 추가 크롤링 후 중단)")
        print(f"{'='*60}")
        
        stop_controller_2 = StopController(stop_after=9, checkpoint_path=checkpoint_1, blog_id=blog_id)  # 총 9개까지 (5 + 4)
        
        def should_stop_2():
            return stop_controller_2.should_stop()
        
        def progress_callback_2(current, total):
            # current는 현재 포스트 인덱스 (1부터 시작)
            stop_controller_2.count = current
            # 목표에 도달하면 즉시 중단 플래그 설정
            if stop_controller_2.stop_after and current >= stop_controller_2.stop_after:
                stop_controller_2.stopped = True
                print(f"[테스트] 목표 도달: {current}개 >= {stop_controller_2.stop_after}개, 중단 플래그 설정")
        
        posts_2 = resume_crawling(
            checkpoint_path=str(checkpoint_1),
            output_path=output_path,
            checkpoint_manager=checkpoint_manager,
            delay=0.5,
            timeout=30,
            should_stop=should_stop_2,
            save_interval=1,
            progress_callback=progress_callback_2
        )
        
        additional_count = stop_controller_2.count - 5
        print(f"\n[완료] 2단계 완료: {additional_count}개 포스트 추가 크롤링 후 중단")
        print(f"   총 크롤링된 포스트: {stop_controller_2.count}개")
        
        # 체크포인트 파일 확인 (같은 파일이 갱신되었는지 확인)
        checkpoint_files_2 = sorted(
            checkpoint_manager.checkpoint_dir.glob("*.json"),
            key=lambda x: x.stat().st_mtime,
            reverse=True
        )
        
        checkpoint_2 = checkpoint_files_2[0]
        print(f"📁 체크포인트 파일: {checkpoint_2.name}")
        
        # 같은 파일이 갱신되었는지 확인
        if checkpoint_2 != checkpoint_1:
            print(f"[경고] 체크포인트 파일이 변경되었습니다: {checkpoint_1.name} -> {checkpoint_2.name}")
        else:
            print(f"[성공] 체크포인트 파일이 갱신되었습니다: {checkpoint_2.name}")
        
        # 체크포인트 검증 (총 9개)
        if not verify_checkpoint(checkpoint_2, 9, blog_id):
            return False
        
        time.sleep(2)  # 파일 시스템 동기화 대기
        
        # ===== 3단계: 두 번째 재개 (10번째 포스트부터 진행) =====
        print(f"\n{'='*60}")
        print("3단계: 두 번째 재개 (10번째 포스트부터 진행)")
        print(f"{'='*60}")
        
        # 체크포인트에서 현재 상태 확인
        with open(checkpoint_2, 'r', encoding='utf-8') as f:
            checkpoint_data = json.load(f)
        
        blog_progress = checkpoint_data.get('blog_progress', [])
        blog_prog = next((bp for bp in blog_progress if bp.get('blog_id') == blog_id), None)
        
        if blog_prog:
            crawled_urls = blog_prog.get('crawled_urls', [])
            all_urls = blog_prog.get('all_post_urls', [])
            print(f"📊 현재 상태:")
            print(f"  - 전체 링크 수: {len(all_urls) if all_urls else 0}개")
            print(f"  - 크롤링된 URL 수: {len(crawled_urls)}개")
            print(f"  - 다음 크롤링 시작 위치: {len(crawled_urls) + 1}번째 포스트")
        
        # 10번째 포스트부터 진행하는지 확인
        if len(crawled_urls) != 9:
            print(f"[오류] 예상과 다릅니다. 현재 크롤링된 포스트: {len(crawled_urls)}개 (예상: 9개)")
            return False
        
        print(f"[성공] 10번째 포스트부터 크롤링 시작 예정")
        
        # 재개 실행 (1개만 크롤링하여 확인)
        stop_controller_3 = StopController(stop_after=10, checkpoint_path=checkpoint_2, blog_id=blog_id)  # 총 10개까지
        
        def should_stop_3():
            return stop_controller_3.should_stop()
        
        def progress_callback_3(current, total):
            # current는 현재 포스트 인덱스 (1부터 시작)
            stop_controller_3.count = current
            # 목표에 도달하면 즉시 중단 플래그 설정
            if stop_controller_3.stop_after and current >= stop_controller_3.stop_after:
                stop_controller_3.stopped = True
                print(f"[테스트] 목표 도달: {current}개 >= {stop_controller_3.stop_after}개, 중단 플래그 설정")
        
        posts_3 = resume_crawling(
            checkpoint_path=str(checkpoint_2),
            output_path=output_path,
            checkpoint_manager=checkpoint_manager,
            delay=0.5,
            timeout=30,
            should_stop=should_stop_3,
            save_interval=1,
            progress_callback=progress_callback_3
        )
        
        additional_count = stop_controller_3.count - 9
        print(f"\n[완료] 3단계 완료: {additional_count}개 포스트 추가 크롤링")
        print(f"   총 크롤링된 포스트: {stop_controller_3.count}개")
        
        # 체크포인트 파일 확인
        checkpoint_files_3 = sorted(
            checkpoint_manager.checkpoint_dir.glob("*.json"),
            key=lambda x: x.stat().st_mtime,
            reverse=True
        )
        
        checkpoint_3 = checkpoint_files_3[0]
        print(f"📁 체크포인트 파일: {checkpoint_3.name}")
        
        # 같은 파일이 갱신되었는지 확인
        if checkpoint_3 != checkpoint_2:
            print(f"[경고] 체크포인트 파일이 변경되었습니다: {checkpoint_2.name} -> {checkpoint_3.name}")
        else:
            print(f"[성공] 체크포인트 파일이 갱신되었습니다: {checkpoint_3.name}")
        
        # 체크포인트 검증 (총 10개)
        if not verify_checkpoint(checkpoint_3, 10, blog_id):
            return False
        
        # ===== 최종 검증 =====
        print(f"\n{'='*60}")
        print("최종 검증")
        print(f"{'='*60}")
        
        # 출력 파일 확인
        if Path(output_path).exists():
            with open(output_path, 'r', encoding='utf-8') as f:
                output_data = json.load(f)
            
            output_posts = output_data.get('posts', [])
            print(f"📊 출력 파일 정보:")
            print(f"  - 총 포스트 수: {len(output_posts)}개")
            
            # 중복 확인
            post_ids = [post.get('post_id') for post in output_posts]
            unique_ids = set(post_ids)
            if len(post_ids) != len(unique_ids):
                print(f"[경고] 중복된 포스트가 있습니다: {len(post_ids)}개 중 {len(unique_ids)}개 고유")
            else:
                print(f"[성공] 중복 없음: {len(post_ids)}개 모두 고유")
        
        print(f"\n{'='*60}")
        print("[성공] 모든 테스트 통과!")
        print(f"{'='*60}")
        return True
        
    except Exception as e:
        print(f"\n[실패] 테스트 실패: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_resume_checkpoint()
    sys.exit(0 if success else 1)

