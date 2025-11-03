"""
체크포인트 관리 모듈
"""
import json
from pathlib import Path
from typing import List, Optional
from datetime import datetime

from src.models import Post


class CheckpointManager:
    """체크포인트 관리 클래스"""
    
    def __init__(self, checkpoint_dir: str = "checkpoints"):
        self.checkpoint_dir = Path(checkpoint_dir)
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)
        self.current_checkpoint_path: Optional[Path] = None
    
    def create_checkpoint(self, job_data: dict) -> Path:
        """체크포인트 생성"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        checkpoint_id = f"batch_{timestamp}"
        
        checkpoint_path = self.checkpoint_dir / f"{checkpoint_id}.json"
        
        checkpoint_data = {
            "checkpoint_id": checkpoint_id,
            "created_at": datetime.now().isoformat(),
            "last_updated": datetime.now().isoformat(),
            **job_data
        }
        
        with open(checkpoint_path, 'w', encoding='utf-8') as f:
            json.dump(checkpoint_data, f, ensure_ascii=False, indent=2)
        
        self.current_checkpoint_path = checkpoint_path
        return checkpoint_path
    
    def save_checkpoint(self, job_data: dict, posts: List[Post], save_interval: int = 10) -> None:
        """체크포인트 저장 (중간 저장)"""
        if not self.current_checkpoint_path:
            self.create_checkpoint(job_data)
        
        # 체크포인트 파일 로드
        try:
            with open(self.current_checkpoint_path, 'r', encoding='utf-8') as f:
                checkpoint_data = json.load(f)
        except FileNotFoundError:
            checkpoint_data = {
                "checkpoint_id": f"batch_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                "created_at": datetime.now().isoformat(),
                **job_data
            }
        
        # 최근 포스트 추가
        if 'posts' not in checkpoint_data:
            checkpoint_data['posts'] = []
        
        # Post 객체를 dict로 변환
        post_dicts = [post.to_dict() for post in posts]
        checkpoint_data['posts'].extend(post_dicts)
        
        # 최근 100개만 유지 (중복 제거)
        seen_ids = set()
        unique_posts = []
        for post in reversed(checkpoint_data['posts']):
            post_id = post.get('post_id', '')
            if post_id and post_id not in seen_ids:
                seen_ids.add(post_id)
                unique_posts.insert(0, post)
        
        checkpoint_data['posts'] = unique_posts[-100:]  # 최근 100개만
        
        # 업데이트
        checkpoint_data['last_updated'] = datetime.now().isoformat()
        checkpoint_data.update(job_data)
        
        # 저장
        with open(self.current_checkpoint_path, 'w', encoding='utf-8') as f:
            json.dump(checkpoint_data, f, ensure_ascii=False, indent=2)
    
    def load_checkpoint(self, checkpoint_path: str) -> dict:
        """체크포인트 로드"""
        path = Path(checkpoint_path)
        if not path.exists():
            raise FileNotFoundError(f"체크포인트 파일을 찾을 수 없습니다: {checkpoint_path}")
        
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        self.current_checkpoint_path = path
        return data

