"""
배치 처리 모듈
다중 블로그 크롤링 및 재개 기능
"""
import json
from typing import List, Optional, Callable
from datetime import datetime
from pathlib import Path

from src.models import Post
from src.crawler.engine import crawl_by_blog_id
from src.utils.checkpoint_manager import CheckpointManager
from src.utils.file_exporter import export_to_json


def crawl_multiple_blog_ids(
    blog_ids: List[str],
    output_path: str,
    checkpoint_manager: CheckpointManager,
    max_posts_per_blog: Optional[int] = None,
    delay: float = 0.5,
    timeout: int = 30,
    should_stop: Optional[Callable[[], bool]] = None,
    existing_blog_progress: Optional[List[dict]] = None,
    save_interval: int = 10,
    progress_callback: Optional[Callable[[int, int], None]] = None,
    headless: bool = True
) -> List[Post]:
    """다중 블로그 크롤링"""
    all_posts = []
    total_saved_posts = 0  # 총 저장된 포스트 수
    
    # 작업 정보
    job_data = {
        "crawl_type": "blog_id",
        "blog_ids": blog_ids,
        "total_blog_ids": len(blog_ids),
        "processed_blog_ids": 0,
        "failed_blog_ids": 0,
        "status": "running",
        "blog_progress": existing_blog_progress.copy() if existing_blog_progress else []
    }
    
    # 체크포인트 생성 (재개 모드가 아닐 때만)
    if not existing_blog_progress:
        checkpoint_manager.create_checkpoint(job_data)
    
    # 초기 저장 (파일이 없을 때만)
    if not Path(output_path).exists():
        export_to_json([], output_path, {
            "crawl_type": "blog_id",
            "total_blog_ids": len(blog_ids),
            "processed_blog_ids": 0,
            "total_posts": 0,
            "status": "running"
        })
    
    # 전체 포스트 수 계산 (진행상황 표시용)
    total_posts_count = 0
    for bp in job_data.get("blog_progress", []):
        all_urls = bp.get("all_post_urls", [])
        if all_urls:
            total_posts_count += len(all_urls)
    
    # 각 블로그 크롤링
    for idx, blog_id in enumerate(blog_ids, 1):
        # should_stop 확인
        if should_stop and should_stop():
            print(f"[경고] 크롤링이 중단되었습니다. ({idx}/{len(blog_ids)})")
            job_data["status"] = "paused"
            if all_posts:
                export_to_json(all_posts, output_path, {
                    "crawl_type": "blog_id",
                    "total_blog_ids": job_data["total_blog_ids"],
                    "processed_blog_ids": job_data["processed_blog_ids"],
                    "total_posts": len(all_posts),
                    "status": "paused",
                    "interrupted": True
                })
            checkpoint_manager.save_checkpoint(job_data, all_posts[-100:] if all_posts else [])
            return all_posts
        
        # 진행상황 업데이트 (블로그 시작)
        if progress_callback:
            progress_callback(idx - 1, len(blog_ids))
        
        print(f"\n[단계] === 블로그 {idx}/{len(blog_ids)}: {blog_id} ===")
        
        # 기존 블로그 진행 상황 확인 (재개 모드)
        existing_progress = None
        for bp in job_data.get("blog_progress", []):
            if bp.get("blog_id") == blog_id:
                existing_progress = bp
                break
        
        # 이미 크롤링된 포스트 URL 목록 가져오기
        crawled_urls = []
        all_post_urls = None
        if existing_progress:
            crawled_urls = existing_progress.get("crawled_urls", [])
            all_post_urls = existing_progress.get("all_post_urls", None)
            if all_post_urls:
                print(f"[단계] 블로그 {blog_id}: 전체 링크 목록 {len(all_post_urls)}개 로드됨 (재개 모드)")
                print(f"[단계] 이미 크롤링된 포스트 {len(crawled_urls)}개 발견")
        
        blog_progress = {
            "blog_id": blog_id,
            "status": "in_progress",
            "posts_crawled": len(crawled_urls),
            "started_at": datetime.now().isoformat(),
            "crawled_urls": crawled_urls.copy() if crawled_urls else [],
            "all_post_urls": all_post_urls if all_post_urls else None  # 전체 링크 목록
        }
        
        try:
            # 저장된 포스트 카운트 추적
            saved_count_in_callback = 0
            
            # 저장 콜백 함수 정의 (개별 포스트 크롤링 중 저장)
            def save_posts(posts_to_save: List[Post]):
                """포스트 저장 콜백"""
                nonlocal total_saved_posts, saved_count_in_callback
                if posts_to_save:
                    export_to_json(
                        posts_to_save,
                        output_path,
                        {
                            "crawl_type": "blog_id",
                            "total_blog_ids": job_data["total_blog_ids"],
                            "processed_blog_ids": job_data["processed_blog_ids"],
                            "total_posts": total_saved_posts + len(posts_to_save),
                            "status": "running"
                        },
                        append=True
                    )
                    total_saved_posts += len(posts_to_save)
                    saved_count_in_callback += len(posts_to_save)
                    print(f"[단계] {len(posts_to_save)}개 포스트 저장 완료. (총 저장된 포스트: {total_saved_posts}개)")
            
            # 진행상황 콜백 정의 (블로그 내 포스트 크롤링 진행상황)
            post_progress_callback = None
            if progress_callback:
                # 블로그별 진행상황 계산을 위한 콜백
                def create_post_progress_callback(blog_idx, total_blogs):
                    def callback(current_post, total_posts):
                        # 전체 진행상황 계산: 블로그 진행률 + 현재 블로그 내 포스트 진행률
                        # 블로그 단위로 진행상황 표시 (블로그 수 기준)
                        # 현재 블로그 내 포스트 진행률을 블로그 진행률에 반영
                        if total_posts > 0:
                            post_progress = current_post / total_posts
                            # 전체 진행률 = (완료된 블로그 수 + 현재 블로그 진행률) / 전체 블로그 수
                            # post_progress는 0~1 사이이므로, 이를 블로그 단위로 변환
                            overall_current = blog_idx - 1 + post_progress
                            overall_total = total_blogs
                            progress_callback(overall_current, overall_total)
                    return callback
                
                post_progress_callback = create_post_progress_callback(idx, len(blog_ids))
            
            # 블로그 크롤링 (저장 콜백 전달)
            blog_info, blog_posts = crawl_by_blog_id(
                blog_id=blog_id,
                max_posts=max_posts_per_blog,
                delay=delay,
                timeout=timeout,
                should_stop=should_stop,
                all_post_urls=all_post_urls if all_post_urls else None,
                crawled_urls=crawled_urls if crawled_urls else None,
                save_callback=save_posts,
                save_interval=save_interval,
                progress_callback=post_progress_callback,
                headless=headless
            )
            
            # 전체 링크 목록 저장 (Phase 1에서 수집된 전체 링크 또는 재개 모드에서 로드한 링크)
            if 'all_post_urls' in blog_info:
                blog_progress["all_post_urls"] = blog_info['all_post_urls']
            
            # 저장 콜백에서 저장된 포스트 URL 추가
            if 'saved_urls' in blog_info and blog_info['saved_urls']:
                saved_urls = blog_info['saved_urls']
                blog_progress["crawled_urls"].extend(saved_urls)
                print(f"[단계] 저장 콜백에서 저장된 포스트 {len(saved_urls)}개 URL 추가")
            
            # 중복 제거 (URL 기준)
            existing_urls = {post.url for post in all_posts}
            new_posts = [post for post in blog_posts if post.url not in existing_urls]
            
            all_posts.extend(new_posts)
            
            # 크롤링된 URL 목록 업데이트
            # blog_posts에 있는 포스트의 URL 추가 (저장 콜백에서 저장된 것은 이미 추가됨)
            blog_progress["crawled_urls"].extend([post.url for post in blog_posts])
            blog_progress["crawled_urls"] = list(set(blog_progress["crawled_urls"]))  # 중복 제거
            
            # 완료 여부 확인: 전체 링크 수와 크롤링된 URL 수 비교
            all_urls_count = len(blog_progress.get("all_post_urls", []))
            crawled_urls_count = len(blog_progress["crawled_urls"])
            
            if all_urls_count > 0 and crawled_urls_count >= all_urls_count:
                blog_progress["status"] = "completed"
                blog_progress["completed_at"] = datetime.now().isoformat()
                print(f"[단계] 블로그 {blog_id} 크롤링 완료: {crawled_urls_count}/{all_urls_count}개 포스트")
            else:
                # 일부만 크롤링된 경우 "in_progress" 상태 유지
                blog_progress["status"] = "in_progress"
                print(f"[단계] 블로그 {blog_id} 부분 크롤링: {crawled_urls_count}/{all_urls_count}개 포스트 (재개 가능)")
            
            blog_progress["posts_crawled"] = crawled_urls_count
            
            if blog_progress["status"] == "completed":
                job_data["processed_blog_ids"] += 1
            print(f"[단계] 블로그 {blog_id}: {len(blog_posts)}개 새 포스트 크롤링됨 (총 {crawled_urls_count}/{all_urls_count}개)")
            
            # 진행상황 업데이트 (블로그 완료)
            if progress_callback:
                progress_callback(idx, len(blog_ids))
            
            # 남은 포스트 저장 (저장 간격 미만)
            if all_posts and len(all_posts) > 0:
                save_posts(all_posts.copy())
                all_posts.clear()
            
        except Exception as e:
            print(f"[오류] 블로그 {blog_id} 크롤링 실패: {e}")
            blog_progress["status"] = "failed"
            blog_progress["error"] = str(e)
            job_data["failed_blog_ids"] += 1
        
        # 블로그 진행 상황 업데이트 (기존 항목 찾아서 업데이트)
        if "blog_progress" not in job_data:
            job_data["blog_progress"] = []
        
        # 기존 블로그 진행 상황 찾기
        existing_index = None
        for idx, bp in enumerate(job_data["blog_progress"]):
            if bp.get("blog_id") == blog_id:
                existing_index = idx
                break
        
        # 기존 항목이 있으면 업데이트, 없으면 추가
        if existing_index is not None:
            job_data["blog_progress"][existing_index] = blog_progress
        else:
            job_data["blog_progress"].append(blog_progress)
        
        # 체크포인트 중간 저장 (재개 모드에서도 갱신)
        checkpoint_manager.save_checkpoint(job_data, all_posts[-100:] if all_posts else [])
        
        # should_stop 확인 (블로그 크롤링 후)
        if should_stop and should_stop():
            print(f"[경고] 크롤링이 중단되었습니다.")
            job_data["status"] = "paused"
            # 남은 포스트 저장
            if all_posts:
                export_to_json(
                    all_posts,
                    output_path,
                    {
                        "crawl_type": "blog_id",
                        "total_blog_ids": job_data["total_blog_ids"],
                        "processed_blog_ids": job_data["processed_blog_ids"],
                        "total_posts": total_saved_posts + len(all_posts),
                        "status": "paused",
                        "interrupted": True
                    },
                    append=True
                )
                total_saved_posts += len(all_posts)
                all_posts.clear()
            checkpoint_manager.save_checkpoint(job_data, [])
            return []
    
    # 최종 저장 (남은 포스트)
    if all_posts:
        print(f"[단계] 최종 저장: {len(all_posts)}개 포스트 저장 중...")
        export_to_json(
            all_posts,
            output_path,
            {
                "crawl_type": "blog_id",
                "total_blog_ids": job_data["total_blog_ids"],
                "processed_blog_ids": job_data["processed_blog_ids"],
                "failed_blog_ids": job_data["failed_blog_ids"],
                "total_posts": total_saved_posts + len(all_posts),
                "status": "completed"
            },
            append=True
        )
        total_saved_posts += len(all_posts)
        all_posts.clear()
        print(f"[단계] 최종 저장 완료. (총 저장된 포스트: {total_saved_posts}개)")
    
    job_data["status"] = "completed"
    
    return []


def resume_crawling(
    checkpoint_path: str,
    output_path: str,
    checkpoint_manager: CheckpointManager,
    delay: float = 0.5,
    timeout: int = 30,
    should_stop: Optional[Callable[[], bool]] = None,
    save_interval: int = 10,
    progress_callback: Optional[Callable[[int, int], None]] = None,
    headless: bool = True
) -> List[Post]:
    """체크포인트에서 크롤링 재개"""
    # 체크포인트 로드
    checkpoint_data = checkpoint_manager.load_checkpoint(checkpoint_path)
    
    # 미완료 블로그 찾기
    blog_ids = checkpoint_data.get("blog_ids", [])
    blog_progress = checkpoint_data.get("blog_progress", [])
    
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
                print(f"[단계] 블로그 {blog_id}: 상태가 'completed'이지만 미완료 포스트가 있습니다.")
                print(f"[단계]   전체 링크: {len(all_urls) if all_urls else 0}개, 크롤링됨: {len(crawled_urls)}개")
    
    remaining_blog_ids = [
        blog_id for blog_id in blog_ids 
        if blog_id not in completed_blog_ids
    ]
    
    if not remaining_blog_ids:
        print("[단계] 이미 완료된 크롤링입니다.")
        return []
    
    print(f"[단계] 미완료 블로그 {len(remaining_blog_ids)}개 재개...")
    
    # 기존 체크포인트의 blog_progress를 전달 (재개 모드)
    # 기존 체크포인트를 계속 사용하도록 설정
    from pathlib import Path as PathLib
    checkpoint_manager.current_checkpoint_path = PathLib(checkpoint_path)
    
    # 디버깅: 재개 정보 출력
    print(f"[단계] 재개할 블로그 수: {len(remaining_blog_ids)}")
    for blog_id in remaining_blog_ids:
        blog_prog = next((bp for bp in blog_progress if bp.get("blog_id") == blog_id), None)
        if blog_prog:
            all_urls = blog_prog.get("all_post_urls", [])
            crawled = blog_prog.get("crawled_urls", [])
            print(f"[단계] 블로그 {blog_id}: 전체 링크 {len(all_urls) if all_urls else 0}개, 크롤링됨 {len(crawled)}개")
            if not all_urls:
                print(f"[경고] 블로그 {blog_id}: 전체 링크 목록이 없습니다. 처음부터 다시 크롤링합니다.")
            if not crawled:
                print(f"[단계] 블로그 {blog_id}: 처음부터 크롤링 시작")
        else:
            print(f"[경고] 블로그 {blog_id}: 진행 상황 정보를 찾을 수 없습니다. 처음부터 다시 크롤링합니다.")
    
    # 미완료 블로그 크롤링 (기존 blog_progress 전달)
    new_posts = crawl_multiple_blog_ids(
        remaining_blog_ids,
        output_path,
        checkpoint_manager,
        delay=delay,
        timeout=timeout,
        should_stop=should_stop,
        existing_blog_progress=blog_progress,  # 기존 진행 상황 전달
        save_interval=save_interval,
        progress_callback=progress_callback,
        headless=headless
    )
    
    # 기존 포스트와 병합
    existing_posts = []
    output_file = Path(output_path)
    if output_file.exists():
        try:
            with open(output_file, 'r', encoding='utf-8') as f:
                existing_data = json.load(f)
                existing_posts = existing_data.get("posts", [])
        except Exception as e:
            print(f"[경고] 기존 파일 로드 실패: {e}")
    
    # 중복 제거 (post_id 기준)
    existing_ids = {post.get("post_id") for post in existing_posts}
    merged_posts = existing_posts + [
        post.to_dict() for post in new_posts 
        if post.post_id not in existing_ids
    ]
    
    # 최종 저장
    export_to_json(
        merged_posts,
        output_path,
        {
            "crawl_type": "blog_id",
            "total_blog_ids": checkpoint_data.get("total_blog_ids", 0),
            "processed_blog_ids": checkpoint_data.get("processed_blog_ids", 0) + len(remaining_blog_ids),
            "total_posts": len(merged_posts),
            "status": "completed",
            "resumed": True
        }
    )
    
    return new_posts

