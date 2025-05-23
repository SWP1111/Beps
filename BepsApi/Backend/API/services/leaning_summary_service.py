import logging
import log_config
import datetime
from services import user_summary_service
from models import ( LearningSummaryAgg, LearningSummaryDay, ContentViewingHistory, Users, 
                    ContentRelChannels,ContentRelFolders, ContentRelPages, ContentRelPageDetails)
from extensions import db
from sqlalchemy import and_, func, or_
from sqlalchemy.sql import union_all
from sqlalchemy.orm import aliased

def get_channels():
    channels = db.session.query(
        ContentRelChannels.id,
        ContentRelChannels.name
    ).filter(
        ContentRelChannels.is_deleted == False
    ).all()

    return {f.id: (f.name, datetime.timedelta(0)) for f in channels}

def get_folder_progress(params):
    """
    카테고리별 학습 진행률을 가져오는 함수
    """
    
    scope = params['filter_type']
    filter_value = params.get('filter_value')
    period_type = params['period_type']
    period_value = params['period_value']
    
    start_date, end_date = user_summary_service.get_period_value(period_type, period_value)
    
    # 카테고리별 학습 진행률 결과 저장
    folder_duration_map = get_channels()
    
    used_range = []
    
    # 카테고리별 학습 진행률을 가져오는 쿼리(기간별)
    for period_func, summary_func, period_scope in [
        (user_summary_service.get_year_period_value, LearningSummaryAgg, 'year'),
        (user_summary_service.get_half_period_value, LearningSummaryAgg, 'half'),
        (user_summary_service.get_quarter_period_value, LearningSummaryAgg, 'quarter'),
    ]:
        for period_str, p_start, p_end in period_func(start_date.year):
            if start_date <= p_start and end_date >= p_end:
                rows = user_summary_service.get_summary_rows_agg(
                    summary_func,
                    period_type=period_scope,
                    period_value=period_str,
                    scope=scope,
                    group_fields=[LearningSummaryAgg.channel_id, LearningSummaryAgg.channel_name],
                    join_users=False,
                    extra_filter=build_scope_filter(LearningSummaryAgg, scope, filter_value)
                )
                if rows:
                    used_range.append((p_start, p_end))
                    update_folder_duration_map(folder_duration_map, rows)
                    
    used_range.sort(key=lambda x: x[0])
    current = start_date
    
    # 카테고리별 학습 진행률을 가져오는 쿼리(일별)
    for used_start, used_end in used_range:
        if current < used_start:
            add_summary_day_date(current, used_start - datetime.timedelta(days=1), folder_duration_map, scope, filter_value)
        current = max(current, used_end + datetime.timedelta(days=1))
        
    if current <= end_date:
        add_summary_day_date(current, end_date, folder_duration_map, scope, filter_value)
        

    return folder_duration_map    
            
def get_folder_progress_by_users(user_ids: list[str], period_type: str, period_value: str) -> dict:
    """
    여러 사용자에 대한 카테고리별 학습 진행률 반환    
    """        
    start_date, end_date = user_summary_service.get_period_value(period_type, period_value)
    
    folder_duration_by_user = {}
    used_range = []
    
    channels = get_channels()
    for user_id in user_ids:
        folder_duration_by_user[user_id] = channels.copy()
    
    for period_func, summary_func, period_scope in [
        (user_summary_service.get_year_period_value, LearningSummaryAgg, 'year'),
        (user_summary_service.get_half_period_value, LearningSummaryAgg, 'half'),
        (user_summary_service.get_quarter_period_value, LearningSummaryAgg, 'quarter'),
    ]:
        for period_str, p_start, p_end in period_func(start_date.year):
            if start_date <= p_start and end_date >= p_end:
                rows = user_summary_service.get_summary_rows_agg(
                    summary_func,
                    period_type=period_scope,
                    period_value=period_str,
                    scope='user',
                    group_fields=[LearningSummaryAgg.user_id, LearningSummaryAgg.channel_id, LearningSummaryAgg.channel_name],
                    join_users=False,
                    extra_filter=[LearningSummaryAgg.user_id.in_(user_ids)]
                )
                if rows:
                    used_range.append((p_start, p_end))
                    for row in rows:
                        d = folder_duration_by_user[row.user_id][row.channel_id]                      
                        folder_duration_by_user[row.user_id][row.channel_id] = (d[0], d[1] + row.total)
    
    used_range.sort(key=lambda x: x[0])
    current = start_date
     
    for used_start, used_end in used_range:
        if current < used_start:
            add_summary_day_date_by_users(user_ids, current, used_start - datetime.timedelta(days=1), folder_duration_by_user)
        current = max(current, used_end + datetime.timedelta(days=1))
        
    if current <= end_date:
        add_summary_day_date_by_users(user_ids, current, end_date, folder_duration_by_user)
                           
    return folder_duration_by_user
   
def build_scope_filter(model, scope, filter_value):
    """
    필터 조건을 생성하는 함수
    """
    if scope == 'company':
        return [model.company_key == filter_value]
    elif scope == 'department':
        parts = filter_value.split('||', 1)
        if len(parts) == 2:
            return [model.company_key == parts[0], 
                    model.department_key == parts[1]]
        else:
            return [model.company_key == parts[0]]
    elif scope == 'user':
        return [model.user_id == filter_value]
    elif scope == 'all':
        return None
     
def update_folder_duration_map(folder_duration_map, rows):
    """
    폴더별 학습 진행률을 업데이트하는 함수
    """
    for row in rows:
        key = row.channel_id
        duration = row.total or datetime.timedelta(0)
        if key not in folder_duration_map:
            folder_duration_map[key] = (row.channel_name, datetime.timedelta(0))
        folder_duration_map[key] = (row.channel_name, folder_duration_map[key][1] + duration)

        
def add_summary_day_date(start_dt, end_dt, folder_duration_map, scope, filter_value):
    """
    카테고리별 학습 진행률을 가져오는 쿼리(일별)
    """
    if start_dt > end_dt:
        return

    if end_dt > datetime.datetime.now().date():
        end_dt = datetime.datetime.now().date()
        
    today = datetime.datetime.now().date()
    split_date = today - datetime.timedelta(days=2)
    
    if start_dt <= split_date:
        summary_end_date = min(end_dt, split_date)
        rows = get_learning_summary_rows_day(
            start_date=start_dt,
            end_date=summary_end_date,
            scope=scope,
            group_fields=[LearningSummaryDay.channel_id, LearningSummaryDay.channel_name],
            join_users=False,
            extra_filter=build_scope_filter(LearningSummaryDay, scope, filter_value)
        )
        update_folder_duration_map(folder_duration_map, rows)
        start_dt = summary_end_date + datetime.timedelta(days=1)
    
    if start_dt <= end_dt:
        local_tz = datetime.datetime.now(datetime.timezone.utc).astimezone().tzinfo
        utc_start_dt = datetime.datetime.combine(start_dt, datetime.time.min, local_tz).astimezone(datetime.timezone.utc)
        utc_end_dt = datetime.datetime.combine(end_dt, datetime.time.max, local_tz).astimezone(datetime.timezone.utc)
        
        Page = aliased(ContentRelPages) # 🔹 ContentRelPages 테이블을 alias로 사용
        Detail = aliased(ContentRelPageDetails) # 🔹 ContentRelPageDetails 테이블을 alias로 사용
        DetailPage = aliased(ContentRelPages) # 🔹 ContentRelPages 테이블을 alias로 사용
        Folder = aliased(ContentRelFolders) # 🔹 ContentRelFolders 테이블을 alias로 사용
        Channel = aliased(ContentRelChannels) # 🔹 ContentRelChannels 테이블을 alias로 사용

        query = db.session.query(
            Channel.id.label('channel_id'),
            Channel.name.label('channel_name'),
            func.sum(ContentViewingHistory.stay_duration).label('total')
        ).outerjoin(
            Page, and_(ContentViewingHistory.file_type == 'page', ContentViewingHistory.file_id == Page.id)   
        ).outerjoin(
            Detail, and_(ContentViewingHistory.file_type == 'detail', ContentViewingHistory.file_id == Detail.id)        
        ).outerjoin(
            DetailPage, Detail.page_id == DetailPage.id
        ).outerjoin(
            Folder, or_(Folder.id == Page.folder_id, Folder.id == DetailPage.folder_id) # 🔹 Page와 DetailPage의 folder_id를 join
        ).join(
            Channel, Channel.id == Folder.channel_id
        ).join(
            Users, ContentViewingHistory.user_id == Users.id        # 🔹 ContentViewingHistory와 Users 테이블을 join
        ).filter(
            ContentViewingHistory.start_time >= utc_start_dt,
            ContentViewingHistory.end_time <= utc_end_dt,
        )
        
        if scope == 'company' and filter_value:
            query = query.filter(Users.company == filter_value)
        elif scope == 'department' and filter_value:
            parts = filter_value.split('||', 1)
            if len(parts) == 2:
                query = query.filter(Users.company == parts[0], Users.department == parts[1])
            else:
                query = query.filter(Users.company == parts[0])
        elif scope == 'user' and filter_value:
            query = query.filter(Users.id == filter_value)
             
        query = query.group_by(Channel.id, Channel.name)
        
        # logging.debug(f"[add_summary_day_date] {query.statement.compile(compile_kwargs={"literal_binds": True})}")
        rows = query.all()
        update_folder_duration_map(folder_duration_map, rows)
        
def add_summary_day_date_by_users(user_ids, start_dt, end_dt, folder_duration_by_user):
    """
    여러 사용자에 대한 카테고리별 학습 진행률을 가져오는 쿼리(일별)
    """
    if start_dt > end_dt:
        return
    
    if end_dt > datetime.datetime.now().date():
        end_dt = datetime.datetime.now().date()
        
    today = datetime.datetime.now().date()
    split_date = today - datetime.timedelta(days=2)
    
    if start_dt <= split_date:
        summary_end_date = min(end_dt, split_date)
        rows = get_learning_summary_rows_day(
            start_date=start_dt,
            end_date=summary_end_date,
            scope='user',
            group_fields=[LearningSummaryDay.user_id, LearningSummaryDay.channel_id, LearningSummaryDay.channel_name],
            join_users=False,
            extra_filter=[LearningSummaryDay.user_id.in_(user_ids)]
        )
        for row in rows:
            d = folder_duration_by_user[row.user_id][row.channel_id]                      
            folder_duration_by_user[row.user_id][row.channel_id] = (d[0], d[1] + row.total)
    
    if start_dt <= end_dt:
        local_tz = datetime.datetime.now(datetime.timezone.utc).astimezone().tzinfo
        utc_start_dt = datetime.datetime.combine(start_dt, datetime.time.min, local_tz).astimezone(datetime.timezone.utc)
        utc_end_dt = datetime.datetime.combine(end_dt, datetime.time.max, local_tz).astimezone(datetime.timezone.utc)
        
        Page = aliased(ContentRelPages) # 🔹 ContentRelPages 테이블을 alias로 사용
        Detail = aliased(ContentRelPageDetails) # 🔹 ContentRelPageDetails 테이블을 alias로 사용
        DetailPage = aliased(ContentRelPages) # 🔹 ContentRelPages 테이블을 alias로 사용
        Folder = aliased(ContentRelFolders) # 🔹 ContentRelFolders 테이블을 alias로 사용
        Channel = aliased(ContentRelChannels) # 🔹 ContentRelChannels 테이블을 alias로 사용
           
        query = db.session.query(
            ContentViewingHistory.user_id.label('user_id'),
            Channel.id.label('channel_id'),
            Channel.name.label('channel_name'),
            func.sum(ContentViewingHistory.stay_duration).label('total')
        ).outerjoin(
            Page, and_(ContentViewingHistory.file_type == 'page', ContentViewingHistory.file_id == Page.id)   
        ).outerjoin(
            Detail, and_(ContentViewingHistory.file_type == 'detail', ContentViewingHistory.file_id == Detail.id)        
        ).outerjoin(
            DetailPage, Detail.page_id == DetailPage.id
        ).outerjoin(
            Folder, or_(Folder.id == Page.folder_id, Folder.id == DetailPage.folder_id) # 🔹 Page와 DetailPage의 folder_id를 join
        ).join(
            Channel, Channel.id == Folder.channel_id
        ).join(
            Users, ContentViewingHistory.user_id == Users.id
        ).filter(
            ContentViewingHistory.start_time >= utc_start_dt,
            ContentViewingHistory.end_time <= utc_end_dt,
            Users.id.in_(user_ids)
        )
        
        query = query.group_by(ContentViewingHistory.user_id, Channel.id, Channel.name)
        rows = query.all()
        
        for row in rows: 
            d = folder_duration_by_user[row.user_id][row.channel_id]                      
            folder_duration_by_user[row.user_id][row.channel_id] = (d[0], d[1] + row.total)          
        
def get_learning_summary_rows_day(start_date, end_date, scope, group_fields, join_users=True, extra_filter=None):
    query = db.session.query(*group_fields, func.sum(LearningSummaryDay.total_duration).label('total'))
    
    if join_users:
        query = query.join(Users, Users.id == LearningSummaryDay.user_id_key)

    query = query.filter(
            LearningSummaryDay.stat_date >= start_date,
            LearningSummaryDay.stat_date <= end_date,
            LearningSummaryDay.scope == scope
        )
    
    if extra_filter is not None:
        query = query.filter(*extra_filter)
        
    query = query.group_by(*group_fields)
    
    # logging.debug(f"[get_learning_summary_rows_day] {query.statement.compile(compile_kwargs={"literal_binds": True})}")
    return query.all()
        