import logging
import log_config
import os
import uuid
import pandas as pd
import time
from flask import Blueprint, request, jsonify, send_file
from flask_jwt_extended import jwt_required
from extensions import db
from models import Folders, Files
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import aliased
import traceback
import re

api_statistics_bp = Blueprint('statistics', __name__)   # 블루프린트 생성

UPLOAD_DIR = '/tmp/generated_excels'  # 엑셀 파일 저장 경로

@api_statistics_bp.route('/preview', methods=['GET'])
def preview_statistics():
    """
    엑셀 미리보기
    """
    logging.info("엑셀 미리보기 요청")
    df = get_statistics_data()  # 통계 데이터 가져오기
    # 데이터프레임을 HTML로 변환합니다.
    html = df.to_html(index=False)
    
    id = str(uuid.uuid4())
    filename = f"{UPLOAD_DIR}/{id}.xlsx"
    
    with pd.ExcelWriter(filename, engine='xlsxwriter') as writer:
        # 엑셀 파일에 데이터프레임을 작성합니다.
        df = pd.DataFrame({
            'Column1': [1, 2, 3],
            'Column2': ['A', 'B', 'C']
        })
        df.to_excel(writer, sheet_name='Sheet1', index=False)
        # 엑셀 파일을 저장합니다.
        writer.save()
        
    return jsonify({
        'html': html,
        'filename': id
    })
    
    
@api_statistics_bp.route('/download', methods=['GET'])
def download_statistics():
    """
    엑셀 다운로드
    """
    id = str(uuid.uuid4())
    filename = f"{UPLOAD_DIR}/{id}.xlsx"
    
    if not os.path.exists(filename):
        return jsonify({
            'error': 'File not found'
        }), 404
        
    resposne = send_file(filename, download_name=f"beps 관리자 페이지.xlsx", as_attachment=True)
    os.remove(filename)  # 다운로드 후 파일 삭제
    return resposne

def delete_old_files(folder_path=UPLOAD_DIR, max_age_seconds=3600):
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
        delete_old_files(folder_path=UPLOAD_DIR, max_age_seconds=3600)  # 1시간 이상된 파일 삭제
    except Exception as e:
        logging.error(f"Error during scheduled cleanup: {str(e)}, {traceback.format_exc()}")

def export_statistics_to_excel():
    """
    통계 데이터를 엑셀로 내보내기
    """
    files = get_statistics_data()  # 통계 데이터 가져오기
    if files:
        rows = []
        prev_top = prev_mid = None
        for f in files:
            top = f['top_name']
            mid = f['mid_name']
            bottom = f['bottom_name']
        
            if prev_top is not None and top != prev_top:
                rows.append({
                    '대분류': '',
                    '중분류': '',
                    '소분류': '',
                })
                
            row = {
                '대분류': top if top != prev_top else '',
                '중분류': mid if mid != prev_mid else '',
                '소분류': bottom,
            }
            rows.append(row)
        
            prev_top = top
            prev_mid = mid
    
        df = pd.DataFrame(rows)
    
    excel_path = f"{UPLOAD_DIR}/{str(uuid.uuid4())}.xlsx"
    logging.info(f"엑셀 파일 저장 경로: {excel_path}")
    os.makedirs(UPLOAD_DIR, exist_ok=True)  # 디렉토리 생성
    df.to_excel(excel_path, index=False)
    
                         
def get_statistics_data():
    files = get_normal_files_width_category_names() 
    if not files:
        logging.error("No files found")
        return None
    
    return files
                
def get_normal_files_width_category_names():
    """
    폴더 타입이 normal인 파일 목록에 카테고리 이름도 같이 가져오기(상세보기 제외)
    """
    try:        
        FolderCur = aliased(Folders)
        FolderTop = aliased(Folders)
        
        def clean_name(name):
            return re.sub(r'^\d+_', '', name) if name else None
        
        query = db.session.query(
            Files, FolderTop.folder_name.label('top_name')).join(
            FolderCur, Files.folder_id == FolderCur.folder_id
        ).join(
            FolderTop, FolderCur.top_category_folder_id == FolderTop.folder_id
        ).filter(
            Files.is_deleted == False,
            FolderCur.folder_type == 'normal',
        ).order_by(Files.file_path)
        
        results = []
        for file_obj, top_name in query.all():
            parts = file_obj.file_path.split('/')
            try:
                top_index = parts.index(top_name)
                mid_name = parts[top_index + 1] if top_index + 1 < len(parts) else ''
            except ValueError:
                mid_name = ''
            
            top_name = clean_name(top_name)
            mid_name = clean_name(mid_name)
            bottom_name = clean_name(file_obj.file_name)
            
            result = {
                **{k: v for k, v in file_obj.__dict__.items() if not k.startswith('_')},
                'top_name': top_name,
                'mid_name': mid_name,
                'bottom_name': bottom_name
            }   
            results.append(result)
        
        return results
    except Exception as e:
        logging.error(f"[get_normal_files]: {str(e)}, {traceback.format_exc()}")
        return None
   