from flask import Blueprint

# 🔹 블루프린트 생성
def register_blueprints(app):
    from blueprints.user_routes import api_user_bp
    from blueprints.leaning_routes import api_leaning_bp
    from blueprints.contents_routes import api_contents_bp
    from blueprints.memo_routes import api_memo_bp
    
    app.register_blueprint(api_user_bp, url_prefix='/user')
    app.register_blueprint(api_leaning_bp, url_prefix='/leaning')
    app.register_blueprint(api_contents_bp, url_prefix='/contents')
    app.register_blueprint(api_memo_bp, url_prefix='/memo')