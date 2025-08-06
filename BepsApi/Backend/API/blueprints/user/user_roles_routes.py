import logging
import log_config
import datetime
import os
import requests
from datetime import timezone
from extensions import db
from flask import jsonify, request
from sqlalchemy.exc import OperationalError
from utils.swagger_loader import get_swag_from
from models import Roles
from . import api_user_bp, yaml_folder
          
# GET /user/roles API Roles 테이블 조회
@api_user_bp.route('/roles', methods=['GET'])
@get_swag_from(yaml_folder, 'roles.yaml')
def get_roles():
    try:
        roles = Roles.query.all()
        return jsonify([role.to_dict() for role in roles])
    except OperationalError as e:
        return jsonify({'error': str(e)}), 500

# POST /user/roles API Roles 테이블 Row 추가
@api_user_bp.route('/roles', methods=['POST'])
def create_role():
    try:
        data = request.get_json() # JSON 데이터를 가져옴
        if not data or 'role_name' not in data:
            return jsonify({'error': 'Please provide role_name'}), 400
        
        new_role = Roles(role_name=data.get('role_name'))
        db.session.add(new_role)
        db.session.commit()
        return jsonify(new_role.to_dict()), 201
    except OperationalError as e:   # DB 접속 오류 처리
        return jsonify({'error': str(e)}), 500
    except Exception as e:  # 그 외 오류 처리
        return jsonify({'error': str(e)}), 500
