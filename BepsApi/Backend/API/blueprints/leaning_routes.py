import logging
import log_config
from flask import Blueprint, jsonify, request
import datetime
from datetime import timezone
from datetime import timedelta
from extensions import db
from flask_jwt_extended import jwt_required
from models import Users, ContentViewingHistory, Files, ContentPointRecord
from sqlalchemy.exc import OperationalError
from sqlalchemy.sql import text
from config import Config
import pandas as pd
import glob
import os
import pickle
from flask import session

api_leaning_bp = Blueprint('leaning', __name__) # 🔹 블루프린트 생성

#region 문자열 변환
def serialize_row(row):
    row_dict = dict(row._mapping)

    # stay_duration을 문자열로 변환 (HH:MM:SS 형식)
    if isinstance(row_dict.get("stay_duration"), datetime.timedelta):
        row_dict["stay_duration"] = str(row_dict["stay_duration"])  

    # start_time과 end_time을 문자열로 변환 (ISO 8601 형식)
    if isinstance(row_dict.get("start_time"), datetime.datetime):
        row_dict["start_time"] = row_dict["start_time"].isoformat()
    if isinstance(row_dict.get("end_time"), datetime.datetime):
        row_dict["end_time"] = row_dict["end_time"].isoformat()

    return row_dict
#endregion

# 🔹 GET /leaning/start API 시간 반환
@api_leaning_bp.route('/start', methods=['GET'])
def start():
    try:
        start_time = datetime.datetime.now(timezone.utc).isoformat()
        return jsonify({'status': 'OK', 'start_time': start_time})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# 🔹 POST /leaning/end API 기록 저장
@api_leaning_bp.route('/end', methods=['POST']) # 🔹 POST /leaning/end API
@jwt_required(locations=['headers','cookies'])  # 🔹 JWT 검증을 먼저 수행
def end():
    try:
        data = request.get_json() # 🔹 JSON 데이터를 가져옴
        logging.info(f"POST /leaning/end: {data}")
        
        user_id = data.get('user_id')
        file_id = data.get('file_id')
        file_name = data.get('file_name')
        ip_address = data.get('ip_address')
        start_time_str = data.get('start_time')
        start_time = datetime.datetime.fromisoformat(start_time_str)
        
        if user_id is None or (file_id is None and file_name is None) or ip_address is None:
            return jsonify({'error': 'Please provide id'}), 400 # 400: Bad Request
        
        # file_id가 없는 경우 file_name으로 file_id를 조회
        if file_id is None and file_name:
            file_id = Files.query.filter_by(file_name=file_name).first().file_id
        
        end_time = datetime.datetime.now(timezone.utc)
        duration = end_time - start_time
        
        if duration >= timedelta(seconds=Config.POINT_DURATION_SECONDS): # 최소 5분 이상 시청한 경우 DB 저장          
            # 🔹 ContentViewingHistory 객체 생성
            learning = ContentViewingHistory(
                user_id=user_id,
                file_id=file_id,
                start_time=start_time, # - timedelta(seconds=15),
                end_time=end_time,
                ip_address=ip_address,
                )
            db.session.add(learning)            
            point_success, point_reason = try_add_point(user_id, file_id, end_time, duration)
            db.session.commit()

            return jsonify({
                'status': 'OK', 
                'id': learning.id, 
                'point_added': point_success, 
                'point_reason': point_reason
                }), 201 # 201: Created
        else:
            return jsonify({"message": "Viewing duration too short, not saved"}), 204 # 204: No Content
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def try_add_point(user_id, file_id, end_time, duration, max_point=5):
    """포인트 추가 로직"""
    try:
        if duration.total_seconds() >= Config.POINT_DURATION_SECONDS:  # 5분 이상 시청한 경우
            record = ContentPointRecord.query.filter_by(user_id=user_id, file_id=file_id).first()
            
            if record:
                if record.point < max_point:
                    record.point += 1
                    record.earned_times = record.earned_times + [end_time.strftime("%Y-%m-%d %H:%M:%S")]
                    return True, None
                else:
                    return False, "Max points reached"
            else:
                record = ContentPointRecord(
                    user_id=user_id,
                    file_id=file_id,
                    point=1,
                    earned_times=[end_time.strftime("%Y-%m-%d %H:%M:%S")]
                )
                db.session.add(record)
                return True, None
        else:
            return False, "Duration too short"
    except Exception as e:
        return False, str(e)  # 에러 메시지 반환

# 🔹 GET /leaning/data API 기록 조회
@api_leaning_bp.route('/data', methods=['GET']) # 🔹 GET /leaning/data API
@jwt_required(locations=['headers','cookies'])  # 🔹 JWT 검증을 먼저 수행
def data():
    try:
        page = int(request.args.get('page', 1))
        page_size = int(request.args.get('page_size', 30))
        offset = (page-1)*page_size
        
        user_id = request.args.get('user_id')
        user_name = request.args.get('user_name')
        file_name = request.args.get('file_name')
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        
        base_query = """
            SELECT v.id, v.user_id, COALESCE(u.name,'[삭제된 사용자]') AS name, v.file_id, COALESCE(f.file_name,'[삭제된 파일]') As file_name, v.start_time, v.end_time, v.stay_duration, v.ip_address
            FROM content_viewing_history_view v
            LEFT JOIN users u ON v.user_id = u.id
            LEFT JOIN files f ON v.file_id = f.file_id
            """
        
        filters = []
        params = {'limit': page_size, 'offset': offset}
        
        if user_id:
            filters.append("v.user_id = :user_id")
            params['user_id'] = user_id
        if user_name:
            filters.append("u.name LIKE :user_name")
            params['user_name'] = f"%{user_name}%"
        if file_name:
            filters.append("f.file_name LIKE :file_name")
            params['file_name'] = f"%{file_name}%"
        if start_date:
            filters.append("v.start_time >= :start_date")
            params['start_date'] = f"{start_date} 00:00:00"
        if end_date:
            filters.append("v.end_time <= :end_date")
            params['end_date'] = f"{end_date} 23:59:59"
        
        if filters:
            base_query += " WHERE " + " AND ".join(filters)
            
        final_query = base_query + " ORDER BY v.id LIMIT :limit OFFSET :offset"
        
        count_query = """SELECT COUNT(*) 
                         FROM content_viewing_history_view v
                         LEFT JOIN users u ON v.user_id = u.id
                         LEFT JOIN files f ON v.file_id = f.file_id
        """
        if(filters):
            count_query += " WHERE " + " AND ".join(filters)
        
        total_db_count = db.session.execute(text(count_query), {k: v for k, v in params.items() if k not in ["limit", "offset"]}).scalar()
        db_data = [serialize_row(row) for row in db.session.execute(text(final_query), params).fetchall()]
        
        logging.info(f"total_db_count: {total_db_count}")
        
        return jsonify({
            'db_count' : total_db_count,
            'page': page,
            'page_size': page_size,
            'data': db_data
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500