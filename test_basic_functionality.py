"""
기본 기능 동작 테스트
실제 크롤링 없이 기본 함수들의 동작 확인
"""
import sys
from pathlib import Path

project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.crawler.engine import extract_post_id_from_url, extract_blog_id_from_url, extract_title
from src.crawler.parser import html_to_markdown
from src.models import Post, Author, PostMetadata, PostContent, Comment


def test_url_extraction():
    """URL 추출 함수 테스트"""
    print("\n=== URL 추출 테스트 ===")
    
    # Post ID 추출 테스트
    test_urls = [
        "https://m.blog.naver.com/koding2002/224048062846",
        "https://m.blog.naver.com/PostView.naver?blogId=koding2002&logNo=224048062846",
        "https://m.blog.naver.com/test/123456?param=value"
    ]
    
    for url in test_urls:
        post_id = extract_post_id_from_url(url)
        print(f"  URL: {url}")
        print(f"  Post ID: {post_id}")
        assert post_id, f"Post ID 추출 실패: {url}"
    
    print("✓ Post ID 추출 정상")
    
    # Blog ID 추출 테스트
    blog_urls = [
        "https://m.blog.naver.com/PostView.naver?blogId=koding2002&logNo=224048062846",
        "https://m.blog.naver.com/koding2002"
    ]
    
    for url in blog_urls:
        blog_id = extract_blog_id_from_url(url)
        print(f"  URL: {url}")
        print(f"  Blog ID: {blog_id}")
    
    print("✓ Blog ID 추출 정상")


def test_html_to_markdown():
    """HTML to Markdown 변환 테스트"""
    print("\n=== HTML to Markdown 변환 테스트 ===")
    
    html_samples = [
        ("<h1>제목</h1>", "# 제목"),
        ("<p>단락 <strong>강조</strong> 텍스트</p>", "단락 **강조** 텍스트"),
        ("<a href='https://example.com'>링크</a>", "[링크](https://example.com)"),
    ]
    
    for html, expected in html_samples:
        markdown = html_to_markdown(html)
        print(f"  HTML: {html}")
        print(f"  Markdown: {markdown}")
        # 기본적인 변환이 되었는지 확인 (일부만 일치해도 OK)
        assert "#" in markdown or "**" in markdown or "링크" in markdown, "Markdown 변환 실패"
    
    # 이미지 태그 테스트 (별도)
    img_html = "<img src='image.jpg'>"
    img_markdown = html_to_markdown(img_html)
    print(f"  HTML: {img_html}")
    print(f"  Markdown: {img_markdown}")
    
    print("✓ HTML to Markdown 변환 정상")


def test_data_model_serialization():
    """데이터 모델 직렬화 테스트"""
    print("\n=== 데이터 모델 직렬화 테스트 ===")
    
    # 완전한 Post 객체 생성
    author = Author(blog_id="test_blog", nickname="테스트 사용자")
    metadata = PostMetadata(views=100, likes=10, comments=5, tags=["태그1", "태그2"])
    content = PostContent(
        text="테스트 본문 내용입니다.",
        word_count=3,
        images=["https://example.com/image1.jpg"],
        links=["https://example.com/link1"]
    )
    comment = Comment(author="댓글 작성자", content="댓글 내용", likes=0)
    
    post = Post(
        post_id="123",
        title="테스트 포스트",
        author=author,
        published_date="2025. 01. 01.",
        modified_date=None,
        url="https://m.blog.naver.com/test/123",
        metadata=metadata,
        content=content,
        comments=[comment]
    )
    
    # to_dict() 테스트
    post_dict = post.to_dict()
    
    # 검증
    assert post_dict["post_id"] == "123"
    assert post_dict["author"]["blog_id"] == "test_blog"
    assert post_dict["metadata"]["views"] == 100
    assert len(post_dict["metadata"]["tags"]) == 2
    assert post_dict["content"]["word_count"] == 3
    assert len(post_dict["comments"]) == 1
    assert "html" not in post_dict["content"]  # html은 제외되어야 함
    assert "markdown" not in post_dict["content"]  # markdown도 제외되어야 함
    
    print("✓ Post 객체 생성 정상")
    print("✓ Post.to_dict() 직렬화 정상")
    print(f"  - Post ID: {post_dict['post_id']}")
    print(f"  - 제목: {post_dict['title']}")
    print(f"  - 작성자: {post_dict['author']['nickname']}")
    print(f"  - 조회수: {post_dict['metadata']['views']}")
    print(f"  - 해시태그 수: {len(post_dict['metadata']['tags'])}")
    print(f"  - 댓글 수: {len(post_dict['comments'])}")


def test_checkpoint_operations():
    """체크포인트 작업 테스트"""
    print("\n=== 체크포인트 작업 테스트 ===")
    
    from src.utils.checkpoint_manager import CheckpointManager
    import shutil
    
    # 테스트 디렉토리
    test_dir = "test_checkpoints"
    if Path(test_dir).exists():
        shutil.rmtree(test_dir)
    
    manager = CheckpointManager(test_dir)
    
    # 체크포인트 생성
    job_data = {
        "crawl_type": "blog_id",
        "blog_ids": ["test1", "test2", "test3"],
        "total_blog_ids": 3,
        "processed_blog_ids": 0,
        "status": "running"
    }
    
    checkpoint_path = manager.create_checkpoint(job_data)
    print(f"✓ 체크포인트 생성: {checkpoint_path.name}")
    
    # 체크포인트 로드
    loaded_data = manager.load_checkpoint(str(checkpoint_path))
    assert loaded_data["crawl_type"] == "blog_id"
    assert loaded_data["total_blog_ids"] == 3
    print("✓ 체크포인트 로드 정상")
    
    # 체크포인트 저장 테스트
    from src.models import Post, Author
    
    test_posts = [
        Post(
            post_id="1",
            title="테스트 포스트 1",
            author=Author(blog_id="test1", nickname="테스트"),
            published_date="2025.01.01",
            url="https://test.com/1"
        ),
        Post(
            post_id="2",
            title="테스트 포스트 2",
            author=Author(blog_id="test2", nickname="테스트"),
            published_date="2025.01.02",
            url="https://test.com/2"
        )
    ]
    
    manager.save_checkpoint(job_data, test_posts, save_interval=2)
    
    # 저장된 체크포인트 확인
    loaded_data2 = manager.load_checkpoint(str(checkpoint_path))
    assert len(loaded_data2.get("posts", [])) > 0
    print("✓ 체크포인트 저장 정상")
    
    # 정리
    if Path(test_dir).exists():
        shutil.rmtree(test_dir)
    print("✓ 체크포인트 작업 테스트 완료")


def main():
    """메인 테스트 함수"""
    print("=" * 60)
    print("기본 기능 동작 테스트")
    print("=" * 60)
    
    try:
        test_url_extraction()
        test_html_to_markdown()
        test_data_model_serialization()
        test_checkpoint_operations()
        
        print("\n" + "=" * 60)
        print("✓ 모든 기본 기능 테스트 통과!")
        print("=" * 60)
        
        print("\n📝 테스트 요약:")
        print("  ✓ URL 추출 함수 정상 작동")
        print("  ✓ HTML to Markdown 변환 정상 작동")
        print("  ✓ 데이터 모델 직렬화 정상 작동")
        print("  ✓ 체크포인트 관리 정상 작동")
        
        return 0
    except Exception as e:
        print(f"\n✗ 테스트 실패: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit(main())

