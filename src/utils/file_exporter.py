"""
파일 출력 모듈
"""
import json
from pathlib import Path
from typing import List, Dict
from datetime import datetime

from src.models import Post


def export_to_json(
    posts: List[Post],
    output_path: str,
    crawl_info: Dict,
    sort_by_date: bool = False
) -> Path:
    """JSON 파일로 출력"""
    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    # Post 객체를 dict로 변환
    post_list = [post.to_dict() if isinstance(post, Post) else post for post in posts]
    
    # 날짜 기준 정렬 (옵션)
    if sort_by_date:
        try:
            post_list.sort(
                key=lambda p: (
                    datetime.fromisoformat(
                        p.get('published_date', '').replace('Z', '+00:00')
                    ) if p.get('published_date') else datetime.min
                ),
                reverse=True  # 내림차순 (최신순)
            )
        except Exception as e:
            print(f"[경고] 날짜 기준 정렬 실패: {e}")
    
    # 데이터 구조화
    data = {
        "crawl_info": {
            **crawl_info,
            "crawl_date": datetime.now().isoformat(),
            "total_posts": len(post_list),
            "sort_order": "date_desc" if sort_by_date else "crawl_order"
        },
        "posts": post_list
    }
    
    # JSON 파일로 저장
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2, default=str)
    
    return output_file

