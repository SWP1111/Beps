import logging
import log_config
import datetime
from services import user_summary_service
from models import ( LearningSummaryAgg, LearningSummaryDay, ContentViewingHistory, Users, 
                    ContentRelChannels,ContentRelFolders, ContentRelPages, ContentRelPageDetails)
from extensions import db
from sqlalchemy import func
from sqlalchemy.sql import union_all
from sqlalchemy.orm import aliased

def get_top_folders():
    channels = db.session.query(
        ContentRelFolders.id,
        ContentRelFolders.name
    ).filter(
        ContentRelFolders.is_deleted == False,
        ContentRelFolders.parent_id == None
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
    folder_duration_map = get_top_folders()
    
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
                    group_fields=[LearningSummaryAgg.folder_id, LearningSummaryAgg.folder_name],
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
        key = row.folder_id
        duration = row.total or datetime.timedelta(0)
        if key not in folder_duration_map:
            folder_duration_map[key] = (row.folder_name, datetime.timedelta(0))
            logging.debug(f"[update_folder_duration_map] New folder added: {key} - {row.folder_name}")
        folder_duration_map[key] = (row.folder_name, folder_duration_map[key][1] + duration)

        
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
            group_fields=[LearningSummaryDay.folder_id, LearningSummaryDay.folder_name],
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
        Folder = aliased(ContentRelFolders) # 🔹 ContentRelFolders 테이블을 alias로 사용
        TopFolder = aliased(ContentRelFolders) # 🔹 ContentRelFolders 테이블을 alias로 사용
        Channel = aliased(ContentRelChannels) # 🔹 ContentRelChannels 테이블을 alias로 사용
        
        page_subq = db.session.query(
            Page.id.label('file_id'),
            Page.folder_id.label('folder_id')
        )  
        
        detail_subq = db.session.query(
            Detail.id.label('file_id'),
            ContentRelPages.folder_id.label('folder_id')
        ).join(ContentRelPages, Detail.page_id == ContentRelPages.id)
        
        file_folder_union = union_all(page_subq, detail_subq).alias('f')
        
        query = db.session.query(
            TopFolder.id.label('folder_id'),
            Channel.name.label('folder_name'),
            func.sum(ContentViewingHistory.stay_duration).label('total')
        ).join(
            file_folder_union, file_folder_union.c.file_id == ContentViewingHistory.file_id
        ).join(
            Folder, Folder.id == file_folder_union.c.folder_id
        ).join(
            Channel, Channel.id == Folder.channel_id
        ).join(
            TopFolder, db.and_(
                TopFolder.channel_id == Channel.id,
                TopFolder.parent_id == None
            )
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
             
        query = query.group_by(TopFolder.id, Channel.name)
        
        # logging.debug(f"[add_summary_day_date] {query.statement.compile(compile_kwargs={"literal_binds": True})}")
        rows = query.all()
        update_folder_duration_map(folder_duration_map, rows)
        

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
        