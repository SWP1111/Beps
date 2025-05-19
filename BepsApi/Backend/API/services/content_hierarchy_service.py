import logging
from models import ContentRelChannels, ContentRelFolders, ContentRelPages
from extensions import db, cache
from typing import Dict, List, Optional, Tuple, Any

class ContentHierarchyService:
    """
    Service for managing content hierarchy (channels > folders > files)
    
    Provides methods to:
    - Build a complete tree structure of all content
    - Get children of a specific channel/folder
    - Find the path to a specific file
    - Cache the hierarchy for improved performance
    """
    
    CACHE_TTL = 3600  # Cache time to live (1 hour)
    CACHE_KEY_HIERARCHY = 'content_hierarchy'
    CACHE_KEY_PATH_PREFIX = 'content_path_'
    
    def __init__(self):
        """Initialize the service"""
        pass
        
    def get_full_hierarchy(self, use_cache: bool = True) -> Dict[str, Any]:
        """
        Build and return the complete channel > folder > file hierarchy
        
        Args:
            use_cache: Whether to use cached data (if available)
            
        Returns:
            Dict representing the complete hierarchy
        """
        # Try to get from cache first if requested
        if use_cache:
            cached_hierarchy = cache.get(self.CACHE_KEY_HIERARCHY)
            if cached_hierarchy:
                return cached_hierarchy
                
        # Build hierarchy
        hierarchy = self._build_hierarchy()
        
        # Cache for future requests
        cache.set(self.CACHE_KEY_HIERARCHY, hierarchy, timeout=self.CACHE_TTL)
        
        return hierarchy
    
    def clear_cache(self) -> None:
        """Clear all cached hierarchy data"""
        cache.delete(self.CACHE_KEY_HIERARCHY)
        # Future enhancement: Could selectively clear specific paths
    
    def get_channel_children(self, channel_id: int) -> List[int]:
        """
        Get all top-level folders for a specific channel
        
        Args:
            channel_id: ID of the channel to query
            
        Returns:
            List of folder IDs that are direct children of the channel
        """
        folders = ContentRelFolders.query.filter_by(
            parent_id=None,
            channel_id=channel_id,
            is_deleted=False
        ).all()
        
        return [folder.id for folder in folders]
    
    def get_folder_children(self, folder_id: int) -> Tuple[List[int], bool]:
        """
        Get children of a specific folder
        
        Args:
            folder_id: ID of the folder to query
            
        Returns:
            Tuple of (child_ids, is_leaf_folder) where:
            - child_ids: List of IDs (either folder IDs or page IDs depending on is_leaf_folder)
            - is_leaf_folder: True if this folder has no subfolders (contains pages)
        """
        # Check for subfolders
        subfolders = ContentRelFolders.query.filter_by(
            parent_id=folder_id,
            is_deleted=False
        ).all()
        
        # If there are no subfolders, it's a leaf folder
        is_leaf_folder = len(subfolders) == 0
        
        if is_leaf_folder:
            # Return page IDs
            pages = ContentRelPages.query.filter_by(
                folder_id=folder_id,
                is_deleted=False
            ).all()
            return [page.id for page in pages], True
        else:
            # Return subfolder IDs
            return [folder.id for folder in subfolders], False
    
    def get_file_path(self, file_id: int, use_cache: bool = True) -> Dict[str, Any]:
        """
        Get the complete path to a specific file
        
        Args:
            file_id: ID of the file (page) to find
            use_cache: Whether to use cached data (if available)
            
        Returns:
            Dict containing:
            - path_components: List of names from root to file
            - ids: Dict mapping each level to its ID
        """
        cache_key = f"{self.CACHE_KEY_PATH_PREFIX}{file_id}"
        
        # Try cache first if requested
        if use_cache:
            cached_path = cache.get(cache_key)
            if cached_path:
                return cached_path
        
        # Start with the file
        page = ContentRelPages.query.filter_by(id=file_id, is_deleted=False).first()
        if not page:
            return None
            
        # Build path components
        path_components = [page.name]
        ids = {'file': file_id}
        
        # Get folder
        folder_id = page.folder_id
        ids['folder'] = folder_id
        
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
                    ids['channel'] = channel.id
                break
                
            folder_id = folder.parent_id
        
        # Reverse to get root -> file order
        path_components.reverse()
        
        result = {
            'path_components': path_components,
            'ids': ids,
            'path_string': '/'.join(path_components)
        }
        
        # Cache result
        cache.set(cache_key, result, timeout=self.CACHE_TTL)
        
        return result
    
    def _build_hierarchy(self) -> Dict[str, Any]:
        """
        Build the complete hierarchy as a nested dictionary
        
        Returns:
            Dict containing the complete hierarchy tree
        """
        try:
            # Start with channels
            channels = ContentRelChannels.query.filter_by(is_deleted=False).all()
            
            hierarchy = []
            
            for channel in channels:
                channel_node = {
                    'id': channel.id,
                    'name': channel.name,
                    'type': 'channel',
                    'folders': []
                }
                
                # Get top-level folders for this channel
                top_folders = ContentRelFolders.query.filter_by(
                    channel_id=channel.id,
                    parent_id=None,
                    is_deleted=False
                ).all()
                
                # Process each top folder and its children recursively
                for folder in top_folders:
                    folder_node = self._process_folder(folder)
                    channel_node['folders'].append(folder_node)
                    
                hierarchy.append(channel_node)
                
            return {
                'channels': hierarchy,
                'timestamp': db.func.now()
            }
                
        except Exception as e:
            logging.error(f"Error building content hierarchy: {str(e)}")
            return {
                'channels': [],
                'error': str(e)
            }
    
    def _process_folder(self, folder) -> Dict[str, Any]:
        """
        Recursively process a folder and its children
        
        Args:
            folder: ContentRelFolders instance to process
            
        Returns:
            Dict representing the folder and its contents
        """
        folder_node = {
            'id': folder.id,
            'name': folder.name,
            'type': 'folder',
            'subfolders': [],
            'pages': []
        }
        
        # Get subfolders
        subfolders = ContentRelFolders.query.filter_by(
            parent_id=folder.id,
            is_deleted=False
        ).all()
        
        # Process each subfolder recursively
        for subfolder in subfolders:
            subfolder_node = self._process_folder(subfolder)
            folder_node['subfolders'].append(subfolder_node)
        
        # Get pages in this folder
        pages = ContentRelPages.query.filter_by(
            folder_id=folder.id,
            is_deleted=False
        ).all()
        
        # Add pages
        folder_node['pages'] = [
            {
                'id': page.id,
                'name': page.name,
                'type': 'page',
                'object_id': page.object_id
            }
            for page in pages
        ]
        
        return folder_node 