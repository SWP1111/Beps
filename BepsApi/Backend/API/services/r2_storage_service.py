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
            
        except ValueError as e:
            # This is likely a credentials error
            if "Missing required R2 credentials" in str(e):
                logging.warning(f"🔑 R2 credentials not configured, falling back to object_id check for page detail {detail_id}")
                # When R2 is not available, assume files with object_id have content
                # This is a reasonable assumption since object_id is typically set when content is uploaded
                fallback_result = bool(detail_object_id and detail_object_id.strip())
                logging.debug(f"🔄 Fallback result for page detail {detail_id}: {fallback_result} (object_id: '{detail_object_id}')")
                
                # Cache the fallback result too
                if use_cache:
                    _r2_existence_cache[cache_key] = {
                        'exists': fallback_result,
                        'timestamp': datetime.datetime.now()
                    }
                
                return fallback_result
            else:
                raise
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
        logging.debug(f"🔍 Checking page {page_id} content exists: name='{page_name}', object_id='{page_object_id}'")
        
        if not page_object_id or page_object_id.strip() == '':
            logging.debug(f"❌ Page {page_id} has no object_id")
            return False
        
        # Generate cache key
        cache_key = f"page_{page_id}_{updated_at.timestamp() if updated_at else 0}"
        
        # Check cache first
        if use_cache and cache_key in _r2_existence_cache:
            cache_entry = _r2_existence_cache[cache_key]
            # Check if cache entry is still valid
            if (datetime.datetime.now() - cache_entry['timestamp']).seconds < CACHE_TTL_SECONDS:
                logging.debug(f"📋 Cache hit for page {page_id}: {cache_entry['exists']}")
                return cache_entry['exists']
        
        try:
            # Import here to avoid circular imports
            from blueprints.contents.r2_utils import check_r2_object_exists, generate_r2_object_key
            
            # If object_id is already an R2 object key, check it directly
            if '/' in page_object_id:
                logging.debug(f"🔗 Page {page_id} object_id looks like R2 key: '{page_object_id}'")
                result = check_r2_object_exists(page_object_id)
                logging.debug(f"🔍 Direct R2 check for page {page_id}: {result}")
            else:
                # Generate the R2 object key from hierarchy and check
                filename = page_name if page_name else "file"
                if not any(filename.endswith(ext) for ext in ['.png', '.jpg', '.jpeg', '.gif', '.webp', '.pdf']):
                    filename += '.png'  # Default extension for pages
                
                logging.debug(f"🏗️ Generating R2 object key for page {page_id} with filename: '{filename}'")
                object_key = generate_r2_object_key(page_id, filename, is_page_detail=False)
                logging.debug(f"🔑 Generated object key for page {page_id}: '{object_key}'")
                result = check_r2_object_exists(object_key)
                logging.debug(f"🔍 Generated key R2 check for page {page_id}: {result}")
            
            # Cache the result
            if use_cache:
                _r2_existence_cache[cache_key] = {
                    'exists': result,
                    'timestamp': datetime.datetime.now()
                }
                
                # Simple cache cleanup
                R2StorageService._cleanup_cache()
            
            logging.debug(f"✅ Final result for page {page_id}: {result}")
            return result
            
        except ValueError as e:
            # This is likely a credentials error
            if "Missing required R2 credentials" in str(e):
                logging.warning(f"🔑 R2 credentials not configured, falling back to object_id check for page {page_id}")
                # When R2 is not available, assume files with object_id have content
                # This is a reasonable assumption since object_id is typically set when content is uploaded
                fallback_result = bool(page_object_id and page_object_id.strip())
                logging.debug(f"🔄 Fallback result for page {page_id}: {fallback_result} (object_id: '{page_object_id}')")
                
                # Cache the fallback result too
                if use_cache:
                    _r2_existence_cache[cache_key] = {
                        'exists': fallback_result,
                        'timestamp': datetime.datetime.now()
                    }
                
                return fallback_result
            else:
                raise
        except Exception as e:
            logging.error(f"❌ Error checking R2 content for page {page_id}: {str(e)}", exc_info=True)
            # Fallback to simple object_id check
            fallback_result = page_object_id is not None and page_object_id.strip() != ''
            logging.debug(f"🔄 Fallback result for page {page_id}: {fallback_result}")
            return fallback_result
    
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