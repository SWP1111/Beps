#!/bin/bash

DB_USER="postgres"
DB_NAME="beps"
DB_HOST="127.0.0.1"

NOW=$(date +"%m-%d")
HOUR=$(date +"%H")

LOG_DIR="$HOME/service/BepsApi/Backend/DB/log"
LOG_PATH="$LOG_DIR/login_summary_executor.log"

mkdir -p "$LOG_DIR"
chown "$(whoami)":"$(whoami)" "$LOG_DIR"
chmod u+w "$LOG_DIR"

echo "$(date '+%Y-%m-%d %H:%M:%S'): ▶ 스크립트 시작" >> "$LOG_PATH"

case "$NOW-$HOUR" in
    "01-02-03" | "04-02-03" | "07-02-03" | "10-02-03") 
        #분기 집계(3시)
        psql -h $DB_HOST -U $DB_USER -d $DB_NAME -c "
        SELECT aggregate_quarterly_stats(
            EXTRACT(YEAR FROM current_date - interval '1 month')::int, 
            CEILING(EXTRACT(MONTH FROM current_date - interval '1 month') / 3)::int
        );" >> "$LOG_PATH" 2>&1

        if [ $? -eq 0 ]; then
            echo "$(date +"%Y-%m-%d %H:%M:%S"): ✅ 접속 현황 분기 집계 성공" >> "$LOG_PATH" 
        else
            echo "$(date +"%Y-%m-%d %H:%M:%S"): ❌ 분기 집계 실패" >> "$LOG_PATH"
        fi

        psql -h $DB_HOST -U $DB_USER -d $DB_NAME -c "
        SELECT aggregate_learning_summary_quarterly(
            EXTRACT(YEAR FROM current_date - interval '1 month')::int, 
            CEILING(EXTRACT(MONTH FROM current_date - interval '1 month') / 3)::int
        );" >> "$LOG_PATH" 2>&1
        if [ $? -eq 0 ]; then
            echo "$(date +"%Y-%m-%d %H:%M:%S"): ✅ 학습 현황 분기 집계 성공" >> "$LOG_PATH" 
        else
            echo "$(date +"%Y-%m-%d %H:%M:%S"): ❌ 학습 현황 분기 집계 실패" >> "$LOG_PATH"
        fi
    ;;
    "01-03-03" | "07-03-03")
        #반기 집계(3시)
        psql -h $DB_HOST -U $DB_USER -d $DB_NAME -c "
        SELECT aggregate_halfyearly_stats(
            EXTRACT(YEAR FROM current_date - interval '1 month')::int,
            CASE WHEN EXTRACT(MONTH FROM current_date - interval '1 month') < 7 THEN 1 ELSE 2 END
        );" >> "$LOG_PATH" 2>&1

        if [ $? -eq 0 ]; then
            echo "$(date +"%Y-%m-%d %H:%M:%S"): ✅ 접속 현황 반기 집계 성공" >> "$LOG_PATH" 
        else
            echo "$(date +"%Y-%m-%d %H:%M:%S"): ❌ 접속 현황 반기 집계 실패" >> "$LOG_PATH"
        fi 

        psql -h $DB_HOST -U $DB_USER -d $DB_NAME -c "
        SELECT aggregate_learning_summary_halfyearly(
            EXTRACT(YEAR FROM current_date - interval '1 month')::int,
            CASE WHEN EXTRACT(MONTH FROM current_date - interval '1 month') < 7 THEN 1 ELSE 2 END
        );" >> "$LOG_PATH" 2>&1
        if [ $? -eq 0 ]; then
            echo "$(date +"%Y-%m-%d %H:%M:%S"): ✅ 학습 현황 반기 집계 성공" >> "$LOG_PATH" 
        else
            echo "$(date +"%Y-%m-%d %H:%M:%S"): ❌ 학습 현황 반기 집계 실패" >> "$LOG_PATH"
        fi       
    ;;
    "01-04-03")
        #연간 집계(3시)
        psql -h $DB_HOST -U $DB_USER -d $DB_NAME -c "
        SELECT aggregate_yearly_stats(
            EXTRACT(YEAR FROM current_date - interval '1 month')::int
        );" >> "$LOG_PATH" 2>&1

        if [ $? -eq 0 ]; then
            echo "$(date +"%Y-%m-%d %H:%M:%S"): ✅ 접속 현황 연간 집계 성공" >> "$LOG_PATH" 
        else
            echo "$(date +"%Y-%m-%d %H:%M:%S"): ❌ 접속 현황 연간 집계 실패" >> "$LOG_PATH"
        fi

        psql -h $DB_HOST -U $DB_USER -d $DB_NAME -c "
        SELECT aggregate_learning_summary_yearly(
            EXTRACT(YEAR FROM current_date - interval '1 month')::int
        );" >> "$LOG_PATH" 2>&1
        if [ $? -eq 0 ]; then
            echo "$(date +"%Y-%m-%d %H:%M:%S"): ✅ 학습 현황 연간 집계 성공" >> "$LOG_PATH" 
        else
            echo "$(date +"%Y-%m-%d %H:%M:%S"): ❌ 학습 현황 연간 집계 실패" >> "$LOG_PATH"
        fi
    ;;
    "01-05-03" | "04-05-03" | "07-05-03" | "10-05-03")
        #파티션 생성(3시)
        psql -h $DB_HOST -U $DB_USER -d $DB_NAME -c "
        SELECT create_login_summary_quarter_partition();" >> "$LOG_PATH" 2>&1

        if [ $? -eq 0 ]; then
            echo "$(date +"%Y-%m-%d %H:%M:%S"): ✅ 접속 현황 파티션 생성 성공" >> "$LOG_PATH" 
        else
            echo "$(date +"%Y-%m-%d %H:%M:%S"): ❌ 접속 현황 파티션 생성 실패" >> "$LOG_PATH"
        fi    

        psql -h $DB_HOST -U $DB_USER -d $DB_NAME -c "
        SELECT create_learning_summary_quarter_partition();" >> "$LOG_PATH" 2>&1
        
        if [ $? -eq 0 ]; then
            echo "$(date +"%Y-%m-%d %H:%M:%S"): ✅ 학습 현황 파티션 생성 성공" >> "$LOG_PATH" 
        else
            echo "$(date +"%Y-%m-%d %H:%M:%S"): ❌ 학습 현황 파티션 생성 실패" >> "$LOG_PATH"
        fi
    ;;
    *)
    
    if [ "$HOUR" == "01" ]; then
        #일일 집계(1시)
        psql -v ON_ERROR_STOP=1 -h $DB_HOST -U $DB_USER -d $DB_NAME -c "
        SELECT aggregate_daily_stats(
            (DATE_TRUNC('day', now() AT TIME ZONE 'Asia/Seoul') - INTERVAL '1 day') -- 시간대가 없는 시간 형식의 숫자값(KST 기준 자정 시각): timestamp  2025-04-01 00:00:00
            AT TIME ZONE 'Asia/Seoul'   -- 숫자값을 한국 시간이라고 해석해서 UTC 기준으로 변환(시간대 추가. -9시간 적용) : timestamptz 2025-03-31 15:00:00+00
        );" >> "$LOG_PATH" 2>&1
        
        if [ $? -eq 0 ]; then
            echo "$(date +"%Y-%m-%d %H:%M:%S"): ✅ 접속 현황 일일 집계 성공" >> "$LOG_PATH" 
        else
            echo "$(date +"%Y-%m-%d %H:%M:%S"): ❌ 접속 현황 일일 집계 실패" >> "$LOG_PATH"
        fi
        
        psql -v ON_ERROR_STOP=1 -h $DB_HOST -U $DB_USER -d $DB_NAME -c "
        SELECT aggregate_learning_summary_daily(
            (DATE_TRUNC('day', now() AT TIME ZONE 'Asia/Seoul') - INTERVAL '1 day') -- 시간대가 없는 시간 형식의 숫자값(KST 기준 자정 시각): timestamp  2025-04-01 00:00:00
            AT TIME ZONE 'Asia/Seoul'   -- 숫자값을 한국 시간이라고 해석해서 UTC 기준으로 변환(시간대 추가. -9시간 적용) : timestamptz 2025-03-31 15:00:00+00
        );" >> "$LOG_PATH" 2>&1
        
        if [ $? -eq 0 ]; then
            echo "$(date +"%Y-%m-%d %H:%M:%S"): ✅ 학습 현황 일일 집계 성공" >> "$LOG_PATH" 
        else
            echo "$(date +"%Y-%m-%d %H:%M:%S"): ❌ 학습 현황 일일 집계 실패" >> "$LOG_PATH"
        fi
    fi
    ;;
esac


# # 매일집계(1시)
# 0 1 * * * cd /home/user_ccp/service/BepsApi/Backend/DB && /bin/bash login_summary_executor.bash >> log/archive_automation.log 2>&1
# # 분기 집계(1/4/7/10월 2일 3시)
# 0 3 2 1,4,7,10 * cd /home/user_ccp/service/BepsApi/Backend/DB && /bin/bash login_summary_executor.bash >> log/archive_automation.log 2>&1
# # 반기 집계(1월, 7월 3일 3시)
# 0 3 3 1,7 * cd /home/user_ccp/service/BepsApi/Backend/DB && /bin/bash login_summary_executor.bash >> log/archive_automation.log 2>&1
# # 연간 집계(1월 4일 3시)
# 0 3 4 1 * cd /home/user_ccp/service/BepsApi/Backend/DB && /bin/bash login_summary_executor.bash >> log/archive_automation.log 2>&1
# # 분기 파티션(1/4/7/10월 5일 3시)
# 0 3 5 1,4,7,10 * cd /home/user_ccp/service/BepsApi/Backend/DB && /bin/bash login_summary_executor.bash >> log/archive_automation.log 2>&1
