import logging
import log_config
import re
from flask_jwt_extended import jwt_required
from extensions import db
from models import Folders, Files, Users, ContentViewingHistory, MemoData, ContentManager
from sqlalchemy import func
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import aliased
import traceback

def get_statistics_data(start_date, end_date, filter_type, filter_value):
    files = get_normal_files_width_category_names() 
    avgtimes = get_avg_learning_time_per_file(start_date, end_date, filter_type, filter_value)
    memocounts = get_memo_count_per_file(start_date, end_date, filter_type, filter_value)
    managers = get_file_managers()
    
    if not files:
        logging.error("No files found")
        return None
    
    for f in files:
        f['avg_stay_duration'] = round(avgtimes.get(f['file_id'], 0), 1)
        f['memo_count'] = memocounts.get(f['file_id'], 0)
        f['manager_name'] = managers.get(f['file_id'], '')
        
    return files
                
def get_normal_files_width_category_names():
    """
    폴더 타입이 normal인 파일 목록에 카테고리 이름도 같이 가져오기(상세보기 제외)
    """
    try:        
        FolderCur = aliased(Folders)
        FolderTop = aliased(Folders)
        
        def clean_name(name):
            return re.sub(r'^\d+_', '', name) if name else None
        
        query = db.session.query(
            Files.file_id, 
            Files.file_name, 
            Files.file_path, 
            Files.update_at,
            FolderTop.folder_name.label('top_name')).join(
            FolderCur, Files.folder_id == FolderCur.folder_id
        ).join(
            FolderTop, FolderCur.top_category_folder_id == FolderTop.folder_id
        ).filter(
            Files.is_deleted == False,
            FolderCur.folder_type == 'normal',
        ).order_by(Files.file_path)
        
        results = []
        for file_id,file_name,file_path,update_at,top_name in query.all():
            parts = file_path.split('/')
            try:
                top_index = parts.index(top_name)
                mid_name = parts[top_index + 1] if top_index + 1 < len(parts) else ''
            except ValueError:
                mid_name = ''
            
            top_name = clean_name(top_name)
            mid_name = clean_name(mid_name)
            bottom_name = clean_name(file_name)
            
            result = {
                'file_id': file_id,
                'file_name': file_name,
                'file_path': file_path,
                'top_name': top_name,
                'mid_name': mid_name,
                'bottom_name': bottom_name,
                'update_at': update_at.strftime('%Y-%m-%d')
            }  
            results.append(result)
        
        return results
    except Exception as e:
        logging.error(f"[get_normal_files]: {str(e)}, {traceback.format_exc()}")
        return None

def get_avg_learning_time_per_file(start_dt, end_dt, scope, filter_value):
    """
    파일별 평균 학습 시간
    """
    user_ids = get_user_ids_by_scope(scope, filter_value) if scope != 'all' else None
    
    avg_seconds_expr = func.avg(func.extract('epoch', ContentViewingHistory.stay_duration))
    
    query = db.session.query(
        ContentViewingHistory.file_id,
        avg_seconds_expr.label('avg_stay_duration')
    ).filter(
        ContentViewingHistory.start_time >= start_dt,
        ContentViewingHistory.start_time < end_dt
    )
    
    if user_ids:
        query = query.filter(ContentViewingHistory.user_id.in_(user_ids))
        
    query = query.group_by(ContentViewingHistory.file_id)
    
    return {row.file_id: round(float(row.avg_stay_duration),1) for row in query.all()}

def get_memo_count_per_file(start_dt, end_dt, scope, filter_value):
    user_ids = get_user_ids_by_scope(scope, filter_value) if scope != 'all' else None
    
    query = db.session.query(
        MemoData.file_id,
        func.count(MemoData.id).label('memo_count')
    ).filter(
        MemoData.modified_at >= start_dt,
        MemoData.modified_at < end_dt
    )
    
    if user_ids:
        query = query.filter(MemoData.user_id.in_(user_ids))
        
    query = query.group_by(MemoData.file_id)
    return {row.file_id: row.memo_count for row in query.all()}

def get_file_managers():
    """
    파일 관리자 목록 가져오기
    """
    query = db.session.query(
        ContentManager.file_id,
        Users.name.label('manager_name')
    ).join(
        Users, ContentManager.user_id == Users.id
    ).filter(ContentManager.type == 'file')
        
    return {row.file_id: row.manager_name for row in query.all()}

def get_user_ids_by_scope(scope, filter_value):
    """
    scope에 따라 사용자 ID 목록 가져오기
    """
    query = db.session.query(Users.id)
    
    if scope == 'company':
        query = query.filter(Users.company == filter_value)
    elif scope == 'department':
        parts = filter_value.split('||', 1)
        if len(parts) == 2:
            query = query.filter(Users.company == parts[0], Users.department == parts[1])
        else:
            query = query.filter(Users.department == parts[0])
    elif scope == 'user':
        query = query.filter(Users.id == filter_value)
    
    return [row.id for row in query.all()]

def format_seconds_to_hhmmss(seconds):
    """
    초를 시:분:초 형식으로 변환
    """
    if seconds is None:
        return '00시간 00분 00초'
    
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    seconds = int(seconds % 60)
    
    return f"{hours:02}시간 {minutes:02}분 {seconds:02}초"