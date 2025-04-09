CREATE OR REPLACE FUNCTION aggregate_halfyearly_stats(p_year INT, p_half INT)
RETURNS VOID AS $$
DECLARE
    v_quarters TEXT[];
    v_period_value TEXT := format('%s-H%s', p_year, p_half);
BEGIN
    -- 반기: Q1+Q2 또는 Q3+Q4
    v_quarters := CASE WHEN p_half = 1
                       THEN ARRAY[format('%s-Q1', p_year), format('%s-Q2', p_year)]
                       ELSE ARRAY[format('%s-Q3', p_year), format('%s-Q4', p_year)]
                 END;

    -- 1. 전체 범위 집계
    INSERT INTO login_summary_agg (
        period_type, period_value, scope,
        company_key, department_key, user_id_key,
        total_duration, worktime_duration, offhour_duration,
        internal_count, external_count
    )
    SELECT
        'half', v_period_value, 'all',
        '', '', '',
        SUM(total_duration), SUM(worktime_duration), SUM(offhour_duration),
        SUM(internal_count), SUM(external_count)
    FROM login_summary_agg
    WHERE period_type = 'quarter' AND period_value = ANY(v_quarters) AND scope = 'all'
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
        'half', v_period_value, 'company', company,
         company_key, '', '',
        SUM(total_duration), SUM(worktime_duration), SUM(offhour_duration),
        SUM(internal_count), SUM(external_count)
    FROM login_summary_agg
    WHERE period_type = 'quarter' AND period_value = ANY(v_quarters) AND scope = 'company'
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
        'half', v_period_value, 'department', company, department,
        company_key, department_key, '',
        SUM(total_duration), SUM(worktime_duration), SUM(offhour_duration),
        SUM(internal_count), SUM(external_count)
    FROM login_summary_agg
    WHERE period_type = 'quarter' AND period_value = ANY(v_quarters) AND scope = 'department'
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
        'half', v_period_value, 'user', company, department, user_id, user_name,
        company_key, department_key, user_id_key,
        SUM(total_duration), SUM(worktime_duration), SUM(offhour_duration),
        SUM(internal_count), SUM(external_count)
    FROM login_summary_agg
    WHERE period_type = 'quarter' AND period_value = ANY(v_quarters) AND scope = 'user'
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


-- 반기별 집계 (KST: 1월 3일, 7월 3일 새벽 3시)
-- SELECT cron.schedule(
--   'halfyearly_login_summary',
--   '0 18 2 1,7 *',
--   $$SELECT aggregate_halfyearly_stats(EXTRACT(YEAR FROM current_date - interval '1 month')::int,
--                                       CASE WHEN EXTRACT(MONTH FROM current_date - interval '1 month') < 7 THEN 1 ELSE 2 END);$$
-- );
