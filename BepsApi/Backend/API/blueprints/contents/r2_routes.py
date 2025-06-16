"""
R2 Storage routes

This module handles:
- R2 file existence checking
- R2 batch operations
- R2 upload/download operations
- R2 image handling
"""

import logging
import datetime
from datetime import timezone
from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from extensions import db
from models import ContentRelPages, ContentRelPageDetails, Users
from log_config import get_content_logger
from .r2_utils import check_r2_object_exists, generate_r2_object_key, generate_r2_signed_url
from services.r2_storage_service import R2StorageService

# Initialize logger
logger = get_content_logger()


def register_r2_routes(api_contents_bp):
    """Register all R2 storage routes to the blueprint"""
    
    @api_contents_bp.route('/files/r2-batch-check', methods=['POST'])
    @jwt_required(locations=['headers','cookies'])
    def batch_check_r2_files():
        """
        Batch check R2 file existence for multiple files
        
        Request body:
        {
            "file_ids": [1, 2, 3, ...]
        }
        
        Response:
        {
            "1": {"r2_exists": true, "object_key": "path/to/file"},
            "2": {"r2_exists": false, "object_key": null},
            ...
        }
        """
        try:
            data = request.get_json()
            if not data or 'file_ids' not in data:
                return jsonify({'error': 'Missing file_ids in request body'}), 400
            
            file_ids = data['file_ids']
            if not isinstance(file_ids, list):
                return jsonify({'error': 'file_ids must be a list'}), 400
            
            logger.info(f"Batch checking R2 existence for {len(file_ids)} files")
            
            results = {}
            
            for file_id in file_ids:
                try:
                    # Check if it's a page or page detail
                    page = ContentRelPages.query.filter_by(id=file_id, is_deleted=False).first()
                    
                    if page:
                        # This is a page
                        r2_exists = page.check_r2_content_exists()
                        object_key = page.object_id if r2_exists else None
                    else:
                        # Check if it's a page detail
                        detail = ContentRelPageDetails.query.filter_by(id=file_id, is_deleted=False).first()
                        if detail:
                            # This is a page detail
                            r2_exists = detail.check_r2_content_exists()
                            object_key = detail.object_id if r2_exists else None
                        else:
                            # File not found
                            r2_exists = False
                            object_key = None
                    
                    results[str(file_id)] = {
                        'r2_exists': r2_exists,
                        'object_key': object_key
                    }
                    
                except Exception as e:
                    logger.error(f"Error checking R2 for file {file_id}: {str(e)}")
                    results[str(file_id)] = {
                        'r2_exists': False,
                        'object_key': None
                    }
            
            logger.info(f"Batch R2 check completed. {sum(1 for r in results.values() if r['r2_exists'])} files have R2 content")
            
            return jsonify(results)
            
        except Exception as e:
            logger.error(f"Error in batch R2 check: {str(e)}")
            return jsonify({'error': str(e)}), 500

    @api_contents_bp.route('/file/<int:file_id>/r2-exists', methods=['GET'])
    @jwt_required(locations=['headers','cookies'])
    def check_r2_file_exists(file_id):
        """
        Check if a specific file exists in R2 storage
        """
        try:
            # Check if it's a page or page detail
            page = ContentRelPages.query.filter_by(id=file_id, is_deleted=False).first()
            
            if page:
                r2_exists = page.check_r2_content_exists()
                object_key = page.object_id if r2_exists else None
            else:
                # Check if it's a page detail
                detail = ContentRelPageDetails.query.filter_by(id=file_id, is_deleted=False).first()
                if detail:
                    r2_exists = detail.check_r2_content_exists()
                    object_key = detail.object_id if r2_exists else None
                else:
                    return jsonify({'error': 'File not found'}), 404
            
            return jsonify({
                'file_id': file_id,
                'r2_exists': r2_exists,
                'object_key': object_key
            })
            
        except Exception as e:
            logger.error(f"Error checking R2 existence for file {file_id}: {str(e)}")
            return jsonify({'error': str(e)}), 500

    @api_contents_bp.route('/file/<int:file_id>/r2-upload-url', methods=['POST'])
    @jwt_required(locations=['headers','cookies'])
    def get_r2_upload_url(file_id):
        """
        Get R2 upload URL for a file
        """
        try:
            current_user_id = get_jwt_identity()
            
            # Check if user has permission (admin, reviewer, or super admin)
            user = Users.query.filter_by(id=current_user_id).first()
            if not user or user.role_id not in [1, 2, 999]:
                return jsonify({'error': 'Insufficient permissions'}), 403
            
            data = request.get_json()
            if not data or 'filename' not in data:
                return jsonify({'error': 'Missing filename'}), 400
            
            filename = data['filename']
            content_type = data.get('content_type', 'application/octet-stream')
            
            # Find the file
            page = ContentRelPages.query.filter_by(id=file_id, is_deleted=False).first()
            if not page:
                return jsonify({'error': 'File not found'}), 404
            
            # Generate R2 object key
            object_key = generate_r2_object_key(file_id, filename, is_page_detail=False)
            
            # Generate signed upload URL
            upload_url = generate_r2_signed_url(object_key, expires_in=3600, method='PUT')
            
            return jsonify({
                'upload_url': upload_url,
                'object_key': object_key,
                'filename': filename
            })
            
        except Exception as e:
            logger.error(f"Error generating R2 upload URL for file {file_id}: {str(e)}")
            return jsonify({'error': str(e)}), 500

    @api_contents_bp.route('/file/<int:file_id>/confirm-r2-upload', methods=['POST'])
    @jwt_required(locations=['headers','cookies'])
    def confirm_r2_upload(file_id):
        """
        Confirm R2 upload completion and update database
        """
        try:
            current_user_id = get_jwt_identity()
            
            data = request.get_json()
            if not data or 'object_key' not in data:
                return jsonify({'error': 'Missing object_key'}), 400
            
            object_key = data['object_key']
            filename = data.get('filename', '')
            
            # Find the file
            page = ContentRelPages.query.filter_by(id=file_id, is_deleted=False).first()
            if not page:
                return jsonify({'error': 'File not found'}), 404
            
            # Update the page record
            page.object_id = object_key
            page.updated_at = datetime.datetime.now(timezone.utc)
            
            db.session.commit()
            
            logger.info(f"User {current_user_id} confirmed R2 upload for file {file_id}: {filename}")
            
            return jsonify({
                'message': 'R2 upload confirmed successfully',
                'file': page.to_dict()
            })
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error confirming R2 upload for file {file_id}: {str(e)}")
            return jsonify({'error': str(e)}), 500

    @api_contents_bp.route('/file/<int:file_id>/r2-image-url', methods=['GET'])
    @jwt_required(locations=['headers','cookies'])
    def get_r2_image_url(file_id):
        """
        Get R2 image URL for viewing
        """
        try:
            # Find the file
            page = ContentRelPages.query.filter_by(id=file_id, is_deleted=False).first()
            if not page:
                return jsonify({'error': 'File not found'}), 404
            
            if not page.object_id:
                return jsonify({'error': 'No R2 content available'}), 404
            
            # Generate signed URL for viewing
            signed_url = generate_r2_signed_url(page.object_id, expires_in=3600, method='GET')
            
            return jsonify({
                'signed_url': signed_url,
                'object_key': page.object_id,
                'file_id': file_id
            })
            
        except Exception as e:
            logger.error(f"Error getting R2 image URL for file {file_id}: {str(e)}")
            return jsonify({'error': str(e)}), 500

    @api_contents_bp.route('/file/<int:file_id>/r2-object-key', methods=['GET'])
    @jwt_required(locations=['headers','cookies'])
    def get_r2_object_key_preview(file_id):
        """
        Get R2 object key preview for a file
        """
        try:
            filename = request.args.get('filename', 'preview.png')
            is_page_detail = request.args.get('is_page_detail', 'false').lower() == 'true'
            
            # Generate object key preview
            object_key = generate_r2_object_key(file_id, filename, is_page_detail=is_page_detail)
            
            return jsonify({
                'file_id': file_id,
                'filename': filename,
                'object_key': object_key,
                'is_page_detail': is_page_detail
            })
            
        except Exception as e:
            logger.error(f"Error generating R2 object key preview for file {file_id}: {str(e)}")
            return jsonify({'error': str(e)}), 500 