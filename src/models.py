"""
데이터 모델 정의
"""
from dataclasses import dataclass, field, asdict
from typing import Optional, List
from datetime import datetime


@dataclass
class Author:
    """작성자 정보"""
    blog_id: str
    nickname: str

    def to_dict(self):
        return asdict(self)


@dataclass
class PostMetadata:
    """포스트 메타데이터"""
    views: int = 0
    likes: int = 0
    comments: int = 0
    category: Optional[str] = None
    tags: List[str] = field(default_factory=list)

    def to_dict(self):
        return asdict(self)


@dataclass
class PostContent:
    """포스트 본문 내용"""
    html: str = ""
    text: str = ""
    markdown: str = ""
    word_count: int = 0
    images: List[str] = field(default_factory=list)
    links: List[str] = field(default_factory=list)

    def to_dict(self):
        # JSON 출력 시 html과 markdown은 제외
        result = asdict(self)
        result.pop('html', None)
        result.pop('markdown', None)
        return result


@dataclass
class Comment:
    """댓글 정보"""
    author: str
    content: str
    date: Optional[str] = None
    likes: int = 0

    def to_dict(self):
        return asdict(self)


@dataclass
class Post:
    """포스트 정보"""
    post_id: str
    title: str
    author: Author
    published_date: str
    modified_date: Optional[str] = None
    url: str = ""
    metadata: PostMetadata = field(default_factory=PostMetadata)
    content: PostContent = field(default_factory=PostContent)
    comments: List[Comment] = field(default_factory=list)

    def to_dict(self):
        """딕셔너리로 변환 (JSON 출력용)"""
        return {
            'post_id': self.post_id,
            'title': self.title,
            'author': self.author.to_dict(),
            'published_date': self.published_date,
            'modified_date': self.modified_date,
            'url': self.url,
            'metadata': self.metadata.to_dict(),
            'content': self.content.to_dict(),
            'comments': [comment.to_dict() for comment in self.comments]
        }

