"""
R2/Cloudflare R2 Storage utility functions

This module provides utility functions for interacting with Cloudflare R2 storage:
- R2 client management
- Object existence checking
- Signed URL generation
- Object key generation
"""

import os
import boto3
from botocore.client import Config
from botocore.exceptions import ClientError, NoCredentialsError
import logging
from flask import current_app
from log_config import get_content_logger
from models import ContentRelPages, ContentRelFolders, ContentRelChannels, ContentRelPageDetails

# Initialize logger
logger = get_content_logger()


def get_r2_client():
    """
    Create and return a configured R2 (S3-compatible) client using Flask app config
    """
    try:
        # Get credentials from Flask app config (like the original implementation)
        aws_access_key_id = current_app.config.get('AWS_ACCESS_KEY_ID')
        aws_secret_access_key = current_app.config.get('AWS_SECRET_ACCESS_KEY')
        r2_endpoint_url = current_app.config.get('R2_ENDPOINT_URL')
        
        if not aws_access_key_id or not aws_secret_access_key:
            error_msg = "R2 credentials not found in Flask app configuration"
            logger.warning(error_msg)  # Changed from error to warning
            raise ValueError(error_msg)
        
        # Configure the client with specific settings for R2 (matching original)
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
        logger.warning(f"Failed to create R2 client: {str(e)}")  # Changed from error to warning
        raise


def generate_r2_signed_url(object_key, expires_in=3600, method='GET'):
    """
    Generate a pre-signed URL for R2 object access
    
    Args:
        object_key: The R2 object key
        expires_in: URL expiration time in seconds (default: 1 hour)
        method: HTTP method ('GET' or 'PUT')
    
    Returns:
        Signed URL string
    """
    try:
        r2_client = get_r2_client()
        bucket_name = current_app.config.get('R2_BUCKET_NAME')
        
        if not bucket_name:
            raise ValueError("R2 bucket name not found in Flask app configuration")
        
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
        logger.warning(f"Failed to generate signed URL for {object_key}: {str(e)}")  # Changed from error to warning
        raise


def check_r2_object_exists(object_key):
    """
    Check if an object exists in R2 storage
    
    Args:
        object_key: The R2 object key to check
    
    Returns:
        True if object exists, False otherwise
    """
    try:
        logger.debug(f"🔍 Checking R2 object existence: '{object_key}'")
        
        r2_client = get_r2_client()
        bucket_name = current_app.config.get('R2_BUCKET_NAME')
        
        logger.debug(f"🪣 Using bucket: '{bucket_name}'")
        
        # Try to get object metadata
        response = r2_client.head_object(Bucket=bucket_name, Key=object_key)
        logger.debug(f"✅ R2 object '{object_key}' exists - metadata: {response.get('Metadata', {})}")
        return True
    except ClientError as e:
        # Object doesn't exist if we get a 404
        if e.response['Error']['Code'] == '404':
            logger.debug(f"❌ R2 object '{object_key}' does not exist (404)")
            return False
        else:
            # Other errors (permissions, etc.) - log and return False
            logger.warning(f"❌ Error checking R2 object '{object_key}': {str(e)}")  # Changed from error to warning
            return False
    except ValueError as ve:
        # R2 credentials not available - this is expected in development
        logger.debug(f"❌ R2 credentials not available for checking '{object_key}': {str(ve)}")
        return False
    except Exception as e:
        logger.warning(f"❌ Unexpected error checking R2 object '{object_key}': {str(e)}", exc_info=True)  # Changed from error to warning
        return False


def delete_r2_object(object_key):
    """
    Delete an object from R2 storage
    
    Args:
        object_key: The R2 object key to delete
    
    Returns:
        True if deletion was successful, False otherwise
    """
    try:
        r2_client = get_r2_client()
        bucket_name = current_app.config.get('R2_BUCKET_NAME')
        
        # Delete the object
        r2_client.delete_object(Bucket=bucket_name, Key=object_key)
        logger.info(f"Successfully deleted R2 object: {object_key}")
        return True
    except Exception as e:
        logger.error(f"Failed to delete R2 object {object_key}: {str(e)}")
        return False


def generate_r2_object_key(file_id, filename, is_page_detail=False, page_detail_name=None):
    """
    Generate R2 object key based on content hierarchy
    
    Args:
        file_id: The file ID (page or page detail)
        filename: The filename
        is_page_detail: Whether this is a page detail
        page_detail_name: Name of the page detail (if applicable)
    
    Returns:
        Generated R2 object key
    """
    try:
        if is_page_detail:
            # For page details, get the parent page information
            detail = ContentRelPageDetails.query.filter_by(id=file_id, is_deleted=False).first()
            if not detail:
                raise ValueError(f"Page detail with ID {file_id} not found")
            
            # Get the parent page
            parent_page = ContentRelPages.query.filter_by(id=detail.page_id, is_deleted=False).first()
            if not parent_page:
                raise ValueError(f"Parent page for detail {file_id} not found")
            
            # Use the parent page's folder hierarchy
            folder_id = parent_page.folder_id
            page_name = parent_page.name
        else:
            # For pages, get the page information
            page = ContentRelPages.query.filter_by(id=file_id, is_deleted=False).first()
            if not page:
                raise ValueError(f"Page with ID {file_id} not found")
            
            folder_id = page.folder_id
            page_name = page.name
        
        # Build the path components
        path_components = []
        
        # Traverse the folder hierarchy
        current_folder_id = folder_id
        while current_folder_id is not None:
            folder = ContentRelFolders.query.filter_by(id=current_folder_id, is_deleted=False).first()
            if not folder:
                break
            
            # Replace problematic characters for R2 path
            safe_folder_name = folder.name.replace('/', '⁄').replace('\\', '⁄')
            path_components.append(safe_folder_name)
            
            if folder.parent_id is None:
                # Top-level folder, get the channel
                channel = ContentRelChannels.query.filter_by(id=folder.channel_id, is_deleted=False).first()
                if channel:
                    safe_channel_name = channel.name.replace('/', '⁄').replace('\\', '⁄')
                    path_components.append(safe_channel_name)
                break
            
            current_folder_id = folder.parent_id
        
        # Reverse to get correct order (channel -> folders -> page)
        path_components.reverse()
        
        if is_page_detail:
            # For page details, add page folder (without extension)
            import os as os_module
            page_name_without_ext = os_module.path.splitext(page_name)[0]
            safe_page_name = page_name_without_ext.replace('/', '⁄').replace('\\', '⁄')
            path_components.append(safe_page_name)
        
        # Add the filename
        safe_filename = filename.replace('/', '⁄').replace('\\', '⁄')
        path_components.append(safe_filename)
        
        # Join with forward slashes for R2 object key
        object_key = '/'.join(path_components)
        
        logger.debug(f"Generated R2 object key for file {file_id}: {object_key}")
        return object_key
        
    except Exception as e:
        logger.error(f"Error generating R2 object key for file {file_id}: {str(e)}")
        # Fallback to simple key
        return f"files/{file_id}/{filename}" 