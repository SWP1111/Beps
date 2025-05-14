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