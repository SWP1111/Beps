import atexit
import logging
import log_config
from flask_jwt_extended import JWTManager
from flask import Flask, request
from config import Config
from extensions import db, jwt
from blueprints import register_blueprints
import traceback
from apscheduler.schedulers.background import BackgroundScheduler


def init_scheduler(app):
    try:
        from blueprints.statistics_routes import scheduled_cleanup
        with app.app_context():
            lock_acquired = db.session.execute(db.text("SELECT pg_try_advisory_lock(1234567890)")).scalar()
            if not lock_acquired:
                logging.warning("다른 프로세스가 이미 DB 잠금을 보유하고 있습니다.")
                return None
            logging.info("DB 잠금 획득 성공")
            scheduler = BackgroundScheduler()
            scheduler.add_job(scheduled_cleanup, 'interval', minutes=65, max_instances=1, coalesce=True)
            
            def shutdown():
                with app.app_context():
                    logging.info("스케줄러 종료")
                    db.session.execute(db.text("SELECT pg_advisory_unlock(1234567890)"))
                    db.session.commit()
                scheduler.shutdown(wait=False)
                
            atexit.register(shutdown)
            scheduler.start()
            return scheduler
    except Exception as e:
        logging.error(f"DB 연결 오류: {str(e)}, {traceback.format_exc()}")
        return None
    
def create_app():    
    # Flask 애플리케이션 생성
    app = Flask(__name__)
    # Config 클래스를 사용하여 환경 변수 설정
    app.config.from_object(Config)
    # JWT 초기화
    jwt.init_app(app)   
    # DB 초기화
    db.init_app(app)   
    # 블루프린트 등록(API 등록)
    register_blueprints(app)
    # 스케줄러 초기화
    scheduler = init_scheduler(app)
    
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

    return app

app = create_app()

# app.register_blueprint(api_user_bp, url_prefix='/user')
# app.register_blueprint(api_leaning_bp, url_prefix='/leaning')
# app.register_blueprint(api_contents_bp, url_prefix='/contents')

#if __name__ == '__main__':
#    app.run(debug=True, host='0.0.0.0', port=2000)
