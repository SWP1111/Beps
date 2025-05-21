import os
import logging
import log_config
from flask import Blueprint, jsonify, request, send_file, current_app
import datetime
from datetime import timezone
from datetime import timedelta
from extensions import db
from models import ContentRelPages, ContentRelFolders, ContentRelChannels, ContentRelPageDetails, Users, ContentManager
from sqlalchemy.exc import OperationalError
from sqlalchemy.sql import text
import re
import urllib.parse
from flask_jwt_extended import jwt_required, get_jwt_identity
from services.content_hierarchy_service import ContentHierarchyService
from werkzeug.utils import secure_filename
import uuid

api_contents_bp = Blueprint('contents', __name__) # 🔹 블루프린트 생성


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

@api_contents_bp.route('/channel/children', methods=['GET'])
def get_channel_child():
    """
    Get all top-level folders for a given channel
    
    Returns a list of folder IDs that have parent_id=null and belong to the given channel_id
    """
    try:
        channel_id = request.args.get('channel_id')
        if not channel_id:
            return jsonify({'error': 'Missing channel_id parameter'}), 400
            
        # Use the hierarchy service
        service = ContentHierarchyService()
        folder_ids = service.get_channel_children(int(channel_id))
        
        return jsonify({
            'folder_ids': folder_ids,
            'count': len(folder_ids)
        })
    except Exception as e:
        logging.error(f"Error in get_channel_child: {str(e)}")
        return jsonify({'error': str(e)}), 500

@api_contents_bp.route('/folder/children', methods=['GET'])
def get_folder_child():
    """
    Get all subfolders or pages within a given folder
    
    If there are subfolders, returns those IDs and sets isLeafFolder=false
    If there are no subfolders, returns page IDs and sets isLeafFolder=true
    """
    try:
        folder_id = request.args.get('folder_id')
        if not folder_id:
            return jsonify({'error': 'Missing folder_id parameter'}), 400
            
        # Use the hierarchy service
        service = ContentHierarchyService()
        child_ids, is_leaf_folder = service.get_folder_children(int(folder_id))
        
        response_data = {
            'is_leaf_folder': is_leaf_folder,
            'count': len(child_ids)
        }
        
        # Set the correct field based on whether this is a leaf folder
        if is_leaf_folder:
            response_data['page_ids'] = child_ids
        else:
            response_data['folder_ids'] = child_ids
        
        return jsonify(response_data)
    except Exception as e:
        logging.error(f"Error in get_folder_child: {str(e)}")
        return jsonify({'error': str(e)}), 500

@api_contents_bp.route('/hierarchy', methods=['GET'])
def get_content_hierarchy():
    """
    Get the full content hierarchy (channels, folders, and pages)
    
    Optional query parameters:
    - refresh: If true, rebuilds the hierarchy instead of using cache
    - format: 'full' (default) or 'summary' 
    """
    try:
        # Check if we should bypass cache
        refresh = request.args.get('refresh', 'false').lower() == 'true'
        
        # Get hierarchy
        service = ContentHierarchyService()
        hierarchy = service.get_full_hierarchy(use_cache=not refresh)
        
        return jsonify(hierarchy)
    except Exception as e:
        logging.error(f"Error getting content hierarchy: {str(e)}")
        return jsonify({'error': str(e)}), 500

@api_contents_bp.route('/file/<int:file_id>/path', methods=['GET'])
def get_file_path(file_id):
    """
    Get the complete path to a specific file
    
    Returns the full path information including all components and IDs
    """
    try:
        service = ContentHierarchyService()
        path_info = service.get_file_path(file_id)
        
        if not path_info:
            return jsonify({'error': 'File not found'}), 404
            
        return jsonify(path_info)
    except Exception as e:
        logging.error(f"Error getting file path: {str(e)}")
        return jsonify({'error': str(e)}), 500

# 새로운 API 엔드포인트 추가

@api_contents_bp.route('/channels', methods=['GET'])
def get_channels():
    """
    Get all channels
    
    Returns a list of all available channels
    """
    try:
        service = ContentHierarchyService()
        channels = service.get_channels()
        
        return jsonify({
            'channels': channels
        })
    except Exception as e:
        logging.error(f"Error getting channels: {str(e)}")
        return jsonify({'error': str(e)}), 500

@api_contents_bp.route('/hierarchy/channel/<int:channel_id>', methods=['GET'])
def get_channel_hierarchy(channel_id):
    """
    Get the hierarchy for a specific channel
    
    Returns folders and files for the given channel, with optional filtering
    
    Query parameters:
    - filters: JSON encoded filter configuration
    """
    try:
        # Get filter parameters
        filters_json = request.args.get('filters', '{}')
        try:
            import json
            filters = json.loads(filters_json)
        except:
            filters = {'all': True}
        
        service = ContentHierarchyService()
        hierarchy = service.get_channel_hierarchy(channel_id, filters)
        
        return jsonify(hierarchy)
    except Exception as e:
        logging.error(f"Error getting channel hierarchy: {str(e)}")
        return jsonify({'error': str(e)}), 500

@api_contents_bp.route('/user-accessible', methods=['GET'])
def get_user_accessible_content():
    """
    Get content that is accessible to a specific user
    
    Returns lists of folder_ids and file_ids that the user has access to
    
    Query parameters:
    - user_id: ID of the user to check access for
    """
    try:
        user_id = request.args.get('user_id')
        if not user_id:
            return jsonify({'error': 'Missing user_id parameter'}), 400
        
        service = ContentHierarchyService()
        folder_ids, file_ids = service.get_user_accessible_content(int(user_id))
        
        return jsonify({
            'folderIds': folder_ids,
            'fileIds': file_ids
        })
    except Exception as e:
        logging.error(f"Error getting user accessible content: {str(e)}")
        return jsonify({'error': str(e)}), 500

@api_contents_bp.route('/channel/<int:channel_id>/check-accessibility', methods=['GET'])
def check_channel_accessibility(channel_id):
    """
    Check if a channel contains any content accessible to a user
    
    Returns a boolean indicating if the user has access to anything in the channel
    
    Query parameters:
    - user_id: ID of the user to check access for
    """
    try:
        user_id = request.args.get('user_id')
        if not user_id:
            return jsonify({'error': 'Missing user_id parameter'}), 400
        
        service = ContentHierarchyService()
        has_accessible_content = service.channel_has_accessible_content(channel_id, int(user_id))
        
        return jsonify({
            'has_accessible_content': has_accessible_content
        })
    except Exception as e:
        logging.error(f"Error checking channel accessibility: {str(e)}")
        return jsonify({'error': str(e)}), 500

@api_contents_bp.route('/file/<int:file_id>/download', methods=['GET'])
def download_file(file_id):
    """
    Download a file
    
    Returns the file for download
    """
    try:
        service = ContentHierarchyService()
        file_path, filename = service.get_file_download_info(file_id)
        
        if not file_path or not os.path.exists(file_path):
            return jsonify({'error': 'File not found or not available for download'}), 404
        
        return send_file(
            file_path,
            as_attachment=True,
            download_name=filename
        )
    except Exception as e:
        logging.error(f"Error downloading file: {str(e)}")
        return jsonify({'error': str(e)}), 500

@api_contents_bp.route('/channel', methods=['POST'])
@jwt_required()
def create_channel():
    """
    Create a new channel
    
    Requires admin or developer role
    
    Request body:
    - name: Name of the channel
    """
    try:
        # Check user role for permission
        user_id = get_jwt_identity()
        user = Users.query.get(user_id)
        
        if not user or (user.role_id not in [1, 999]):  # 1=admin, 999=developer
            return jsonify({'error': 'Permission denied. Admin role required.'}), 403
        
        # Get request data
        request_data = request.json
        if not request_data or 'name' not in request_data:
            return jsonify({'error': 'Channel name is required'}), 400
        
        # Create channel
        service = ContentHierarchyService()
        channel_id = service.create_channel(request_data['name'], user_id)
        
        # Clear cache for hierarchy
        service.clear_hierarchy_cache()
        
        return jsonify({
            'message': 'Channel created successfully',
            'channel_id': channel_id
        })
    except Exception as e:
        logging.error(f"Error creating channel: {str(e)}")
        return jsonify({'error': str(e)}), 500

@api_contents_bp.route('/channel/<int:channel_id>', methods=['DELETE'])
@jwt_required()
def delete_channel(channel_id):
    """
    Delete a channel
    
    Requires admin or developer role
    """
    try:
        # Check user role for permission
        user_id = get_jwt_identity()
        user = Users.query.get(user_id)
        
        if not user or (user.role_id not in [1, 999]):  # 1=admin, 999=developer
            return jsonify({'error': 'Permission denied. Admin role required.'}), 403
        
        # Delete channel
        service = ContentHierarchyService()
        success = service.delete_channel(channel_id, user_id)
        
        if not success:
            return jsonify({'error': 'Channel not found or could not be deleted'}), 404
        
        # Clear cache for hierarchy
        service.clear_hierarchy_cache()
        
        return jsonify({
            'message': 'Channel deleted successfully'
        })
    except Exception as e:
        logging.error(f"Error deleting channel: {str(e)}")
        return jsonify({'error': str(e)}), 500

@api_contents_bp.route('/file', methods=['POST'])
@jwt_required()
def upload_file():
    """
    Upload a file to a channel or folder
    
    Requires admin, developer, or reviewer role
    
    Form data:
    - file: The file to upload
    - channelId: Channel ID
    - folderId: (Optional) Folder ID
    - name: (Optional) Name for the file, defaults to filename
    - version: (Optional) Version of the file
    """
    try:
        # Check user role for permission
        user_id = get_jwt_identity()
        user = Users.query.get(user_id)
        
        if not user or (user.role_id not in [1, 2, 999]):  # 1=admin, 2=reviewer, 999=developer
            return jsonify({'error': 'Permission denied. Admin or reviewer role required.'}), 403
        
        # Check if file is included
        if 'file' not in request.files:
            return jsonify({'error': 'No file part in the request'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No selected file'}), 400
        
        # Get other form data
        channel_id = request.form.get('channelId')
        if not channel_id:
            return jsonify({'error': 'Channel ID is required'}), 400
        
        folder_id = request.form.get('folderId', None)
        name = request.form.get('name', None) or file.filename
        version = request.form.get('version', '1.0')
        
        # Save file
        filename = secure_filename(file.filename)
        temp_dir = current_app.config.get('UPLOAD_FOLDER', '/tmp')
        os.makedirs(temp_dir, exist_ok=True)
        
        # Generate unique filename
        file_uuid = str(uuid.uuid4())
        temp_path = os.path.join(temp_dir, f"{file_uuid}_{filename}")
        file.save(temp_path)
        
        # Add to database
        service = ContentHierarchyService()
        file_id = service.add_file(
            temp_path,
            name,
            int(channel_id),
            folder_id=int(folder_id) if folder_id else None,
            version=version,
            user_id=user_id
        )
        
        # Clear cache for hierarchy
        service.clear_hierarchy_cache()
        
        return jsonify({
            'message': 'File uploaded successfully',
            'file_id': file_id
        })
    except Exception as e:
        logging.error(f"Error uploading file: {str(e)}")
        return jsonify({'error': str(e)}), 500

@api_contents_bp.route('/files', methods=['DELETE'])
@jwt_required()
def delete_files():
    """
    Delete one or more files
    
    Requires admin, developer, or reviewer role
    
    Request body:
    - fileIds: Array of file IDs to delete
    """
    try:
        # Check user role for permission
        user_id = get_jwt_identity()
        user = Users.query.get(user_id)
        
        if not user or (user.role_id not in [1, 2, 999]):  # 1=admin, 2=reviewer, 999=developer
            return jsonify({'error': 'Permission denied. Admin or reviewer role required.'}), 403
        
        # Get request data
        request_data = request.json
        if not request_data or 'fileIds' not in request_data or not request_data['fileIds']:
            return jsonify({'error': 'File IDs are required'}), 400
        
        # Delete files
        service = ContentHierarchyService()
        success, failed = service.delete_files(request_data['fileIds'], user_id)
        
        # Clear cache for hierarchy
        service.clear_hierarchy_cache()
        
        if failed:
            return jsonify({
                'message': f'Some files could not be deleted',
                'success': success,
                'failed': failed
            }), 207  # Multi-Status
        
        return jsonify({
            'message': 'Files deleted successfully',
            'count': len(success)
        })
    except Exception as e:
        logging.error(f"Error deleting files: {str(e)}")
        return jsonify({'error': str(e)}), 500

@api_contents_bp.route('/folder', methods=['POST'])
@jwt_required()
def create_folder():
    """
    Create a new folder
    
    Requires admin, developer, or reviewer role
    
    Request body:
    - name: Name of the folder
    - channelId: Channel ID
    - parentId: (Optional) Parent folder ID
    """
    try:
        # Check user role for permission
        user_id = get_jwt_identity()
        user = Users.query.get(user_id)
        
        if not user or (user.role_id not in [1, 2, 999]):  # 1=admin, 2=reviewer, 999=developer
            return jsonify({'error': 'Permission denied. Admin or reviewer role required.'}), 403
        
        # Get request data
        request_data = request.json
        if not request_data:
            return jsonify({'error': 'Request body is required'}), 400
        
        if 'name' not in request_data:
            return jsonify({'error': 'Folder name is required'}), 400
            
        if 'channelId' not in request_data:
            return jsonify({'error': 'Channel ID is required'}), 400
        
        parent_id = request_data.get('parentId', None)
        
        # Create folder
        service = ContentHierarchyService()
        folder_id = service.create_folder(
            request_data['name'],
            int(request_data['channelId']),
            parent_id=int(parent_id) if parent_id else None,
            user_id=user_id
        )
        
        # Clear cache for hierarchy
        service.clear_hierarchy_cache()
        
        return jsonify({
            'message': 'Folder created successfully',
            'folder_id': folder_id
        })
    except Exception as e:
        logging.error(f"Error creating folder: {str(e)}")
        return jsonify({'error': str(e)}), 500

@api_contents_bp.route('/folder/<int:folder_id>', methods=['DELETE'])
@jwt_required()
def delete_folder(folder_id):
    """
    Delete a folder and its contents
    
    Requires admin or developer role
    """
    try:
        # Check user role for permission
        user_id = get_jwt_identity()
        user = Users.query.get(user_id)
        
        if not user or (user.role_id not in [1, 999]):  # 1=admin, 999=developer
            return jsonify({'error': 'Permission denied. Admin role required.'}), 403
        
        # Delete folder
        service = ContentHierarchyService()
        success = service.delete_folder(folder_id, user_id)
        
        if not success:
            return jsonify({'error': 'Folder not found or could not be deleted'}), 404
        
        # Clear cache for hierarchy
        service.clear_hierarchy_cache()
        
        return jsonify({
            'message': 'Folder deleted successfully'
        })
    except Exception as e:
        logging.error(f"Error deleting folder: {str(e)}")
        return jsonify({'error': str(e)}), 500

@api_contents_bp.route('/content_manager', methods=['GET'])
def get_content_managers():
    """
    Get all content managers
    
    Returns a list of content manager entries
    """
    try:
        managers = ContentManager.query.all()
        return jsonify([manager.to_dict() for manager in managers])
    except Exception as e:
        logging.error(f"Error getting content managers: {str(e)}")
        return jsonify({'error': str(e)}), 500

@api_contents_bp.route('/content_manager', methods=['POST'])
def add_content_manager():
    """
    Add a new content manager entry
    
    Request body:
    - user_id: ID of the user to add as manager
    - type: Type of permission ('channel', 'folder', or 'file')
    - file_id: ID of the file (when type is 'file')
    - folder_id: ID of the folder (when type is 'folder')
    - channel_id: ID of the channel (when type is 'channel')
    """
    try:
        data = request.json
        
        if not data or 'user_id' not in data or 'type' not in data:
            return jsonify({'error': 'Required fields missing: user_id and type'}), 400
        
        user_id = data['user_id']
        permission_type = data['type']
        
        # Validate user exists
        user = Users.query.get(user_id)
        if not user:
            return jsonify({'error': f'User with ID {user_id} not found'}), 404
        
        # Create manager entry based on type
        manager = ContentManager(
            user_id=user_id,
            type=permission_type
        )
        
        if permission_type == 'channel' and 'channel_id' in data:
            channel_id = data['channel_id']
            
            # Verify channel exists
            channel = ContentRelChannels.query.filter_by(id=int(channel_id), is_deleted=False).first()
            if not channel:
                return jsonify({'error': f'Channel with ID {channel_id} not found'}), 404
            
            # Set channel_id
            manager.channel_id = int(channel_id)
        
        elif permission_type == 'folder' and 'folder_id' in data:
            folder_id = data['folder_id']
            
            # Verify folder exists
            folder = ContentRelFolders.query.filter_by(id=int(folder_id), is_deleted=False).first()
            if not folder:
                return jsonify({'error': f'Folder with ID {folder_id} not found'}), 404
            
            manager.folder_id = int(folder_id)
        
        elif permission_type == 'file' and 'file_id' in data:
            file_id = data['file_id']
            
            # Verify file exists
            file = ContentRelPages.query.filter_by(id=int(file_id), is_deleted=False).first()
            if not file:
                return jsonify({'error': f'File with ID {file_id} not found'}), 404
            
            manager.file_id = int(file_id)
        
        else:
            # Missing required IDs for the selected type
            missing_field = 'channel_id' if permission_type == 'channel' else ('folder_id' if permission_type == 'folder' else 'file_id')
            return jsonify({'error': f'Required field missing: {missing_field}'}), 400
        
        # Save to database
        db.session.add(manager)
        db.session.commit()
        
        return jsonify(manager.to_dict())
    
    except Exception as e:
        db.session.rollback()
        logging.error(f"Error adding content manager: {str(e)}")
        return jsonify({'error': str(e)}), 500

@api_contents_bp.route('/content_manager/<int:manager_id>', methods=['DELETE'])
def delete_content_manager(manager_id):
    """
    Delete a content manager entry
    
    Path parameter:
    - manager_id: ID of the content manager entry to delete
    """
    try:
        manager = ContentManager.query.get(manager_id)
        
        if not manager:
            return jsonify({'error': f'Content manager entry with ID {manager_id} not found'}), 404
        
        db.session.delete(manager)
        db.session.commit()
        
        return jsonify({'message': 'Content manager entry deleted successfully'})
    
    except Exception as e:
        db.session.rollback()
        logging.error(f"Error deleting content manager: {str(e)}")
        return jsonify({'error': str(e)}), 500
#endregion