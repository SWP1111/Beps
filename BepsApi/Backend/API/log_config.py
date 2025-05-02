import logging
import os
import time
import glob
import threading
from concurrent_log_handler import ConcurrentRotatingFileHandler

# 🔹 로그 폴더 설정
LOG_DIR = "logs"
if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR)

# 크기별 로그 파일 핸들러 (최대 300MB, 10개 파일 보관) -> 멀티프로세스 안전
log_handler = ConcurrentRotatingFileHandler(
    filename=os.path.join(LOG_DIR, "app.log"),
    maxBytes=300*1024*1024, # 300MB
    backupCount=10,         # 최대 10개 파일 보관
    encoding="utf-8",
)
log_handler.setLevel(logging.DEBUG)
formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
log_handler.setFormatter(formatter)

# 🔹 기존 로거 가져오기 (Gunicorn 등에서 사용 시 필요)
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

if not any(isinstance(h, logging.FileHandler) for h in logger.handlers):
    logger.addHandler(log_handler)
if not any(isinstance(h, logging.StreamHandler) for h in logger.handlers):
    logger.addHandler(logging.StreamHandler())
    
# 🚀 로그 설정 완료
logging.info("🚀 Gunicorn 멀티프로세스 + **안전한 크기별 로그 (300MB)** 설정 완료.")