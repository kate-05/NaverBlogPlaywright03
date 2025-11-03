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
    should_stop: Optional[Callable[[], bool]] = None
) -> List[Post]:
    """다중 블로그 크롤링"""
    all_posts = []
    
    # 작업 정보
    job_data = {
        "crawl_type": "blog_id",
        "blog_ids": blog_ids,
        "total_blog_ids": len(blog_ids),
        "processed_blog_ids": 0,
        "failed_blog_ids": 0,
        "status": "running",
        "blog_progress": []
    }
    
    # 체크포인트 생성
    checkpoint_manager.create_checkpoint(job_data)
    
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
        
        print(f"\n[단계] === 블로그 {idx}/{len(blog_ids)}: {blog_id} ===")
        
        blog_progress = {
            "blog_id": blog_id,
            "status": "in_progress",
            "posts_crawled": 0,
            "started_at": datetime.now().isoformat()
        }
        
        try:
            # 블로그 크롤링
            blog_info, blog_posts = crawl_by_blog_id(
                blog_id=blog_id,
                max_posts=max_posts_per_blog,
                delay=delay,
                timeout=timeout,
                should_stop=should_stop
            )
            
            # 중복 제거 (URL 기준)
            existing_urls = {post.url for post in all_posts}
            new_posts = [post for post in blog_posts if post.url not in existing_urls]
            
            all_posts.extend(new_posts)
            
            blog_progress["status"] = "completed"
            blog_progress["posts_crawled"] = len(blog_posts)
            blog_progress["completed_at"] = datetime.now().isoformat()
            
            job_data["processed_blog_ids"] += 1
            print(f"[단계] 블로그 {blog_id} 크롤링 완료: {len(blog_posts)}개 포스트")
            
        except Exception as e:
            print(f"[오류] 블로그 {blog_id} 크롤링 실패: {e}")
            blog_progress["status"] = "failed"
            blog_progress["error"] = str(e)
            job_data["failed_blog_ids"] += 1
        
        # 블로그 진행 상황 업데이트
        if "blog_progress" not in job_data:
            job_data["blog_progress"] = []
        job_data["blog_progress"].append(blog_progress)
        
        # 체크포인트 중간 저장
        checkpoint_manager.save_checkpoint(job_data, all_posts[-100:] if all_posts else [])
        
        # should_stop 확인 (블로그 크롤링 후)
        if should_stop and should_stop():
            print(f"[경고] 크롤링이 중단되었습니다.")
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
    
    # 최종 저장
    job_data["status"] = "completed"
    export_to_json(all_posts, output_path, {
        "crawl_type": "blog_id",
        "total_blog_ids": job_data["total_blog_ids"],
        "processed_blog_ids": job_data["processed_blog_ids"],
        "failed_blog_ids": job_data["failed_blog_ids"],
        "total_posts": len(all_posts)
    })
    
    return all_posts


def resume_crawling(
    checkpoint_path: str,
    output_path: str,
    checkpoint_manager: CheckpointManager,
    delay: float = 0.5,
    timeout: int = 30
) -> List[Post]:
    """체크포인트에서 크롤링 재개"""
    # 체크포인트 로드
    checkpoint_data = checkpoint_manager.load_checkpoint(checkpoint_path)
    
    # 미완료 블로그 찾기
    blog_ids = checkpoint_data.get("blog_ids", [])
    blog_progress = checkpoint_data.get("blog_progress", [])
    
    completed_blog_ids = {
        bp["blog_id"] for bp in blog_progress 
        if bp.get("status") == "completed"
    }
    
    remaining_blog_ids = [
        blog_id for blog_id in blog_ids 
        if blog_id not in completed_blog_ids
    ]
    
    if not remaining_blog_ids:
        print("[단계] 이미 완료된 크롤링입니다.")
        return []
    
    print(f"[단계] 미완료 블로그 {len(remaining_blog_ids)}개 재개...")
    
    # 미완료 블로그 크롤링
    new_posts = crawl_multiple_blog_ids(
        remaining_blog_ids,
        output_path,
        checkpoint_manager,
        delay=delay,
        timeout=timeout
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

