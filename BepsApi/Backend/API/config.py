import os
from dotenv import load_dotenv

# .env 파일에서 환경변수 로드
load_dotenv()

class Config:
    # PostgreSQL 데이터베이스 연결 설정
    # 포맷: postgresql://username:password@hostname/database
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@127.0.0.1:5432/beps")  # 🔹 데이터베이스 URL
    SQLALCHEMY_TRACK_MODIFICATIONS =False   # 🔹 SQLAlchemy의 이벤트를 추적하는 기능을 비활성화(사용하면 성능 저하)
    SECRET_KEY = os.getenv("JWT_SECRET_KEY","default-secret-key")   # 🔹 JWT 암호화 키
    BACKUP_DIR = os.path.expanduser("~/BepsApi/DB/backup")  # 🔹 DB content_viewing_history 테이블 백업 폴더
    
    
