CREATE OR REPLACE FUNCTION aggregate_yearly_stats(p_year INT)
RETURNS VOID AS $$
DECLARE
    v_period_value TEXT := p_year::TEXT;
BEGIN
    -- 1. 전체 집계
    INSERT INTO login_summary_agg (
        period_type, period_value, scope,
        company_key, department_key, user_id_key,
        total_duration, worktime_duration, offhour_duration,
        internal_count, external_count
    )
    SELECT
        'year', v_period_value, 'all',
        '', '', '',
        SUM(total_duration), SUM(worktime_duration), SUM(offhour_duration),
        SUM(internal_count), SUM(external_count)
    FROM login_summary_agg
    WHERE period_type = 'half' AND period_value LIKE format('%s-H%%', p_year) AND scope = 'all'
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
        period_type, period_value, scope, company,
        company_key, department_key, user_id_key,
        total_duration, worktime_duration, offhour_duration,
        internal_count, external_count
    )
    SELECT
        'year', v_period_value, 'company', company,
        company_key, '', '',
        SUM(total_duration), SUM(worktime_duration), SUM(offhour_duration),
        SUM(internal_count), SUM(external_count)
    FROM login_summary_agg
    WHERE period_type = 'half' AND period_value LIKE format('%s-H%%', p_year) AND scope = 'company'
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
        period_type, period_value, scope, company, department,
        company_key, department_key, user_id_key,
        total_duration, worktime_duration, offhour_duration,
        internal_count, external_count
    )
    SELECT
        'year', v_period_value, 'department', company, department,
        company_key, department_key, '',
        SUM(total_duration), SUM(worktime_duration), SUM(offhour_duration),
        SUM(internal_count), SUM(external_count)
    FROM login_summary_agg
    WHERE period_type = 'half' AND period_value LIKE format('%s-H%%', p_year) AND scope = 'department'
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
        period_type, period_value, scope, company, department, user_id, user_name,
        company_key, department_key, user_id_key,
        total_duration, worktime_duration, offhour_duration,
        internal_count, external_count
    )
    SELECT
        'year', v_period_value, 'user', company, department, user_id, user_name,
        company_key, department_key, user_id_key,
        SUM(total_duration), SUM(worktime_duration), SUM(offhour_duration),
        SUM(internal_count), SUM(external_count)
    FROM login_summary_agg
    WHERE period_type = 'half' AND period_value LIKE format('%s-H%%', p_year) AND scope = 'user'
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

-- 연간 집계 (KST: 1월 4일 새벽 3시)
-- SELECT cron.schedule(
--   'yearly_login_summary',
--   '0 18 3 1 *',
--   $$SELECT aggregate_yearly_stats(EXTRACT(YEAR FROM current_date - interval '1 day')::int);$$
-- );