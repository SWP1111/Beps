import logging
import log_config
from flask_jwt_extended import JWTManager
from flask import Flask, request
from config import Config
from extensions import db, jwt
from blueprints import register_blueprints
import traceback

# Flask 애플리케이션 생성
app = Flask(__name__)
# Config 클래스를 사용하여 환경 변수 설정
app.config.from_object(Config)

# JWT 초기화
jwt.init_app(app)

# 🔹 Flask 요청/응답 로깅 추가 (선택 사항)
@app.before_request
def log_request():
    logging.info(f"요청: {request.method} {request.url} - 데이터: {request.get_json(silent=True)}")

@app.after_request
def log_response(response):
    logging.info(f"응답: [{request.path}] {response.status_code} - 데이터: {response.get_json(silent=True)}")
    return response

@app.errorhandler(Exception)
def handle_exception(e):
    # 모든 예외를 로깅합니다.
    logging.error(f"예외 발생: {str(e)}, {traceback.format_exc()}")
    return {"error": str(e)}, 500

@app.errorhandler(500)
def internal_error(error):
    # 500 에러를 로깅합니다.
    logging.error(f"500 Internal Server Error: {str(error)}, {traceback.format_exc()}")
    return {"error": "Internal Server Error"}, 500

# DB 초기화
db.init_app(app)

# 블루프린트 등록(API 등록)
register_blueprints(app)
# app.register_blueprint(api_user_bp, url_prefix='/user')
# app.register_blueprint(api_leaning_bp, url_prefix='/leaning')
# app.register_blueprint(api_contents_bp, url_prefix='/contents')

#if __name__ == '__main__':
#    app.run(debug=True, host='0.0.0.0', port=2000)
