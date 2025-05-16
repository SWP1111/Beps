import os
import logging
import log_config
from flask import Blueprint, jsonify, request
import datetime
from datetime import timezone
from datetime import timedelta
from extensions import db
from models import  ContentRelPages, ContentRelFolders, ContentRelChannels, ContentRelPageDetails
from sqlalchemy.exc import OperationalError
from sqlalchemy.sql import text
import re
import urllib.parse
from flask_jwt_extended import jwt_required

api_contents_bp = Blueprint('contents', __name__) # 🔹 블루프린트 생성

'''
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
'''
@api_contents_bp.route('/file/get_detailed_path', methods=['GET'])
def get_detailed_path():
    """Build a detailed path from ContentRel tables using file_id"""
    file_id = request.args.get('file_id')
    
    if not file_id:
        return jsonify({'error': 'Missing file_id parameter'}), 400
    
    try:
        # Start with the file - check if it's a page or page detail
        page = ContentRelPages.query.filter_by(id=file_id, is_deleted=False).first()
        
        # Stack to build the path
        path_components = []
        
        if page:
            # This is a page
            path_components.append(page.name)
            folder_id = page.folder_id
        else:
            # Check if it's a page detail
            detail = ContentRelPageDetails.query.filter_by(id=file_id, is_deleted=False).first()
            if detail:
                path_components.append(detail.name)
                # Get the parent page
                parent_page = ContentRelPages.query.filter_by(id=detail.page_id, is_deleted=False).first()
                if parent_page:
                    path_components.append(parent_page.name)
                    folder_id = parent_page.folder_id
                else:
                    return jsonify({'error': 'Parent page not found'}), 404
            else:
                return jsonify({'error': 'File not found in content tables'}), 404
        
        # Traverse the folder hierarchy
        while folder_id is not None:
            folder = ContentRelFolders.query.filter_by(id=folder_id, is_deleted=False).first()
            if not folder:
                break
            
            path_components.append(folder.name)
            
            if folder.parent_id is None:
                # Top-level folder, get the channel
                channel = ContentRelChannels.query.filter_by(id=folder.channel_id, is_deleted=False).first()
                if channel:
                    path_components.append(channel.name)
                break
            
            folder_id = folder.parent_id
        
        # Reverse the path components to build the path
        path_components.reverse()
        full_path = '/'.join(path_components)
        
        return jsonify({
            'detailed_path': full_path
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500
#endregion