import logging
import log_config
import datetime
from extensions import db
from models import LoginHistory, loginSummaryDay, loginSummaryAgg
from collections import defaultdict
from sqlalchemy import func

def get_quarter_period_value(year):
    """주어진 연도에 대한 분기 기간을 반환합니다."""
    return [
        ("{}-Q1".format(year), datetime.date(year, 1, 1), datetime.date(year, 3, 31)),
        ("{}-Q2".format(year), datetime.date(year, 4, 1), datetime.date(year, 6, 30)),
        ("{}-Q3".format(year), datetime.date(year, 7, 1), datetime.date(year, 9, 30)),
        ("{}-Q4".format(year), datetime.date(year, 10, 1), datetime.date(year, 12, 31))
    ]
    
def get_half_period_value(year):
    """주어진 연도에 대한 반기 기간을 반환합니다."""
    return [
        ("{}-H1".format(year), datetime.date(year, 1, 1), datetime.date(year, 6, 30)),
        ("{}-H2".format(year), datetime.date(year, 7, 1), datetime.date(year, 12, 31))
    ]

def get_year_period_value(year):
    """주어진 연도에 대한 연도 기간을 반환합니다."""
    return [
        ("{}".format(year), datetime.date(year, 1, 1), datetime.date(year, 12, 31))
    ]

def is_range_used(start, end, used_ranges):
    """주어진 범위가 이미 사용된 범위에 포함되는지 확인합니다."""
    for u_start, u_end in used_ranges:
        if start >= u_start and end <= u_end:
            return True
    return False

def get_top_user_duration_mixed(start_date, end_date):
    """주어진 기간 동안의 사용자별 총 로그인 시간 중 제일 높은 시간 정보를 반환합니다."""
    user_duration_map = defaultdict(datetime.timedelta)
    used_ranges = []

    for period_str, y_start, y_end in get_year_period_value(start_date.year):
        if start_date <= y_start and end_date >= y_end:
            summary_year_rows = db.session.query(
                loginSummaryAgg.user_id,
                func.sum(loginSummaryAgg.total_duration).label('total')
            ).filter(
                loginSummaryAgg.period_type == 'year',
                loginSummaryAgg.period_value == period_str,
                loginSummaryAgg.scope == 'user',
            ).group_by(loginSummaryAgg.user_id).all()
            for row in summary_year_rows:
                if row.user_id:
                    user_duration_map[row.user_id] += row.total or datetime.timedelta(0)
                    logging.debug(f"[get_top_user_duration_mixed] Yearly summary for user {row.user_id}: {row.total}")
            used_ranges.append((y_start, y_end))
            
    for period_str, h_start, h_end in get_half_period_value(start_date.year):
        if start_date <= h_start and end_date >= h_end and not is_range_used(h_start, h_end, used_ranges):
            summary_half_rows = db.session.query(
                loginSummaryAgg.user_id,
                func.sum(loginSummaryAgg.total_duration).label('total')
            ).filter(
                loginSummaryAgg.period_type == 'half',
                loginSummaryAgg.period_value == period_str,
                loginSummaryAgg.scope == 'user',
            ).group_by(loginSummaryAgg.user_id).all()
            for row in summary_half_rows:
                if row.user_id:
                    user_duration_map[row.user_id] += row.total or datetime.timedelta(0)
                    logging.debug(f"[get_top_user_duration_mixed] Half yearly summary for user {row.user_id}: {row.total}")
            used_ranges.append((h_start, h_end))
            
    for period_str, q_start, q_end in get_quarter_period_value(start_date.year):
        if start_date <= q_start and end_date >= q_end and not is_range_used(q_start, q_end, used_ranges):
            summary_quarter_rows = db.session.query(
                loginSummaryAgg.user_id,
                func.sum(loginSummaryAgg.total_duration).label('total')
            ).filter(
                loginSummaryAgg.period_type == 'quarter',
                loginSummaryAgg.period_value == period_str,
                loginSummaryAgg.scope == 'user',
            ).group_by(loginSummaryAgg.user_id).all()
            for row in summary_quarter_rows:
                if row.user_id:
                    user_duration_map[row.user_id] += row.total or datetime.timedelta(0)
                    logging.debug(f"[get_top_user_duration_mixed] Quarterly summary for user {row.user_id}: {row.total}")
            used_ranges.append((q_start, q_end))
            logging.debug(f"[get_top_user_duration_mixed] Used ranges: {(q_start, q_end)}")
    
    used_ranges.sort(key=lambda x: x[0])
    if used_ranges:
        current = min(start_date, used_ranges[0][0])
    else:
        current = start_date
    
    for used_start, used_end in used_ranges:
        logging.debug(f"[get_top_user_duration_mixed] used_start: {used_start}, current: {current}, end: {used_end}")
        if current < used_start:
            logging.debug(f"[get_top_user_duration_mixed] current < used_start")
            
            if current < (datetime.date.today() - datetime.timedelta(days=1)):     
                try:
                    summary_day_rows = db.session.query(
                        loginSummaryDay.user_id_key,
                        func.sum(loginSummaryDay.total_duration).label('total')
                    ).filter(
                        loginSummaryDay.period_value >= current,
                        loginSummaryDay.period_value <= min(used_start - datetime.timedelta(days=1), datetime.date.today() - datetime.timedelta(days=2)),
                        loginSummaryDay.scope == 'user'
                    ).group_by(loginSummaryDay.user_id_key).all()
                    
                    for row in summary_day_rows:
                        if row.user_id:
                            user_duration_map[row.user_id] += row.total or datetime.timedelta(0)
                except Exception as e:
                    logging.error(f"Error in summary_day_rows query: {e}")
                    return {
                        'has_data': False,
                        'user_id': None,
                        'duration': datetime.timedelta(0)
                    }
                        
            if used_start - datetime.timedelta(days=1) in (datetime.date.today(), datetime.date.today() - datetime.timedelta(days=1)):
                local_tz = datetime.datetime.now().astimezone().tzinfo
                utc_start_dt = datetime.datetime.combine(current, datetime.time.min, tzinfo=local_tz).astimezone(datetime.timezone.utc)
                utc_end_dt = datetime.datetime.combine(used_start - datetime.timedelta(days=1), datetime.time.max, tzinfo=local_tz).astimezone(datetime.timezone.utc)
                login_history_rows = db.session.query(
                    LoginHistory.user_id,
                    func.sum(LoginHistory.session_duration).label('total')
                ).filter(
                    LoginHistory.login_time >= utc_start_dt,
                    LoginHistory.login_time <= utc_end_dt
                ).group_by(LoginHistory.user_id).all()
                for row in login_history_rows:
                    if row.user_id:
                        user_duration_map[row.user_id] += row.total or datetime.timedelta(0)
        current = max(current, used_end + datetime.timedelta(days=1))
        logging.debug(f"[get_top_user_duration_mixed] current: {current}")
                   
    if current <= end_date:
        if current < (datetime.date.today() - datetime.timedelta(days=1)):
            logging.debug(f"[get_top_user_duration_mixed] current {current} end_date { min(end_date, datetime.date.today() - datetime.timedelta(days=2))}")
            summary_day_rows = db.session.query(
                loginSummaryDay.user_id_key,
                func.sum(loginSummaryDay.total_duration).label('total')
            ).filter(
                loginSummaryDay.period_value >= current,
                loginSummaryDay.period_value <= min(end_date, datetime.date.today() - datetime.timedelta(days=2)),
                loginSummaryDay.scope == 'user'
            ).group_by(loginSummaryDay.user_id_key).all()
            for row in summary_day_rows:
                if row.user_id_key:
                    user_duration_map[row.user_id_key] += row.total or datetime.timedelta(0)
                    logging.debug(f"[get_top_user_duration_mixed] Daily summary for user {row.user_id_key}: {row.total}")
            current = max(current, end_date)
        if end_date in (datetime.date.today(), datetime.date.today() - datetime.timedelta(days=1)):
            local_tz = datetime.datetime.now().astimezone().tzinfo
            utc_start_dt = datetime.datetime.combine(max(current, datetime.date.today() - datetime.timedelta(days=1)), datetime.time.min, tzinfo=local_tz).astimezone(datetime.timezone.utc)
            utc_end_dt = datetime.datetime.combine(end_date, datetime.time.max, tzinfo=local_tz).astimezone(datetime.timezone.utc)
            logging.debug(f"[get_top_user_duration_mixed] Current: {current}, End date: {end_date}")
            logging.debug(f"[get_top_user_duration_mixed] UTC Start: {utc_start_dt}, UTC End: {utc_end_dt}")
            login_history_rows = db.session.query(
                LoginHistory.user_id,
                func.sum(LoginHistory.session_duration).label('total')
            ).filter(
                LoginHistory.login_time >= utc_start_dt,
                LoginHistory.login_time <= utc_end_dt
            ).group_by(LoginHistory.user_id).all()
            for row in login_history_rows:
                if row.user_id:
                    user_duration_map[row.user_id] += row.total or datetime.timedelta(0)
                    logging.debug(f"[get_top_user_duration_mixed] LoginHistory for user {row.user_id}: {row.total}")
    
    if user_duration_map:
        top_user_id, top_duration = max(user_duration_map.items(), key=lambda x: x[1])   
        logging.info(f"[get_top_user_duration_mixed] Top user: {top_user_id}, Duration: {top_duration}")    
        return {
            'has_data': True,
            'user_id': top_user_id,
            'duration': top_duration
        }
    else:
        return {
            'has_data': False,
            'user_id': None,
            'duration': datetime.timedelta(0)
        }
    
           
def get_connection_summary_mixed(start_date, end_date, scope, filter_value=None):
    total = datetime.timedelta(0)
    work = datetime.timedelta(0)
    off = datetime.timedelta(0)
    internal = 0
    external = 0
    has_data = False
    
    used_ranges = []
    
    for period_str, y_start, y_end in get_year_period_value(start_date.year):
        if start_date <= y_start and end_date >= y_end:
            data = get_connection_summary_agg('year', period_str, scope, filter_value)
            if data['has_data']:
                has_data = True
                total += data['total_duration']
                work += data['worktime_duration']
                off += data['offhour_duration']
                internal += data['internal_count']
                external += data['external_count']
            used_ranges.append((y_start, y_end))
    
    for period_str, h_start, h_end in get_half_period_value(start_date.year):
        if start_date <= h_start and end_date >= h_end and not is_range_used(h_start, h_end, used_ranges):
            data = get_connection_summary_agg('half', period_str, scope, filter_value)
            if data['has_data']:
                has_data = True
                total += data['total_duration']
                work += data['worktime_duration']
                off += data['offhour_duration']
                internal += data['internal_count']
                external += data['external_count']
            used_ranges.append((h_start, h_end))
    
    for period_str, q_start, q_end in get_quarter_period_value(start_date.year):
        if start_date <= q_start and end_date >= q_end and not is_range_used(q_start, q_end, used_ranges):
            data = get_connection_summary_agg('quarter', period_str, scope, filter_value)
            if data['has_data']:
                has_data = True
                total += data['total_duration']
                work += data['worktime_duration']
                off += data['offhour_duration']
                internal += data['internal_count']
                external += data['external_count']
            used_ranges.append((q_start, q_end))
    
    used_ranges.sort(key=lambda x: x[0])
    if used_ranges:
        current = min(start_date, used_ranges[0][0])
    else:
        current = start_date
        
    for used_start, used_end in used_ranges:
        logging.debug(f"[get_connection_summary_mixed] used_start: {used_start}, end: {used_end}")       
        if current < used_start:
            logging.debug(f"[get_connection_summary_mixed] current: {current}, end: {used_start - datetime.timedelta(days=1)}")
            data = get_connection_summary_day(current, used_start - datetime.timedelta(days=1), scope, filter_value)
            if data['has_data']:
                has_data = True
                total += data['total_duration']
                work += data['worktime_duration']
                off += data['offhour_duration']
                internal += data['internal_count']
                external += data['external_count']
        current = max(current, used_end + datetime.timedelta(days=1))
        logging.debug(f"[get_connection_summary_mixed] current: {current}")
    if current <= end_date:
        data = get_connection_summary_day(current, end_date, scope, filter_value)
        if data['has_data']:
            has_data = True
            total += data['total_duration']
            work += data['worktime_duration']
            off += data['offhour_duration']
            internal += data['internal_count']
            external += data['external_count']
    
    logging.info(f"[get_connection_summary_mixed] Total duration: {total}, Worktime duration: {work}, Offhour duration: {off}, Internal count: {internal}, External count: {external}")
    
    return {
        'has_data': has_data,
        'total_duration': total,
        'worktime_duration': work,
        'offhour_duration': off,
        'internal_count': internal,
        'external_count': external
    }
                  
   
def get_connection_summary_day(start_date, end_date, scope, filter_value=None):
    total = datetime.timedelta(0)
    work = datetime.timedelta(0)
    off = datetime.timedelta(0)
    internal = 0
    external = 0
    has_data = False
    
    logging.debug(f"[get_connection_summary_day] start_date: {start_date}, end_date: {end_date}, scope: {scope}, filter_value: {filter_value}")
    
    if start_date < (datetime.date.today() - datetime.timedelta(days=1)):
        filters = [
            loginSummaryDay.period_value >= start_date,
            loginSummaryDay.period_value <= min(end_date, datetime.date.today() - datetime.timedelta(days=2)),
            loginSummaryDay.scope == scope
        ]
        if scope == 'user' and filter_value:
            filters.append(loginSummaryDay.user_id_key == filter_value)
        elif scope == 'department' and filter_value:
            filters.append(loginSummaryDay.department_key == filter_value)
        elif scope == 'company' and filter_value:
            filters.append(loginSummaryDay.company_key == filter_value)
        
        datas = loginSummaryDay.query.filter(*filters).all()
        for data in datas:
            has_data = True
            total += data.total_duration or datetime.timedelta(0)
            work += data.worktime_duration or datetime.timedelta(0)
            off += data.offhour_duration or datetime.timedelta(0)
            internal += data.internal_count or 0
            external += data.external_count or 0
            logging.debug(f"[loginSummaryDay] total: {total}, work: {work}, off: {off}, internal: {internal}, external: {external}")
            
    if end_date in (datetime.date.today(), datetime.date.today() - datetime.timedelta(days=1)):
        local_tz = datetime.datetime.now().astimezone().tzinfo
        utc_start_dt = datetime.datetime.combine(max(start_date, datetime.date.today() - datetime.timedelta(days=1)), datetime.time.min, tzinfo=local_tz).astimezone(datetime.timezone.utc)
        utc_end_dt = datetime.datetime.combine(end_date, datetime.time.max, tzinfo=local_tz).astimezone(datetime.timezone.utc)       
        filters = [
            LoginHistory.login_time >= utc_start_dt,
            LoginHistory.login_time <= utc_end_dt
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
                logging.debug(f"[LoginHistory] User: {record.user_id}, total: {total}, duration: {duration}, work {work}, off: {off}, internal: {internal}, external: {external}")


    logging.debug(f"[get_connection_summary_day] RESULT total: {total}, work: {work}, off: {off}, internal: {internal}, external: {external}")
    return {
        'has_data': has_data,
        'total_duration': total,
        'worktime_duration': work,
        'offhour_duration': off,
        'internal_count': internal,
        'external_count': external
    }
    
def get_connection_summary_agg(period_type, period_value, scope, filter_value=None):
    total = datetime.timedelta(0)
    work = datetime.timedelta(0)
    off = datetime.timedelta(0)
    internal = 0
    external = 0
    has_data = False
    
    filters = [
        loginSummaryAgg.period_type == period_type,
        loginSummaryAgg.period_value == period_value,
        loginSummaryAgg.scope == scope
    ]
    if scope == 'user' and filter_value:
        filters.append(loginSummaryAgg.user_id_key == filter_value)
    elif scope == 'department' and filter_value:
        filters.append(loginSummaryAgg.department_key == filter_value)
    elif scope == 'company' and filter_value:
        filters.append(loginSummaryAgg.company_key == filter_value)
    
    data = loginSummaryAgg.query.filter(*filters).first()
    
    if data:
        has_data = True
        total = data.total_duration or datetime.timedelta(0)
        work = data.worktime_duration or datetime.timedelta(0)
        off = data.offhour_duration or datetime.timedelta(0)
        internal = data.internal_count or 0
        external = data.external_count or 0
        
        logging.debug(f"[loginSummaryAgg] RESULT total: {total}, work: {work}, off: {off}, internal: {internal}, external: {external}")
        return {
            'has_data': has_data,
            'total_duration': total,
            'worktime_duration': work,
            'offhour_duration': off,
            'internal_count': internal,
            'external_count': external
        }
    else:
        return {
            'has_data': has_data,
            'total_duration': total,
            'worktime_duration': work,
            'offhour_duration': off,
            'internal_count': internal,
            'external_count': external
        }
        
            