import datetime
import logging
import traceback
import log_config
from flask import Blueprint, jsonify, request
from extensions import db
from flask_jwt_extended import jwt_required, get_jwt_identity
from blueprints.leaning_routes import api_leaning_bp
from config import Config
from models import (Users, ContentViewingHistory, ContentPointRecord, ContentRelPages, LearningCompletionHistory
                    , ContentManager, ContentRelFolders, ContentRelChannels)
from sqlalchemy import text

@api_leaning_bp.route('/my_learning_rank', methods=['GET'])
@jwt_required(locations=['headers', 'cookies'])
def get_my_learning_rank():
    """
    사용자 학습 랭킹 조회
    Returns:
        JSON: 사용자 학습 랭킹
    """
    try:
        user_id = get_jwt_identity()
        
        min_seconds = Config.LEARNING_COMPLETED_MINUTES * 60  # Convert minutes to seconds
        
        query = text("""
                    WITH user_completed AS (
                        SELECT user_id, COUNT(*) AS completed_pages
                        FROM learning_completion_history
                        WHERE EXTRACT(EPOCH FROM total_duration) >= :min_seconds
                        GROUP BY user_id
                    )
                    SELECT COUNT(*) + 1 AS rank
                    FROM user_completed
                    WHERE completed_pages > (
                        SELECT COUNT(*)
                        FROM learning_completion_history
                        WHERE user_id = :user_id AND EXTRACT(EPOCH FROM total_duration) >= :min_seconds
                    )
                    """)
        
        result = db.session.execute(query, {'user_id': user_id, 'min_seconds': min_seconds})
        row = result.fetchone()
        return jsonify({'rank': row[0] if row else 0}), 200
    except Exception as e:
        logging.error(f"Error in get_my_learning_rank: {str(e)}, {traceback.format_exc()}")
        return jsonify({"error": "Internal server error"}), 500


@api_leaning_bp.route('/learning_time_by_week', methods=['GET'])
@jwt_required(locations=['headers', 'cookies'])
def get_learning_time_of_week():
    """
    일주일간 학습시간 조회
    Returns:
        JSON: 전체 학습자 일별 평균 학습시간 및 특정 사용자 일별 학습시간
    """
    try:
        user_id = get_jwt_identity()
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        
        if not start_date or not end_date:
            return jsonify({"error": "Please provide start_date and end_date"}), 400
        
        try:
            start_date_obj = datetime.datetime.strptime(start_date, '%Y-%m-%d').date()
            end_date_obj = datetime.datetime.strptime(end_date, '%Y-%m-%d').date()
        except ValueError:
            return jsonify({"error": "Invalid date format. Use YYYY-MM-DD"}), 400
        
        # 로컬 시간대를 UTC로 변환
        local_tz = datetime.datetime.now().astimezone().tzinfo
        local_tz_name = local_tz.tzname(None)
        if local_tz_name == 'KST':
            local_tz_name = 'Asia/Seoul'
            
        utc_start_date = datetime.datetime.combine(start_date_obj, datetime.time.min, tzinfo=local_tz).astimezone(datetime.timezone.utc)
        utc_end_date = datetime.datetime.combine(end_date_obj, datetime.time.max, tzinfo=local_tz).astimezone(datetime.timezone.utc)
        
        logging.debug(f"Request range: {start_date} ~ {end_date}")
        logging.debug(f"UTC range: {utc_start_date} ~ {utc_end_date}")
        logging.debug(f"Local timezone: {local_tz}")
        
        # 디버그: 실제 데이터 확인
        debug_query = text("""
            SELECT 
                id,
                user_id,
                start_time,
                stay_duration,
                EXTRACT(EPOCH FROM stay_duration) as duration_seconds,
                DATE(start_time AT TIME ZONE :local_tz_name) as local_date
            FROM content_viewing_history
            WHERE start_time >= :utc_start_date 
                AND start_time <= :utc_end_date
                AND stay_duration IS NOT NULL
            ORDER BY start_time
        """)
        
        debug_result = db.session.execute(debug_query, {
            'utc_start_date': utc_start_date,
            'utc_end_date': utc_end_date,
            'local_tz_name': local_tz_name
        })
        
        logging.debug("=== RAW DATA DEBUG ===")
        total_debug_records = 0
        for row in debug_result:
            total_debug_records += 1
            logging.debug(f"ID: {row[0]}, User: {row[1]}, Start: {row[2]}, Duration: {row[3]}, Seconds: {row[4]}, Local Date: {row[5]}")
        logging.debug(f"Total debug records found: {total_debug_records}")
        
        # 디버그: daily_learning CTE 확인
        daily_debug_query = text("""
            SELECT 
                DATE(start_time AT TIME ZONE :local_tz_name) as date,
                user_id,
                SUM(EXTRACT(EPOCH FROM stay_duration)) as daily_seconds,
                COUNT(*) as record_count
            FROM content_viewing_history
            WHERE start_time >= :utc_start_date 
                AND start_time <= :utc_end_date
                AND stay_duration IS NOT NULL
            GROUP BY DATE(start_time AT TIME ZONE :local_tz_name), user_id
            ORDER BY date, user_id
        """)
        
        daily_debug_result = db.session.execute(daily_debug_query, {
            'utc_start_date': utc_start_date,
            'utc_end_date': utc_end_date,
            'local_tz_name': local_tz_name
        })
        
        logging.debug("=== DAILY LEARNING DEBUG ===")
        for row in daily_debug_result:
            logging.debug(f"Date: {row[0]}, User: {row[1]}, Total seconds: {row[2]}, Records: {row[3]}, Minutes: {round(row[2]/60, 2)}")
        
        # 디버그: 사용자 수 확인
        user_count_query = text("SELECT COUNT(*) as total_user_count FROM users WHERE is_deleted = false")
        user_count_result = db.session.execute(user_count_query)
        user_count = user_count_result.fetchone()[0]
        logging.debug(f"Total user count: {user_count}")
        
        # 디버그: users 테이블 상세 확인
        user_detail_query = text("""
            SELECT 
                COUNT(*) as total_users,
                COUNT(CASE WHEN is_deleted = false THEN 1 END) as active_users,
                COUNT(CASE WHEN is_deleted = true THEN 1 END) as deleted_users,
                COUNT(CASE WHEN is_deleted IS NULL THEN 1 END) as null_deleted
            FROM users
        """)
        user_detail_result = db.session.execute(user_detail_query)
        user_detail = user_detail_result.fetchone()
        logging.debug(f"Users detail - Total: {user_detail[0]}, Active: {user_detail[1]}, Deleted: {user_detail[2]}, Null: {user_detail[3]}")
        
        # is_deleted 컬럼의 실제 값들 확인
        sample_users_query = text("SELECT * FROM users LIMIT 5")
        sample_users_result = db.session.execute(sample_users_query)
        logging.debug("Sample users (all columns):")
        for row in sample_users_result:
            logging.debug(f"Row: {dict(row._mapping)}")
        
        # users 테이블 구조 확인
        table_structure_query = text("""
            SELECT column_name, data_type, is_nullable 
            FROM information_schema.columns 
            WHERE table_name = 'users'
            ORDER BY ordinal_position
        """)
        structure_result = db.session.execute(table_structure_query)
        logging.debug("Users table structure:")
        for row in structure_result:
            logging.debug(f"Column: {row[0]}, Type: {row[1]}, Nullable: {row[2]}")
        
        # 전체 학습자 일별 평균 학습시간 조회 (전체 사용자 기준 평균)
        all_users_query = text("""
            WITH all_users AS (
                SELECT COUNT(*) as total_user_count FROM users WHERE is_deleted = false
            ),
            daily_learning AS (
                SELECT 
                    DATE(start_time AT TIME ZONE :local_tz_name) as date,
                    user_id,
                    SUM(EXTRACT(EPOCH FROM stay_duration)) as daily_seconds
                FROM content_viewing_history
                WHERE start_time >= :utc_start_date 
                    AND start_time <= :utc_end_date
                    AND stay_duration IS NOT NULL
                GROUP BY DATE(start_time AT TIME ZONE :local_tz_name), user_id
            )
            SELECT 
                dl.date,
                SUM(dl.daily_seconds) / au.total_user_count as avg_duration_seconds,
                au.total_user_count,
                COUNT(dl.user_id) as active_user_count
            FROM daily_learning dl
            CROSS JOIN all_users au
            GROUP BY dl.date, au.total_user_count
            ORDER BY dl.date
        """)
        
        all_users_result = db.session.execute(all_users_query, {
            'utc_start_date': utc_start_date,
            'utc_end_date': utc_end_date,
            'local_tz_name': local_tz_name
        })
        
        # 특정 사용자 일별 학습시간 조회 (한국 시간 기준)
        user_query = text("""
            SELECT 
                DATE(start_time AT TIME ZONE :local_tz_name) as date,
                SUM(EXTRACT(EPOCH FROM stay_duration)) as total_duration_seconds
            FROM content_viewing_history
            WHERE user_id = :user_id
                AND start_time >= :utc_start_date 
                AND start_time <= :utc_end_date
                AND stay_duration IS NOT NULL
            GROUP BY DATE(start_time AT TIME ZONE :local_tz_name)
            ORDER BY date
        """)
        
        logging.debug(f"User query parameters: user_id={user_id}, utc_start_date={utc_start_date}, utc_end_date={utc_end_date}")
        
        user_result = db.session.execute(user_query, {
            'user_id': user_id,
            'utc_start_date': utc_start_date,
            'utc_end_date': utc_end_date,
            'local_tz_name': local_tz_name
        })
        
        # 전체 학습자 평균 데이터 처리
        all_users_data = []
        for row in all_users_result:
            date_str = row[0].strftime('%Y-%m-%d')
            avg_minutes = round(float(row[1]) / 60, 2) if row[1] else 0
            total_user_count = row[2] if row[2] else 0
            active_user_count = row[3] if row[3] else 0
            all_users_data.append({
                'date': date_str,
                'avg_duration_minutes': avg_minutes
            })
            logging.debug(f"All users data - Date: {date_str}, Avg minutes: {avg_minutes}, Total users: {total_user_count}, Active users: {active_user_count}")
        
        # 특정 사용자 데이터 처리
        user_data = []
        user_record_count = 0
        for row in user_result:
            user_record_count += 1
            date_str = row[0].strftime('%Y-%m-%d')
            duration_minutes = round(float(row[1]) / 60, 2) if row[1] else 0
            user_data.append({
                'date': date_str,
                'total_duration_minutes': duration_minutes
            })
            logging.debug(f"User data - Date: {date_str}, Duration minutes: {duration_minutes}")
        
        logging.debug(f"User query returned {user_record_count} records")
        if user_record_count == 0:
            logging.debug(f"No user data found for user_id: {user_id}")
            # 사용자 데이터가 없는 경우 디버그를 위해 사용자별 원시 데이터 확인
            user_debug_query = text("""
                SELECT COUNT(*) as count
                FROM content_viewing_history
                WHERE user_id = :user_id
                    AND start_time >= :utc_start_date 
                    AND start_time <= :utc_end_date
                    AND stay_duration IS NOT NULL
            """)
            user_debug_result = db.session.execute(user_debug_query, {
                'user_id': user_id,
                'utc_start_date': utc_start_date,
                'utc_end_date': utc_end_date
            })
            user_debug_count = user_debug_result.fetchone()[0]
            logging.debug(f"Raw user data count for debugging: {user_debug_count}")
        
        logging.debug(f"Final all_users_data count: {len(all_users_data)}")
        logging.debug(f"Final user_data count: {len(user_data)}")
        
        data = {
            'all_users_daily_average': all_users_data,
            'user_daily_total': user_data
        }
        
        return jsonify(data), 200
    except Exception as e:
        logging.error(f"Error in get_learning_time_of_week: {str(e)}, {traceback.format_exc()}")
        return jsonify({"error": "Internal server error"}), 500
    
    
@api_leaning_bp.route('/continuous_learning_days', methods=['GET'])
@jwt_required(locations=['headers', 'cookies'])
def get_continuous_learning_days():
    """
    사용자의 연속 학습일 조회
    Returns:
        JSON: 특정 날짜 기준으로 연속 학습일 수
    """
    try:
        user_id = get_jwt_identity()
        reference_date = request.args.get('reference_date')
        
        if not reference_date:
            return jsonify({"error": "Please provide reference_date"}), 400
        
        try:
            reference_date_obj = datetime.datetime.strptime(reference_date, '%Y-%m-%d').date()
        except ValueError:
            return jsonify({"error": "Invalid date format. Use YYYY-MM-DD"}), 400
        
        # 로컬 시간대 설정
        local_tz = datetime.datetime.now().astimezone().tzinfo
        local_tz_name = local_tz.tzname(None)
        if local_tz_name == 'KST':
            local_tz_name = 'Asia/Seoul'
        
        logging.debug(f"Calculating continuous learning days for user: {user_id}, reference_date: {reference_date}")
        
        # 기준 날짜부터 과거로 거슬러 올라가면서 연속 학습일 계산
        query = text("""
            WITH learning_dates AS (
                SELECT DISTINCT DATE(start_time AT TIME ZONE :local_tz_name) as learning_date
                FROM content_viewing_history
                WHERE user_id = :user_id
                    AND stay_duration IS NOT NULL
                    AND EXTRACT(EPOCH FROM stay_duration) > 0
                    AND DATE(start_time AT TIME ZONE :local_tz_name) <= :reference_date
                ORDER BY learning_date DESC
            ),
            consecutive_check AS (
                SELECT 
                    learning_date,
                    ROW_NUMBER() OVER (ORDER BY learning_date DESC) as row_num,
                    :reference_date - learning_date as days_diff
                FROM learning_dates
            )
            SELECT COUNT(*) as continuous_days
            FROM consecutive_check
            WHERE days_diff = row_num - 1
                AND learning_date <= :reference_date
        """)
        
        params = {
            'user_id': user_id,
            'reference_date': reference_date_obj,  # date 객체 전달
            'local_tz_name': local_tz_name
        }
        
        logging.debug(f"Executing query: {query}")
        logging.debug(f"Query parameters: {params}")
        
        result = db.session.execute(query, params)
        
        row = result.fetchone()
        continuous_days = row[0] if row and row[0] else 0
        
        logging.debug(f"Continuous learning days calculated: {continuous_days}")
        
        return jsonify({
            'user_id': user_id,
            'reference_date': reference_date,
            'continuous_days': continuous_days
        }), 200
        
    except Exception as e:
        logging.error(f"Error in get_continuous_learning_days: {str(e)}, {traceback.format_exc()}")
        return jsonify({"error": "Internal server error"}), 500
    
    
@api_leaning_bp.route('/get_updated_contents', methods=['GET'])
@jwt_required(locations=['headers', 'cookies'])
def get_updated_contents():
    """최근 업데이트 된 콘텐츠 조회"""
    try:
        user_id = get_jwt_identity()
        searchDays = request.args.get('days', 14, type=int)
        if searchDays <= 0:
            return jsonify({"error": "Invalid number of days"}), 400
        
        today = datetime.datetime.now().astimezone().replace(hour=0, minute=0, second=0, microsecond=0)
        utc_today = today.astimezone(datetime.timezone.utc)
        start_date = utc_today - datetime.timedelta(days=searchDays)
        
        # 최근 업데이트된 콘텐츠와 사용자의 학습 상태, 담당자 정보를 함께 조회
        query = text("""
            SELECT 
                p.id,
                p.name,
                p.updated_at,
                CASE 
                    WHEN cvh.latest_start_time IS NOT NULL AND cvh.latest_start_time > p.updated_at 
                    THEN true 
                    ELSE false 
                END as viewed_after_update,
                u.name as manager_name
            FROM content_rel_pages p
            LEFT JOIN (
                SELECT 
                    file_id,
                    MAX(start_time) as latest_start_time
                FROM content_viewing_history
                WHERE user_id = :user_id 
                    AND file_type = 'page'
                GROUP BY file_id
            ) cvh ON p.id = cvh.file_id
            LEFT JOIN content_manager cm ON p.id = cm.file_id AND cm.type = 'file'
            LEFT JOIN users u ON cm.user_id = u.id AND u.is_deleted = false
            WHERE p.updated_at >= :start_date
                AND p.is_deleted = false
            ORDER BY p.updated_at DESC
        """)
        
        result = db.session.execute(query, {
            'user_id': user_id,
            'start_date': start_date
        })
        
        contents = []
        for row in result:
            content_dict = {
                'id': row[0],
                'name': row[1],
                'updated_at': row[2].isoformat() if row[2] else None,
                'viewed_after_update': row[3],
                'manager_name': row[4]  # 담당자 이름 (없으면 None)
            }
            contents.append(content_dict)
        
        return jsonify({
            "contents": contents
        }), 200
    except Exception as e:
        logging.error(f"Error in get_updated_contents: {str(e)}, {traceback.format_exc()}")
        return jsonify({"error": "Internal server error"}), 500