import logging
import log_config
import decryption
from flask import Blueprint, jsonify, request, make_response
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity, verify_jwt_in_request, get_jwt
import datetime
from datetime import timezone
from extensions import db
from models import Users, Roles, ContentAccessGroups, LoginHistory, loginSummaryDay, loginSummaryAgg
from sqlalchemy.exc import OperationalError
from sqlalchemy.sql import text
import requests
from collections import defaultdict
from sqlalchemy import func

api_user_bp = Blueprint('user', __name__)

# 유효한 값인지 확인하는 함수, key가 data에 존재하고 '@' 또는 -1이 아닌 값이면 유효한 값으로 판단
def is_valid(key, data):
    return key in data and data[key] not in ('@', -1)

#DB /user/db_status API 연결 상태 확인
@api_user_bp.route('/db_status', methods=['GET'])
def check_db_status():
    try:
        logging.info(f"GET /db_status {db.engine.url}")
        db.session.execute(text('SELECT 1'))
        return jsonify({'status': 'OK'})
    except OperationalError as e:
        return jsonify({'error': str(e)}), 500


# GET /user/token_check API 토큰(쿠키) 유효 체크
@api_user_bp.route('/token_check', methods=['GET'])
@jwt_required(locations=['cookies'])  # JWT 검증을 먼저 수행
def check():
    current_user = get_jwt_identity()
    
    if current_user:
        return jsonify({"success": True, "user": current_user}), 200
    else:
        return jsonify({"success": False, "error":"Invalid token"}), 401

# POST /user/user API Users 테이블 Row 조회 API (로그인)
@api_user_bp.route('/user', methods=['POST'])
def get_user():
    try:
        data = request.get_json() # JSON 데이터를 가져옴
        logging.info(f"POST /user: {data}")
        
        user_id = data.get('id')
        password = data.get('password')
        is_encrypted = data.get('is_encrypted', True)
        id_address = data.get('ip_address')
                
        if not user_id or not password:
            return jsonify({'error': 'Please provide id and password'}), 400 # 400: Bad Request
        
        user = Users.query.filter_by(id=user_id).first()
        
        if user:               
            if is_encrypted: 
                logging.info(f"Encrypted data from client length: {len(password)} bytes")
            else:
                logging.info(f"No Encrypted data from client length: {len(password)} bytes")
                
            logging.info(f"Encrypted data from db length: {len(user.password)} bytes")
            
            decrypted_password_from_client = password
            if is_encrypted:
                logging.info(f"password from client: {password}")
                decrypted_password_from_client = decryption.decrypt(password, 'BEPS')            
            decryption_password_from_db = decryption.decrypt(user.password, 'BEPS')
            
            logging.info(f"decrypted_password_from_client: {decrypted_password_from_client}")
            logging.info(f"decryption_password_from_db: {decryption_password_from_db}")
            
            if decrypted_password_from_client != decryption_password_from_db:
                return jsonify({'error': 'Password is incorrect'}), 401 # 401: Unauthorized
                              
            user_data = user.to_dict()
            user_data.pop('password', None) # password 필드는 제외
                        
            ua = (request.headers.get('User-Agent') or '').lower()
            logging.info(f"User-Agent: {ua}")
            
            #로그인 이력 저장
            if not ua:               
                login_history = LoginHistory(user_id=user_id, login_time=datetime.datetime.now(timezone.utc), ip_address=id_address) 
                db.session.add(login_history)
                db.session.commit()
                       
                access_token = create_access_token(identity=user_id, additional_claims={'login_id':login_history.id}, expires_delta=datetime.timedelta(days=1)) # 1일 유효한 access token 생성
            else:
                access_token = create_access_token(identity=user_id, expires_delta=datetime.timedelta(days=1))
            response = jsonify({"user":user_data, "token":access_token})
            
            # 웹에서는 쿠키 설정
            if any(browser in ua for browser in ['chrome', 'safari', 'edge', 'opr', 'firefox']):  #"web" in request.headers.get('User-Agent',"").lower():                        
                response.set_cookie(
                    'access_token_cookie',     # 쿠키 이름
                    access_token,       # 쿠키 값
                    httponly=True,      # JS에서 쿠키 접근 금지
                    secure=False,       # HTTPS에서만 쿠키 전송(False: HTTP에서도 전송)
                    samesite='Lax',      # SameSite 설정(Lax: 외부 도메인으로는 쿠키 전송 안 함)
                    expires=(datetime.datetime.now(datetime.UTC) + datetime.timedelta(days=1)) # 1일 유효
                )     
            
            
            
            return response
        else:
            return jsonify({'error': 'User not found'}), 404    # 404: Not Found
    except OperationalError as e:
        return jsonify({'error': str(e)}), 500  # 500: Internal Server Error

# GET /user/user_info API Users 테이블 Row 조회 API (사용자 정보 조회)_인증된 사용자용
@api_user_bp.route('/user_info', methods=['GET'])
@jwt_required(locations=['headers','cookies'])  # JWT 검증을 먼저 수행
def get_user_info():
    try:
        user_id = request.args.get('id')
        if user_id is None:
            return jsonify({'error': 'Please provide id'}), 400
        
        user = Users.query.filter_by(id=user_id).first()
        if user is None:
            return jsonify({'error': 'User not found'}), 404
        else:
            user_data = user.to_dict()
            user_data.pop('password', None) # password 필드는 제외
            return jsonify(user_data), 200
        
    except OperationalError as e:
        return jsonify({'error': str(e)}), 500

# GET /user/user_auth_time API User 테이블의 특정 사용자의 인증 시간 조회
@api_user_bp.route('/user_auth_time', methods=['GET'])
def get_user_auth_time():
    try:
        user_id = request.args.get('id')
        
        if user_id is None:
            return jsonify({'error': 'Please provide id'}), 400 # 400: Bad Request
        
        user = Users.query.filter_by(id=user_id).first()
        if user:
            return jsonify(user.time_stamp)
        else:
            return jsonify({'error': 'User not found'}), 404    # 404: Not Found
    except OperationalError as e:
        return jsonify({'error': str(e)}), 500

     
# POST /user/update_user API Users 테이블 Row Insert/Update API
@api_user_bp.route('/update_user', methods=['POST'])
def upsert_user():
    try:
        data = request.get_json() # JSON 데이터를 가져옴
        if not data or 'id' not in data:
            return jsonify({'error': 'Please provide id'}), 400
        
        user_id = data.get('id')
        login = data.get('login')
        logging.info(f"login: {login}")
        
        user = Users.query.filter_by(id=user_id).first()
        if user is None:    # 새로운 Row 추가
            user = Users(id=user_id)
            user.password = data.get('password')
            if(is_valid('company', data)): user.company = data.get('company')
            if(is_valid('department', data)): user.department = data.get('department')
            if(is_valid('position', data)): user.position = data.get('position')
            if(is_valid('name', data)): user.name = data.get('name')
            if(is_valid('access_group_id', data)): user.access_group_id = data.get('access_group_id')
            if(is_valid('role_id', data)): user.role_id = data.get('role_id')
            if login is True: user.login_time = datetime.datetime.now(timezone.utc)
            db.session.add(user)
            db.session.commit()
        else:   # Row 업데이트
            if(is_valid('password',data)): user.password = data.get('password')
            if(is_valid('company',data)):user.company = data.get('company')
            if(is_valid('department',data)):user.department = data.get('department')
            if(is_valid('position',data)):user.position = data.get('position')
            if(is_valid('name',data)):user.name = data.get('name')
            if(is_valid('access_group_id',data)):user.access_group_id = data.get('access_group_id')
            if(is_valid('role_id',data)):user.role_id = data.get('role_id')
            if login is True: user.login_time = datetime.datetime.now(timezone.utc)
            db.session.commit()
        return jsonify(user.to_dict()), 201
    except OperationalError as e:   # DB 접속 오류 처리
        return jsonify({'error': str(e)}), 500

# GET /user/logout API 사용자 로그아웃 API
@api_user_bp.route('/logout', methods=['GET'])
@jwt_required(locations=['headers','cookies'])  # JWT 검증을 먼저 수행
def logout():  
    try:
        user_id = get_jwt_identity()
        claims = get_jwt()
        
        login_id = claims.get('login_id')
        logging.info(f"login_id: {login_id}")
        
        logout_update =  request.args.get('logout_update', 'false').lower() == 'true'
        
        if not user_id:
            return jsonify({'error': 'Please provide id'}), 400
    
        user = Users.query.filter_by(id=user_id).first()
    
        # 로그인 이력 업데이트
        if login_id:
            login = LoginHistory.query.filter_by(id=login_id).first()
            if login:
                login.logout_time = datetime.datetime.now(timezone.utc)
                duration = login.logout_time - login.login_time
                
                if duration.total_seconds() < 5:
                    db.session.delete(login) # 로그인 이력이 5초 미만이면 삭                
                
                db.session.commit()
            
        if user:
            if logout_update is True:
                user.logout_time = datetime.datetime.now(timezone.utc) # 로그아웃 시간 업데이트(UTC)
                db.session.commit()
            
            response = make_response(jsonify({'message': f'User {user_id} logged out successfully.', 'logout_time': user.logout_time}))
            response.set_cookie('access_token_cookie', '', expires=0, httponly=True, secure=False, samesite='Lax') # 쿠키 삭제
            
            return response, 200
        else:
            return jsonify({'error': 'User not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500
          
# GET /user/roles API Roles 테이블 조회
@api_user_bp.route('/roles', methods=['GET'])
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

# POST /user/erp_login API ERP Login
@api_user_bp.route('/erp_login', methods=['POST'])
def erp_login():
    try:
        data = request.get_json() # JSON 데이터를 가져옴
        targetUrl = data.get('targetUrl')
        params = data.get('params')
        
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded',
        }
        
        # ERP 로그인 API 호출
        response = requests.post(targetUrl, headers=headers, data=params)
        logging.info(f"ERP Login Response: {response.text} {response.status_code} {response.headers}")
        logging.info(f"ERP Login Cookies: {response.cookies}")
        logging.info(f"ERP Login Set-Cookie Headers: {response.headers.get('Set-Cookie')}")
        
        # 응답 데이터와 상태 코드 반환
        return jsonify({"status": response.status_code, "data": response.text}), response.status_code

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@api_user_bp.route('/get_connection_duration', methods=['GET'])
@jwt_required(locations=['headers','cookies'])  # JWT 검증을 먼저 수행
def get_connection_duration():
    try:
        filter_type = request.args.get('filter_type', 'all')
        filter_value = request.args.get('filter_value')
        logging.info(f"filter_type: {filter_type}, filter_value: {filter_value}")
        
        if filter_type != 'all' and filter_value is None:
            return jsonify({'error': 'Please provide filter_value'}), 400
               
        period_type = request.args.get('period_type', 'day')
        period_value = request.args.get('period_value')
        logging.info(f"period_type: {period_type}, period_value: {period_value}")
        
        if period_value is None:
            return jsonify({'error': 'Please provide period_value'}), 400
        
        if(period_type == 'day'):
            start_date, end_date = [datetime.datetime.strptime(d.strip(), '%Y-%m-%d').date() for d in period_value.split('~')]
            data = get_connection_summary_day(start_date, end_date, filter_value)
                                
            if data['has_data']:
                return jsonify({
                    'total_duration': str(data['total_duration']),
                    'worktime_duration': str(data['worktime_duration']),
                    'offhour_duration': str(data['offhour_duration']),
                    'internal_count': data['internal_count'],
                    'external_count': data['external_count']
                })
            else:    
                return jsonify({'error': 'Invalid period_type'}), 400      
             
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    
    
@api_user_bp.route('/get_top_user_duration', methods=['GET'])
@jwt_required(locations=['headers','cookies'])  # JWT 검증을 먼저 수행
def get_top_user_duration():
    try:
        period_type = request.args.get('period_type', 'day')
        period_value = request.args.get('period_value')
        
        if period_value is None:
            return jsonify({'error': 'Please provide period_value'}), 400
        
        if period_type == 'day':
            start_date, end_date = [datetime.datetime.strptime(d.strip(), '%Y-%m-%d').date() for d in period_value.split('~')]           
            user_duration_map = defaultdict(datetime.timedelta)
            
            if start_date < (datetime.date.today() - datetime.timedelta(days=1)):
                summary_day_rows = db.session.query(
                    loginSummaryDay.user_id,
                    func.sum(loginSummaryDay.total_duration).label('total')
                ).filter(
                    loginSummaryDay.period_value >= start_date,
                    loginSummaryDay.period_value <= min(end_date, datetime.date.today() - datetime.timedelta(days=2)),
                    loginSummaryDay.scope == 'user'
                ).all()
                for record in summary_day_rows:
                    if record.user_id:
                        user_duration_map[record.user_id] += record.total or datetime.timedelta()
            
            if end_date in (datetime.date.today(), datetime.date.today() - datetime.timedelta(days=1)):
                today_rows = db.session.query(
                    LoginHistory.user_id,
                    func.sum(LoginHistory.session_duration).label('total')
                ).filter(
                    LoginHistory.login_time >= max(start_date, datetime.date.today() - datetime.timedelta(days=1)),
                    LoginHistory.login_time <= end_date
                ).group_by(LoginHistory.user_id).all()
                for record in today_rows:
                    if record.user_id:
                        user_duration_map[record.user_id] += record.total or datetime.timedelta()
            
            if user_duration_map:
                top_user_id, top_duration = max(user_duration_map.items(), key=lambda x: x[1])
                return jsonify({
                    'user_id': top_user_id,
                    'duration': str(top_duration)
                }), 200
            else:
                return jsonify({'error': 'No data found'}), 404
                              
    except Exception as e:
        return jsonify({'error': str(e)}), 500
  
    
def get_connection_summary_day(start_date, end_date, scope, filter_value=None):
    total = datetime.timedelta(0)
    work = datetime.timedelta(0)
    off = datetime.timedelta(0)
    internal = 0
    external = 0
    has_data = False
    
    if start_date < (datetime.date.today() - datetime.timedelta(days=1)):
        filters = [
            loginSummaryDay.period_value >= start_date,
            loginSummaryDay.period_value <= min(end_date, datetime.date.today() - datetime.timedelta(days=2)),
            loginSummaryDay.scope == scope
        ]
        if scope == 'user' and filter_value:
            filters.append(loginSummaryDay.user_id == filter_value)
        elif scope == 'department' and filter_value:
            filters.append(loginSummaryDay.department == filter_value)
        elif scope == 'company' and filter_value:
            filters.append(loginSummaryDay.company == filter_value)
        
        data = loginSummaryDay.query.filter(*filters).first()
        if data:
            has_data = True
            total = data.total_duration or datetime.timedelta(0)
            work = data.worktime_duration or datetime.timedelta(0)
            off = data.offhour_duration or datetime.timedelta(0)
            internal = data.internal_count or 0
            external = data.external_count or 0
            
    if end_date in (datetime.date.today(), datetime.date.today() - datetime.timedelta(days=1)):
        filters = [
            LoginHistory.login_time >= max(start_date, datetime.date.today() - datetime.timedelta(days=1)),
            LoginHistory.login_time <= end_date
        ]
        if scope == 'user' and filter_value:
            filters.append(LoginHistory.user_id == filter_value)
        elif scope == 'department' and filter_value:
            filters.append(LoginHistory.department == filter_value)
        elif scope == 'company' and filter_value:
            filters.append(LoginHistory.company == filter_value)
        
        datas = LoginHistory.query.filter(*filters).all()
        if datas:
            has_data = True
            for record in datas:
                if record.login_time is None or record.logout_time is None:
                    continue
                
                duration = record.session_duration or datetime.timedelta(0)
                total += duration
                
                login_locale = record.login_time.astimezone()
                logout_locale = record.logout_time.astimezone()
                if login_locale.hour >= 8 and logout_locale.hour <= 18:
                    work += duration
                else:
                    off += duration
                
                if record.ip_address.startswith('61.') or record.ip_address.startswith('172.'):
                    internal += 1 
                else:
                    external += 1
        
    return {
        'has_data': has_data,
        'total_duration': total,
        'worktime_duration': work,
        'offhour_duration': off,
        'internal_count': internal,
        'external_count': external
    }
        
            