"""
크롤러 기능 테스트 스크립트
"""
import sys
from pathlib import Path

# 프로젝트 루트를 path에 추가
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.models import Post, Author, PostMetadata, PostContent, Comment
from src.crawler.engine import extract_post_id_from_url, extract_blog_id_from_url
from src.utils.checkpoint_manager import CheckpointManager
from src.utils.file_exporter import export_to_json


def test_models():
    """모델 생성 및 변환 테스트"""
    print("\n=== 모델 테스트 ===")
    
    # Author 테스트
    author = Author(blog_id="test_blog", nickname="테스트 사용자")
    assert author.blog_id == "test_blog"
    assert author.nickname == "테스트 사용자"
    print("✓ Author 모델 정상")
    
    # PostMetadata 테스트
    metadata = PostMetadata(views=100, likes=10, comments=5, tags=["태그1", "태그2"])
    assert metadata.views == 100
    assert metadata.likes == 10
    assert len(metadata.tags) == 2
    print("✓ PostMetadata 모델 정상")
    
    # PostContent 테스트
    content = PostContent(text="테스트 본문", word_count=2, images=["url1"], links=["url2"])
    assert content.word_count == 2
    assert len(content.images) == 1
    print("✓ PostContent 모델 정상")
    
    # Comment 테스트
    comment = Comment(author="댓글 작성자", content="댓글 내용", likes=0)
    assert comment.author == "댓글 작성자"
    print("✓ Comment 모델 정상")
    
    # Post 테스트
    post = Post(
        post_id="123",
        title="테스트 포스트",
        author=author,
        published_date="2025. 01. 01.",
        url="https://m.blog.naver.com/test",
        metadata=metadata,
        content=content,
        comments=[comment]
    )
    assert post.post_id == "123"
    assert post.title == "테스트 포스트"
    print("✓ Post 모델 정상")
    
    # to_dict() 테스트
    post_dict = post.to_dict()
    assert isinstance(post_dict, dict)
    assert post_dict["post_id"] == "123"
    assert post_dict["author"]["blog_id"] == "test_blog"
    assert "html" not in post_dict["content"]  # html은 제외되어야 함
    print("✓ Post.to_dict() 정상")


def test_url_parsing():
    """URL 파싱 테스트"""
    print("\n=== URL 파싱 테스트 ===")
    
    test_url = "https://m.blog.naver.com/koding2002/224048062846"
    post_id = extract_post_id_from_url(test_url)
    assert post_id == "224048062846"
    print(f"✓ Post ID 추출: {post_id}")
    
    test_url2 = "https://m.blog.naver.com/PostView.naver?blogId=koding2002&logNo=224048062846"
    blog_id = extract_blog_id_from_url(test_url2)
    assert blog_id == "koding2002"
    print(f"✓ Blog ID 추출: {blog_id}")


def test_checkpoint_manager():
    """체크포인트 관리 테스트"""
    print("\n=== 체크포인트 관리 테스트 ===")
    
    manager = CheckpointManager("test_checkpoints")
    
    # 체크포인트 생성
    job_data = {
        "crawl_type": "blog_id",
        "blog_ids": ["test1", "test2"],
        "total_blog_ids": 2
    }
    checkpoint_path = manager.create_checkpoint(job_data)
    assert checkpoint_path.exists()
    print(f"✓ 체크포인트 생성: {checkpoint_path.name}")
    
    # 체크포인트 로드
    loaded_data = manager.load_checkpoint(str(checkpoint_path))
    assert loaded_data["crawl_type"] == "blog_id"
    assert loaded_data["total_blog_ids"] == 2
    print("✓ 체크포인트 로드 정상")
    
    # 테스트 디렉토리 정리
    import shutil
    if Path("test_checkpoints").exists():
        shutil.rmtree("test_checkpoints")
    print("✓ 체크포인트 관리 테스트 완료")


def test_file_exporter():
    """파일 출력 테스트"""
    print("\n=== 파일 출력 테스트 ===")
    
    # 테스트 데이터 생성
    author = Author(blog_id="test_blog", nickname="테스트")
    post = Post(
        post_id="123",
        title="테스트 포스트",
        author=author,
        published_date="2025. 01. 01.",
        url="https://test.com"
    )
    
    # JSON 출력
    output_path = "test_output/test.json"
    crawl_info = {
        "crawl_type": "blog_id",
        "total_blog_ids": 1,
        "total_posts": 1
    }
    
    export_path = export_to_json([post], output_path, crawl_info)
    assert export_path.exists()
    print(f"✓ JSON 파일 출력: {export_path}")
    
    # 파일 내용 확인
    import json
    with open(export_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
        assert data["crawl_info"]["total_posts"] == 1
        assert len(data["posts"]) == 1
        assert data["posts"][0]["post_id"] == "123"
    print("✓ JSON 파일 내용 검증 완료")
    
    # 테스트 디렉토리 정리
    import shutil
    if Path("test_output").exists():
        shutil.rmtree("test_output")
    print("✓ 파일 출력 테스트 완료")


def main():
    """메인 테스트 함수"""
    print("=" * 50)
    print("크롤러 기능 테스트 시작")
    print("=" * 50)
    
    try:
        test_models()
        test_url_parsing()
        test_checkpoint_manager()
        test_file_exporter()
        
        print("\n" + "=" * 50)
        print("✓ 모든 테스트 통과!")
        print("=" * 50)
        return 0
    except Exception as e:
        print(f"\n✗ 테스트 실패: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit(main())

