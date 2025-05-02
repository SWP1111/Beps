import os
import logging
import log_config
from flask import Blueprint, jsonify, request
import datetime
from datetime import timezone
from datetime import timedelta
from extensions import db
from models import Folders, Files
from sqlalchemy.exc import OperationalError
from sqlalchemy.sql import text
import re
import urllib.parse
from flask_jwt_extended import jwt_required

api_contents_bp = Blueprint('contents', __name__) # 🔹 블루프린트 생성

#region 🔹 파일 경로로 폴더 ID를 조회, 없으면 생성하는 함수
def get_folder_id_from_path(path):
    abs_path = os.path.abspath(os.path.expanduser(path))  # ✅ 절대 경로 변환
    logging.info(f"Absolute Path: {abs_path}")

    parts = abs_path.strip(os.sep).split(os.sep)  # ✅ 폴더 리스트 생성
    parent_id = None  # Root를 찾을 때까지 None
    depth = 0  # Root는 depth=0부터 시작
    folder_type = 'normal'

    # ✅ Root 자동 탐색 (숫자 패턴 폴더의 상위 폴더까지 포함)
    root_index = None
    for i, part in enumerate(parts):
        if re.match(r'^\d{3}_', part):  # "001_", "002_" 등의 패턴 확인
            root_index = i - 1  # 숫자 패턴 폴더의 상위 폴더를 Root로 설정
            break

    if root_index is None or root_index < 0:
        logging.info("No valid Root found. Using the whole path as Root.")
        root_index = len(parts) - 1  # 숫자 패턴이 없으면 전체 경로를 Root로 사용

    root_folder_name = parts[root_index]  # ✅ 개별 폴더 이름만 사용 ("/" 없음)

    # ✅ DB에서 Root 확인
    root_folder = Folders.query.filter_by(folder_name=root_folder_name, parent_id=None).first()
    if not root_folder:
        logging.info(f"Creating new Root: {root_folder_name}")
        root_folder = Folders(
            parent_id=None,
            folder_name=root_folder_name,  # ✅ 개별 폴더 이름만 저장 ("/" 없음)
            depth=0,
            is_visible=True,
            folder_type='normal',
        )
        db.session.add(root_folder)
        db.session.commit()

    parent_id = root_folder.folder_id
    top_category_folder_id = None

    # ✅ Root 이후의 폴더 추가
    for i in range(root_index + 1, len(parts)):
        folder_name = parts[i]  # ✅ 개별 폴더 이름 저장 ("/" 없음)
        if folder_name == "상세보기":
            folder_type = 'meta'

        folder = Folders.query.filter_by(parent_id=parent_id, folder_name=folder_name).first()
        if not folder:
            logging.info(f"Creating folder: {folder_name} under Parent ID: {parent_id} with type {folder_type}")
            folder = Folders(
                parent_id=parent_id,
                folder_name=folder_name,  # ✅ 개별 폴더 이름만 저장 ("/" 없음)
                depth=depth + 1,
                is_visible=True,
                folder_type=folder_type,
                top_category_folder_id=top_category_folder_id or None,
            )
            db.session.add(folder)
            db.session.flush()
            
            if top_category_folder_id is None:
                folder.top_category_folder_id = folder.folder_id
                top_category_folder_id = folder.folder_id
                db.session.commit()
        else:
            if top_category_folder_id is None:
                top_category_folder_id = folder.top_category_folder_id

        parent_id = folder.folder_id
        depth += 1

    return parent_id  # 최종 폴더 ID 반환
 #endregion
 
#region 🔹 파일 정보 조회 또는 생성하는 API       
@api_contents_bp.route('/file/get_or_create', methods=['GET']) # 🔹 GET /contents/fileInfo API
@jwt_required(locations=['headers','cookies'])  # 🔹 JWT 검증을 먼저 수행
def file_info():
    try:
        raw_path = request.full_path.replace('/contents/file/get_or_create?path=', '') # 🔹 파일 경로를 가져옴(&가 있으면 잘려서 이 방식 사용)
        #request.args.get('path') # 🔹 파일 경로를 가져옴
        logging.debug(f"Raw Path: {raw_path}")
        
        if not raw_path:
            return jsonify({'error': 'Please provide path'}), 400
        
        path = urllib.parse.unquote(raw_path) # 🔹 URL 디코딩
        logging.debug(f"Decoded Path: {path}")
        
        folder_id = get_folder_id_from_path(os.path.dirname(path)) # 🔹 파일 경로로 folder_id를 조회
        
        if folder_id is None:
            return jsonify({'error': 'Invalid path'}), 400
        
        filename_without_ext, file_ext = os.path.splitext(os.path.basename(path)) # 🔹 파일명과 확장자 구분
        file = Files.query.filter_by(folder_id=folder_id, file_name=filename_without_ext).first() # 🔹 folder_id로 파일 조회
        
        if file is None:
            logging.info(f"File not found: {folder_id}, {filename_without_ext}")
            newfile = Files(
                folder_id=folder_id,
                file_name=filename_without_ext,
                file_type=file_ext.lstrip('.'),
                file_size=0,
                file_path=path
            )
            db.session.add(newfile)
            db.session.commit()
            file = newfile
            logging.info(f"New file added: {file.file_id}")
        
        file_data = file.to_dict() # 🔹 파일 정보를 딕셔너리로 변환
        return jsonify(file_data) # 🔹 파일 정보 반환
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@api_contents_bp.route('/file/get_by_path', methods=['GET'])
def get_file_by_path():
    try:
        file_path = request.args.get('file_path')
        if not file_path:
            return jsonify({'error': 'Missing file_path parameter'}), 400
        
        file_path = urllib.parse.unquote(file_path)
        file = Files.query.filter_by(file_path=file_path, is_deleted=False).first()
        
        if not file:
            # Try by filename
            filename = file_path.split('/')[-1]
            if '.' in filename:
                file = Files.query.filter_by(file_name=filename.split('.')[0], is_deleted=False).first()
            else:
                file = Files.query.filter_by(file_name=filename, is_deleted=False).first()
        
        if not file:
            return jsonify({'error': 'File not found'}), 404
            
        return jsonify({
            'file_id': file.file_id,
            'folder_id': file.folder_id
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@api_contents_bp.route('/file/get_path', methods=['GET'])
def get_path_by_ids():
    try:
        file_id = request.args.get('file_id')
        if not file_id:
            return jsonify({'error': 'Missing file_id parameter'}), 400
        
        query = Files.query.filter_by(is_deleted=False)
        query = query.filter_by(file_id=file_id)
        
        if folder_id := request.args.get('folder_id'):
            query = query.filter_by(folder_id=folder_id)
        
        file = query.first()
        
        if not file:
            return jsonify({'error': 'File not found'}), 404
        
        return jsonify({'file_path': file.file_path})
    except Exception as e:
        return jsonify({'error': str(e)}), 500
#endregion