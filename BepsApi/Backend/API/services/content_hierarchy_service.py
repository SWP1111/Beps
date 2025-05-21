import logging
import os
import uuid
import datetime
from models import ContentRelChannels, ContentRelFolders, ContentRelPages, ContentRelPageDetails, ContentManager
from extensions import db, cache
from typing import Dict, List, Optional, Tuple, Any
from sqlalchemy import or_, and_

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
    
    def clear_hierarchy_cache(self) -> None:
        """Clear all cached hierarchy data"""
        cache.delete(self.CACHE_KEY_HIERARCHY)
        # Future enhancement: Could selectively clear specific paths
    
    clear_cache = clear_hierarchy_cache  # Alias for backward compatibility
    
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
                'timestamp': datetime.datetime.now().isoformat()
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

    #
    # New methods to support CRUD operations for channels, folders, and files
    #
    
    def get_channels(self) -> List[Dict[str, Any]]:
        """
        Get all channels
        
        Returns:
            List of channel objects with id, name, etc.
        """
        channels = ContentRelChannels.query.filter_by(is_deleted=False).all()
        
        return [
            {
                'id': channel.id,
                'name': channel.name,
                'is_new': channel.created_at and (datetime.datetime.now() - channel.created_at).days < 7
            }
            for channel in channels
        ]
        
    def get_channel_hierarchy(self, channel_id: int, filters: Dict[str, bool] = None) -> Dict[str, Any]:
        """
        Get hierarchy for a specific channel, with optional filtering
        
        Args:
            channel_id: ID of the channel
            filters: Dict of filter flags (e.g. {'all': True, 'reviewing': True})
            
        Returns:
            Dict containing the filtered hierarchy for this channel
        """
        # Default filter is 'all'
        if not filters:
            filters = {'all': True}
            
        # Get the full hierarchy (potentially from cache)
        full_hierarchy = self.get_full_hierarchy()
        
        # Find the specific channel
        channel_data = None
        for channel in full_hierarchy.get('channels', []):
            if channel.get('id') == channel_id:
                channel_data = channel
                break
                
        if not channel_data:
            return {'folders': []}
            
        # Apply filters if needed
        if not filters.get('all', True):
            channel_data = self._apply_filters_to_hierarchy(channel_data, filters)
            
        return {
            'folders': channel_data.get('folders', [])
        }
        
    def _apply_filters_to_hierarchy(self, hierarchy_node: Dict[str, Any], filters: Dict[str, bool]) -> Dict[str, Any]:
        """
        Apply status filters to a hierarchy node and its children
        
        Args:
            hierarchy_node: Dict representing a node in the hierarchy
            filters: Dict of filter flags
            
        Returns:
            Filtered copy of the hierarchy node
        """
        # Create a shallow copy to avoid modifying the original
        filtered_node = hierarchy_node.copy()
        
        # If this is a page/file node, check its status
        if hierarchy_node.get('type') == 'page':
            # Get the page to check its status
            page = ContentRelPages.query.filter_by(id=hierarchy_node.get('id'), is_deleted=False).first()
            if page:
                # Check if this page's status matches any active filter
                if (filters.get('reviewing') and page.status == '검토중') or \
                   (filters.get('rejected') and page.status == '반려') or \
                   (filters.get('approved') and page.status == '승인') or \
                   (filters.get('updated') and page.status == '업데이트'):
                    return filtered_node
                else:
                    return None
            else:
                return None
                
        # For folders, process subfolders and pages
        if 'subfolders' in hierarchy_node:
            filtered_subfolders = []
            
            # Process each subfolder
            for subfolder in hierarchy_node.get('subfolders', []):
                filtered_subfolder = self._apply_filters_to_hierarchy(subfolder, filters)
                if filtered_subfolder:
                    filtered_subfolders.append(filtered_subfolder)
                    
            filtered_node['subfolders'] = filtered_subfolders
            
        # For folders, process pages
        if 'pages' in hierarchy_node:
            filtered_pages = []
            
            # Process each page
            for page in hierarchy_node.get('pages', []):
                filtered_page = self._apply_filters_to_hierarchy(page, filters)
                if filtered_page:
                    filtered_pages.append(filtered_page)
                    
            filtered_node['pages'] = filtered_pages
            
        # If this node has no children after filtering, return None
        if ('subfolders' in filtered_node and not filtered_node['subfolders']) and \
           ('pages' in filtered_node and not filtered_node['pages']):
            return None
            
        return filtered_node
        
    def get_user_accessible_content(self, user_id: int) -> Tuple[List[int], List[int]]:
        """
        Get content accessible to a specific user
        
        Args:
            user_id: ID of the user
            
        Returns:
            Tuple of (folder_ids, file_ids) that the user has access to
        """
        # Get content assignments for this user from ContentManager table
        content_assignments = ContentManager.query.filter_by(
            user_id=user_id,
            is_deleted=False
        ).all()
        
        folder_ids = [cm.folder_id for cm in content_assignments if cm.folder_id is not None]
        file_ids = [cm.file_id for cm in content_assignments if cm.file_id is not None]
        
        # For folders, add all subfolders and files
        all_folder_ids = folder_ids.copy()
        
        # Process each folder to find subfolders
        for folder_id in folder_ids:
            subfolder_ids = self._get_all_subfolder_ids(folder_id)
            all_folder_ids.extend(subfolder_ids)
            
            # Get page IDs for this folder and subfolders
            page_ids = self._get_all_page_ids_in_folders([folder_id] + subfolder_ids)
            file_ids.extend(page_ids)
            
        return list(set(all_folder_ids)), list(set(file_ids))
        
    def _get_all_subfolder_ids(self, folder_id: int) -> List[int]:
        """
        Get all subfolder IDs recursively for a folder
        
        Args:
            folder_id: ID of the parent folder
            
        Returns:
            List of subfolder IDs
        """
        subfolder_ids = []
        
        # Get direct subfolders
        subfolders = ContentRelFolders.query.filter_by(
            parent_id=folder_id,
            is_deleted=False
        ).all()
        
        for subfolder in subfolders:
            subfolder_ids.append(subfolder.id)
            # Recursively get their subfolders
            child_subfolders = self._get_all_subfolder_ids(subfolder.id)
            subfolder_ids.extend(child_subfolders)
            
        return subfolder_ids
        
    def _get_all_page_ids_in_folders(self, folder_ids: List[int]) -> List[int]:
        """
        Get all page IDs in a list of folders
        
        Args:
            folder_ids: List of folder IDs
            
        Returns:
            List of page IDs
        """
        if not folder_ids:
            return []
            
        pages = ContentRelPages.query.filter(
            ContentRelPages.folder_id.in_(folder_ids),
            ContentRelPages.is_deleted == False
        ).all()
        
        return [page.id for page in pages]
        
    def channel_has_accessible_content(self, channel_id: int, user_id: int) -> bool:
        """
        Check if a channel contains any content accessible to a user
        
        Args:
            channel_id: ID of the channel
            user_id: ID of the user
            
        Returns:
            True if the user has access to any content in the channel
        """
        # Get accessible folders and files for the user
        folder_ids, file_ids = self.get_user_accessible_content(user_id)
        
        if not folder_ids and not file_ids:
            return False
            
        # Get all folders in this channel
        channel_folders = ContentRelFolders.query.filter_by(
            channel_id=channel_id,
            is_deleted=False
        ).all()
        
        channel_folder_ids = [folder.id for folder in channel_folders]
        
        # Check if any of the user's accessible folders are in this channel
        for folder_id in folder_ids:
            if folder_id in channel_folder_ids:
                return True
                
        # Check if any of the user's accessible files are in this channel
        for file_id in file_ids:
            page = ContentRelPages.query.filter_by(id=file_id, is_deleted=False).first()
            if page and page.folder_id in channel_folder_ids:
                return True
                
        return False
        
    def get_file_download_info(self, file_id: int) -> Tuple[Optional[str], Optional[str]]:
        """
        Get download information for a file
        
        Args:
            file_id: ID of the file (page)
            
        Returns:
            Tuple of (file_path, filename) or (None, None) if not found
        """
        page = ContentRelPages.query.filter_by(id=file_id, is_deleted=False).first()
        if not page:
            return None, None
            
        # In a real implementation, this would get the actual file path
        # Here we simulate by returning a placeholder
        # Actual implementation would retrieve the file path from storage
        file_path = page.file_path if hasattr(page, 'file_path') and page.file_path else None
        filename = page.name if page.name else f"file_{file_id}"
        
        # Add extension if missing
        if filename and '.' not in filename:
            filename += '.pdf'  # Default extension
            
        return file_path, filename
        
    def create_channel(self, name: str, created_by: int) -> int:
        """
        Create a new channel
        
        Args:
            name: Name of the channel
            created_by: User ID of creator
            
        Returns:
            ID of the created channel
        """
        try:
            # Create new channel in ContentRelChannels table
            channel = ContentRelChannels(
                name=name,
                object_id=str(uuid.uuid4()),
                created_by=created_by,
                created_at=datetime.datetime.now()
            )
            
            db.session.add(channel)
            db.session.commit()
            
            # Clear cache to reflect changes
            self.clear_hierarchy_cache()
            
            return channel.id
        except Exception as e:
            db.session.rollback()
            logging.error(f"Error creating channel: {str(e)}")
            raise
            
    def delete_channel(self, channel_id: int, deleted_by: int) -> bool:
        """
        Delete a channel (mark as deleted)
        
        Args:
            channel_id: ID of the channel to delete
            deleted_by: User ID performing the deletion
            
        Returns:
            True if successful, False otherwise
        """
        try:
            channel = ContentRelChannels.query.filter_by(id=channel_id, is_deleted=False).first()
            if not channel:
                return False
                
            # Mark as deleted
            channel.is_deleted = True
            channel.deleted_by = deleted_by
            channel.deleted_at = datetime.datetime.now()
            
            # Mark all associated folders as deleted
            folders = ContentRelFolders.query.filter_by(
                channel_id=channel_id,
                is_deleted=False
            ).all()
            
            for folder in folders:
                self._mark_folder_as_deleted(folder.id, deleted_by)
                
            db.session.commit()
            
            # Clear cache to reflect changes
            self.clear_hierarchy_cache()
            
            return True
        except Exception as e:
            db.session.rollback()
            logging.error(f"Error deleting channel: {str(e)}")
            return False
            
    def create_folder(self, name: str, channel_id: int, parent_id: Optional[int] = None, user_id: int = None) -> int:
        """
        Create a new folder
        
        Args:
            name: Name of the folder
            channel_id: ID of the channel it belongs to
            parent_id: Optional parent folder ID
            user_id: User ID of creator
            
        Returns:
            ID of the created folder
        """
        try:
            # Create new folder in ContentRelFolders table
            folder = ContentRelFolders(
                name=name,
                channel_id=channel_id,
                parent_id=parent_id,
                object_id=str(uuid.uuid4()),
                created_by=user_id,
                created_at=datetime.datetime.now()
            )
            
            db.session.add(folder)
            db.session.commit()
            
            # Clear cache to reflect changes
            self.clear_hierarchy_cache()
            
            return folder.id
        except Exception as e:
            db.session.rollback()
            logging.error(f"Error creating folder: {str(e)}")
            raise
            
    def delete_folder(self, folder_id: int, deleted_by: int) -> bool:
        """
        Delete a folder and all its contents
        
        Args:
            folder_id: ID of the folder to delete
            deleted_by: User ID performing the deletion
            
        Returns:
            True if successful, False otherwise
        """
        try:
            return self._mark_folder_as_deleted(folder_id, deleted_by)
        except Exception as e:
            db.session.rollback()
            logging.error(f"Error deleting folder: {str(e)}")
            return False
            
    def _mark_folder_as_deleted(self, folder_id: int, deleted_by: int) -> bool:
        """
        Mark a folder and all its contents as deleted
        
        Args:
            folder_id: ID of the folder to mark as deleted
            deleted_by: User ID performing the deletion
            
        Returns:
            True if successful, False otherwise
        """
        folder = ContentRelFolders.query.filter_by(id=folder_id, is_deleted=False).first()
        if not folder:
            return False
            
        # Mark folder as deleted
        folder.is_deleted = True
        folder.deleted_by = deleted_by
        folder.deleted_at = datetime.datetime.now()
        
        # Mark all subfolders as deleted
        subfolders = ContentRelFolders.query.filter_by(
            parent_id=folder_id,
            is_deleted=False
        ).all()
        
        for subfolder in subfolders:
            self._mark_folder_as_deleted(subfolder.id, deleted_by)
            
        # Mark all pages in this folder as deleted
        pages = ContentRelPages.query.filter_by(
            folder_id=folder_id,
            is_deleted=False
        ).all()
        
        for page in pages:
            page.is_deleted = True
            page.deleted_by = deleted_by
            page.deleted_at = datetime.datetime.now()
            
        db.session.commit()
        
        # Clear cache to reflect changes
        self.clear_hierarchy_cache()
        
        return True
        
    def add_file(self, file_path: str, name: str, channel_id: int, folder_id: Optional[int] = None, 
                 version: str = "1.0", user_id: Optional[int] = None) -> int:
        """
        Add a new file (page)
        
        Args:
            file_path: Path to the uploaded file
            name: Name of the file
            channel_id: ID of the channel
            folder_id: Optional folder ID (required if not at root)
            version: Version string
            user_id: User ID of the uploader
            
        Returns:
            ID of the created file
        """
        try:
            # If no folder_id provided, find or create a default folder
            if not folder_id:
                # Try to find a "root" folder for this channel
                root_folder = ContentRelFolders.query.filter_by(
                    channel_id=channel_id,
                    parent_id=None,
                    name="Files",  # Default root folder name
                    is_deleted=False
                ).first()
                
                if not root_folder:
                    # Create a default root folder
                    folder = ContentRelFolders(
                        name="Files",
                        channel_id=channel_id,
                        parent_id=None,
                        object_id=str(uuid.uuid4()),
                        created_by=user_id,
                        created_at=datetime.datetime.now()
                    )
                    
                    db.session.add(folder)
                    db.session.flush()  # Get ID without committing
                    folder_id = folder.id
                else:
                    folder_id = root_folder.id
                    
            # Create the file (page) entry
            page = ContentRelPages(
                name=name,
                folder_id=folder_id,
                object_id=str(uuid.uuid4()),
                version=version,
                status='검토중',  # Default status
                file_path=file_path,  # Store the file path
                created_by=user_id,
                created_at=datetime.datetime.now()
            )
            
            db.session.add(page)
            db.session.commit()
            
            # Clear cache to reflect changes
            self.clear_hierarchy_cache()
            
            return page.id
        except Exception as e:
            db.session.rollback()
            logging.error(f"Error adding file: {str(e)}")
            raise
            
    def delete_files(self, file_ids: List[int], deleted_by: int) -> Tuple[List[int], List[int]]:
        """
        Delete multiple files (mark as deleted)
        
        Args:
            file_ids: List of file IDs to delete
            deleted_by: User ID performing the deletion
            
        Returns:
            Tuple of (successful_ids, failed_ids)
        """
        successful_ids = []
        failed_ids = []
        
        try:
            for file_id in file_ids:
                page = ContentRelPages.query.filter_by(id=file_id, is_deleted=False).first()
                
                if not page:
                    failed_ids.append(file_id)
                    continue
                    
                # Mark as deleted
                page.is_deleted = True
                page.deleted_by = deleted_by
                page.deleted_at = datetime.datetime.now()
                
                successful_ids.append(file_id)
                
            db.session.commit()
            
            # Clear cache to reflect changes
            self.clear_hierarchy_cache()
            
            return successful_ids, failed_ids
        except Exception as e:
            db.session.rollback()
            logging.error(f"Error deleting files: {str(e)}")
            raise 