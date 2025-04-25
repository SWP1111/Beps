import logging
import log_config
import datetime
from extensions import db
from models import LoginHistory, loginSummaryDay, loginSummaryAgg, Users
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

def get_period_value(period_type: str, period_value: str):
    """
    주어진 기간 유형과 값에 따라 시작일과 종료일을 반환합니다.
    period_type: 'year', 'half', 'quarter'
    period_value:
        - year: '2025'
        - half: '20251', '20252'
        - quarter: '20251', '20252', '20253', '20254'
    """
    if period_type == 'year':
        year = int(period_value)
        return datetime.date(year, 1, 1), datetime.date(year, 12, 31)

    elif period_type == 'half':
        year = int(period_value[:4])
        half = int(period_value[4:])
        if half == 1:
            return datetime.date(year, 1, 1), datetime.date(year, 6, 30)
        elif half == 2:
            return datetime.date(year, 7, 1), datetime.date(year, 12, 31)
        else:
            raise ValueError(f"Invalid half value: {period_value}")

    elif period_type == 'quarter':
        year = int(period_value[:4])
        quarter = int(period_value[4:])
        if quarter == 1:
            return datetime.date(year, 1, 1), datetime.date(year, 3, 31)
        elif quarter == 2:
            return datetime.date(year, 4, 1), datetime.date(year, 6, 30)
        elif quarter == 3:
            return datetime.date(year, 7, 1), datetime.date(year, 9, 30)
        elif quarter == 4:
            return datetime.date(year, 10, 1), datetime.date(year, 12, 31)
        else:
            raise ValueError(f"Invalid quarter value: {period_value}")

    else:
        raise ValueError(f"Invalid period_type: {period_type}")

def get_top_user_duration_mixed(start_date, end_date):
    """주어진 기간 동안의 사용자별 총 로그인 시간 중 제일 높은 시간 정보를 반환합니다."""
    user_duration_map = {}
    used_ranges = []

    all_users = db.session.query(Users.id, Users.name).all()
    for user in all_users:
        user_duration_map[user.id.lower()] = (user.name, datetime.timedelta(0))
        
    for period_str, y_start, y_end in get_year_period_value(start_date.year):
        if start_date <= y_start and end_date >= y_end:
            summary_year_rows = get_summary_rows_agg(
                loginSummaryAgg,
                period_type='year',
                period_value=period_str,
                scope='user',
                group_fields=[loginSummaryAgg.user_id, Users.name])
            
            if summary_year_rows:               
                used_ranges.append((y_start, y_end))
            for row in summary_year_rows:
                if row.user_id:
                    prev = user_duration_map.get(row.user_id.lower())
                    duration = row.total or datetime.timedelta(0)
                    if prev:
                        user_duration_map[row.user_id.lower()] = (row.name, prev[1]+ duration)
                    else:
                        user_duration_map[row.user_id.lower()] = (row.name, duration)                  
                    logging.debug(f"[get_top_user_duration_mixed] Yearly summary for user {row.user_id}: {row.name} : {row.total}")
            
    for period_str, h_start, h_end in get_half_period_value(start_date.year):
        if start_date <= h_start and end_date >= h_end and not is_range_used(h_start, h_end, used_ranges):
            summary_half_rows = get_summary_rows_agg(
                loginSummaryAgg,
                period_type='half',
                period_value=period_str,
                scope='user',
                group_fields=[loginSummaryAgg.user_id, Users.name]
            )
            if summary_half_rows:
                used_ranges.append((h_start, h_end))
            for row in summary_half_rows:
                if row.user_id:
                    prev = user_duration_map.get(row.user_id.lower())
                    duration = row.total or datetime.timedelta(0)
                    if prev:
                        user_duration_map[row.user_id.lower()] = (row.name, prev[1]+ duration)
                    else:
                        user_duration_map[row.user_id.lower()] = (row.name, duration)
                    logging.debug(f"[get_top_user_duration_mixed] Half yearly summary for user {row.user_id}: {row.name} : {row.total}")
            
    for period_str, q_start, q_end in get_quarter_period_value(start_date.year):
        if start_date <= q_start and end_date >= q_end and not is_range_used(q_start, q_end, used_ranges):
            summary_quarter_rows = get_summary_rows_agg(
                loginSummaryAgg,
                period_type='quarter',
                period_value=period_str,
                scope='user',
                group_fields=[loginSummaryAgg.user_id, Users.name])
            if summary_quarter_rows:
                used_ranges.append((q_start, q_end))               
                logging.debug(f"[get_top_user_duration_mixed] Used ranges: {(q_start, q_end)}")
            for row in summary_quarter_rows:
                if row.user_id:
                    prev = user_duration_map.get(row.user_id.lower())
                    duration = row.total or datetime.timedelta(0)
                    if prev:
                        user_duration_map[row.user_id.lower()] = (row.name, prev[1]+ duration)
                    else:
                        user_duration_map[row.user_id.lower()] = (row.name, duration)
                    logging.debug(f"[get_top_user_duration_mixed] Quarterly summary for user {row.user_id}: {row.name} : {row.total}")
    
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
                    summary_day_rows = get_summary_rows_day(
                        loginSummaryDay,
                        start_date=current,
                        end_date=min(used_start - datetime.timedelta(days=1), datetime.date.today() - datetime.timedelta(days=2)),
                        scope='user',
                        group_fields=[loginSummaryDay.user_id_key, Users.name]
                    )                 
                    
                    for row in summary_day_rows:
                        if row.user_id:
                            prev = user_duration_map.get(row.user_id.lower())
                            duration = row.total or datetime.timedelta(0)
                            if prev:
                                user_duration_map[row.user_id.lower()] = (row.name, prev[1]+ duration)
                            else:
                                user_duration_map[row.user_id.lower()] = (row.name, duration)
                            logging.debug(f"[get_top_user_duration_mixed] Daily summary for user {row.user_id}: {row.name} : {row.total}")
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
                login_history_rows = get_summary_rows_history(
                    LoginHistory,
                    start_date=utc_start_dt,
                    end_date=utc_end_dt,
                    group_fields=[LoginHistory.user_id, Users.name]
                )                
                for row in login_history_rows:
                    if row.user_id:
                        prev = user_duration_map.get(row.user_id.lower())
                        duration = row.total or datetime.timedelta(0)
                        if prev:
                            user_duration_map[row.user_id.lower()] = (row.name, prev[1]+ duration)
                        else:
                            user_duration_map[row.user_id.lower()] = (row.name, duration)
                        logging.debug(f"[get_top_user_duration_mixed] LoginHistory for user {row.user_id}: {row.name} : {row.total}")
        current = max(current, used_end + datetime.timedelta(days=1))
        logging.debug(f"[get_top_user_duration_mixed] current: {current}")
                   
    if current <= end_date:
        if current < (datetime.date.today() - datetime.timedelta(days=1)):
            logging.debug(f"[get_top_user_duration_mixed] current {current} end_date { min(end_date, datetime.date.today() - datetime.timedelta(days=2))}")
            summary_day_rows = get_summary_rows_day(
                loginSummaryDay,
                start_date=current,
                end_date=min(end_date, datetime.date.today() - datetime.timedelta(days=2)),
                scope='user',
                group_fields=[loginSummaryDay.user_id_key, Users.name]
            )          
            for row in summary_day_rows:
                if row.user_id_key:
                    prev = user_duration_map.get(row.user_id_key.lower())
                    duration = row.total or datetime.timedelta(0)
                    if prev:
                        user_duration_map[row.user_id_key.lower()] = (row.name, prev[1]+ duration)
                    else:
                        user_duration_map[row.user_id_key.lower()] = (row.name, duration)
                    logging.debug(f"[get_top_user_duration_mixed] Daily summary for user {row.user_id_key}: {row.name} : {row.total}")
        if end_date in (datetime.date.today(), datetime.date.today() - datetime.timedelta(days=1)):
            local_tz = datetime.datetime.now().astimezone().tzinfo
            utc_start_dt = datetime.datetime.combine(max(current, datetime.date.today() - datetime.timedelta(days=1)), datetime.time.min, tzinfo=local_tz).astimezone(datetime.timezone.utc)
            utc_end_dt = datetime.datetime.combine(end_date, datetime.time.max, tzinfo=local_tz).astimezone(datetime.timezone.utc)
            logging.debug(f"[get_top_user_duration_mixed] Current: {current}, End date: {end_date}")
            logging.debug(f"[get_top_user_duration_mixed] UTC Start: {utc_start_dt}, UTC End: {utc_end_dt}")
            login_history_rows = get_summary_rows_history(
                LoginHistory,
                start_date=utc_start_dt,
                end_date=utc_end_dt,
                group_fields=[LoginHistory.user_id, Users.name]
            )         
            for row in login_history_rows:
                if row.user_id:
                    prev = user_duration_map.get(row.user_id.lower())
                    duration = row.total or datetime.timedelta(0)
                    if prev:
                        user_duration_map[row.user_id.lower()] = (row.name, prev[1]+ duration)
                    else:
                        user_duration_map[row.user_id.lower()] = (row.name, duration)
                    logging.debug(f"[get_top_user_duration_mixed] LoginHistory for user {row.user_id}: {row.name} : {row.total}")
    
    if user_duration_map:
        sorted_users = sorted(user_duration_map.items(), key=lambda x: x[1][1], reverse=True)
        sorted_users_by_low = sorted(user_duration_map.items(), key=lambda x: x[1][1])
        return {
            'has_data': True,
            'top':  [(user_id, name, str(duration)) for user_id, (name, duration) in sorted_users[:3]],
            'bottom': [(user_id, name, str(duration)) for user_id, (name, duration) in sorted_users_by_low[:3]],
        }
    else:
        return {
            'has_data': False,
            'user_id': None,
            'duration': datetime.timedelta(0)
        }

def get_top_department_duration_mixed(start_date, end_date):
    dept_duration_map = {}
    used_ranges = []
    
    all_departments = db.session.query(Users.company, Users.department).distinct().all()
    for company, department in all_departments:
        dept_duration_map[(company, department)] = datetime.timedelta(0)
        
    for period_str, y_start, y_end in get_year_period_value(start_date.year):
        if start_date <= y_start and end_date >= y_end:
            rows = get_summary_rows_agg(
                loginSummaryAgg,
                period_type='year',
                period_value=period_str,
                scope='department',
                group_fields=[loginSummaryAgg.company_key, loginSummaryAgg.department_key],
                join_users=False
            )
            if rows:
                used_ranges.append((y_start, y_end))
            for row in rows:
                key = (row.company_key, row.department_key)
                if dept_duration_map.get(key) is None:
                    dept_duration_map[key] = datetime.timedelta(0)
                else:
                    dept_duration_map[key] += row.total or datetime.timedelta(0)
            
    for period_str, h_start, h_end in get_half_period_value(start_date.year):
        if start_date <= h_start and end_date >= h_end and not is_range_used(h_start, h_end, used_ranges):
            rows = get_summary_rows_agg(
                loginSummaryAgg,
                period_type='half',
                period_value=period_str,
                scope='department',
                group_fields=[loginSummaryAgg.company_key, loginSummaryAgg.department_key],
                join_users=False
            )
            if rows:
                used_ranges.append((h_start, h_end))
            for row in rows:
                key = (row.company_key, row.department_key)
                if dept_duration_map.get(key) is None:
                    dept_duration_map[key] = datetime.timedelta(0)
                else:
                    dept_duration_map[key] += row.total or datetime.timedelta(0)
            
    for period_str, q_start, q_end in get_quarter_period_value(start_date.year):
        if start_date <= q_start and end_date >= q_end and not is_range_used(q_start, q_end, used_ranges):
            logging.debug(f"[get_top_department_duration_mixed] Quarterly summary for {period_str}: {q_start} - {q_end}")
            rows = get_summary_rows_agg(
                loginSummaryAgg,
                period_type='quarter',
                period_value=period_str,
                scope='department',
                group_fields=[loginSummaryAgg.company_key, loginSummaryAgg.department_key],
                join_users=False
            )
            if rows:
                used_ranges.append((q_start, q_end))
            for row in rows:
                key = (row.company_key, row.department_key)
                if dept_duration_map.get(key) is None:
                    dept_duration_map[key] = datetime.timedelta(0)
                else:
                    dept_duration_map[key] += row.total or datetime.timedelta(0)
                logging.debug(f"[get_top_department_duration_mixed] Quarterly summary for {row.company_key}: {row.department_key} : {row.total}")
            
    used_ranges.sort(key=lambda x: x[0])
    if used_ranges:
        current = min(start_date, used_ranges[0][0])
    else:
        current = start_date
    
    for used_start, used_end in used_ranges:
        logging.debug(f"[get_top_department_duration_mixed] used_start: {used_start}, current: {current}, end: {used_end}")
        if current < used_start:
            if current < (datetime.date.today() - datetime.timedelta(days=1)):
                try:
                    rows = get_summary_rows_day(
                        loginSummaryDay,
                        start_date=current,
                        end_date=min(used_start - datetime.timedelta(days=1), datetime.date.today() - datetime.timedelta(days=2)),
                        scope='department',
                        group_fields=[loginSummaryDay.company_key, loginSummaryDay.department_key],
                        join_users=False
                    )
                    for row in rows:
                        key = (row.company_key, row.department_key)
                        dept_duration_map[key] += row.total or datetime.timedelta(0)
                except Exception as e:
                    logging.error(f"Error in summary_day_rows query: {e}")
                    return {
                        'has_data': False,
                        'company': None,
                        'department': None,
                        'duration': datetime.timedelta(0)
                    }
                        
            if used_start - datetime.timedelta(days=1) in (datetime.date.today(), datetime.date.today() - datetime.timedelta(days=1)):
                local_tz = datetime.datetime.now().astimezone().tzinfo
                utc_start_dt = datetime.datetime.combine(current, datetime.time.min, tzinfo=local_tz).astimezone(datetime.timezone.utc)
                utc_end_dt = datetime.datetime.combine(used_start - datetime.timedelta(days=1), datetime.time.max, tzinfo=local_tz).astimezone(datetime.timezone.utc)
                rows = get_summary_rows_history(
                    LoginHistory,
                    start_date=utc_start_dt,
                    end_date=utc_end_dt,
                    group_fields=[Users.company, Users.department],
                )
                for row in rows:
                    key = (row.company, row.department)
                    if dept_duration_map.get(key) is None:
                        dept_duration_map[key] = datetime.timedelta(0)
                    else:
                        dept_duration_map[key] += row.total or datetime.timedelta(0)
        current = max(current, used_end + datetime.timedelta(days=1))
        logging.debug(f"[get_top_department_duration_mixed] current: {current}")
        
    if current <= end_date:
        logging.debug(f"[get_top_department_duration_mixed] current <= end_date {current} <= {end_date}")
        if current < (datetime.date.today() - datetime.timedelta(days=1)):
            logging.debug(f"[get_top_department_duration_mixed]111 current {current} end_date { min(end_date, datetime.date.today() - datetime.timedelta(days=2))}")
            rows = get_summary_rows_day(
                loginSummaryDay,
                start_date=current,
                end_date=min(end_date, datetime.date.today() - datetime.timedelta(days=2)),
                scope='department',
                group_fields=[loginSummaryDay.company_key, loginSummaryDay.department_key],
                join_users=False
            )
            for row in rows:
                key = (row.company_key, row.department_key)
                if dept_duration_map.get(key) is None:
                    dept_duration_map[key] = datetime.timedelta(0)
                else:
                    dept_duration_map[key] += row.total or datetime.timedelta(0)
        logging.debug(f"[get_top_department_duration_mixed]222 current {current} end_date {end_date}")
        if end_date in (datetime.date.today(), datetime.date.today() - datetime.timedelta(days=1)):
            logging.debug(f"[get_top_department_duration_mixed]333 current {current} end_date {end_date}")
            local_tz = datetime.datetime.now().astimezone().tzinfo
            utc_start_dt = datetime.datetime.combine(max(current, datetime.date.today() - datetime.timedelta(days=1)), datetime.time.min, tzinfo=local_tz).astimezone(datetime.timezone.utc)
            utc_end_dt = datetime.datetime.combine(end_date, datetime.time.max, tzinfo=local_tz).astimezone(datetime.timezone.utc)
            logging.debug(f"[get_top_department_duration_mixed] utc_start_dt : {utc_start_dt} utc_end_dt: {utc_end_dt}")
            rows = get_summary_rows_history(
                LoginHistory,
                start_date=utc_start_dt,
                end_date=utc_end_dt,
                group_fields=[Users.company, Users.department],
            )
            for row in rows:
                logging.debug(f"[get_top_department_duration_mixed] row: {row}")
                key = (row.company, row.department)
                if dept_duration_map.get(key) is None:
                    dept_duration_map[key] = datetime.timedelta(0)
                else:
                    dept_duration_map[key] += row.total or datetime.timedelta(0)
                
    if dept_duration_map:
        sorted_departments = sorted(dept_duration_map.items(), key=lambda x: x[1], reverse=True)
        sorted_departments_by_low = sorted(dept_duration_map.items(), key=lambda x: x[1])
        return {
            'has_data': True,
            'top': [(company, department, str(duration)) for (company, department), duration in sorted_departments[:3]],
            'bottom': [(company, department, str(duration)) for (company, department), duration in sorted_departments_by_low[:3]],
        }
    else:
        return {
            'has_data': False,
            'company': None,
            'department': None,
            'duration': datetime.timedelta(0)
        }

def get_top_company_duration_mixed(start_date, end_date):
    company_duaration_map = {}
    used_ranges = []
    
    all_companies = db.session.query(Users.company).distinct().all()
    for (company,) in all_companies:
        company_duaration_map[company] = datetime.timedelta(0)
        
    for period_str, y_start, y_end in get_year_period_value(start_date.year):
        if start_date <= y_start and end_date >= y_end:
            rows = get_summary_rows_agg(
                loginSummaryAgg,
                period_type='year',
                period_value=period_str,
                scope='company',
                group_fields=[loginSummaryAgg.company_key],
                join_users=False
            )
            if rows:
                used_ranges.append((y_start, y_end))
            for row in rows:
                if company_duaration_map.get(row.company_key) is None:
                    company_duaration_map[row.company_key] = datetime.timedelta(0)
                else:
                    company_duaration_map[company] += row.total or datetime.timedelta(0)
    
    for period_str, h_start, h_end in get_half_period_value(start_date.year):
        if start_date <= h_start and end_date >= h_end and not is_range_used(h_start, h_end, used_ranges):
            rows = get_summary_rows_agg(
                loginSummaryAgg,
                period_type='half',
                period_value=period_str,
                scope='company',
                group_fields=[loginSummaryAgg.company_key],
                join_users=False
            )
            if rows:
                used_ranges.append((h_start, h_end))
            for row in rows:
                if company_duaration_map.get(row.company_key) is None:
                    company_duaration_map[row.company_key] = datetime.timedelta(0)
                else:
                    company_duaration_map[company] += row.total or datetime.timedelta(0)
    
    for period_str, q_start, q_end in get_quarter_period_value(start_date.year):
        if start_date <= q_start and end_date >= q_end and not is_range_used(q_start, q_end, used_ranges):
            rows = get_summary_rows_agg(
                loginSummaryAgg,
                period_type='quarter',
                period_value=period_str,
                scope='company',
                group_fields=[loginSummaryAgg.company_key],
                join_users=False
            )
            if rows:
                used_ranges.append((q_start, q_end))
            for row in rows:
                if company_duaration_map.get(row.company_key) is None:
                    company_duaration_map[row.company_key] = datetime.timedelta(0)
                else:
                    company_duaration_map[company] += row.total or datetime.timedelta(0)
    
    used_ranges.sort(key=lambda x: x[0])
    if used_ranges:
        current = min(start_date, used_ranges[0][0])
    else:
        current = start_date
        
    for used_start, used_end in used_ranges:
        if current < used_start:
            if current < (datetime.date.today() - datetime.timedelta(days=1)):
                try:
                    rows = get_summary_rows_day(
                        loginSummaryDay,
                        start_date=current,
                        end_date=min(used_start - datetime.timedelta(days=1), datetime.date.today() - datetime.timedelta(days=2)),
                        scope='company',
                        group_fields=[loginSummaryDay.company_key],
                        join_users=False
                    )
                    for row in rows:
                        if company_duaration_map.get(row.company_key) is None:
                            company_duaration_map[row.company_key] = datetime.timedelta(0)
                        else:
                            company_duaration_map[company] += row.total or datetime.timedelta(0)
                except Exception as e:
                    logging.error(f"Error in summary_day_rows query: {e}")
                    return {
                        'has_data': False,
                        'company': None,
                        'duration': datetime.timedelta(0)
                    }
            
            if used_start - datetime.timedelta(days=1) in (datetime.date.today(), datetime.date.today() - datetime.timedelta(days=1)):
                local_tz = datetime.datetime.now().astimezone().tzinfo
                utc_start_dt = datetime.datetime.combine(current, datetime.time.min, tzinfo=local_tz).astimezone(datetime.timezone.utc)
                utc_end_dt = datetime.datetime.combine(used_start - datetime.timedelta(days=1), datetime.time.max, tzinfo=local_tz).astimezone(datetime.timezone.utc)
                rows = get_summary_rows_history(
                    LoginHistory,
                    start_date=utc_start_dt,
                    end_date=utc_end_dt,
                    group_fields=[Users.company]
                )
                for row in rows:
                    if company_duaration_map.get(row.company) is None:
                        company_duaration_map[row.company] = datetime.timedelta(0)
                    else:
                        company_duaration_map[company] += row.total or datetime.timedelta(0)
                        
        current = max(current, used_end + datetime.timedelta(days=1))
        
    if current <= end_date:
        if current < (datetime.date.today() - datetime.timedelta(days=1)):
            rows = get_summary_rows_day(
                loginSummaryDay,
                start_date=current,
                end_date=min(end_date, datetime.date.today() - datetime.timedelta(days=2)),
                scope='company',
                group_fields=[loginSummaryDay.company_key],
                join_users=False
            )
            for row in rows:
                if company_duaration_map.get(row.company_key) is None:
                    company_duaration_map[row.company_key] = datetime.timedelta(0)
                else:
                    company_duaration_map[company] += row.total or datetime.timedelta(0)
        if end_date in (datetime.date.today(), datetime.date.today() - datetime.timedelta(days=1)):
            local_tz = datetime.datetime.now().astimezone().tzinfo
            utc_start_dt = datetime.datetime.combine(max(current, datetime.date.today() - datetime.timedelta(days=1)), datetime.time.min, tzinfo=local_tz).astimezone(datetime.timezone.utc)
            utc_end_dt = datetime.datetime.combine(end_date, datetime.time.max, tzinfo=local_tz).astimezone(datetime.timezone.utc)
            rows = get_summary_rows_history(
                LoginHistory,
                start_date=utc_start_dt,
                end_date=utc_end_dt,
                group_fields=[Users.company]
            )
            for row in rows:
                if company_duaration_map.get(row.company) is None:
                    company_duaration_map[row.company] = datetime.timedelta(0)
                else:
                    company_duaration_map[company] += row.total or datetime.timedelta(0)
    
    if company_duaration_map:
        sorted_companies = sorted(company_duaration_map.items(), key=lambda x: x[1], reverse=True)
        sorted_companies_by_low = sorted(company_duaration_map.items(), key=lambda x: x[1])
        return {
            'has_data': True,
            'top': [(company, str(duration)) for company, duration in sorted_companies[:3]],
            'bottom': [(company, str(duration)) for company, duration in sorted_companies_by_low[:3]],
        }
    else:
        return {
            'has_data': False,
            'company': None,
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
        logging.debug(f"[get_connection_summary_mixed] Yearly summary for {period_str}: {y_start} - {y_end}")
        if start_date <= y_start and end_date >= y_end:
            data = get_connection_summary_agg('year', period_str, scope, filter_value)
            if data['has_data']:
                has_data = True
                total += data['total_duration']
                work += data['worktime_duration']
                off += data['offhour_duration']
                internal += data['internal_count']
                external += data['external_count']
                logging.debug(f"[get_connection_summary_mixed] Yearly summary data: {data}")
                used_ranges.append((y_start, y_end))
    
    for period_str, h_start, h_end in get_half_period_value(start_date.year):
        logging.debug(f"[get_connection_summary_mixed] Half yearly summary for {period_str}: {h_start} - {h_end}")
        if start_date <= h_start and end_date >= h_end and not is_range_used(h_start, h_end, used_ranges):
            data = get_connection_summary_agg('half', period_str, scope, filter_value)
            if data['has_data']:
                has_data = True
                total += data['total_duration']
                work += data['worktime_duration']
                off += data['offhour_duration']
                internal += data['internal_count']
                external += data['external_count']
                logging.debug(f"[get_connection_summary_mixed] Half yearly summary data: {data}")
                used_ranges.append((h_start, h_end))
    
    for period_str, q_start, q_end in get_quarter_period_value(start_date.year):
        logging.debug(f"[get_connection_summary_mixed] Quarterly summary for {start_date} {period_str}: {q_start} - {q_end}")
        if start_date <= q_start and end_date >= q_end and not is_range_used(q_start, q_end, used_ranges):
            data = get_connection_summary_agg('quarter', period_str, scope, filter_value)
            if data['has_data']:
                has_data = True
                total += data['total_duration']
                work += data['worktime_duration']
                off += data['offhour_duration']
                internal += data['internal_count']
                external += data['external_count']
                logging.debug(f"[get_connection_summary_mixed] Quarterly summary data: {data}")
                used_ranges.append((q_start, q_end))
    
    used_ranges.sort(key=lambda x: x[0])
    logging.debug(f"[get_connection_summary_mixed] Used ranges: {used_ranges}")
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
                logging.debug(f"[get_connection_summary_mixed] Daily summary data: {data}")
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
            logging.debug(f"[get_connection_summary_mixed] Daily summary data: {data}")
    
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
            parts = filter_value.split('||', 1)
            if len(parts) == 2:
                company_name, department_name = parts
                filters.append(loginSummaryDay.company_key == company_name)
                filters.append(loginSummaryDay.department_key == department_name)
            else:
                department_name = parts[0]
                filters.append(loginSummaryDay.department_key == department_name)
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
        
        logging.debug(f"UTC Start: {utc_start_dt}, UTC End: {utc_end_dt}")
        query = db.session.query(LoginHistory)
        
        if scope in ['department', 'company']:
            query = query.join(Users, LoginHistory.user_id == Users.id)
        
        filters = [
            LoginHistory.login_time >= utc_start_dt,
            LoginHistory.login_time <= utc_end_dt
        ]
        
        if scope == 'user' and filter_value:
            filters.append(LoginHistory.user_id == filter_value)
        elif scope == 'department' and filter_value:
            parts = filter_value.split('||', 1)
            if len(parts) == 2:
                company_name, department_name = parts
                filters.append(Users.company == company_name)
                filters.append(Users.department == department_name)
            else:
                department_name = parts[0]
                filters.append(Users.department == department_name)
        elif scope == 'company' and filter_value:
            logging.debug(f"[get_connection_summary_day] filter_value: {filter_value}")
            filters.append(Users.company == filter_value)
        
        datas = query.filter(*filters).all()
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
    logging.debug(f"[get_connection_summary_agg] period_type: {period_type}, period_value: {period_value}, scope: {scope}, filter_value: {filter_value}")
    
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
        parts = filter_value.split('||', 1)
        if len(parts) == 2:
            company_name, department_name = parts
            filters.append(loginSummaryAgg.company_key == company_name)
            filters.append(loginSummaryAgg.department_key == department_name)
        else:
            department_name = parts[0]
            filters.append(loginSummaryAgg.department_key == department_name)
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

  
        
def get_summary_rows_agg(model, period_type, period_value, scope, group_fields, join_users = True):
    query = db.session.query(*group_fields, func.sum(model.total_duration).label('total'))
    
    if join_users:
        query = query.join(Users, Users.id == model.user_id_key)
        
    query = query.filter(
            model.period_type == period_type,
            model.period_value == period_value,
            model.scope == scope
        ) \
        .group_by(*group_fields)
    
    logging.debug(query.statement.compile(compile_kwargs={"literal_binds": True}))     
    return query.all()

def get_summary_rows_day(model, start_date, end_date, scope, group_fields, join_users=True):
    query = db.session.query(*group_fields, func.sum(model.total_duration).label('total'))
    
    if join_users:
        query = query.join(Users, Users.id == model.user_id_key)

    query = query.filter(
            model.period_value >= start_date,
            model.period_value <= end_date,
            model.scope == scope
        ) \
        .group_by(*group_fields)
    
    logging.debug(query.statement.compile(compile_kwargs={"literal_binds": True}))
    return query.all()

def get_summary_rows_history(model, start_date, end_date, group_fields, join_users=True):
    query = db.session.query(*group_fields, func.sum(model.session_duration).label('total'))
    
    if join_users:
        query = query.join(Users, Users.id == model.user_id)
        
    query = query.filter(
            model.login_time >= start_date,
            model.login_time <= end_date
        ) \
        .group_by(*group_fields)
    
    logging.debug(query.statement.compile(compile_kwargs={"literal_binds": True}))
    return query.all()