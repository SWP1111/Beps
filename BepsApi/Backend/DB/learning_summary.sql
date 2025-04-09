-- 최상위 카테고리 폴더 id 조회
CREATE OR REPLACE FUNCTION get_top_category_folder(fid INT)
RETURNS INT AS $$
WITH RECURSIVE parent_tree AS (
    SELECT folder_id, parent_id
    FROM folders
    WHERE folder_id = fid
    UNION ALL
    SELECT f.folder_id, f.parent_id
    FROM folders f
    JOIN parent_tree pt ON f.folder_id = pt.parent_id
)
SELECT folder_id
FROM parent_tree
WHERE parent_id IN (SELECT folder_id FROM folders WHERE parent_id IS NULL)
LIMIT 1;
$$ LANGUAGE SQL STABLE;

-- folders 테이블에 최상위 카테고리 폴더 id 업데이트
-- UPDATE folders SET top_category_folder_id = get_top_category_folder(folder_id);


CREATE OR REPLACE FUNCTION aggregate_learning_summary_daily(
    p_start_utc TIMESTAMPTZ
) RETURNS VOID AS $$
DECLARE
    v_start_value DATE := (p_start_utc AT TIME ZONE 'Asia/Seoul')::DATE;
BEGIN

    -- 전체 집계
    INSERT INTO learning_summary_day (
        stat_date, scope, folder_id, folder_name, total_duration
    )
    SELECT
        v_start_value, 'all', d.folder_id, d.folder_name,SUM(cvh.stay_duration) AS total_duration
    FROM content_viewing_history_view cvh
    JOIN files f ON f.file_id = cvh.file_id
    JOIN folders fd ON fd.folder_id = f.folder_id
    -- 재귀호출로 최상위 카테고리 폴더 id 조회
    -- JOIN (
    --     SELECT folder_id, folder_name
    --     FROM folders
    --     WHERE parent_id IN (SELECT folder_id FROM folders WHERE parent_id IS NULL)
    -- )d ON get_top_level_folder(fd.folder_id) = d.folder_id
    JOIN folders d ON fd.top_category_folder_id = d.folder_id   -- 최상위 카테고리 폴더 id
    WHERE cvh.start_time >= p_start_utc AND cvh.start_time < p_start_utc + INTERVAL '1 day'
    GROUP BY d.folder_id, d.folder_name
    HAVING SUM(cvh.stay_duration) > INTERVAL '0'
    ON CONFLICT(stat_date, scope, company_key, department_key, user_id_key, folder_key)
    DO UPDATE SET
        total_duration = EXCLUDED.total_duration;

    -- 회사별 집계
    INSERT INTO learning_summary_day (
        stat_date, scope, company_id, company, folder_id, folder_name, total_duration
    )
    SELECT
        v_start_value, 'company', NULL, u.company, d.folder_id, d.folder_name,
        SUM(cvh.stay_duration) AS total_duration
    FROM content_viewing_history_view cvh
    JOIN users u ON u.id = cvh.user_id
    JOIN files f ON f.file_id = cvh.file_id
    JOIN folders fd ON fd.folder_id = f.folder_id
    JOIN folders d ON fd.top_category_folder_id = d.folder_id   -- 최상위 카테고리 폴더 id
    WHERE cvh.start_time >= p_start_utc AND cvh.start_time < p_start_utc + INTERVAL '1 day'
    GROUP BY u.company, d.folder_id, d.folder_name
    HAVING SUM(cvh.stay_duration) > INTERVAL '0'
    ON CONFLICT(stat_date, scope, company_key, department_key, user_id_key, folder_key)
    DO UPDATE SET
        total_duration = EXCLUDED.total_duration;

   
    -- 부서별 집계
    INSERT INTO learning_summary_day (
        stat_date, scope, company_id, company, department_id, department, folder_id, folder_name, total_duration
    )
    SELECT
        v_start_value, 'department', NULL, u.company, NULL, u.department, d.folder_id, d.folder_name,
        SUM(cvh.stay_duration) AS total_duration
    FROM content_viewing_history_view cvh
    JOIN users u ON u.id = cvh.user_id
    JOIN files f ON f.file_id = cvh.file_id
    JOIN folders fd ON fd.folder_id = f.folder_id
    JOIN folders d ON fd.top_category_folder_id = d.folder_id   -- 최상위 카테고리 폴더 id
    WHERE cvh.start_time >= p_start_utc AND cvh.start_time < p_start_utc + INTERVAL '1 day'
    GROUP BY u.company, u.department, d.folder_id, d.folder_name
    HAVING SUM(cvh.stay_duration) > INTERVAL '0'
    ON CONFLICT(stat_date, scope, company_key, department_key, user_id_key, folder_key)
    DO UPDATE SET
        total_duration = EXCLUDED.total_duration;

    -- 사용자별 집계
    INSERT INTO learning_summary_day (
        stat_date, scope, company_id, company, department_id, department, user_id, user_name, folder_id, folder_name, total_duration
    )
    SELECT
        v_start_value, 'user', NULL, u.company, NULL, u.department, u.id, u.name, d.folder_id, d.folder_name,
        SUM(cvh.stay_duration)
    FROM content_viewing_history_view cvh
    JOIN users u ON u.id = cvh.user_id
    JOIN files f ON f.file_id = cvh.file_id
    JOIN folders fd ON fd.folder_id = f.folder_id
    JOIN folders d ON fd.top_category_folder_id = d.folder_id   -- 최상위 카테고리 폴더 id
    WHERE cvh.start_time >= p_start_utc AND cvh.start_time < p_start_utc + INTERVAL '1 day'
    GROUP BY u.company, u.department, u.id, u.name, d.folder_id, d.folder_name
    HAVING SUM(cvh.stay_duration) > INTERVAL '0'
    ON CONFLICT(stat_date, scope, company_key, department_key, user_id_key, folder_key)
    DO UPDATE SET total_duration = EXCLUDED.total_duration;

EXCEPTION
    WHEN OTHERS THEN
        RAISE NOTICE 'Error in aggregate_learning_summary_daily: %', SQLERRM;
        RAISE;  

END;
$$ LANGUAGE plpgsql;



-- SELECT aggregate_learning_summary_daily((DATE_TRUNC('day', '2025-03-13' AT TIME ZONE 'Asia/Seoul') - INTERVAL '1 day') AT TIME ZONE 'Asia/Seoul');


-- top_pages 쿼리
-- SELECT f.file_id, f.file_name, COUNT(*) AS view_count
-- FROM content_viewing_history_archive cvh
-- JOIN files f ON f.file_id = cvh.file_id
-- JOIN users u ON u.id = cvh.user_id
-- WHERE cvh.start_time >= :start_date AND cvh.start_time < :end_date
--   AND (:company IS NULL OR u.company = :company)
--   AND (:department IS NULL OR u.department = :department)
--   AND (:user_id IS NULL OR u.id = :user_id)
-- GROUP BY f.file_id, f.file_name
-- ORDER BY view_count DESC
-- LIMIT 10;


CREATE OR REPLACE FUNCTION aggregate_learning_summary_quarterly(p_year INT, p_quarter INT)
RETURNS VOID AS $$
DECLARE
    v_start DATE;
    v_end DATE;
    v_period_value TEXT := format('%s-Q%s', p_year, p_quarter);
BEGIN
    v_start := make_date(p_year, (p_quarter - 1) * 3 + 1, 1);
    v_end := (v_start + interval '3 months - 1 day')::DATE;

    -- 전체 범위 집계
    INSERT INTO learning_summary_agg (
        period_type, period_value, scope, folder_id, folder_name, total_duration
    )
    SELECT
        'quarter', v_period_value, 'all', folder_id, folder_name, SUM(total_duration)
    FROM learning_summary_day
    WHERE stat_date >= v_start AND stat_date < v_end AND scope = 'all'
    GROUP BY folder_id, folder_name
    HAVING SUM(total_duration) > INTERVAL '0'
    ON CONFLICT (period_value, scope, company_key, department_key, user_id_key, folder_key)
    DO UPDATE SET
        total_duration = EXCLUDED.total_duration;

    -- 회사별 집계
    INSERT INTO learning_summary_agg (
        period_type, period_value, scope, company_id, company, folder_id, folder_name, total_duration
    )
    SELECT
        'quarter', v_period_value, 'company', NULL, company, folder_id, folder_name, SUM(total_duration)
    FROM learning_summary_day
    WHERE stat_date >= v_start AND stat_date < v_end AND scope = 'company'
    GROUP BY company, folder_id, folder_name
    HAVING SUM(total_duration) > INTERVAL '0'
    ON CONFLICT (period_value, scope, company_key, department_key, user_id_key, folder_key)
    DO UPDATE SET
        total_duration = EXCLUDED.total_duration;

    -- 부서별 집계
    INSERT INTO learning_summary_agg (
        period_type, period_value, scope, company_id, company, department_id, department, folder_id, folder_name, total_duration
    )
    SELECT
        'quarter', v_period_value, 'department', NULL, company, NULL, department, folder_id, folder_name, SUM(total_duration)
    FROM learning_summary_day
    WHERE stat_date >= v_start AND stat_date < v_end AND scope = 'department'
    GROUP BY company, department, folder_id, folder_name
    HAVING SUM(total_duration) > INTERVAL '0'
    ON CONFLICT (period_value, scope, company_key, department_key, user_id_key, folder_key)
    DO UPDATE SET
        total_duration = EXCLUDED.total_duration;

    -- 사용자별 집계
    INSERT INTO learning_summary_agg (
        period_type, period_value, scope, company_id, company, department_id, department, user_id, user_name, folder_id, folder_name, total_duration
    )
    SELECT
        'quarter', v_period_value, 'user', NULL, company, NULL, department, user_id, user_name, folder_id, folder_name, SUM(total_duration)
    FROM learning_summary_day
    WHERE stat_date >= v_start AND stat_date < v_end AND scope = 'user'
    GROUP BY company, department, user_id, user_name, folder_id, folder_name
    HAVING SUM(total_duration) > INTERVAL '0'
    ON CONFLICT (period_value, scope, company_key, department_key, user_id_key, folder_key)
    DO UPDATE SET
        total_duration = EXCLUDED.total_duration;

EXCEPTION
    WHEN OTHERS THEN
        RAISE NOTICE 'Error in aggregate_learning_summary_quaterly: %', SQLERRM;
        RAISE; 

END;
$$ LANGUAGE plpgsql;


CREATE OR REPLACE FUNCTION aggregate_learning_summary_halfyearly(p_year INT, p_halfyear INT)
RETURNS VOID AS $$
DECLARE
    v_quarters TEXT[];
    v_period_value TEXT := format('%s-H%s', p_year, p_halfyear);
BEGIN
    v_quarters := CASE WHEN p_halfyear = 1
                        THEN ARRAY[format('%s-Q1', p_year), format('%s-Q2', p_year)]
                        ELSE ARRAY[format('%s-Q3', p_year), format('%s-Q4', p_year)]
                  END;

    -- 전체 범위 집계
    INSERT INTO learning_summary_agg (
        period_type, period_value, scope, folder_id, folder_name, total_duration
    )
    SELECT
        'half', v_period_value, 'all', folder_id, folder_name, SUM(total_duration)
    FROM learning_summary_agg
    WHERE period_type = 'quarter' AND period_value = ANY(v_quarters) AND scope = 'all'
    GROUP BY folder_id, folder_name
    HAVING SUM(total_duration) > INTERVAL '0'
    ON CONFLICT (period_value, scope, company_key, department_key, user_id_key, folder_key)
    DO UPDATE SET
        total_duration = EXCLUDED.total_duration;

    -- 회사별 집계
    INSERT INTO learning_summary_agg (
        period_type, period_value, scope, company_id, company, folder_id, folder_name, total_duration
    )
    SELECT
        'half', v_period_value, 'company', NULL, company, folder_id, folder_name, SUM(total_duration)
    FROM learning_summary_agg
    WHERE period_type = 'quarter' AND period_value = ANY(v_quarters) AND scope = 'company'
    GROUP BY company, folder_id, folder_name
    HAVING SUM(total_duration) > INTERVAL '0'
    ON CONFLICT (period_value, scope, company_key, department_key, user_id_key, folder_key)
    DO UPDATE SET
        total_duration = EXCLUDED.total_duration;

    -- 부서별 집계
    INSERT INTO learning_summary_agg (
        period_type, period_value, scope, company_id, company, department_id, department, folder_id, folder_name, total_duration
    )
    SELECT
        'half', v_period_value, 'department', NULL, company, NULL, department, folder_id, folder_name, SUM(total_duration)
    FROM learning_summary_agg
    WHERE period_type = 'quarter' AND period_value = ANY(v_quarters) AND scope = 'department'
    GROUP BY company, department, folder_id, folder_name
    HAVING SUM(total_duration) > INTERVAL '0'
    ON CONFLICT (period_value, scope, company_key, department_key, user_id_key, folder_key)
    DO UPDATE SET
        total_duration = EXCLUDED.total_duration;

    -- 사용자별 집계
    INSERT INTO learning_summary_agg (
        period_type, period_value, scope, company_id, company, department_id, department, user_id, user_name, folder_id, folder_name, total_duration
    )
    SELECT
        'half', v_period_value, 'user', NULL, company, NULL, department, user_id, user_name, folder_id, folder_name, SUM(total_duration)
    FROM learning_summary_agg
    WHERE period_type = 'quarter' AND period_value = ANY(v_quarters) AND scope = 'user'
    GROUP BY company, department, user_id, user_name, folder_id, folder_name
    HAVING SUM(total_duration) > INTERVAL '0'
    ON CONFLICT (period_value, scope, company_key, department_key, user_id_key, folder_key)
    DO UPDATE SET
        total_duration = EXCLUDED.total_duration;

EXCEPTION
    WHEN OTHERS THEN
        RAISE NOTICE 'Error in aggregate_learning_summary_halfyearly: %', SQLERRM;
        RAISE;  

END;
$$ LANGUAGE plpgsql;


CREATE OR REPLACE FUNCTION aggregate_learning_summary_yearly(p_year INT)
RETURNS VOID AS $$
DECLARE
    v_period_value TEXT := format('%s', p_year);
BEGIN

    INSERT INTO learning_summary_agg (
        period_type, period_value, scope, folder_id, folder_name, total_duration
    )
    SELECT
        'year', v_period_value, 'all', folder_id, folder_name, SUM(total_duration)
    FROM learning_summary_agg
    WHERE period_type = 'half' AND period_value LIKE format('%s-H%%', p_year) AND scope = 'all'
    GROUP BY folder_id, folder_name
    HAVING SUM(total_duration) > INTERVAL '0'
    ON CONFLICT (period_value, scope, company_key, department_key, user_id_key, folder_key)
    DO UPDATE SET
        total_duration = EXCLUDED.total_duration;

    -- 회사별 집계
    INSERT INTO learning_summary_agg (
        period_type, period_value, scope, company_id, company, folder_id, folder_name, total_duration
    )
    SELECT
        'year', v_period_value, 'company', NULL, company, folder_id, folder_name, SUM(total_duration)
    FROM learning_summary_agg
    WHERE period_type = 'half' AND period_value LIKE format('%s-H%%', p_year) AND scope = 'company'
    GROUP BY company, folder_id, folder_name
    HAVING SUM(total_duration) > INTERVAL '0'
    ON CONFLICT (period_value, scope, company_key, department_key, user_id_key, folder_key)
    DO UPDATE SET
        total_duration = EXCLUDED.total_duration;
    
    -- 부서별 집계
    INSERT INTO learning_summary_agg (
        period_type, period_value, scope, company_id, company, department_id, department, folder_id, folder_name, total_duration
    )
    SELECT
        'year', v_period_value, 'department', NULL, company, NULL, department, folder_id, folder_name, SUM(total_duration)
    FROM learning_summary_agg
    WHERE period_type = 'half' AND period_value LIKE format('%s-H%%', p_year) AND scope = 'department'
    GROUP BY company, department, folder_id, folder_name
    HAVING SUM(total_duration) > INTERVAL '0'
    ON CONFLICT (period_value, scope, company_key, department_key, user_id_key, folder_key)
    DO UPDATE SET
        total_duration = EXCLUDED.total_duration;

    -- 사용자별 집계
    INSERT INTO learning_summary_agg (
        period_type, period_value, scope, company_id, company, department_id, department, user_id, user_name, folder_id, folder_name, total_duration
    )
    SELECT
        'year', v_period_value, 'user', NULL, company, NULL, department, user_id, user_name, folder_id, folder_name, SUM(total_duration)
    FROM learning_summary_agg   
    WHERE period_type = 'half' AND period_value LIKE format('%s-H%%', p_year) AND scope = 'user'
    GROUP BY company, department, user_id, user_name, folder_id, folder_name
    HAVING SUM(total_duration) > INTERVAL '0'
    ON CONFLICT (period_value, scope, company_key, department_key, user_id_key, folder_key)
    DO UPDATE SET
        total_duration = EXCLUDED.total_duration;

EXCEPTION
    WHEN OTHERS THEN
        RAISE NOTICE 'Error in aggregate_learning_summary_yearly: %', SQLERRM;
        RAISE; 

END;
$$ LANGUAGE plpgsql;
