from flask import Blueprint, request, jsonify
from API.models import Files
from extensions import db
import urllib.parse

file_bp = Blueprint('file_bp', __name__)

@file_bp.route('/get_file_info', methods=['GET'])
def get_file_info_by_path():
    """Get file_id and folder_id for a given file_path"""
    file_path = request.args.get('file_path')
    if not file_path:
        return jsonify({'error': 'Missing file_path parameter'}), 400
    file_path = urllib.parse.unquote(file_path)
    
    file = Files.query.filter_by(file_path=file_path, is_deleted=False).first()
    
    if not file:
        return jsonify({'error': 'File not found'}), 404
    
    return jsonify({
        'file_id': file.file_id,
        'folder_id': file.folder_id
    })

@file_bp.route('/get_file_path', methods=['GET'])
def get_file_path_by_ids():
    """Get file_path for given file_id and folder_id"""
    file_id = request.args.get('file_id')
    folder_id = request.args.get('folder_id')
    
    if not file_id:
        return jsonify({'error': 'Missing file_id parameter'}), 400
    
    query = Files.query.filter_by(is_deleted=False)
    
    if file_id:
        query = query.filter_by(file_id=file_id)
    
    if folder_id:
        query = query.filter_by(folder_id=folder_id)
    
    file = query.first()
    
    if not file:
        return jsonify({'error': 'File not found'}), 404
    
    return jsonify({
        'file_path': file.file_path
    }) 