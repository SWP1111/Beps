from extensions import db
from flask import Blueprint, jsonify, request, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import MemoReply, MemoData, Users, MemoReplyAttachment
import logging
import log_config
from log_config import get_memo_logger, get_content_logger
from datetime import datetime, timezone
import os
import boto3
from botocore.client import Config
from botocore.exceptions import ClientError

api_memo_reply_bp = Blueprint('memo_reply', __name__)

# 기존 메모 전용 로거 초기화
logger = get_memo_logger()
# 콘텐츠 로거도 추가 (R2 관련 로깅용)
content_logger = get_content_logger()

@api_memo_reply_bp.route('/', methods=['POST'])
def create_memo_reply():
    try:
        data = request.json
        logger.info(f"Received POST request to /memo/reply with data: {data}")
        
        # Validate required fields
        if not all(key in data for key in ['memo_id', 'user_id', 'content']):
            return jsonify({"error": "Missing required fields"}), 400
            
        # Check if memo exists
        memo = MemoData.query.get(data['memo_id'])
        if not memo:
            return jsonify({"error": "Memo not found"}), 404
            
        # Create new reply
        reply = MemoReply(
            memo_id=data['memo_id'],
            user_id=data['user_id'],
            content=data['content']
        )
        
        # Update memo status to 1 (답변완료) when a reply is added
        memo.status = 1
        
        db.session.add(reply)
        db.session.commit()
        
        logger.info(f"Successfully created memo reply with id: {reply.id}, updated memo status to 1")
        return jsonify(reply.to_dict()), 201
    except Exception as e:
        logger.error(f"Error creating memo reply: {str(e)}")
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

@api_memo_reply_bp.route('/memo/<int:memo_id>', methods=['GET'])
def get_replies_by_memo(memo_id):
    try:
        # Check if memo exists
        memo = MemoData.query.get_or_404(memo_id)
        
        # Get replies for this memo that are not deleted
        replies = MemoReply.query.filter_by(memo_id=memo_id, is_deleted=False).all()
        
        # The to_dict() method already includes user information through the relationship
        result = [reply.to_dict() for reply in replies]
            
        return jsonify(result), 200
    except Exception as e:
        logger.error(f"Error retrieving memo replies: {str(e)}")
        return jsonify({"error": str(e)}), 500

@api_memo_reply_bp.route('/memo/<int:memo_id>/mark_viewed', methods=['POST'])
@jwt_required(locations=['headers','cookies'])
def mark_memo_viewed(memo_id):
    try:
        # Get current user from JWT token
        current_user_id = get_jwt_identity()
        logger.info(f"Received mark_viewed request for memo {memo_id} from user {current_user_id}")
        
        # Check if memo exists
        memo = MemoData.query.get_or_404(memo_id)
        logger.info(f"Found memo {memo_id} with current status {memo.status} and author {memo.user_id}")
        
        # Only allow the memo author to mark it as viewed
        if memo.user_id != current_user_id:
            logger.warning(f"User {current_user_id} attempted to mark memo {memo_id} as viewed, but author is {memo.user_id}")
            return jsonify({"error": "Only the memo author can mark it as viewed"}), 403
            
        # If memo status is 1 (답변완료), change it to 2 (처리완료)
        old_status = memo.status
        if memo.status == 1:
            memo.status = 2
            db.session.commit()
            logger.info(f"Memo {memo_id} status changed from {old_status} to 2 (처리완료) by author {current_user_id}")
        else:
            logger.info(f"Memo {memo_id} status is {memo.status}, no change needed (only changes from 1 to 2)")
            
        return jsonify({"message": "Memo marked as viewed", "status": memo.status}), 200
    except Exception as e:
        logger.error(f"Error marking memo as viewed: {str(e)}")
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

@api_memo_reply_bp.route('/memo/<int:memo_id>/debug', methods=['GET'])
@jwt_required(locations=['headers','cookies'])
def debug_memo_status(memo_id):
    try:
        # Get current user from JWT token
        current_user_id = get_jwt_identity()
        
        # Check if memo exists
        memo = MemoData.query.get_or_404(memo_id)
        
        return jsonify({
            "memo_id": memo_id,
            "memo_status": memo.status,
            "memo_author": memo.user_id, 
            "current_user": current_user_id,
            "is_author": memo.user_id == current_user_id,
            "can_change_status": memo.status == 1 and memo.user_id == current_user_id
        }), 200
    except Exception as e:
        logger.error(f"Error debugging memo status: {str(e)}")
        return jsonify({"error": str(e)}), 500

@api_memo_reply_bp.route('/<int:id>', methods=['PUT'])
def update_reply(id):
    try:
        reply = MemoReply.query.get_or_404(id)
        data = request.json
        
        # Update content if provided
        if 'content' in data:
            reply.content = data['content']
            
        # Update timestamp
        reply.modified_at = datetime.now(timezone.utc)
        
        db.session.commit()
        logger.info(f"Successfully updated memo reply with id: {reply.id}")
        return jsonify(reply.to_dict()), 200
    except Exception as e:
        logger.error(f"Error updating memo reply: {str(e)}")
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

@api_memo_reply_bp.route('/<int:id>', methods=['DELETE'])
def delete_reply(id):
    try:
        reply = MemoReply.query.get_or_404(id)
        
        # Soft delete by setting is_deleted flag
        reply.is_deleted = True
        db.session.commit()
        
        logger.info(f"Successfully deleted memo reply with id: {reply.id}")
        return '', 204
    except Exception as e:
        logger.error(f"Error deleting memo reply: {str(e)}")
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


# ======== R2 ATTACHMENT UTILITY FUNCTIONS ========

def get_r2_client():
    """Create and return a configured R2 (S3-compatible) client"""
    try:
        aws_access_key_id = current_app.config.get('AWS_ACCESS_KEY_ID')
        aws_secret_access_key = current_app.config.get('AWS_SECRET_ACCESS_KEY')
        r2_endpoint_url = current_app.config.get('R2_ENDPOINT_URL')
        
        if not aws_access_key_id or not aws_secret_access_key:
            raise ValueError("R2 credentials not found in configuration")
        
        # Configure the client with specific settings for R2
        config = Config(
            signature_version='s3v4',
            retries={'max_attempts': 3},
            s3={
                'addressing_style': 'virtual'  # Use virtual hosted-style requests
            }
        )
        
        client = boto3.client(
            's3',
            endpoint_url=r2_endpoint_url,
            aws_access_key_id=aws_access_key_id,
            aws_secret_access_key=aws_secret_access_key,
            region_name='auto',  # R2 uses 'auto' region
            config=config
        )
        
        return client
    except Exception as e:
        content_logger.error(f"Failed to create R2 client: {str(e)}")
        raise


def generate_r2_signed_url(object_key, expires_in=3600, method='GET'):
    """Generate a pre-signed URL for R2 object access"""
    try:
        r2_client = get_r2_client()
        bucket_name = current_app.config.get('R2_BUCKET_NAME')
        
        if not bucket_name:
            raise ValueError("R2 bucket name not found in configuration")
        
        # Generate signed URL
        if method.upper() == 'GET':
            signed_url = r2_client.generate_presigned_url(
                'get_object',
                Params={'Bucket': bucket_name, 'Key': object_key},
                ExpiresIn=expires_in
            )
        elif method.upper() == 'PUT':
            signed_url = r2_client.generate_presigned_url(
                'put_object',
                Params={'Bucket': bucket_name, 'Key': object_key},
                ExpiresIn=expires_in
            )
        else:
            raise ValueError(f"Unsupported method: {method}")
        
        return signed_url
    except Exception as e:
        content_logger.error(f"Failed to generate R2 signed URL: {str(e)}")
        raise


def generate_attachment_object_key(reply_id, filename):
    """Generate R2 object key for memo reply attachment"""
    try:
        # Get reply to get the created date
        reply = MemoReply.query.get(reply_id)
        if not reply:
            raise ValueError(f"Reply {reply_id} not found")
        
        # Use reply creation date for folder structure
        reply_date = reply.created_at
        year = reply_date.strftime('%Y')
        month = reply_date.strftime('%m')
        day = reply_date.strftime('%d')
        
        # Sanitize filename
        safe_filename = os.path.basename(filename)
        
        # Generate object key: beps-lfs/opinion-reply-attachment/YYYY/MM/DD/{reply-id}/{filename}
        object_key = f"beps-lfs/opinion-reply-attachment/{year}/{month}/{day}/{reply_id}/{safe_filename}"
        
        return object_key
    except Exception as e:
        content_logger.error(f"Failed to generate attachment object key: {str(e)}")
        raise


def check_r2_object_exists(object_key):
    """Check if an object exists in R2 storage"""
    try:
        r2_client = get_r2_client()
        bucket_name = current_app.config.get('R2_BUCKET_NAME')
        
        r2_client.head_object(Bucket=bucket_name, Key=object_key)
        return True
    except ClientError as e:
        if e.response['Error']['Code'] == '404':
            return False
        else:
            content_logger.error(f"Error checking R2 object existence: {str(e)}")
            raise
    except Exception as e:
        content_logger.error(f"Failed to check R2 object existence: {str(e)}")
        raise


# ======== ATTACHMENT API ENDPOINTS ========

@api_memo_reply_bp.route('/<int:reply_id>/attachment/upload-url', methods=['POST'])
@jwt_required(locations=['headers','cookies'])
def get_attachment_upload_url(reply_id):
    """Get R2 upload URL for memo reply attachment"""
    try:
        current_user_id = get_jwt_identity()
        
        # Check if reply exists
        reply = MemoReply.query.filter_by(id=reply_id, is_deleted=False).first()
        if not reply:
            return jsonify({'error': 'Reply not found'}), 404
        
        # Only allow the reply author to add attachments
        if reply.user_id != current_user_id:
            return jsonify({'error': 'Only reply author can add attachments'}), 403
        
        # Get request data
        data = request.get_json()
        if not data or 'filename' not in data:
            return jsonify({'error': 'Missing filename'}), 400
        
        filename = data['filename']
        content_type = data.get('content_type', 'application/octet-stream')
        file_size = data.get('file_size', 0)
        
        # Validate file type (allow images primarily)
        allowed_extensions = {'.png', '.jpg', '.jpeg', '.gif', '.webp', '.pdf', '.doc', '.docx', '.txt'}
        file_ext = os.path.splitext(filename)[1].lower()
        if file_ext not in allowed_extensions:
            return jsonify({'error': f'Invalid file type {file_ext}. Allowed types: {", ".join(allowed_extensions)}'}), 400
        
        # Validate file size (50MB limit for attachments)
        if file_size > 50 * 1024 * 1024:  # 50MB
            return jsonify({'error': 'File size too large. Maximum 50MB allowed.'}), 400
        
        # Generate object key
        object_key = generate_attachment_object_key(reply_id, filename)
        
        # Generate signed upload URL
        upload_url = generate_r2_signed_url(object_key, expires_in=1800, method='PUT')  # 30 minutes
        
        return jsonify({
            'upload_url': upload_url,
            'object_key': object_key,
            'reply_id': reply_id,
            'filename': filename,
            'expires_in': 1800
        })
        
    except Exception as e:
        content_logger.error(f"Error generating attachment upload URL for reply {reply_id}: {str(e)}")
        return jsonify({'error': str(e)}), 500


@api_memo_reply_bp.route('/<int:reply_id>/attachment/confirm-upload', methods=['POST'])
@jwt_required(locations=['headers','cookies'])
def confirm_attachment_upload(reply_id):
    """Confirm attachment upload and save to database"""
    try:
        current_user_id = get_jwt_identity()
        
        # Check if reply exists and user has permission
        reply = MemoReply.query.filter_by(id=reply_id, is_deleted=False).first()
        if not reply:
            return jsonify({'error': 'Reply not found'}), 404
        
        if reply.user_id != current_user_id:
            return jsonify({'error': 'Only reply author can add attachments'}), 403
        
        # Get request data
        data = request.get_json()
        if not data or 'object_key' not in data or 'filename' not in data:
            return jsonify({'error': 'Missing object_key or filename'}), 400
        
        object_key = data['object_key']
        filename = data['filename']
        content_type = data.get('content_type', 'application/octet-stream')
        file_size = data.get('file_size', 0)
        
        # Verify the object exists in R2
        if not check_r2_object_exists(object_key):
            return jsonify({'error': 'Object not found in R2 storage'}), 404
        
        # Create attachment record
        attachment = MemoReplyAttachment(
            memo_reply_id=reply_id,
            filename=filename,
            object_key=object_key,
            file_size=file_size,
            content_type=content_type
        )
        
        db.session.add(attachment)
        db.session.commit()
        
        content_logger.info(f"User {current_user_id} uploaded attachment for reply {reply_id}: {filename}")
        
        return jsonify({
            'message': 'Attachment uploaded successfully',
            'attachment': attachment.to_dict()
        })
        
    except Exception as e:
        db.session.rollback()
        content_logger.error(f"Error confirming attachment upload for reply {reply_id}: {str(e)}")
        return jsonify({'error': str(e)}), 500


@api_memo_reply_bp.route('/attachment/<int:attachment_id>/url', methods=['GET'])
@jwt_required(locations=['headers','cookies'])
def get_attachment_url(attachment_id):
    """Get signed URL for viewing attachment"""
    try:
        # Check if attachment exists
        attachment = MemoReplyAttachment.query.get_or_404(attachment_id)
        
        # Check if related reply exists and is not deleted
        reply = MemoReply.query.filter_by(id=attachment.memo_reply_id, is_deleted=False).first()
        if not reply:
            return jsonify({'error': 'Related reply not found'}), 404
        
        # Get expires parameter
        expires = int(request.args.get('expires', 3600))
        
        # Generate signed URL for viewing
        signed_url = generate_r2_signed_url(attachment.object_key, expires_in=expires, method='GET')
        
        return jsonify({
            'signed_url': signed_url,
            'filename': attachment.filename,
            'content_type': attachment.content_type,
            'file_size': attachment.file_size,
            'expires_in': expires
        })
        
    except Exception as e:
        content_logger.error(f"Error generating attachment URL for attachment {attachment_id}: {str(e)}")
        return jsonify({'error': str(e)}), 500


@api_memo_reply_bp.route('/attachment/<int:attachment_id>', methods=['DELETE'])
@jwt_required(locations=['headers','cookies'])
def delete_attachment(attachment_id):
    """Delete attachment"""
    try:
        current_user_id = get_jwt_identity()
        
        # Check if attachment exists
        attachment = MemoReplyAttachment.query.get_or_404(attachment_id)
        
        # Check if related reply exists and user has permission
        reply = MemoReply.query.filter_by(id=attachment.memo_reply_id, is_deleted=False).first()
        if not reply:
            return jsonify({'error': 'Related reply not found'}), 404
        
        if reply.user_id != current_user_id:
            return jsonify({'error': 'Only reply author can delete attachments'}), 403
        
        # Delete from database
        db.session.delete(attachment)
        db.session.commit()
        
        # Note: We're not deleting from R2 storage for now to avoid data loss
        # This can be implemented later with a cleanup job
        
        content_logger.info(f"User {current_user_id} deleted attachment {attachment_id}")
        
        return '', 204
        
    except Exception as e:
        db.session.rollback()
        content_logger.error(f"Error deleting attachment {attachment_id}: {str(e)}")
        return jsonify({'error': str(e)}), 500 
