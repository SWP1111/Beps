"""
R2 Storage Service

Handles all R2/Cloudflare storage operations including:
- File existence checking
- Path generation
- Upload/download operations
"""

import logging
import datetime
from typing import Optional, Dict, Any

# Cache for R2 existence checks to improve performance
_r2_existence_cache: Dict[str, Dict[str, Any]] = {}
CACHE_TTL_SECONDS = 300  # 5 minutes


class R2StorageService:
    """Service for handling R2 storage operations"""
    
    @staticmethod
    def check_page_detail_content_exists(detail_id: int, detail_name: str = None, 
                                       detail_object_id: str = None, 
                                       updated_at: datetime.datetime = None,
                                       use_cache: bool = True) -> bool:
        """
        Check if a page detail's content actually exists in R2 storage
        
        Args:
            detail_id: ID of the page detail
            detail_name: Name of the detail (for path generation)
            detail_object_id: Object ID from database
            updated_at: Last update timestamp (for cache invalidation)
            use_cache: Whether to use caching
            
        Returns:
            True if file exists in R2, False otherwise
        """
        if not detail_object_id or detail_object_id.strip() == '':
            return False
        
        # Generate cache key
        cache_key = f"page_detail_{detail_id}_{updated_at.timestamp() if updated_at else 0}"
        
        # Check cache first
        if use_cache and cache_key in _r2_existence_cache:
            cache_entry = _r2_existence_cache[cache_key]
            # Check if cache entry is still valid
            if (datetime.datetime.now() - cache_entry['timestamp']).seconds < CACHE_TTL_SECONDS:
                return cache_entry['exists']
        
        try:
            # Import here to avoid circular imports
            from blueprints.contents.r2_utils import check_r2_object_exists, generate_r2_object_key
            
            # If object_id is already an R2 object key, check it directly
            if '/' in detail_object_id:
                result = check_r2_object_exists(detail_object_id)
            else:
                # Generate the R2 object key from hierarchy and check
                filename = detail_name if detail_name else "detail"
                if not any(filename.endswith(ext) for ext in ['.pdf', '.webm', '.mp4', '.avi', '.mov', '.wmv', '.doc', '.docx', '.ppt', '.pptx', '.xls', '.xlsx']):
                    filename += '.pdf'  # Default extension
                
                object_key = generate_r2_object_key(detail_id, filename, is_page_detail=True)
                result = check_r2_object_exists(object_key)
            
            # Cache the result
            if use_cache:
                _r2_existence_cache[cache_key] = {
                    'exists': result,
                    'timestamp': datetime.datetime.now()
                }
                
                # Simple cache cleanup
                R2StorageService._cleanup_cache()
            
            return result
            
        except Exception as e:
            logging.error(f"Error checking R2 content for page detail {detail_id}: {str(e)}")
            # Fallback to simple object_id check
            return detail_object_id is not None and detail_object_id.strip() != ''
    
    @staticmethod
    def check_page_content_exists(page_id: int, page_name: str = None, 
                                page_object_id: str = None,
                                updated_at: datetime.datetime = None,
                                use_cache: bool = True) -> bool:
        """
        Check if a page's content actually exists in R2 storage
        
        Args:
            page_id: ID of the page
            page_name: Name of the page (for path generation)
            page_object_id: Object ID from database
            updated_at: Last update timestamp (for cache invalidation)
            use_cache: Whether to use caching
            
        Returns:
            True if file exists in R2, False otherwise
        """
        if not page_object_id or page_object_id.strip() == '':
            return False
        
        # Generate cache key
        cache_key = f"page_{page_id}_{updated_at.timestamp() if updated_at else 0}"
        
        # Check cache first
        if use_cache and cache_key in _r2_existence_cache:
            cache_entry = _r2_existence_cache[cache_key]
            # Check if cache entry is still valid
            if (datetime.datetime.now() - cache_entry['timestamp']).seconds < CACHE_TTL_SECONDS:
                return cache_entry['exists']
        
        try:
            # Import here to avoid circular imports
            from blueprints.contents.r2_utils import check_r2_object_exists, generate_r2_object_key
            
            # If object_id is already an R2 object key, check it directly
            if '/' in page_object_id:
                result = check_r2_object_exists(page_object_id)
            else:
                # Generate the R2 object key from hierarchy and check
                filename = page_name if page_name else "file"
                if not any(filename.endswith(ext) for ext in ['.png', '.jpg', '.jpeg', '.gif', '.webp', '.pdf']):
                    filename += '.png'  # Default extension for pages
                
                object_key = generate_r2_object_key(page_id, filename, is_page_detail=False)
                result = check_r2_object_exists(object_key)
            
            # Cache the result
            if use_cache:
                _r2_existence_cache[cache_key] = {
                    'exists': result,
                    'timestamp': datetime.datetime.now()
                }
                
                # Simple cache cleanup
                R2StorageService._cleanup_cache()
            
            return result
            
        except Exception as e:
            logging.error(f"Error checking R2 content for page {page_id}: {str(e)}")
            # Fallback to simple object_id check
            return page_object_id is not None and page_object_id.strip() != ''
    
    @staticmethod
    def _cleanup_cache():
        """Clean up old cache entries to prevent memory bloat"""
        if len(_r2_existence_cache) > 1000:
            # Remove entries older than TTL
            now = datetime.datetime.now()
            keys_to_remove = []
            
            for key, entry in _r2_existence_cache.items():
                if (now - entry['timestamp']).seconds > CACHE_TTL_SECONDS:
                    keys_to_remove.append(key)
            
            for key in keys_to_remove:
                del _r2_existence_cache[key]
            
            # If still too many, remove oldest entries
            if len(_r2_existence_cache) > 800:
                oldest_keys = sorted(_r2_existence_cache.keys(), 
                                   key=lambda k: _r2_existence_cache[k]['timestamp'])[:200]
                for key in oldest_keys:
                    del _r2_existence_cache[key]
    
    @staticmethod
    def clear_cache():
        """Clear all cached R2 existence checks"""
        global _r2_existence_cache
        _r2_existence_cache.clear() 