from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager

db = SQLAlchemy()   # SQLAlchemy 초기화
jwt = JWTManager()  # JWT 초기화
