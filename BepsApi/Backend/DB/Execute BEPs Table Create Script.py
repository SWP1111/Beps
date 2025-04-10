# psycopg2 설치가 우선되어야 함
# 터미널에서 아래 명령어 실행
# pip install psycopg2

import psycopg2
from psycopg2 import sql

# PostgreSQL 데이터베이스에 연결
connection = psycopg2.connect(
    host="172.16.10.191",   # 데이터베이스 호스트
    port=15432,             # 데이터베이스 포트
    database="postgres",    # 데이터베이스 이름
    user="postgres",    # 데이터베이스 사용자 이름
    password="postgres" # 데이터베이스 사용자 비밀번호
)

#autocommit 활성화
connection.autocommit = True

# 커서 생성
cursor = connection.cursor()

try:
    # 데이터베이스 생성
    cursor.execute("""
        CREATE DATABASE beps
        WITH 
        OWNER = postgres
        ENCODING = 'UTF8'
        LC_COLLATE = 'en_US.UTF-8'
        LC_CTYPE = 'en_US.UTF-8'
        LOCALE_PROVIDER = 'libc'
        TABLESPACE = pg_default
        CONNECTION LIMIT = -1
        IS_TEMPLATE = False;
    """)
except Exception as e:
    print(f"Error: {e}")
finally:
    cursor.close()
    connection.close()

# beps 데이터베이스에 연결
connection = psycopg2.connect(
    host="172.16.10.191",   # 데이터베이스 호스트
    port=15432,
    database="beps",    # 데이터베이스 이름
    user="postgres",    # 데이터베이스 사용자 이름
    password="postgres" # 데이터베이스 사용자 비밀번호
)

# 커서 생성
cursor = connection.cursor()

try:

    #region contents 테이블  - 제거
    contents_queries = """
        create table public.contents (
        content_id integer not null,
        content_name text not null,
        is_active boolean,
        description text,
        time_stamp bigint,
        constraint contents_pkey primary key (content_id),
        constraint content_name unique (content_name)
        );
        """
    
    # contents_content_id_seq 시퀀스 생성 쿼리
    contents_sequence = [
        """
        create sequence public.contents_content_id_seq
        as integer
        start with 1
        increment by 1
        no minvalue
        no maxvalue
        cache 1;
        """,
        """
        alter sequence public.contents_content_id_seq owned by public.contents.content_id;
        """,
        """
        alter table only public.contents alter column content_id set default nextval('public.contents_content_id_seq'::regclass);
        """,
        # """
        # select pg_catalog.setval('public.contents_content_id_seq', 1, false);
        # """,
    ]

    #endregion

    #region content_access_groups 테이블
    content_access_groups_queries =  """
        CREATE TABLE IF NOT EXISTS public.content_access_groups (
            access_group_id integer NOT NULL,       -- 접근 그룹 ID                   
            group_name text,                        -- 그룹 이름
            time_stamp bigint,
            CONSTRAINT content_access_groups_pkey PRIMARY KEY (access_group_id)
        );
        """
    
    # ContentAccessGroups_AccessGroupId_seq 시퀀스 생성 쿼리
    content_access_groups_sequence = ["""
        CREATE SEQUENCE public.content_access_groups_id_seq
        AS integer
        START WITH 1
        INCREMENT BY 1
        NO MINVALUE
        NO MAXVALUE
        CACHE 1;
        """,
        """
        ALTER SEQUENCE public.content_access_groups_id_seq OWNER TO postgres;
        """,
        """
        ALTER SEQUENCE public.content_access_groups_id_seq OWNED BY public.content_access_groups.access_group_id;
        """,
        """
        ALTER TABLE ONLY public.content_access_groups ALTER COLUMN access_group_id SET DEFAULT nextval('public.content_access_groups_id_seq'::regclass);
        """,
        # """
        # SELECT pg_catalog.setval('public.content_access_groups_id_seq', 1, false);
        # """,
    ]

    #endregion
    
    #region folders 테이블
    folders_queries = [
        """
        CREATE TABLE public.folders (
            folder_id SERIAL NOT NULL PRIMARY KEY,                                              -- 폴더 ID
            parent_id integer NULL REFERENCES folders(folder_id) ON DELETE CASCADE,             -- 상위 폴더 ID
            folder_name text NOT NULL,                                                          -- 폴더 이름
            depth smallint NOT NULL,                                                            -- 폴더 깊이    
            is_visible boolean DEFAULT TRUE,                                                    -- 폴더 표시 여부
            folder_type varchar(20) DEFAULT 'normal' CHECK (folder_type IN ('normal', 'meta')), -- 폴더 타입
            is_deleted boolean DEFAULT FALSE,
            create_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP,                                      
            update_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
            top_category_folder_id INTEGER,                                                         -- 카테고리 폴더 ID
            time_stamp bigint
            );           
        """,
        """
        CREATE INDEX icx_folders_parent_id ON folders(parent_id);
        """
    ]
    #endregion
    
    #region files 테이블
    files_queries = [
        """
        CREATE TABLE public.files (
            file_id SERIAL NOT NULL,                                            -- 파일 ID
            folder_id integer REFERENCES folders(folder_id) ON DELETE CASCADE,  -- 폴더 ID
            file_name text NOT NULL,                                            -- 파일 이름
            file_type varchar(10) NOT NULL,                                     -- 파일 타입(확장자)
            file_size bigint NOT NULL,                                          -- 파일 크기
            file_path text,                                                     -- 파일 경로
            create_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
            update_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
            time_stamp bigint,
            is_deleted boolean DEFAULT FALSE,
            CONSTRAINT files_pkey PRIMARY KEY (file_id)
        );
        """,
        """
        CREATE INDEX icx_files_folder_id ON files(folder_id);
        """
    ]
    #endregion

    #region filedata 테이블
    filedata_queries = """
        CREATE TABLE public.filedata (
            file_id integer NOT NULL REFERENCES files(file_id) ON DELETE CASCADE,   -- 파일 ID
            data bytea NOT NULL,                                                    -- 파일 데이터
            time_stamp bigint,
            CONSTRAINT filedata_pkey PRIMARY KEY (file_id)
        );
    """
    #endregion

    #region metadata 테이블
    metadata_queries = [
        """
        CREATE TABLE public.metadata (
            metadata_id SERIAL NOT NULL,                                            -- 메타데이터 ID        
            metadata_type varchar(10) NOT NULL,                                     -- 메타데이터 타입(json, xml)    
            metadata_purpose VARCHAR(50) NOT NULL,                                  -- 메타데이터 용도(detail, resources)
            data jsonb NOT NULL,                                                    -- 메타데이터
            file_id integer NOT NULL REFERENCES files(file_id) ON DELETE CASCADE,   -- 파일 ID
            time_stamp bigint,
            CONSTRAINT metadata_pkey PRIMARY KEY (metadata_id)
        );
        """,
        """
        CREATE INDEX icx_metadata_metadata_name ON metadata(file_id);
        """     
    ]

    #endregion

    #region access_group_contents 테이블
    access_group_contents_queries ="""
        CREATE TABLE IF NOT EXISTS public.access_group_contents (
            access_group_id integer NOT NULL,
            folder_id integer NOT NULL,
            time_stamp bigint,
            CONSTRAINT access_group_contents_pkey PRIMARY KEY (access_group_id, folder_id),
            CONSTRAINT access_group_id FOREIGN KEY (access_group_id) REFERENCES public.content_access_groups(access_group_id) ON DELETE CASCADE,
            CONSTRAINT folder_id FOREIGN KEY (folder_id) REFERENCES public.folders(folder_id) ON DELETE CASCADE
        );
        """
    #endregion

    #region roles 테이블
    roles_queries = """
        CREATE TABLE public.roles (
        role_id integer NOT NULL,
        role_name text NOT NULL,
        time_stamp bigint,
        CONSTRAINT roles_pkey PRIMARY KEY (role_id)
        );  
        """

    # Roles_RoleId_seq 시퀀스 생성 쿼리
    roles_sequence = [
        """
        CREATE SEQUENCE public.roles_role_id_seq
            AS integer
            START WITH 1
            INCREMENT BY 1
            NO MINVALUE
            NO MAXVALUE
            CACHE 1;
        """,
        """
        ALTER SEQUENCE public.roles_role_id_seq OWNED BY public.roles.role_id;
        """,
        """
        ALTER TABLE ONLY public.roles ALTER COLUMN role_id SET DEFAULT nextval('public.roles_role_id_seq'::regclass);
        """,
        # """
        # SELECT pg_catalog.setval('public.roles_role_id_seq', 1, false);
        # """
    ]

    #endregion

    #region users 테이블
    users_queries =  """
        CREATE TABLE public.users (
        id text NOT NULL,
        password text NOT NULL,  
        company text,
        department text,
        position text,
        name text,
        access_group_id integer,   
        role_id integer,
        time_stamp bigint,
        logout_time timestamp with time zone,
        is_deleted boolean DEFAULT FALSE,
        login_time timestamp with time zone,
        CONSTRAINT users_pkey PRIMARY KEY (id),
        CONSTRAINT access_group_id FOREIGN KEY (access_group_id) REFERENCES public.content_access_groups(access_group_id) ON DELETE SET NULL,
        CONSTRAINT role_id FOREIGN KEY (role_id) REFERENCES public.roles(role_id) ON DELETE SET NULL NOT VALID 
        );
        """
    #endregion

    #region login_history 테이블
    
    login_history_queries = [
        """
        CREATE TABLE public.login_history (
            id SERIAL NOT NULL PRIMARY KEY,                                         -- 로그인 기록 ID
            user_id text NOT NULL,                                                  -- 사용자 ID
            ip_address text NOT NULL,                                               -- IP 주소
            login_time timestamp with time zone NOT NULL,                           -- 로그인 시간
            logout_time timestamp with time zone,                                   -- 로그아웃 시간
            session_duration interval,                                              -- 세션 지속 시간
            time_stamp bigint,
            CONSTRAINT login_history_pkey PRIMARY KEY (id)
        );
        """,
        """
        CREATE TABLE public.login_history_archive (
            id integer NOT NULL,                                                   -- 로그인 기록 ID
            user_id text NOT NULL,                                                -- 사용자 ID
            ip_address text NOT NULL,                                             -- IP 주소
            login_time timestamp with time zone NOT NULL,                         -- 로그인 시간
            logout_time timestamp with time zone,                                 -- 로그아웃 시간
            session_duration interval,                                            -- 세션 지속 시간
            time_stamp bigint
        ) PARTITION BY RANGE (login_time);
        """
    ]
    
    calculate_session_duration_queries = [
        """
        CREATE OR REPLACE FUNCTION public.calculate_session_duration()
        RETURNS trigger
        LANGUAGE plpgsql
        AS $$
        BEGIN
            IF NEW.logout_time IS NOT NULL THEN
                NEW.session_duration = NEW.logout_time - NEW.login_time;
            END IF;
            RETURN NEW;
        END;
        $$;
        """,
        """
        CREATE TRIGGER set_session_duration BEFORE INSERT OR UPDATE ON public.login_history FOR EACH ROW EXECUTE FUNCTION public.calculate_session_duration();
        """
    ]
    
    #endregion
    
    #region content_viewing_history 테이블
    content_viewing_history_queries = [
        """
        CREATE TABLE public.content_viewing_history (
            id SERIAL NOT NULL,
            user_id text,                                   -- 사용자 ID
            file_id integer,                                -- 컨텐츠(파일) ID
            start_time timestamp with time zone NOT NULL,   -- 시작 시간
            end_time timestamp with time zone,              -- 종료 시간
            stay_duration interval,                         -- 체류 시간
            ip_address text NOT NULL,                       -- IP 주소
            time_stamp bigint,
            CONSTRAINT content_viewing_history_pkey PRIMARY KEY (id)
        );
        """,
        """
        CREATE INDEX idx_cvh_start_time ON public.content_viewing_history (start_time);
        """,
        """
        CREATE INDEX idx_cvh_user_file ON public.content_viewing_history (user_id, file_id);
        """
    ]
    
    content_viewing_history_archive_queries = """
        CREATE TABLE public.content_viewing_history_archive (
            id integer NOT NULL,
            user_id text,                                   -- 사용자 ID
            file_id integer,                                -- 컨텐츠(파일) ID
            start_time timestamp with time zone NOT NULL,   -- 시작 시간
            end_time timestamp with time zone,              -- 종료 시간
            stay_duration interval,                         -- 체류 시간
            ip_address text NOT NULL,                       -- IP 주소
            time_stamp bigint
        ) PARTITION BY RANGE (start_time);
    """
    
    content_viewing_history_view_queries = """
        CREATE OR REPLACE VIEW public.content_viewing_history_view AS
        SELECT
            id,
            user_id,
            file_id,
            start_time,
            end_time,
            stay_duration,
            ip_address,
            time_stamp::bigint
        FROM public.content_viewing_history
        UNION ALL
        SELECT
            id,
            user_id,
            file_id,
            start_time,
            end_time,
            stay_duration,
            ip_address,
            time_stamp::bigint
        FROM public.content_viewing_history_archive;
    """
    
    #endregion

    #region Timestamp 업데이트 트리거
    timestamp_update_queries = [     
        """ 
        CREATE FUNCTION public.update_timestamp() RETURNS trigger
            LANGUAGE plpgsql
            AS $$BEGIN
            NEW.time_stamp := EXTRACT(EPOCH FROM NOW() AT TIME ZONE 'UTC');
            RETURN NEW;
        END;$$;
        """,
        """
        CREATE TRIGGER set_timestamp_users BEFORE INSERT OR UPDATE ON public.users FOR EACH ROW EXECUTE FUNCTION public.update_timestamp();
        """,
        """
        CREATE TRIGGER set_timestamp_accessgroupcontents BEFORE INSERT OR UPDATE ON public.access_group_contents FOR EACH ROW EXECUTE FUNCTION public.update_timestamp();
        """,
         """
        CREATE TRIGGER set_timestamp_contentaccessgroups BEFORE INSERT OR UPDATE ON public.content_access_groups FOR EACH ROW EXECUTE FUNCTION public.update_timestamp();
        """,
        # """
        # CREATE TRIGGER set_timestamp_contents BEFORE INSERT OR UPDATE ON public.contents FOR EACH ROW EXECUTE FUNCTION public.update_timestamp();
        # """,
        """
        CREATE TRIGGER set_timestamp_roles BEFORE INSERT OR UPDATE ON public.roles FOR EACH ROW EXECUTE FUNCTION public.update_timestamp();
        """,
        """
        CREATE TRIGGER set_timestamp_folders BEFORE INSERT OR UPDATE ON public.folders FOR EACH ROW EXECUTE FUNCTION public.update_timestamp();
        """,
        """
        CREATE TRIGGER set_timestamp_files BEFORE INSERT OR UPDATE ON public.files FOR EACH ROW EXECUTE FUNCTION public.update_timestamp();
        """,
        """
        CREATE TRIGGER set_timestamp_metadata BEFORE INSERT OR UPDATE ON public.metadata FOR EACH ROW EXECUTE FUNCTION public.update_timestamp();
        """,
        """
        CREATE TRIGGER set_timestamp_filedata BEFORE INSERT OR UPDATE ON public.filedata FOR EACH ROW EXECUTE FUNCTION public.update_timestamp();
        """,
        """
        CREATE TRIGGER set_timestamp_content_viewing_history BEFORE INSERT OR UPDATE ON public.content_viewing_history FOR EACH ROW EXECUTE FUNCTION public.update_timestamp();
        """,
        """
        CREATE TRIGGER set_timestamp_login_history BEFORE INSERT OR UPDATE ON public.login_history FOR EACH ROW EXECUTE FUNCTION public.update_timestamp();
        """    
    ]
    #endregion
    
    #region login_summary 테이블(로그인 통계 테이블)
    login_summary_queries = [
        """
        CREATE TABLE login_summary_day (
            period_value DATE NOT NULL,         -- '2024-03-28' 등
            scope TEXT NOT NULL CHECK (scope IN ('all','company','department','user')),                -- 'all(전체)', 'company(회사)', 'department(팀)', 'user(개인)'
            company_id INTEGER,
            company TEXT,                       -- 회사명 (scope가 회사인 경우)
            department_id INTEGER,
            department TEXT,               -- 부서명 (scope가 특정 부서에 해당하는 경우)
            user_id TEXT,                       -- scope가 개인인 경우
            user_name TEXT,                         -- 사용자명 (scope가 개인인 경우)
            total_duration INTERVAL NOT NULL DEFAULT '0',            -- 총 접속 시간
            worktime_duration INTERVAL NOT NULL DEFAULT '0',         -- 근무 시간 내 접속
            offhour_duration INTERVAL NOT NULL DEFAULT '0',          -- 근무 시간 외 접속
            internal_count INT NOT NULL DEFAULT 0,                 -- 사내 접속 횟수
            external_count INT NOT NULL DEFAULT 0,                 -- 사외 접속 횟수
            
            -- 가상 컬럼 생성(company, department, user_id에 대한 대체값)
            company_key TEXT GENERATED ALWAYS AS (COALESCE(company, '')) STORED,         -- company_id가 주어지면  COALESCE(company_id, -1)로 대체. -1은 NULL을 대체하기 위한 값으로 실제 칼럼에 사용되지 않는 값.
            department_key TEXT GENERATED ALWAYS AS (COALESCE(department, '')) STORED,   -- department_id가 주어지면 COALESCE(department_id, -1)로 대체. -1은 NULL을 대체하기 위한 값으로 실제 칼럼에 사용되지 않는 값.
            user_id_key TEXT GENERATED ALWAYS AS (COALESCE(user_id, '')) STORED,

            CONSTRAINT login_summary_day_pkey PRIMARY KEY (  -- 기본키 제약 조건
                period_value, 
                scope, 
                company_key,    
                department_key,  
                user_id_key
            ),
            
            CONSTRAINT chk_scope_columns CHECK (                                                                                                         -- CHECK 제약 조건
                -- 만약 company_id, department_id가 주어진다면 그걸로 대체체
                (scope = 'all' AND company IS NULL AND department IS NULL AND user_id IS NULL) OR                   -- scope가 'all'인 경우 모든 컬럼이 NULL이어야 함
                (scope = 'company' AND company IS NOT NULL AND department IS NULL AND user_id IS NULL) OR           -- scope가 'company'인 경우 company 컬럼만 NOT NULL이어야 함
                (scope = 'department' AND company IS NOT NULL AND department IS NOT NULL AND user_id IS NULL) OR    -- scope가 'department'인 경우 company, department 컬럼만 NOT NULL이어야 함
                (scope = 'user' AND company IS NOT NULL AND department IS NOT NULL AND user_id IS NOT NULL)         -- scope가 'user'인 경우 company, department, user_id 컬럼 NOT NULL이어야 함    
            )
        ) PARTITION BY RANGE (period_value);
        """,      
        """
        CREATE INDEX login_summary_day_unique_user_idx ON login_summary_day (period_value, user_id) WHERE scope = 'user'; -- 조회 시 칼럼 순서 동일해야 함
        """,
        """
        CREATE INDEX login_summary_day_unique_department_idx ON login_summary_day (period_value, company, department) WHERE scope = 'department'; -- department_id가 주어지면 대체하고 company는 제거해도 될 듯
        """,
        """
        CREATE INDEX login_summary_day_unique_company_idx ON login_summary_day (period_value, company) WHERE scope = 'company';
        """,
        """
        CREATE INDEX login_summary_day_unique_all_idx ON login_summary_day (period_value) WHERE scope = 'all';
        """,
        """
         CREATE TABLE login_summary_agg (
            period_type TEXT NOT NULL,          -- 'year', 'half', 'quarter'
            period_value TEXT NOT NULL,         -- '2024', '2024H1', '2024Q3' 등
            scope TEXT NOT NULL CHECK (scope IN ('all','company','department','user')),     -- 'all(전체)', 'company(회사)', 'department(팀)', 'user(개인)'
            company_id INTEGER,
            company TEXT,                       -- 회사명 (scope가 회사인 경우)
            department_id INTEGER,
            department TEXT,               -- 부서명 (scope가 특정 부서에 해당하는 경우)
            user_id TEXT,                       -- scope가 개인인 경우
            user_name TEXT,                         -- 사용자명 (scope가 개인인 경우)
            total_duration INTERVAL NOT NULL DEFAULT '0',            -- 총 접속 시간
            worktime_duration INTERVAL NOT NULL DEFAULT '0',         -- 근무 시간 내 접속
            offhour_duration INTERVAL NOT NULL DEFAULT '0',          -- 근무 시간 외 접속
            internal_count INT NOT NULL DEFAULT 0,                 -- 사내 접속 횟수
            external_count INT NOT NULL DEFAULT 0,                 -- 사외 접속 횟수   
            
            -- 가상 컬럼 생성(company, department, user_id에 대한 대체값)
            company_key TEXT GENERATED ALWAYS AS (COALESCE(company, '')) STORED,         -- company_id가 주어지면  COALESCE(company_id, -1)로 대체. -1은 NULL을 대체하기 위한 값으로 실제 칼럼에 사용되지 않는 값.
            department_key TEXT GENERATED ALWAYS AS (COALESCE(department, '')) STORED,   -- department_id가 주어지면 COALESCE(department_id, -1)로 대체. -1은 NULL을 대체하기 위한 값으로 실제 칼럼에 사용되지 않는 값.
            user_id_key TEXT GENERATED ALWAYS AS (COALESCE(user_id, '')) STORED,
            
            CONSTRAINT login_summary_agg_pkey PRIMARY KEY (  -- 기본키 제약 조건
                period_type,
                period_value, 
                scope, 
                company_key ,   
                department_key ,
                user_id_key
            ),
            
            CONSTRAINT chk_scope_columns CHECK (                                                                                                         -- CHECK 제약 조건
                -- 만약 company_id, department_id가 주어진다면 그걸로 대체체
                (scope = 'all' AND company IS NULL AND department IS NULL AND user_id IS NULL) OR                   -- scope가 'all'인 경우 모든 컬럼이 NULL이어야 함
                (scope = 'company' AND company IS NOT NULL AND department IS NULL AND user_id IS NULL) OR           -- scope가 'company'인 경우 company 컬럼만 NOT NULL이어야 함
                (scope = 'department' AND company IS NOT NULL AND department IS NOT NULL AND user_id IS NULL) OR    -- scope가 'department'인 경우 company, department 컬럼만 NOT NULL이어야 함
                (scope = 'user' AND company IS NOT NULL AND department IS NOT NULL AND user_id IS NOT NULL)         -- scope가 'user'인 경우 company, department, user_id 컬럼 NOT NULL이어야 함      
            )                    
        );
        """,
        """
        CREATE INDEX login_summary_agg_unique_user_idx ON login_summary_agg (period_type, period_value, user_id) WHERE scope = 'user';
        """,
        """
        CREATE INDEX login_summary_agg_unique_department_idx ON login_summary_agg (period_type, period_value, company, department) WHERE scope = 'department';
        """,
        """
        CREATE INDEX login_summary_agg_unique_company_idx ON login_summary_agg (period_type, period_value, company) WHERE scope = 'company';
        """,
        """
        CREATE INDEX login_summary_agg_unique_all_idx ON login_summary_agg (period_type, period_value) WHERE scope = 'all';
        """      
    ]
    #endregion
    
    #region leaning_summary 테이블(학습 통계 테이블)
    learning_summary_queries = [
    """
    CREATE TABLE learning_summary_day (
        stat_date  DATE NOT NULL,         -- '2024-03-28' 등
        scope TEXT NOT NULL CHECK (scope IN ('all','company','department','user')),                -- 'all(전체)', 'company(회사)', 'department(팀)', 'user(개인)'
        company_id INTEGER,
        company TEXT,                       -- 회사명 (scope가 회사인 경우)
        department_id INTEGER,
        department TEXT,               -- 부서명 (scope가 특정 부서에 해당하는 경우)
        user_id TEXT,                       -- scope가 개인인 경우
        user_name TEXT,                         -- 사용자명 (scope가 개인인 경우)
        folder_id INTEGER,                  -- 폴더 ID
        folder_name TEXT,                -- 폴더 이름
        total_duration INTERVAL NOT NULL DEFAULT '0',            -- 총 접속 시간
              
        --가상 키(NULL 대체용)
        company_key TEXT GENERATED ALWAYS AS (COALESCE(company, '')) STORED,         -- company_id가 주어지면  COALESCE(company_id, -1)로 대체. -1은 NULL을 대체하기 위한 값으로 실제 칼럼에 사용되지 않는 값.
        department_key TEXT GENERATED ALWAYS AS (COALESCE(department, '')) STORED,   -- department_id가 주어지면 COALESCE(department_id, -1)로 대체. -1은 NULL을 대체하기 위한 값으로 실제 칼럼에 사용되지 않는 값.
        user_id_key TEXT GENERATED ALWAYS AS (COALESCE(user_id, '')) STORED,
        folder_key TEXT GENERATED ALWAYS AS (COALESCE(folder_id, '-1')) STORED,
        
        --제약 조건
        CONSTRAINT pk_learning_summary_day PRIMARY KEY (stat_date , scope, company_key, department_key, user_id_key, folder_key)
    ) PARTITION BY RANGE (stat_date);
    """,
    """
    CREATE INDEX learning_summary_day_user_idx ON learning_summary_day (stat_date, user_id) WHERE scope = 'user'; -- 조회 시 칼럼 순서 동일해야 함
    """,
    """
    CREATE INDEX learning_summary_day_company_idx ON learning_summary_day (stat_date, company) WHERE scope = 'company';
    """,
    """
    CREATE INDEX learning_summary_day_department_idx ON learning_summary_day (stat_date, company, department) WHERE scope = 'department'; -- department_id가 주어지면 대체하고 company는 제거해도 될 듯
    """,
    """
    CREATE INDEX learning_summary_day_all_idx ON learning_summary_day (stat_date) WHERE scope = 'all';
    """,
    """
    CREATE TABLE learning_summary_agg (
        period_type TEXT NOT NULL,          -- 'year', 'half', 'quarter'
        period_value TEXT NOT NULL,         -- '2024', '2024H1', '2024Q3' 등
        scope TEXT NOT NULL CHECK (scope IN ('all','company','department','user')),                -- 'all(전체)', 'company(회사)', 'department(팀)', 'user(개인)'
        company_id INTEGER,
        company TEXT,                       -- 회사명 (scope가 회사인 경우)
        department_id INTEGER,
        department TEXT,               -- 부서명 (scope가 특정 부서에 해당하는 경우)
        user_id TEXT,                       -- scope가 개인인 경우
        user_name TEXT,                         -- 사용자명 (scope가 개인인 경우)
        folder_id INTEGER,                  -- 폴더 ID
        folder_name TEXT,                -- 폴더 이름
        total_duration INTERVAL NOT NULL DEFAULT '0',            -- 총 접속 시간
                         
        --가상 키(NULL 대체용)
        company_key TEXT GENERATED ALWAYS AS (COALESCE(company, '')) STORED,         -- company_id가 주어지면  COALESCE(company_id, -1)로 대체. -1은 NULL을 대체하기 위한 값으로 실제 칼럼에 사용되지 않는 값.
        department_key TEXT GENERATED ALWAYS AS (COALESCE(department, '')) STORED,   -- department_id가 주어지면 COALESCE(department_id, -1)로 대체. -1은 NULL을 대체하기 위한 값으로 실제 칼럼에 사용되지 않는 값.
        user_id_key TEXT GENERATED ALWAYS AS (COALESCE(user_id, '')) STORED,
        folder_key TEXT GENERATED ALWAYS AS (COALESCE(folder_id, '-1')) STORED,
        
        --제약 조건
        CONSTRAINT pk_learning_summary_agg PRIMARY KEY (period_value , scope, company_key, department_key, user_id_key, folder_key)
    );
    """,
    """
    CREATE INDEX learning_summary_agg_user_idx ON learning_summary_agg (period_value, user_id) WHERE scope = 'user'; -- 조회 시 칼럼 순서 동일해야 함
    """,
    """
    CREATE INDEX learning_summary_agg_company_idx ON learning_summary_agg (period_value, company) WHERE scope = 'company';
    """,
    """
    CREATE INDEX learning_summary_agg_department_idx ON learning_summary_agg (period_value, company, department) WHERE scope = 'department'; -- department_id가 주어지면 대체하고 company는 제거해도 될 듯
    """,
    """
    CREATE INDEX learning_summary_agg_all_idx ON learning_summary_agg (period_value) WHERE scope = 'all';
    """
    ]
    
    #endregion
    
    #region stay_duration(content_viewing_history) 업데이트 트리거
    stay_duration_update_queries = [
        """
        CREATE FUNCTION calculate_stay_duration() RETURNS TRIGGER
        LANGUAGE plpgsql
        AS $$
        BEGIN
            IF NEW.end_time IS NOT NULL THEN
                NEW.stay_duration = NEW.end_time - NEW.start_time;
            END IF;
            RETURN NEW;
        END;
        $$;
        """,
        """
        CREATE TRIGGER set_stay_duration BEFORE INSERT OR UPDATE ON public.content_viewing_history FOR EACH ROW EXECUTE FUNCTION public.calculate_stay_duration();
        """
    ]
    #endregion

    #region 기본 값 추가    
    
    default_insert_queries = [
         # ContentAccessGroups 기본 값 추가
        """
        INSERT INTO public.content_access_groups (group_name) VALUES ('Admin');
        """,
        # Roles 기본 값 추가
        """
        INSERT INTO public.roles (role_name) VALUES ('Admin');
        """,
        """
        INSERT INTO public.roles (role_name) VALUES ('User');
        """
    ]
    
    #endregion

    memos_queries = """
        CREATE TABLE public.memos (
            id text NOT NULL PRIMARY KEY,
            serial_number integer,
            user_id text,
            content text,
            path text,
            rel_position_x double precision,
            rel_position_y double precision,
            world_position_x double precision,
            world_position_y double precision,
            world_position_z double precision,
            status integer NOT NULL,
            modified_at bigint
        );
    """

    queries = [
        #contents_queries, 
        #contents_sequence, 
        folders_queries,
        files_queries,
        filedata_queries,
        metadata_queries,
        content_access_groups_queries, 
        content_access_groups_sequence, 
        access_group_contents_queries, 
        roles_queries, 
        roles_sequence, 
        users_queries, 
        login_history_queries,
        calculate_session_duration_queries,
        content_viewing_history_queries,
        content_viewing_history_archive_queries,
        content_viewing_history_view_queries,
        timestamp_update_queries, 
        stay_duration_update_queries,
        default_insert_queries,
        memos_queries,
        login_summary_queries,
        learning_summary_queries
        ]

    for query in queries:
        if isinstance(query, list):
            for q in query:
                cursor.execute(q)
        else:
            cursor.execute(query)

    connection.commit()
except Exception as e:
    print(f"Error: {e}")
    connection.rollback()
finally:
    cursor.close()
    connection.close()


# region SQL 파일 읽어서 실행하려고 하다가 포기

# # SQL 파일 읽어서 해보려고 하다가 표기
# with open(r"C:\Users\User\Documents\BEPS DB Backup\bepsDB Backup_0113_plain.sql", "r", encoding="utf-8") as file:
#     sql_script = file.read()

# filtered_commands = []
# for line in sql_script.splitlines():
#     stripped_line = line.strip()
#     #주석으로 시작하는 줄 무시
#     if stripped_line.startswith("--"):
#         continue
#     # SQL 문 내 주석 제거
#     stripped_line = stripped_line.split("--")[0].strip()
#     # 빈 줄 무시
#     if stripped_line:
#         filtered_commands.append(stripped_line)

# # SQL 스크립트를 개별 문장으로 분리
# sql_commands = sql_script.split(";")

# # SQL 스크립트에서 주석 제거
# filtered_commands = []
# for line in sql_commands:
#     # 주석 제거
#     stripped_line = line.strip()
#     #주석만 있는 줄 무시
#     if stripped_line.startswith("--"):
#         continue
#     # SQL 문 내 주석 제거
#     stripped_line = stripped_line.split("--")[0].strip()
#     # 빈 줄 무시
#     if stripped_line:
#         filtered_commands.append(stripped_line+";")
    

# # SQL 명령어 합치기 (주석 제거되 상태)
# cleaned_script = " ".join(filtered_commands)

# # SQL 스크립트를 개별 문장으로 분리
# sql_commands = cleaned_script.split(";")


# try:
#     # SQL 명령어 실행
#     for command in sql_commands:
#         command = command.strip()   # 공백 제거
#         if command: #빈 명령어 무시
#             cursor.execute(command+";")

#     # 변경사항 저장
#     connection.commit()
# except Exception as e:
#     print(f"Error: {e}")
#     connection.rollback()
# finally:
#     # 커서와 연결 종료
#     cursor.close()
#     connection.close()

# print("데이터베이스 생성 완료")
# endregion