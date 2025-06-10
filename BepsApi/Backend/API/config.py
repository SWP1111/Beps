import os
from dotenv import load_dotenv

# .env 파일에서 환경변수 로드
load_dotenv()

class Config:
    # PostgreSQL 데이터베이스 연결 설정
    # 포맷: postgresql://username:password@hostname/database
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@127.0.0.1:5432/beps")  # 🔹 데이터베이스 URL
    SQLALCHEMY_TRACK_MODIFICATIONS =False   # 🔹 SQLAlchemy의 이벤트를 추적하는 기능을 비활성화(사용하면 성능 저하)
    #SQLALCHEMY_ECHO = True  # 🔹 SQLAlchemy 쿼리 로깅 활성화(디버깅 용도)
    SECRET_KEY = os.getenv("JWT_SECRET_KEY","default-secret-key")   # 🔹 JWT 암호화 키
    BACKUP_DIR = os.path.expanduser("~/BepsApi/DB/backup")  # 🔹 DB content_viewing_history 테이블 백업 폴더
    POINT_DURATION_SECONDS = int(os.getenv("POINT_DURATION_SECONDS", 30))  # 🔹 학습 포인트 적립 기준 시간(5분) 테스트용으로 30초
    UPLOAD_DIR = '/tmp/generated_excels'  # 엑셀 파일 저장 경로
    
    # 캐시 설정
    CACHE_TYPE = os.getenv("CACHE_TYPE", "SimpleCache")  # 기본값은 SimpleCache (메모리 기반)
    CACHE_DEFAULT_TIMEOUT = int(os.getenv("CACHE_TIMEOUT", 3600))  # 캐시 기본 만료 시간(초)
    
    LEARNING_COMPLETED_MINUTES = 1
    PUSH_MESSAGE_LIMIT = 5  # 🔹 푸시 메시지 최대 개수

    # R2 (Cloudflare S3-compatible storage) 설정
    AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")  # R2 액세스 키 ID
    AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")  # R2 시크릿 액세스 키
    R2_ACCOUNT_ID = os.getenv("R2_ACCOUNT_ID")  # R2 계정 ID
    R2_BUCKET_NAME = os.getenv("R2_BUCKET_NAME")  # R2 버킷 이름
    R2_ENDPOINT_URL = os.getenv("R2_ENDPOINT_URL")  # R2 엔드포인트 URL
    R2_ACCOUNT_CODE = os.getenv("R2_ACCOUNT_CODE")  # R2 계정 코드
    R2_ACCOUNT_HASH = os.getenv("R2_ACCOUNT_HASH")  # R2 계정 해시

    # Legacy Cloudflare Images 설정 (deprecated)
    CLOUDFLARE_ACCOUNT_ID = os.getenv("CLOUDFLARE_ACCOUNT_ID")  # Cloudflare 계정 ID
    CLOUDFLARE_API_TOKEN = os.getenv("CLOUDFLARE_API_TOKEN")  # Cloudflare API 토큰
    CLOUDFLARE_ACCOUNT_HASH = os.getenv("CLOUDFLARE_ACCOUNT_HASH")  # Cloudflare Images 계정 해시
    CLOUDFLARE_SIGNING_KEY = os.getenv("CLOUDFLARE_SIGNING_KEY")  # 서명용 비밀 키
    



