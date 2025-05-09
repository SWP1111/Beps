import logging
import log_config
import os
from openpyxl import load_workbook
import pandas as pd
import time
import traceback
from config import Config
from services.statistics_excel_sheet_content import get_statistics_data, format_seconds_to_hhmmss

def delete_old_files(folder_path, max_age_seconds=3600):
    """
    지정된 폴더에서 오래된 파일 삭제
    """
    if not os.path.exists(folder_path):
        logging.debug(f"Folder does not exist: {folder_path}")
        return

    now = time.time()
    for filename in os.listdir(folder_path):
        file_path = os.path.join(folder_path, filename)
        if os.path.isfile(file_path):
            file_age = now - os.path.getmtime(file_path)
            if file_age > max_age_seconds:
                os.remove(file_path)
                logging.info(f"Deleted old file: {file_path}")

def scheduled_cleanup():
    """
    주기적으로 오래된 파일 삭제
    """
    try:
        delete_old_files(folder_path=Config.UPLOAD_DIR, max_age_seconds=3600)  # 1시간 이상된 파일 삭제
    except Exception as e:
        logging.error(f"Error during scheduled cleanup: {str(e)}, {traceback.format_exc()}")

def export_statistics_to_excel(path, filename, start_date, end_date, filter_type, filter_value):
    """
    통계 데이터를 엑셀로 내보내기
    """
    files = get_statistics_data(start_date, end_date, filter_type, filter_value)  # 통계 데이터 가져오기
    rows = []

    if files:
        prev_top = prev_mid = None
        for f in files:
            top = f['top_name']
            mid = f['mid_name']
            bottom = f['bottom_name']
            avg_seconds = f['avg_stay_duration']
            avg_time = format_seconds_to_hhmmss(avg_seconds)
            
            if prev_top is not None and top != prev_top:
                rows.append({
                    '대분류': '',
                    '중분류': '',
                    '소분류': '',
                    '평균학습시간': '',
                    '의견서 수':'',
                    '최종 업데이트 날짜': '',
                    '관리자':'',
                })
                
            row = {
                '대분류': top if top != prev_top else '',
                '중분류': mid if mid != prev_mid else '',
                '소분류': bottom,
                '평균학습시간': avg_time,
                '의견서 수': f'{f['memo_count']}건',
                '최종 업데이트 날짜': f['update_at'],
                '관리자': f['manager_name'],
            }
            rows.append(row)
        
            prev_top = top
            prev_mid = mid
    
    df = pd.DataFrame(rows)
    
    excel_path = f"{path}/{filename}.xlsx"
    logging.info(f"엑셀 파일 저장 경로: {excel_path}")
    os.makedirs(path, exist_ok=True)  # 디렉토리 생성
    
    with pd.ExcelWriter(excel_path, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name='전체컨텐츠',index=False,startrow=2)
   
    wb = load_workbook(excel_path)
    ws = wb['전체컨텐츠']
    ws.cell(row=1, column=3).value = f'{start_date} ~ {end_date}'
    wb.save(excel_path)
    
    return excel_path
    
                         

    