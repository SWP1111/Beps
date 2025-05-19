from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager
from flask_caching import Cache

db = SQLAlchemy()   # SQLAlchemy 초기화
jwt = JWTManager()  # JWT 초기화
cache = Cache()     # Cache 초기화
