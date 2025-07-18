#!/bin/bash

# 실행하려면
# 1. 이 스크립트를 실행할 수 있는 권한을 부여합니다.
#    chmod +x deploy_prod_backup.sh
# 2. 스크립트를 실행합니다.
#    ./deploy_prod_backup.sh

# ---------- 설정 ----------
PROD_USER="user_beps"
PROD_HOST="172.16.10.191"
PROD_PORT="10022"
PROD_BASE="/home/user_beps/beps_server/BepsApi"
BACKUP_BASE="/home/user_beps/beps_server/BepsApi_backup_$(date +%Y%m%d%H%M)"
TEST_BASE="/home/user_ccp/service/BepsApi"

# ---------- 운영 서버에서 백업 ----------
echo "✅ 운영 서버에 기존 파일 백업 중..."
ssh -p ${PROD_PORT} ${PROD_USER}@${PROD_HOST} "cp -r ${PROD_BASE} ${BACKUP_BASE}"

echo "✅ 백업 완료: ${BACKUP_BASE}"

# ---------- 테스트 서버에서 임시 폴더 복사 ----------
cp -r ${TEST_BASE}/Backend /tmp/backend_release

# ---------- Websocket/websocket_handler.py 수정 ----------
sed -i 's|http://172.16.10.191:20000/user/logout|https://beps.hmac.kr/user/logout|g' /tmp/backend_release/Websocket/websocket_handlers.py

# ---------- 폴더 Backend 복사 ----------
echo "🚀 폴더 Backend 배포 중..."
rsync -avz --delete -e "ssh -p ${PROD_PORT}" \
    --exclude='API/config.py' \
    --exclude='API/.env' \
    --exclude='API/logs/' \
    --exclude='API/__pycache__/' \
    --exclude='API/blueprints/__pycache__/' \
    --exclude='API/blueprints/contents/__pycache__/' \
    --exclude='API/docs/__pycache__/' \
    --exclude='API/services/__pycache__/' \
    --exclude='DB/log/' \
    --exclude='Websocket/logs/' \
    --exclude='Websocket/__pycache__/' \
    /tmp/backend_release/ ${PROD_USER}@${PROD_HOST}:${PROD_BASE}/Backend/

# ---------- 임시 폴더 삭제 ----------
rm -rf /tmp/backend_release

# ---------- 폴더 Frontend 복사 ----------
echo "🚀 폴더 Frontend 배포 중..."
rsync -avz --delete -e "ssh -p ${PROD_PORT}" \
    --exclude='asset/js/config.js' \
    ${TEST_BASE}/Frontend/ ${PROD_USER}@${PROD_HOST}:${PROD_BASE}/Frontend/

echo "✅ 모든 배포 완료!"