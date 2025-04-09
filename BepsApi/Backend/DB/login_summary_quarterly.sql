CREATE OR REPLACE FUNCTION aggregate_quarterly_stats(p_year INT, p_quarter INT)
RETURNS VOID AS $$
DECLARE
    v_start DATE;
    v_end DATE;
    v_period_value TEXT := format('%s-Q%s', p_year, p_quarter);
BEGIN
    v_start := make_date(p_year, (p_quarter - 1) * 3 + 1, 1);
    v_end := (v_start + interval '3 months - 1 day')::DATE;

    -- 1. 전체 범위 집계
    INSERT INTO login_summary_agg (
        period_type, period_value, scope,
        company_key, department_key, user_id_key,
        total_duration, worktime_duration, offhour_duration,
        internal_count, external_count
    )
    SELECT
        'quarter', v_period_value, 'all',
        '','','',
        SUM(total_duration), SUM(worktime_duration), SUM(offhour_duration),
        SUM(internal_count), SUM(external_count)
    FROM login_summary_day
    WHERE period_value::DATE BETWEEN v_start AND v_end AND scope = 'all'
    HAVING COALESCE(SUM(total_duration), '0'::INTERVAL) > '0'::INTERVAL
    ON CONFLICT (period_value, scope, company_key, department_key, user_id_key)
    DO UPDATE SET
        total_duration = EXCLUDED.total_duration,
        worktime_duration = EXCLUDED.worktime_duration,
        offhour_duration = EXCLUDED.offhour_duration,
        internal_count = EXCLUDED.internal_count,
        external_count = EXCLUDED.external_count;

    -- 2. 회사별
    INSERT INTO login_summary_agg (
        period_type, period_value, scope,
        company_key, department_key, user_id_key,
        company, total_duration, worktime_duration, offhour_duration,
        internal_count, external_count
    )
    SELECT
        'quarter', v_period_value, 'company',
        company_key, '', '',
        company,
        SUM(total_duration), SUM(worktime_duration), SUM(offhour_duration),
        SUM(internal_count), SUM(external_count)
    FROM login_summary_day
    WHERE period_value::DATE BETWEEN v_start AND v_end AND scope = 'company'
    GROUP BY company
    HAVING COALESCE(SUM(total_duration), '0'::INTERVAL) > '0'::INTERVAL
    ON CONFLICT (period_value, scope, company_key, department_key, user_id_key)
    DO UPDATE SET
        total_duration = EXCLUDED.total_duration,
        worktime_duration = EXCLUDED.worktime_duration,
        offhour_duration = EXCLUDED.offhour_duration,
        internal_count = EXCLUDED.internal_count,
        external_count = EXCLUDED.external_count;

    -- 3. 부서별
    INSERT INTO login_summary_agg (
        period_type, period_value, scope,
        company, department,
        company_key, department_key, user_id_key,
        total_duration, worktime_duration, offhour_duration,
        internal_count, external_count
    )
    SELECT
        'quarter', v_period_value, 'department',
        company, department,
        company_key, department_key, '',
        SUM(total_duration), SUM(worktime_duration), SUM(offhour_duration),
        SUM(internal_count), SUM(external_count)
    FROM login_summary_day
    WHERE period_value::DATE BETWEEN v_start AND v_end AND scope = 'department'
    GROUP BY company, department
    HAVING COALESCE(SUM(total_duration), '0'::INTERVAL) > '0'::INTERVAL
    ON CONFLICT (period_value, scope, company_key, department_key, user_id_key)
    DO UPDATE SET
        total_duration = EXCLUDED.total_duration,
        worktime_duration = EXCLUDED.worktime_duration,
        offhour_duration = EXCLUDED.offhour_duration,
        internal_count = EXCLUDED.internal_count,
        external_count = EXCLUDED.external_count;

    -- 4. 사용자별
    INSERT INTO login_summary_agg (
        period_type, period_value, scope,
        company, department, user_id, user_name,
        company_key, department_key, user_id_key,
        total_duration, worktime_duration, offhour_duration,
        internal_count, external_count
    )
    SELECT
        'quarter', v_period_value, 'user',
        company, department, user_id, user_name,
        company_key, department_key, user_id_key,
        SUM(total_duration), SUM(worktime_duration), SUM(offhour_duration),
        SUM(internal_count), SUM(external_count)
    FROM login_summary_day
    WHERE period_value::DATE BETWEEN v_start AND v_end AND scope = 'user'
    GROUP BY company, department, user_id, user_name
    HAVING COALESCE(SUM(total_duration), '0'::INTERVAL) > '0'::INTERVAL
    ON CONFLICT (period_value, scope, company_key, department_key, user_id_key)
    DO UPDATE SET
        total_duration = EXCLUDED.total_duration,
        worktime_duration = EXCLUDED.worktime_duration,
        offhour_duration = EXCLUDED.offhour_duration,
        internal_count = EXCLUDED.internal_count,
        external_count = EXCLUDED.external_count;

END;
$$ LANGUAGE plpgsql;


-- 함수 등록
--  sudo -u postgres psql -d beps -f Backend/DB/login_summary_quarterly.sql

-- 분기별 집계 (KST: 1월 2일, 4월 2일, 7월 2일, 10월 2일 새벽 3시)
-- SELECT cron.schedule(
--   'quarterly_login_summary',
--   '0 18 1 1,4,7,10 *',
--   $$SELECT aggregate_quarterly_stats(EXTRACT(YEAR FROM current_date - interval '1 month')::int,
--                                      CEIL(EXTRACT(MONTH FROM current_date - interval '1 month') / 3)::int);$$
-- );
