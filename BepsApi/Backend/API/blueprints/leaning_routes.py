import logging
import log_config
from flask import Blueprint, jsonify, request
import datetime
from datetime import timezone
from datetime import timedelta
from extensions import db
from flask_jwt_extended import jwt_required
from models import Users, ContentViewingHistory, ContentPointRecord, ContentRelPages, ContentRelPageDetails, LearningCompletionHistory
from sqlalchemy.exc import OperationalError
from sqlalchemy.sql import text
from config import Config
import pandas as pd
import glob
import os
import pickle
from flask import session
from sqlalchemy import distinct, func, tuple_
import traceback

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
        
        user_id = data.get('user_id').lower() 
        logging.debug(f"[end] user_id: {user_id}")
        file_id = data.get('file_id')
        file_type = data.get('file_type')
        ip_address = data.get('ip_address')
        start_time_str = data.get('start_time')
        start_time = datetime.datetime.fromisoformat(start_time_str)
        
        if user_id is None or file_id is None or ip_address is None:
            return jsonify({'error': 'Please provide id'}), 400 # 400: Bad Request
               
        end_time = datetime.datetime.now(timezone.utc)
        duration = end_time - start_time
        
        if duration >= timedelta(seconds=Config.POINT_DURATION_SECONDS): # 최소 5분 이상 시청한 경우 DB 저장          
            # 🔹 ContentViewingHistory 객체 생성
            learning = ContentViewingHistory(
                user_id=user_id,
                file_id=file_id,
                file_type=file_type,
                start_time=start_time, # - timedelta(seconds=15),
                end_time=end_time,
                ip_address=ip_address,
                )
            db.session.add(learning)     
            point_success, point_reason = try_add_point(user_id, file_id, file_type, end_time, duration)
            if(file_type == 'page'):
                add_comletion_history(user_id, file_id, duration, end_time)            

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

def try_add_point(user_id, file_id, file_type, end_time, duration, max_point=5):
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
                    file_type=file_type,
                    point=1,
                    earned_times=[end_time.strftime("%Y-%m-%d %H:%M:%S")]
                )
                db.session.add(record)
                return True, None
        else:
            return False, "Duration too short"
    except Exception as e:
        return False, str(e)  # 에러 메시지 반환

def add_comletion_history(user_id, page_id, duration, end_time):
    """학습 완료 기록 추가"""
    try:
        item = LearningCompletionHistory.query.filter_by(user_id=user_id, page_id=page_id).first()
        if item:
             already_completed = item.total_duration >= timedelta(minutes=Config.LEARNING_COMPLETED_MINUTES) 
             
             item.total_duration += duration
             if not already_completed and item.total_duration >= timedelta(minutes=Config.LEARNING_COMPLETED_MINUTES):
                 item.completed_at = end_time           
        else:
            total_duration = duration
            completed_at = end_time if total_duration >= timedelta(minutes=Config.LEARNING_COMPLETED_MINUTES) else None
            
            item = LearningCompletionHistory(
                user_id=user_id,
                page_id=page_id,
                total_duration=total_duration,
                completed_at=completed_at
            )
            db.session.add(item)
    except Exception as e:
        logging.error(f"Error adding completion history: {str(e)}")
        return False
    return True

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
            SELECT v.id, v.user_id, COALESCE(u.name,'[삭제된 사용자]') AS name,
            v.file_id, 
            COALESCE(
                CASE
                    WHEN v.file_type='page' THEN p.name
                    WHEN v.file_type='detail' THEN dp.name
                    ELSE NULL
                END,
                '[삭제된 파일]'
                ) As file_name, 
            CASE
                WHEN v.file_type='detail' THEN d.name
                ELSE ''
            END AS detail_name,
            v.start_time, v.end_time, v.stay_duration, v.ip_address
            FROM content_viewing_history v
            LEFT JOIN users u ON v.user_id = u.id
            LEFT JOIN content_rel_pages p ON v.file_type='page' AND v.file_id = p.id
            LEFT JOIN content_rel_page_details d ON v.file_type='detail' AND v.file_id = d.id
            LEFT JOIN content_rel_pages dp ON d.page_id = dp.id 
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
            filters.append("""
                (
                    (v.file_type='page' AND p.name LIKE :file_name)
                    OR (v.file_type='detail' AND d.name LIKE :file_name)
                )
            """)
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
                         FROM content_viewing_history v
                         LEFT JOIN users u ON v.user_id = u.id
                         LEFT JOIN content_rel_pages p ON v.file_type='page' AND v.file_id = p.id
                         LEFT JOIN content_rel_page_details d ON v.file_type='detail' AND v.file_id = d.id
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

# 🔹 GET /leaning/point API 포인트 조회       
@api_leaning_bp.route('/point', methods=['GET']) 
@jwt_required(locations=['headers','cookies'])  # 🔹 JWT 검증을 먼저 수행
def point():
    import services.user_summary_service as user_summary_service
    try:
        period_type = request.args.get('period_type', 'year')
        period_value = request.args.get('period_value')
        filter_type = request.args.get('filter_type', 'all')
        filter_value = request.args.get('filter_value')
                
        if period_type != 'year' and period_type is None:
            return jsonify({'error': 'Please provide period_type'}), 400    # 400: Bad Request
        
        if filter_type != 'all' and filter_type is None:
            return jsonify({'error': 'Please provide filter_type'}), 400    # 400: Bad Request
                
        start_date, end_date = user_summary_service.get_period_value(period_type, period_value)
        local_tz = datetime.datetime.now().astimezone().tzinfo
        utc_start_date = datetime.datetime.combine(start_date, datetime.time.min, tzinfo=local_tz).astimezone(datetime.timezone.utc)
        utc_end_date = datetime.datetime.combine(end_date, datetime.time.max, tzinfo=local_tz).astimezone(datetime.timezone.utc)
        
        filters = {}

        # 포인트 조회(file_type = page)
        base_sql = """
            SELECT SUM(cpr.point) AS total_points,
            (
                SELECT AVG(COALESCE(points_per_user, 0)) FROM (
                    SELECT u2.id, SUM(cpr2.point) AS points_per_user
                    FROM users u2
                    LEFT JOIN content_point_record cpr2 ON u2.id = cpr2.user_id
                    LEFT JOIN LATERAL jsonb_array_elements_text(cpr2.earned_times) AS et ON TRUE
                    WHERE (
                        et::timestamp BETWEEN :start_date AND :end_date
                        OR et IS NULL
                    ) AND cpr2.file_type = 'page'
                    {inner_clause}
                    GROUP BY u2.id
                ) AS avg_points_sub
            ) AS average_points
            FROM content_point_record cpr
            JOIN users u ON cpr.user_id = u.id
            JOIN LATERAL jsonb_array_elements_text(cpr.earned_times) AS earned_time ON TRUE
            WHERE earned_time::timestamp BETWEEN :start_date AND :end_date AND cpr.file_type = 'page' 
            """
        filters['start_date'] = utc_start_date
        filters['end_date'] = utc_end_date
        
        # 포인트 조회
        innter_clause = ""       
        if filter_type == 'company' and filter_value:
            base_sql += " AND u.company = :filter_value"
            innter_clause += " AND u2.company = :filter_value"
            filters['filter_value'] = filter_value
        elif filter_type == 'department' and filter_value:
            parts = filter_value.split('||',1)
            if len(parts) == 2:
                company_name, department_name = parts
                base_sql += " AND u.company = :company_name AND u.department = :department_name"
                innter_clause += " AND u2.company = :company_name AND u2.department = :department_name"
                filters['company_name'] = company_name
                filters['department_name'] = department_name
            else:
                department_name = parts[0]
                base_sql += " AND u.department = :department_name"
                innter_clause += " AND u2.department = :department_name"
                filters['department_name'] = department_name
        elif filter_type == 'user' and filter_value:
            base_sql += " AND u.id = :user_id"
            innter_clause += " AND u2.id = :user_id"
            filters['user_id'] = filter_value
        
        final_sql = base_sql.format(inner_clause=innter_clause)
        result = db.session.execute(text(final_sql), filters).first()
                
        return jsonify({
            'total_points': result.total_points or 0,
            'average_points': result.average_points or 0,
            }), 200 # 200: OK
      
    except Exception as e:
        return jsonify({'[point] error': str(e)}), 500


# 🔹 GET /leaning/point/rank API 포인트 랭킹 조회
@api_leaning_bp.route('/point/rank', methods=['GET'])
@jwt_required(locations=['headers','cookies'])  # 🔹 JWT 검증을 먼저 수행
def point_rank():
    import services.user_summary_service as user_summary_service
    try:
        period_type = request.args.get('period_type', 'year')
        period_value = request.args.get('period_value')
        filter_type = request.args.get('filter_type', 'all')
        
        if period_type != 'year' and period_type is None:
            return jsonify({'error': 'Please provide period_type'}), 400    # 400: Bad Request
        
        if filter_type in ['all','company', 'department'] is False:
            return jsonify({'error': 'Please provide filter_type'}), 400    # 400: Bad Request
        
        start_date, end_date = user_summary_service.get_period_value(period_type, period_value)
        local_tz = datetime.datetime.now().astimezone().tzinfo
        utc_start_date = datetime.datetime.combine(start_date, datetime.time.min, tzinfo=local_tz).astimezone(datetime.timezone.utc)
        utc_end_date = datetime.datetime.combine(end_date, datetime.time.max, tzinfo=local_tz).astimezone(datetime.timezone.utc)
        
        filters = {'start_date': utc_start_date, 'end_date': utc_end_date}
        
        if filter_type == 'all':
            select_field = 'u.id, COALESCE(u.name,\'[삭제된 사용자]\') AS name'
            group_by_field = 'u.id, u.name'
        elif filter_type == 'company':
            select_field = 'u.company'
            group_by_field = 'u.company'
        elif filter_type == 'department':
            select_field = 'u.company, u.department'
            group_by_field = 'u.company, u.department'
        else:
            return jsonify({'error': 'Invalid filter_type'}), 400    # 400: Bad Request
        
        rank_sql = f"""
            SELECT {select_field}, COALESCE(SUM(
                CASE
                    WHEN earned_time IS NOT NULL
                            AND earned_time::timestamp BETWEEN :start_date AND :end_date
                    THEN cpr.point
                    ELSE 0
                END), 0) AS total_points
            FROM users u
            LEFT JOIN content_point_record cpr ON u.id = cpr.user_id
            LEFT JOIN LATERAL jsonb_array_elements_text(cpr.earned_times) AS earned_time ON TRUE
            GROUP BY {group_by_field}
        """
        
        all_rows = db.session.execute(text(rank_sql), filters).mappings().all()
        sorted_rows = sorted(all_rows, key=lambda x: x['total_points'], reverse=True)   
        
         # 상위, 하위 점수 찾기
        top_score = sorted_rows[0]['total_points']
        bottom_score = sorted_rows[-1]['total_points']
        
        # 상위/하위 동점자 모두 추출
        top_list = [dict(row) for row in sorted_rows if row['total_points'] == top_score]
        bottom_list = [dict(row) for row in sorted_rows if row['total_points'] == bottom_score]
        
        return jsonify({
            'top': top_list,
            'bottom': bottom_list,
        }), 200  # 200: OK
        
    except Exception as e:
        return jsonify({'[point/rank] error': str(e)}), 500
        
#🔹 GET /leaning/category_progress API 카테고리별 학습 진행률 조회       
@api_leaning_bp.route('/category_progress', methods=['GET'])
@jwt_required(locations=['headers','cookies'])  # 🔹 JWT 검증을 먼저 수행
def category_progress():
    from services.leaning_summary_service import get_folder_progress
    try:
        filter_type = request.args.get('filter_type', 'all')
        filter_value = request.args.get('filter_value')
        period_type = request.args.get('period_type', 'year')
        period_value = request.args.get('period_value')
        
        if not period_type or not period_value:
            return jsonify({'error': 'Please provide scope, period_type, and period_value'}), 400
        
        params = {
            'filter_type': filter_type,
            'filter_value': filter_value,
            'period_type': period_type,
            'period_value': period_value
        }
        
        folder_duration_map = get_folder_progress(params)
        
        if not folder_duration_map:
            return jsonify({'error': 'No data found'}), 404
        
        total_duration = sum((duration for _, duration in folder_duration_map.values()), datetime.timedelta(0))
        total_seconds = total_duration.total_seconds()
        if total_seconds == 0:
            total_seconds = 1  # Avoid division by zero
        
        result = []
        for channel_id, (channel_name, duration) in folder_duration_map.items():
            duration_seconds = duration.total_seconds() if duration else 0
            percentage = round(duration_seconds / total_seconds * 100, 1)
            hour = duration_seconds // 3600
            minute = (duration_seconds % 3600) // 60
            second = duration_seconds % 60
            result.append({
                'channel_id': channel_id,
                'channel_name': channel_name,
                'duration': f"{int(hour):02}:{int(minute):02}:{int(second):02}",
                'percentage': percentage
            })
            
        return jsonify({'progress': result}), 200  # 200: OK
    
    except Exception as e:
        logging.error(f"[category_progress] error: {str(e)}, {traceback.format_exc()}")
        return jsonify({'[category_progress] error': str(e)}), 500
 
# 🔹 GET /leaning/top_viewd_pages API 상위 조회 페이지 조회
@api_leaning_bp.route('/top_viewed_pages', methods=['GET'])
@jwt_required(locations=['headers','cookies'])  # 🔹 JWT 검증을 먼저 수행   
def get_top_viewd_pages():
    from services.user_summary_service import get_period_value
    try:
        filter_type = request.args.get('filter_type', 'all')
        filter_value = request.args.get('filter_value')
        period_type = request.args.get('period_type', 'year')
        period_value = request.args.get('period_value')
        
        if not period_type or not period_value:
            return jsonify({'error': 'Please provide scope, period_type, and period_value'}), 400
        
        start_dt, end_dt = get_period_value(period_type, period_value)
        
        query = db.session.query(
            ContentViewingHistory.file_id,
            func.coalesce(ContentRelPages.name, '[삭제된 파일]').label('file_name'),
            func.count().label('view_count')
        )
        
        if filter_type in ('company','department','user'):
            query = query.join(Users, ContentViewingHistory.user_id == Users.id)
            
        query = query.outerjoin(ContentRelPages, ContentViewingHistory.file_id == ContentRelPages.id).filter(
            ContentViewingHistory.start_time >= start_dt,
            ContentViewingHistory.start_time < end_dt
        )     
        
        if filter_type == 'company' and filter_value:
            query = query.filter(Users.company == filter_value)
        elif filter_type == 'department' and filter_value:
            parts = filter_value.split('||', 1)
            if len(parts) == 2:
                query = query.filter(Users.company == parts[0], Users.department == parts[1])
            else:
                query = query.filter(Users.company == filter_value)
        elif filter_type == 'user' and filter_value:
            query = query.filter(Users.id == filter_value)

        query = query.group_by(ContentViewingHistory.file_id, ContentRelPages.name).order_by(func.count().desc())
        query = query.limit(5)  # 🔹 상위 5개 조회
        
        rows = query.all()
        
        return jsonify({
            'top_viewd_pages': [
                {
                    'file_id': row.file_id,
                    'file_name': row.file_name,
                    'view_count': row.view_count
                } for row in rows
            ]
        }), 200  # 200: OK
        
    except Exception as e:
        logging.error(f"[get_top_viewd_pages] error: {str(e)}, {traceback.format_exc()}")
        return jsonify({'[get_top_viewd_pages] error': str(e)}), 500
 
# 🔹 GET /leaning/completion-rate API 학습 완료율 조회   
@api_leaning_bp.route('/completion-rate', methods=['GET'])
@jwt_required(locations=['headers','cookies'])  # 🔹 JWT 검증을 먼저 수행
def get_completion_rate():
    from services.user_summary_service import get_period_value
    try:
        filter_type = request.args.get('filter_type', 'all')
        filter_value = request.args.get('filter_value')
        period_type = request.args.get('period_type', 'year')
        period_value = request.args.get('period_value')
        
        if not period_type or not period_value:
            return jsonify({'error': 'Please provide scope, period_type, and period_value'}), 400
        
        if filter_type != 'all' and not filter_value:
            return jsonify({'error': 'Please provide filter_type and filter_value'}), 400
        
        start_date, end_date = get_period_value(period_type, period_value)
        local_tz = datetime.datetime.now(datetime.timezone.utc).astimezone().tzinfo
        utc_start_dt = datetime.datetime.combine(start_date, datetime.time.min, local_tz).astimezone(datetime.timezone.utc)
        utc_end_dt = datetime.datetime.combine(end_date, datetime.time.max, local_tz).astimezone(datetime.timezone.utc)
        
        user_ids = []
        if filter_type == 'all':
            user_ids = db.session.query(Users.id).all()
        elif filter_type == 'company':
            user_ids = db.session.query(Users.id).filter(Users.company == filter_value).all()
        elif filter_type == 'department':
            parts = filter_value.split('||', 1)
            if len(parts) == 2:
                user_ids = db.session.query(Users.id).filter(Users.company == parts[0], Users.department == parts[1]).all()
            else:
                user_ids = db.session.query(Users.id).filter(Users.department == filter_value).all()
        elif filter_type == 'user':
            user_ids = db.session.query(Users.id).filter(Users.id == filter_value).all()
        if not user_ids:
            return jsonify({'error': 'No users found for the given filter'}), 404       
        user_ids = [u[0] for u in user_ids]  # 튜플 → id만 추출
        
        completion_threshold = timedelta(minutes=Config.LEARNING_COMPLETED_MINUTES)
        
        completed_pages = db.session.query(func.count(distinct(tuple_(LearningCompletionHistory.user_id, LearningCompletionHistory.page_id)))) \
            .filter(
                LearningCompletionHistory.user_id.in_(user_ids),
                LearningCompletionHistory.completed_at.between(utc_start_dt, utc_end_dt),
                LearningCompletionHistory.total_duration >= completion_threshold
            ).scalar() or 0
            
        total_pages = db.session.query(func.count(ContentRelPages.id)) \
            .filter(ContentRelPages.is_deleted == False).scalar() or 0
        
        completion_rate = (completed_pages / (total_pages * len(user_ids)) * 100) if total_pages else 0
        
        return jsonify({
            'completion_rate': round(completion_rate, 2),
            'completed_pages': completed_pages,
            'total_pages': total_pages,
            'completion_threshold_minutes': Config.LEARNING_COMPLETED_MINUTES,
            'count_users': len(user_ids)
        }), 200  # 200: OK
        
    except Exception as e:
        logging.error(f"[get_completion_rate] error: {str(e)}, {traceback.format_exc()}")
        return jsonify({'[get_completion_rate] error': str(e)}), 500

# 🔹 GET /leaning/rank-update-contents API 최근 업데이트된 콘텐츠 랭킹 조회
@api_leaning_bp.route('/rank-update-contents', methods=['GET'])
@jwt_required(locations=['headers','cookies'])  # 🔹 JWT 검증을 먼저 수행
def rank_update_contents():
    try:
        
        top_rows = db.session.query(
                ContentRelPages.id,
                ContentRelPages.name,
                ContentRelPages.updated_at
            ).filter(
                ContentRelPages.is_deleted == False
            ).order_by(
                ContentRelPages.updated_at.desc()
            ).limit(5).all()  # 상위 5개만 조회
            
        bottom_rows = db.session.query(
                ContentRelPages.id,
                ContentRelPages.name,
                ContentRelPages.updated_at
            ).filter(
                ContentRelPages.is_deleted == False
            ).order_by(
                ContentRelPages.updated_at.asc()
            ).limit(5).all()  # 하위 5개만 조회

        return jsonify({
            'top': [
                {
                    'id': row.id,
                    'name': row.name,
                    'updated_at': row.updated_at.isoformat() if row.updated_at else None
                } for row in top_rows
            ],
            'bottom': [
                {
                    'id': row.id,
                    'name': row.name,
                    'updated_at': row.updated_at.isoformat() if row.updated_at else None
                } for row in bottom_rows
            ]
        }), 200  # 200: OK
        
    except Exception as e:
        logging.error(f"[rank_update_contents] error: {str(e)}, {traceback.format_exc()}")
        return jsonify({'[rank_update_contents] error': str(e)}), 500