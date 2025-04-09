import logging
import log_config
from flask import Blueprint, jsonify, request
import datetime
from datetime import timezone
from datetime import timedelta
from extensions import db
from flask_jwt_extended import jwt_required
from models import Users, ContentViewingHistory, Files
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

METADATA_CACHE_FILE = os.path.join(Config.BACKUP_DIR, "csv_metadata.pkl")

#region CSV 파일 조회

def update_csv_metadata():
    """CSV 파일의 메타데이터(개수, 날짜 범위)를 캐싱 - 데이터 처리 속도 개선"""
    metadata = {}
    pattern = os.path.join(Config.BACKUP_DIR, "content_viewing_history_backup_*.csv")
    all_files = glob.glob(pattern)

    logging.info(f"update_csv_metadata")
    for file in all_files:
        try:
            df = pd.read_csv(file, usecols=["start_time"], parse_dates=["start_time"])
            start_time_min = df["start_time"].min()
            start_time_max = df["start_time"].max()
            total_count = len(df)

            metadata[file] = {
                "start_time_min": start_time_min,
                "start_time_max": start_time_max,
                "total_count": total_count
            }
        except Exception as e:
            logging.error(f"[update_csv_metadata] Error processing {file}: {e}")
            
    try:
        os.makedirs(Config.BACKUP_DIR, exist_ok=True)
        with open(METADATA_CACHE_FILE, "wb") as f:
            pickle.dump(metadata, f)
    except Exception as e:
        logging.error(f"[update_csv_metadata] Error saving metadata: {e}")

def load_csv_metadata():
    """CSV 메타데이터 로드 (없으면 업데이트)"""
    if not os.path.exists(METADATA_CACHE_FILE):
        update_csv_metadata()
    
    if not os.path.exists(METADATA_CACHE_FILE):
        logging.info("[load_csv_metadata] Metadata file still missing after update. Returning empty metadata.")
        return {}
    
    with open(METADATA_CACHE_FILE, "rb") as f:
        return pickle.load(f) or {}

def get_relevant_files(start_date, end_date):
    """요청된 날짜 범위에 해당하는 CSV 파일 선택"""
    metadata = load_csv_metadata()
    if not metadata:
        logging.info("[get_relevant_files] No metadata found")
        return [], 0
    
    relevant_files = [
        file for file, info in metadata.items()
        if info["start_time_max"] >= start_date and info["start_time_min"] <= end_date
    ]

    total_csv_count = sum(metadata[file]["total_count"] for file in relevant_files)
    
    logging.info(f"Selected CSV Files: {relevant_files}")
    logging.info(f"Total CSV Count: {total_csv_count}")
    
    return relevant_files, total_csv_count

def fetch_user_info(user_id = None, user_name = None, extra_user_ids=None):
    """사용자 정보 조회(ID 또는 이름으로 ID와 이름 매핑)"""
    user_id_to_name_map = {}
    
    if user_id:
        query = text("SELECT id, name FROM users WHERE id = :user_id")
        result = db.session.execute(query, {"user_id": user_id}).fetchone()
        if result is None:
            return [], {}
        user_id_to_name_map[str(result[0])] = result[1]            
        return [str(user_id)], user_id_to_name_map
    
    if user_name:
        query = text("SELECT id, name FROM users WHERE name LIKE :user_name")
        result = db.session.execute(query, {"user_name": f"%{user_name}%"}).fetchall()
        if not result:
            return [], {}
        user_ids = [str(row[0]) for row in result]
        user_id_to_name_map = {str(row[0]): row[1] for row in result}
        return user_ids, user_id_to_name_map
    
    if extra_user_ids:
        query = text("SELECT id, name FROM users WHERE id IN :extra_user_ids")
        result = db.session.execute(query, {"extra_user_ids": tuple(extra_user_ids)}).fetchall()
        if not result:
            return [], {}
        user_ids = [str(row[0]) for row in result]
        user_id_to_name_map = {str(row[0]): row[1] for row in result}
        return user_ids, user_id_to_name_map
    
    return [], {}

def fetch_file_info(file_name=None, extra_file_ids=None):
    """파일 정보 조회(파일 이름으로 ID와 이름 매핑)"""
    if file_name:      
        query = text("SELECT file_id, file_name FROM files WHERE file_name LIKE :file_name")
        result = db.session.execute(query, {"file_name": f"%{file_name}%"}).fetchall()
        if not result:
            return [], {}
        
        file_ids = [row[0] for row in result]
        file_id_to_name_map = {row[0]: row[1] for row in result}
        
        return file_ids, file_id_to_name_map
    
    if extra_file_ids:
        query = text("SELECT file_id, file_name FROM files WHERE file_id IN :file_ids")
        result = db.session.execute(query, {"file_ids": tuple(extra_file_ids)}).fetchall()
        if not result:
            return [], {}
        
        file_ids = [row[0] for row in result]
        file_id_to_name_map = {row[0]: row[1] for row in result}
        
        return file_ids, file_id_to_name_map
    
    return [], {}
    
def search_csv(user_id=None, user_name=None, file_name=None, start_date=None, end_date=None, offset=0, page_size=30):    
    """CSV 파일에서 데이터 검색"""    
    start_date = pd.to_datetime(start_date).tz_localize("UTC") if start_date else None
    end_date = pd.to_datetime(end_date).tz_localize("UTC") if end_date else None
    
    relevant_files, total_csv_count = get_relevant_files(start_date, end_date)
    
    if not relevant_files:
        logging.error("[search_csv] No backup files found")
        return [], 0
    
    all_data = []
    remaining_offset = offset
    records_needed = page_size
    
    total_filtered_csv_count = 0 if offset == 0 else None
    
    try:       
        user_ids, user_id_to_name_map = fetch_user_info(user_id, user_name)
        file_ids, file_id_to_name_map = fetch_file_info(file_name) if file_name else ([], {})
                            
        for csv_file in relevant_files:
            df = pd.read_csv(csv_file, parse_dates=["start_time", "end_time"])  # CSV 파일 읽기
            df = df[(df["start_time"] >= start_date) & (df["end_time"] <= end_date)]  # 날짜 범위 필터링
            
            if user_ids:
                df = df[df["user_id"].astype(str).isin(user_ids)]
            
            df["file_id"] = pd.to_numeric(df["file_id"], errors="coerce").astype("Int64")
            if file_ids:
                df = df[df["file_id"].isin(file_ids)]    
                                
            df["name"] = df["user_id"].astype(str).map(user_id_to_name_map).fillna("[삭제된 사용자]")            
            missing_user_ids = df.loc[df["name"] == "[삭제된 사용자]", "user_id"].astype(str).unique().tolist()
            if missing_user_ids:
                new_user_ids, new_user_map = fetch_user_info(extra_user_ids=missing_user_ids)
                user_ids.extend(new_user_ids)
                user_id_to_name_map.update(new_user_map)
                df["name"] = df["user_id"].astype(str).map(user_id_to_name_map).fillna("[삭제된 사용자]")
            
            df["file_name"] = df["file_id"].map(file_id_to_name_map).fillna("[삭제된 파일]")
            missing_file_ids = df.loc[df["file_name"] == "[삭제된 파일]", "file_id"].unique().tolist()
            logging.log(logging.INFO, f"Missing file ids: {missing_file_ids}")
            if missing_file_ids:
                new_file_ids, new_file_map = fetch_file_info(extra_file_ids=missing_file_ids)
                file_ids.extend(new_file_ids)
                file_id_to_name_map.update(new_file_map)
                df["file_name"] = df["file_id"].map(file_id_to_name_map).fillna("[삭제된 파일]")
                
            if user_name:
                df = df[df["name"].str.contains(user_name, na=False)]
            if file_name:
                df = df[df["file_name"].str.contains(file_name, na=False)]

            if offset == 0:
                total_filtered_csv_count += len(df)
                
            if remaining_offset > len(df):
                remaining_offset -= len(df)
                continue
            
            if records_needed > 0:
                df = df.iloc[remaining_offset:]
                remaining_offset = 0
                df = df.iloc[:records_needed]
                records_needed -= len(df)
            
            all_data.append(df)
            
            if records_needed <= 0:
                if offset == 0:
                    continue
                else:
                    break
        
        logging.info(f"Total Filtered CSV Count: {total_filtered_csv_count}")
        if all_data:
            return pd.concat(all_data, ignore_index=True).to_dict(orient="records"), total_filtered_csv_count
        else:
            return [], total_filtered_csv_count
    except Exception as e:
        logging.error(f"Error searching CSV: {e}")
        return [], 0
                
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
        
        if duration >= timedelta(seconds=30): # 최소 30초 이상 시청한 경우 DB 저장          
            # 🔹 ContentViewingHistory 객체 생성
            learning = ContentViewingHistory(
                user_id=user_id,
                file_id=file_id,
                start_time=start_time, # - timedelta(seconds=15),
                end_time=end_time,
                ip_address=ip_address,
                )
            db.session.add(learning)
            db.session.commit()
            return jsonify({'status': 'OK', 'id': learning.id})
        else:
            return jsonify({"message": "Viewing duration too short, not saved"}), 204 # 204: No Content
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500
   
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
        
        csv_data, total_csv_count = search_csv(user_id, user_name, file_name, start_date, end_date, offset, page_size)
        if page == 1 and total_csv_count is not None:
            session["total_csv_count"] = total_csv_count
        else:
            total_csv_count = session.get("total_csv_count", 0)
            
        remaining_count = max(0, page_size - len(csv_data))
        db_offset = max(0, offset - total_csv_count)
        logging.info(f"CSV Data: {len(csv_data)}, Remaining: {remaining_count}, DB Offset: {db_offset}")
        
        base_query = """
            SELECT v.id, v.user_id, COALESCE(u.name,'[삭제된 사용자]') AS name, v.file_id, COALESCE(f.file_name,'[삭제된 파일]') As file_name, v.start_time, v.end_time, v.stay_duration, v.ip_address
            FROM content_viewing_history_view v
            LEFT JOIN users u ON v.user_id = u.id
            LEFT JOIN files f ON v.file_id = f.file_id
            """
        
        filters = []
        #params = {'limit': page_size, 'offset': offset}
        params = {'limit': remaining_count, 'offset': db_offset}
        
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
        combined_data = csv_data + db_data
        
        logging.info(f"total_db_count: {total_db_count}, total_csv_count: {total_csv_count}")
        
        return jsonify({
            'csv_count' : total_csv_count if total_csv_count is not None else "N/A",
            'db_count' : total_db_count,
            'page': page,
            'page_size': page_size,
            'data': combined_data
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500