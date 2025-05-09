import logging
import log_config
import os
import uuid
from flask import Blueprint, request, jsonify, send_file
from services.statistics_excel_service import export_statistics_to_excel
from config import Config

api_statistics_bp = Blueprint('statistics', __name__)   # 블루프린트 생성

@api_statistics_bp.route('/preview', methods=['GET'])
def preview_statistics():
    from services.user_summary_service import get_period_value
    """
    엑셀 미리보기
    """
    period_value = request.args.get('period_value')
    period_type = request.args.get('period_type')
    filter_type = request.args.get('filter_type')
    filter_value = request.args.get('filter_value')
    
    start_date, end_date = get_period_value(period_type, period_value)
    filename = str(uuid.uuid4()) 
    result = export_statistics_to_excel(Config.UPLOAD_DIR, filename, start_date, end_date, filter_type, filter_value)  # 엑셀 파일 생성
    return jsonify({
        'filename': result
    })
    
    
@api_statistics_bp.route('/download', methods=['GET'])
def download_statistics():
    """
    엑셀 다운로드
    """
    id = str(uuid.uuid4())
    filename = f"{Config.UPLOAD_DIR}/{id}.xlsx"
    
    if not os.path.exists(filename):
        return jsonify({
            'error': 'File not found'
        }), 404
        
    resposne = send_file(filename, download_name=f"beps 관리자 페이지.xlsx", as_attachment=True)
    os.remove(filename)  # 다운로드 후 파일 삭제
    return resposne
