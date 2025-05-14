from datetime import datetime, time, timezone
import logging
from sqlalchemy import text
import log_config
from extensions import db
from models import Users
import re

def get_statistics_user_data(period_type, period_value, filter_type, filter_value):
    """
    통계 데이터를 가져오는 함수
    """
    users, user_count = get_users_for_export(filter_type, filter_value)
    
    results = []
    for company, departments in users.items():  
        if filter_type == 'all' or filter_type == 'company':
            learnings = get_total_learning_time(period_type, period_value, 'company', company, user_count)
            memo_counts = get_memo_count_per_category(period_type, period_value, 'company', company)

            comapny_rows = {
                'company': company,
                'department': '',
                'user_id': '',
                'name': '',
                'total_learning_time': learnings['total_learning_time'],
                'avg_learning_time': learnings['avg_learning_time']
            }              
            for folder_name, duration in learnings['folder_progress']:
                row = comapny_rows.copy()
                row['category_name'] = re.sub(r"^\d+_", "", folder_name)
                seconds = duration.total_seconds()
                row['learning_time'] = f"{int(seconds // 3600):02}시간{int((seconds % 3600) // 60):02}분{int(seconds % 60):02}초"
                matched = next((item for item in memo_counts if item['category_name'] == folder_name), None)
                if matched:
                    row['memo_count'] = matched['memo_count']
                else:
                    row['memo_count'] = 0
                results.append(row)
        
        for department, user_list in departments.items():
            if filter_type == 'all' or filter_type == 'company' or filter_type == 'department':
                learnings = get_total_learning_time(period_type, period_value, 'department', f"{company}||{department}", user_count)
                memo_counts = get_memo_count_per_category(period_type, period_value, 'department', f"{company}||{department}")
                
                dept_row = {
                    'company': company,
                    'department': department,
                    'user_id': '',
                    'name': '',
                    'total_learning_time': learnings['total_learning_time'],
                    'avg_learning_time': learnings['avg_learning_time']
                }
                for folder_name, duration in learnings['folder_progress']:
                    row = dept_row.copy()
                    row['category_name'] = re.sub(r"^\d+_", "", folder_name)
                    seconds = duration.total_seconds()
                    row['learning_time'] = f"{int(seconds // 3600):02}시간{int((seconds % 3600) // 60):02}분{int(seconds % 60):02}초"
                    matched = next((item for item in memo_counts if item['category_name'] == folder_name), None)
                    if matched:
                        row['memo_count'] = matched['memo_count']
                    else:
                        row['memo_count'] = 0
                    results.append(row)
            
            for user in user_list:
                learnings = get_total_learning_time(period_type, period_value, 'user', user['user_id'], user_count)
                memo_counts = get_memo_count_per_category(period_type, period_value, 'user', user['user_id'])
                
                user_row = {
                    'company': company,
                    'department': department,
                    'user_id': user['user_id'],
                    'name': user['name'],
                    'total_learning_time': learnings['total_learning_time'],
                    'avg_learning_time': learnings['avg_learning_time']
                }
                for folder_name, duration in learnings['folder_progress']:
                    row = user_row.copy()
                    row['category_name'] = re.sub(r"^\d+_", "", folder_name)
                    seconds = duration.total_seconds()
                    row['learning_time'] = f"{int(seconds // 3600):02}시간{int((seconds % 3600) // 60):02}분{int(seconds % 60):02}초"
                    matched = next((item for item in memo_counts if item['category_name'] == folder_name), None)
                    if matched:
                        row['memo_count'] = matched['memo_count']
                    else:
                        row['memo_count'] = 0
                    results.append(row)
                            
    if not users:
        logging.error("No users found")
        return None
    
    return results

def get_users_for_export(filter_type, filter_value):
    """
    사용자 목록을 가져오는 함수
    """
    qeury = db.session.query(
        Users.company,
        Users.department,
        Users.name,
        Users.id).filter(Users.is_deleted == False)
    
    if filter_type == 'company':
        qeury = qeury.filter(Users.company == filter_value)
    elif filter_type == 'department':
        parts = filter_value.split('||', 1)
        if len(parts) == 2:
            qeury = qeury.filter(Users.company == parts[0], Users.department == parts[1])
        else:
            qeury = qeury.filter(Users.department == parts[0])
    elif filter_type == 'user':
        qeury = qeury.filter(Users.id == filter_value)
        
    rows = qeury.order_by(Users.company, Users.department, Users.name).all()
    
    results = {}
    for row in rows:
        company = row.company
        department = row.department
        user_id = row.id
        name = row.name
        if company not in results:
            results[company] = {}
            
        if department not in results[company]:
            results[company][department] = []
            
        results[company][department].append({
            "user_id": user_id,
            "name": name,
        })
                                            
    return results, len(rows)

def get_total_learning_time(period_type, period_value, filter_type, filter_value, user_count):
    """
    총 학습 시간을 가져오는 함수
    """
    from services.leaning_summary_service import get_folder_progress
    
    params = {
        'period_type': period_type,
        'period_value': period_value,
        'filter_type': filter_type,
        'filter_value': filter_value
    }
    folder_progress = get_folder_progress(params)
    sorted_folder_progress = sorted(folder_progress.values(), key=lambda x: x[0])
    total_learning_time = sum(duration.total_seconds() for folder_name, duration in folder_progress.values())
    
    if user_count == 0: user_count = 1
    avg_learning_time = total_learning_time / user_count
    
    return {
        'total_learning_time': f"{int(total_learning_time // 3600):02}시간{int((total_learning_time % 3600) // 60):02}분{int(total_learning_time % 60):02}초" ,
        'avg_learning_time': f"{int(avg_learning_time // 3600):02}시간{int((avg_learning_time % 3600) // 60):02}분{int(avg_learning_time % 60):02}초",
        'folder_progress': sorted_folder_progress
    }

def get_memo_count_per_category(period_type, period_value, filter_type, filter_value):
    """
    카테고리별 메모 수를 가져오는 함수
    """    
    from services.user_summary_service import get_period_value
    
    start_dt, end_dt = get_period_value(period_type, period_value)
    local_tz = datetime.now().astimezone().tzinfo
    utc_start_dt = datetime.combine(start_dt, time.min, tzinfo=local_tz).astimezone(timezone.utc)
    utc_end_dt = datetime.combine(end_dt, time.max, tzinfo=local_tz).astimezone(timezone.utc)    
    
    base_query = """
        SELECT f.top_category_folder_id, fc.folder_name AS top_category_name, COUNT(*) AS memo_count
        FROM memos m
        JOIN folders f ON m.folder_id = f.folder_id
        JOIN folders fc ON f.top_category_folder_id = fc.folder_id
        JOIN users u ON m.user_id = u.id
        WHERE {user_filter}
            AND m.modified_at >= :start_dt
            AND m.modified_at < :end_dt
        GROUP BY f.top_category_folder_id, fc.folder_name
        ORDER BY fc.folder_name
    """
    
    params = {
        'start_dt': utc_start_dt,
        'end_dt': utc_end_dt
    }
    user_filter = '1=1'
    
    if filter_type == 'company':
        user_filter = 'u.company = :company'
        params['company'] = filter_value
    elif filter_type == 'department':
        user_filter = 'u.company = :company AND u.department = :department'
        parts = filter_value.split('||', 1)
        if len(parts) == 2:
            params['company'] = parts[0]
            params['department'] = parts[1]
        else:
            user_filter = 'u.department = :department'
            params['department'] = parts[0]
    elif filter_type == 'user':
        user_filter = 'u.id = :user_id'
        params['user_id'] = filter_value
      
    query = text(base_query.format(user_filter=user_filter)) 
    result = db.session.execute(query, params).mappings().all()

    data = [{
        'category_id': row['top_category_folder_id'],
        'category_name': row['top_category_name'],
        'memo_count': row['memo_count']
    } for row in result]
    
    return data
    