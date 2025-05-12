import logging
import log_config
from extensions import db
from models import Users

def get_statistics_user_data(start_date, end_date, filter_type, filter_value):
    """
    통계 데이터를 가져오는 함수
    """
    users = get_users_for_export(filter_type, filter_value)
    if not users:
        logging.error("No users found")
        return None
    
    return users

def get_users_for_export(filter_type, filter_value):
    """
    사용자 목록을 가져오는 함수
    """
    qeury = db.session.query(
        Users.company,
        Users.department,
        Users.name).filter(Users.is_deleted == False)
    
    if filter_type == 'company':
        queury = qeury.filter(Users.company == filter_value)
    elif filter_type == 'department':
        parts = filter_value.split('||', 1)
        if len(parts) == 2:
            qeury = qeury.filter(Users.company == parts[0], Users.department == parts[1])
        else:
            qeury = qeury.filter(Users.department == parts[0])
    elif filter_type == 'user':
        qeury = qeury.filter(Users.id == filter_value)
        
    return qeury.order_by(Users.company, Users.department, Users.name).all()