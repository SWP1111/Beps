document.addEventListener('DOMContentLoaded', function() {
    // DOM elements
    const permissionScopeRadios = document.querySelectorAll('input[name="permission-scope"]');
    const folderCols = document.querySelectorAll('.folder-col');
    const fileCol = document.querySelector('.file-col');
    const channelSelect = document.getElementById('channel-select');
    const folder1Select = document.getElementById('folder1-select');
    const folder2Select = document.getElementById('folder2-select');
    const folder3Select = document.getElementById('folder3-select');
    const fileSelect = document.getElementById('file-select');
    const managerInput = document.getElementById('manager-input');
    const addBtn = document.getElementById('add-btn');
    const errorMessage = document.getElementById('error-message');
    const permissionsListBody = document.getElementById('permissions-list-body');
    
    // New UI elements
    const companySelect = document.getElementById('company-select');
    const departmentSelect = document.getElementById('department-select');
    const positionSelect = document.getElementById('position-select');
    const nameSelect = document.getElementById('name-select');
    const validationMessage = document.getElementById('validation-message');

    // Base API URL from config
    const url = typeof baseUrl !== "undefined" ? baseUrl : "http://172.16.8.208:20000";
    
    // Ensure url doesn't end with a slash
    const baseApiUrl = url.endsWith('/') ? url.slice(0, -1) : url;
    
    console.log('Using API base URL:', baseApiUrl);
    
    // Store the content hierarchy tree
    let contentHierarchy = null;
    
    // Make sure contentHierarchy is defined globally
    window.contentHierarchy = null;

    // Function to toggle visibility of columns based on selected permission scope
    function updateColumnsVisibility() {
        const selectedScope = document.querySelector('input[name="permission-scope"]:checked').value;
        
        // Get all folder and file columns from both the input table and permissions list
        const allFolderCols = document.querySelectorAll('.folder-col, .folder1-col, .folder2-col, .folder3-col');
        const allFileCols = document.querySelectorAll('.file-col');
        
        // Also specifically update the table headers
        const inputTableHeader = document.getElementById('input-table-header');
        const permissionsTableHeader = document.querySelector('#permissions-table thead tr');
        
        if (selectedScope === 'channel') {
            // Hide folder and file columns
            allFolderCols.forEach(col => col.classList.add('hidden'));
            allFileCols.forEach(col => col.classList.add('hidden'));
            
            // Also update header colspans if needed
            if (inputTableHeader) {
                const thElements = inputTableHeader.querySelectorAll('th');
                thElements.forEach(th => {
                    if (th.classList.contains('folder-col') || th.classList.contains('file-col')) {
                        th.classList.add('hidden');
                    }
                });
            }
        } else if (selectedScope === 'folder') {
            // Show folder columns, hide file column
            allFolderCols.forEach(col => col.classList.remove('hidden'));
            allFileCols.forEach(col => col.classList.add('hidden'));
            
            // Update headers
            if (inputTableHeader) {
                const thElements = inputTableHeader.querySelectorAll('th');
                thElements.forEach(th => {
                    if (th.classList.contains('folder-col')) {
                        th.classList.remove('hidden');
                    }
                    if (th.classList.contains('file-col')) {
                        th.classList.add('hidden');
                    }
                });
            }
        } else if (selectedScope === 'file') {
            // Show all columns
            allFolderCols.forEach(col => col.classList.remove('hidden'));
            allFileCols.forEach(col => col.classList.remove('hidden'));
            
            // Update headers
            if (inputTableHeader) {
                const thElements = inputTableHeader.querySelectorAll('th');
                thElements.forEach(th => {
                    th.classList.remove('hidden');
                });
            }
        }
        
        // Force browser to reflow the table
        if (inputTableHeader) {
            inputTableHeader.parentElement.style.display = 'none';
            setTimeout(() => {
                inputTableHeader.parentElement.style.display = '';
            }, 10);
        }
    }
    
    // Fetch the complete content hierarchy once
    function fetchContentHierarchy() {
        console.log('Fetching content hierarchy...');
        
        // First try main API endpoint
        fetch(`${baseApiUrl}/contents/hierarchy`, {
            method: 'GET',
            credentials: 'include',
            headers: {
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            }
        })
        .then(response => {
            if (!response.ok) {
                console.warn(`Main API endpoint failed: ${response.status}. Trying fallback...`);
                throw new Error('Main API endpoint failed');
            }
            console.log('Main API endpoint succeeded');
            return response.json();
        })
        .then(data => {
            processHierarchyData(data);
        })
        .catch(error => {
            console.warn('Trying fallback endpoint...', error);
            
            // Try fallback endpoint
            fetch(`${baseApiUrl}/hierarchy`, {
                method: 'GET',
                credentials: 'include',
                headers: {
                    'Content-Type': 'application/json',
                    'Accept': 'application/json'
                }
            })
            .then(response => {
                if (!response.ok) {
                    console.error(`Fallback endpoint failed: ${response.status}`);
                    throw new Error('Fallback endpoint failed');
                }
                console.log('Fallback API endpoint succeeded');
                return response.json();
            })
            .then(data => {
                processHierarchyData(data);
            })
            .catch(fallbackError => {
                console.error('All API endpoints failed:', fallbackError);
                errorMessage.textContent = '콘텐츠 구조를 불러오는데 실패했습니다. 샘플 데이터를 사용합니다.';
                
                // Initialize with sample data when all API calls fail
                initializeWithSampleData();
            });
        });
    }
    
    // Process hierarchy data once it's fetched
    function processHierarchyData(data) {
        console.log('Content hierarchy loaded successfully');
        
        // Log raw data structure to debug
        console.log('Raw hierarchy data sample:', JSON.stringify(data).substring(0, 300) + '...');
        
        // Validate hierarchy structure
        if (!data.channels || !Array.isArray(data.channels)) {
            console.error('Invalid hierarchy structure - channels missing or not an array', data);
            // Initialize with sample data if the structure is invalid
            initializeWithSampleData();
            return;
        }
        
        console.log(`Loaded ${data.channels.length} channels`);
        
        // Debug log the structure
        let folderCount = 0;
        let pageCount = 0;
        
        data.channels.forEach(channel => {
            if (channel.folders && Array.isArray(channel.folders)) {
                folderCount += channel.folders.length;
                channel.folders.forEach(folder => {
                    countFolderContents(folder, stats => {
                        folderCount += stats.folders;
                        pageCount += stats.pages;
                    });
                });
            }
        });
        
        console.log(`Hierarchy contains ${folderCount} folders and ${pageCount} pages`);
        
        // Normalize the hierarchy data structure
        data = normalizeHierarchyData(data);
        
        // Store the hierarchy data both locally and globally
        contentHierarchy = data;
        window.contentHierarchy = data;
        
        // Load channel options from the hierarchy
        loadChannelOptions();
    }

    // Helper function to count folders and pages in a folder structure
    function countFolderContents(folder, callback) {
        let stats = { folders: 0, pages: 0 };
        
        if (folder.subfolders && Array.isArray(folder.subfolders)) {
            stats.folders += folder.subfolders.length;
            folder.subfolders.forEach(subfolder => {
                countFolderContents(subfolder, subStats => {
                    stats.folders += subStats.folders;
                    stats.pages += subStats.pages;
                });
            });
        }
        
        if (folder.pages && Array.isArray(folder.pages)) {
            stats.pages += folder.pages.length;
        }
        
        callback(stats);
    }

    // Initialize with sample data for testing when API fails
    function initializeWithSampleData() {
        console.log('Initializing with sample data');
        const sampleData = {
            channels: [
                {
                    id: 1,
                    name: "샘플 채널",
                    type: "channel",
                    folders: [
                        {
                            id: 2,
                            name: "샘플 폴더1",
                            type: "folder",
                            subfolders: [],
                            pages: [
                                {
                                    id: 3,
                                    name: "샘플 파일1",
                                    type: "page"
                                },
                                {
                                    id: 4,
                                    name: "샘플 파일2",
                                    type: "page"
                                }
                            ]
                        },
                        {
                            id: 5,
                            name: "샘플 폴더2",
                            type: "folder",
                            subfolders: [
                                {
                                    id: 6,
                                    name: "샘플 하위폴더",
                                    type: "folder",
                                    subfolders: [],
                                    pages: [
                                        {
                                            id: 7,
                                            name: "샘플 하위 파일",
                                            type: "page"
                                        }
                                    ]
                                }
                            ],
                            pages: []
                        }
                    ]
                },
                {
                    id: 8,
                    name: "샘플 채널2",
                    type: "channel",
                    folders: []
                }
            ],
            timestamp: new Date().toISOString()
        };
        
        // Store the sample data in both local and global variables
        contentHierarchy = sampleData;
        window.contentHierarchy = sampleData;
        
        // Load channel options from the sample data
        loadChannelOptions();
    }

    // Load channel options from the content hierarchy
    function loadChannelOptions() {
        // Clear existing options except the first placeholder
        channelSelect.innerHTML = '<option value="">선택</option>';
        
        // Add channel options from the hierarchy
        if (contentHierarchy && contentHierarchy.channels && Array.isArray(contentHierarchy.channels)) {
            // Sort channels by name
            const sortedChannels = [...contentHierarchy.channels].sort((a, b) => {
                return a.name.localeCompare(b.name, 'ko');
            });
            
            sortedChannels.forEach(channel => {
                const option = document.createElement('option');
                option.value = channel.id;
                option.textContent = channel.name;
                channelSelect.appendChild(option);
            });
            
            console.log(`Loaded ${sortedChannels.length} channels into dropdown`);
        } else {
            console.warn('No channels available to load');
        }
    }

    // Load folder options based on selected channel
    function loadFolderOptions(parentType, parentId, selectElement, level) {
        // Clear the current select and all dependent selects
        selectElement.innerHTML = '<option value="">선택</option>';
        
        if (level === 1) {
            // Top level folders - from channel
            folder2Select.innerHTML = '<option value="">선택</option>';
            folder3Select.innerHTML = '<option value="">선택</option>';
            fileSelect.innerHTML = '<option value="">선택</option>';
            
            if (!contentHierarchy) return;
            
            // Find the selected channel
            const selectedChannel = contentHierarchy.channels.find(channel => channel.id == parentId);
            if (!selectedChannel || !selectedChannel.folders) return;
            
            // Sort folders by name
            const sortedFolders = [...selectedChannel.folders].sort((a, b) => {
                return a.name.localeCompare(b.name, 'ko');
            });
            
            // Add folder options from selected channel
            sortedFolders.forEach(folder => {
                const option = document.createElement('option');
                option.value = folder.id;
                option.textContent = folder.name;
                selectElement.appendChild(option);
            });
        } 
        else if (level === 2 || level === 3) {
            // Find the parent folder and its subfolders
            let parentFolder = null;
            
            if (!contentHierarchy) return;
            
            // Loop through channels to find the target folder
            for (const channel of contentHierarchy.channels) {
                parentFolder = findFolderById(channel.folders, parentId);
                if (parentFolder) break;
            }
            
            if (!parentFolder || !parentFolder.subfolders) return;
            
            // Clear dependent selects
            if (level === 2) {
                folder3Select.innerHTML = '<option value="">선택</option>';
                fileSelect.innerHTML = '<option value="">선택</option>';
            } else if (level === 3) {
                fileSelect.innerHTML = '<option value="">선택</option>';
            }
            
            // Sort subfolders by name
            const sortedSubfolders = [...parentFolder.subfolders].sort((a, b) => {
                return a.name.localeCompare(b.name, 'ko');
            });
            
            // Add subfolder options
            sortedSubfolders.forEach(subfolder => {
                const option = document.createElement('option');
                option.value = subfolder.id;
                option.textContent = subfolder.name;
                selectElement.appendChild(option);
            });
        }
    }

    // Load file options based on selected folder
    function loadFileOptions(folderId) {
        // Clear existing options
        fileSelect.innerHTML = '<option value="">선택</option>';
        
        console.log(`Loading files for folder ID: ${folderId}`);
        
        // First try the main API endpoint
        fetch(`${baseApiUrl}/contents/folder/children?folder_id=${folderId}`, {
            method: 'GET',
            credentials: 'include',
            headers: {
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            }
        })
        .then(response => {
            if (!response.ok) {
                console.warn(`Main folder children API failed: ${response.status}. Trying fallback...`);
                // Try fallback endpoint
                return fetch(`${baseApiUrl}/folder/children?folder_id=${folderId}`, {
                    method: 'GET',
                    credentials: 'include',
                    headers: {
                        'Content-Type': 'application/json',
                        'Accept': 'application/json'
                    }
                });
            }
            return response;
        })
        .then(response => {
            if (!response.ok) {
                console.error(`All folder children APIs failed: ${response.status}`);
                
                // If we have hierarchy data, try to use it
                if (contentHierarchy) {
                    console.log('Using hierarchy data as fallback');
                    const folder = findSelectedFolder(folderId);
                    if (folder && folder.pages && folder.pages.length > 0) {
                        // Sort pages by name
                        const sortedPages = [...folder.pages].sort((a, b) => {
                            return a.name.localeCompare(b.name, 'ko');
                        });
                        
                        // Add to select
                        sortedPages.forEach(page => {
                            const option = document.createElement('option');
                            option.value = page.id;
                            option.textContent = page.name;
                            fileSelect.appendChild(option);
                        });
                        
                        console.log(`Added ${sortedPages.length} pages from hierarchy data`);
                        return null; // Skip further processing
                    }
                }
                
                throw new Error(`Failed to fetch folder children: ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            if (!data) return; // Skip if we already populated from hierarchy
            
            console.log('Folder children API response:', data);
            
            // Check if this is a leaf folder with pages
            if (data.is_leaf_folder && data.page_ids && data.page_ids.length > 0) {
                // Get all the page IDs
                const pageIds = data.page_ids;
                console.log(`Found ${pageIds.length} page IDs:`, pageIds);
                
                // For simplicity, first display IDs 
                const sortedPageIds = [...pageIds].sort();
                sortedPageIds.forEach(pageId => {
                    const option = document.createElement('option');
                    option.value = pageId;
                    option.textContent = `Page ${pageId}`;
                    fileSelect.appendChild(option);
                });
                
                console.log(`Added ${sortedPageIds.length} pages to file select`);
                
                // Then try to get names by fetching details for each page
                pageIds.forEach(pageId => {
                    fetch(`${baseApiUrl}/contents/file/get_detailed_path?file_id=${pageId}`, {
                        method: 'GET',
                        credentials: 'include',
                        headers: {
                            'Content-Type': 'application/json',
                            'Accept': 'application/json'
                        }
                    })
                    .then(response => {
                        if (!response.ok) {
                            // Try fallback
                            return fetch(`${baseApiUrl}/file/get_detailed_path?file_id=${pageId}`, {
                                method: 'GET',
                                credentials: 'include',
                                headers: {
                                    'Content-Type': 'application/json',
                                    'Accept': 'application/json'
                                }
                            });
                        }
                        return response;
                    })
                    .then(response => {
                        if (!response.ok) {
                            console.warn(`Failed to get name for page ${pageId}`);
                            return null;
                        }
                        return response.json();
                    })
                    .then(detailData => {
                        if (detailData && detailData.detailed_path) {
                            console.log(`Got name for page ${pageId}:`, detailData);
                            // Find the option with this ID and update its text
                            const pathParts = detailData.detailed_path.split('/');
                            const fileName = pathParts[pathParts.length - 1];
                            
                            // Find and update the option element
                            const option = Array.from(fileSelect.options).find(opt => opt.value == pageId);
                            if (option) {
                                option.textContent = fileName;
                            }
                        }
                    })
                    .catch(err => {
                        console.error(`Error getting name for page ${pageId}:`, err);
                    });
                });
            } else {
                console.log(`Folder ${folderId} is not a leaf folder or has no pages`);
            }
        })
        .catch(error => {
            console.error('Error loading files for folder:', error);
            errorMessage.textContent = '파일 목록을 불러오는데 실패했습니다.';
        });
    }

    // Helper function to recursively find a folder by ID
    function findFolderById(folders, folderId) {
        if (!folders || !Array.isArray(folders)) {
            return null;
        }
        
        for (const folder of folders) {
            if (folder.id == folderId) {
                // Log folder structure for debugging
                console.log(`Found folder ${folderId}: ${folder.name}`, {
                    hasSubfolders: folder.subfolders && folder.subfolders.length > 0,
                    subfoldersCount: folder.subfolders ? folder.subfolders.length : 0,
                    hasPages: folder.pages && folder.pages.length > 0,
                    pagesCount: folder.pages ? folder.pages.length : 0
                });
                return folder;
            }
            
            if (folder.subfolders && folder.subfolders.length > 0) {
                const found = findFolderById(folder.subfolders, folderId);
                if (found) return found;
            }
        }
        
        return null;
    }

    // Load existing permissions
    function loadPermissions() {
        fetch(`${baseApiUrl}/content_manager`, {
            method: 'GET',
            credentials: 'include',
            headers: {
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            }
        })
        .then(response => {
            if (!response.ok) {
                throw new Error('Failed to fetch permissions');
            }
            return response.json();
        })
        .then(data => {
            // Clear existing rows
            permissionsListBody.innerHTML = '';
            
            // Add each permission to the table
            data.forEach(permission => {
                addPermissionToTable(permission);
            });
        })
        .catch(error => {
            console.error('Error loading permissions:', error);
            errorMessage.textContent = '권한 정보를 불러오는데 실패했습니다.';
        });
    }

    // Helper function to get path for a file or folder for display in permissions table
    function getPathInHierarchy(type, id) {
        if (!contentHierarchy) return '';
        
        if (type === 'channel') {
            // Find channel by ID
            const channel = contentHierarchy.channels.find(c => c.id == id);
            return channel ? channel.name : '';
        } else if (type === 'folder') {
            // Find folder by ID and build path
            let folderPath = '';
            let folder = null;
            
            // Search for the folder in each channel
            for (const channel of contentHierarchy.channels) {
                folder = findFolderById(channel.folders, id);
                if (folder) {
                    // If found, create path: Channel > Folder(s)
                    folderPath = `${channel.name}/${getFolderPathFromHierarchy(channel.folders, id)}`;
                    break;
                }
            }
            
            return folderPath;
        } else if (type === 'file') {
            // Find file by ID and build path
            let filePath = '';
            let foundFile = false;
            
            // Search for the file in each channel's folder structure
            for (const channel of contentHierarchy.channels) {
                for (const folder of channel.folders || []) {
                    const result = findFileInFolder(folder, id);
                    if (result.found) {
                        // If found, create path: Channel > Folder(s) > File
                        filePath = `${channel.name}/${result.path}`;
                        foundFile = true;
                        break;
                    }
                }
                if (foundFile) break;
            }
            
            return filePath;
        }
        
        return '';
    }
    
    // Helper function to find a file's path in a folder structure
    function findFileInFolder(folder, fileId, currentPath = '') {
        const path = currentPath ? `${currentPath}/${folder.name}` : folder.name;
        
        // Check if the file is in this folder
        if (folder.pages) {
            for (const page of folder.pages) {
                if (page.id == fileId) {
                    return { found: true, path: `${path}/${page.name}` };
                }
            }
        }
        
        // Check subfolders
        if (folder.subfolders) {
            for (const subfolder of folder.subfolders) {
                const result = findFileInFolder(subfolder, fileId, path);
                if (result.found) {
                    return result;
                }
            }
        }
        
        return { found: false, path: '' };
    }
    
    // Helper function to build a folder's path in the hierarchy
    function getFolderPathFromHierarchy(folders, folderId, currentPath = '') {
        for (const folder of folders) {
            if (folder.id == folderId) {
                return currentPath ? `${currentPath}/${folder.name}` : folder.name;
            }
            
            if (folder.subfolders && folder.subfolders.length > 0) {
                const newPath = currentPath ? `${currentPath}/${folder.name}` : folder.name;
                const found = getFolderPathFromHierarchy(folder.subfolders, folderId, newPath);
                if (found) return found;
            }
        }
        
        return '';
    }

    // Verify user exists
    function verifyUser(userId) {
        return fetch(`${baseApiUrl}/user/verify?id=${userId}`, {
            method: 'GET',
            credentials: 'include',
            headers: {
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            }
        })
        .then(response => {
            if (!response.ok) {
                if (response.status === 404) {
                    throw new Error('사용자를 찾을 수 없습니다.');
                }
                throw new Error('사용자 확인에 실패했습니다.');
            }
            return response.json();
        });
    }

    // Add permission
    function addPermission() {
        // Clear previous error message
        errorMessage.textContent = '';
        
        // Get selected values
        const permissionScope = document.querySelector('input[name="permission-scope"]:checked').value;
        const channelId = channelSelect.value;
        const folder1Id = folder1Select.value;
        const folder2Id = folder2Select.value;
        const folder3Id = folder3Select.value;
        const fileId = fileSelect.value;
        const managerId = managerInput.value.trim();
        
        // Validate input
        if (!channelId) {
            errorMessage.textContent = '채널을 선택해주세요.';
            return;
        }
        
        if (permissionScope === 'folder' && !folder1Id) {
            errorMessage.textContent = '폴더를 선택해주세요.';
            return;
        }
        
        if (permissionScope === 'file' && !fileId) {
            errorMessage.textContent = '파일을 선택해주세요.';
            return;
        }
        
        if (!managerId) {
            errorMessage.textContent = '담당자 ID를 입력해주세요.';
            return;
        }
        
        // Verify user exists
        verifyUser(managerId)
            .then(userData => {
                // Prepare permission data
                let permissionData = {
                    user_id: managerId,
                    type: permissionScope
                };
                
                if (permissionScope === 'channel') {
                    permissionData.folder_id = channelId;
                } else if (permissionScope === 'folder') {
                    // Use the deepest selected folder
                    permissionData.folder_id = folder3Id || folder2Id || folder1Id;
                } else if (permissionScope === 'file') {
                    permissionData.file_id = fileId;
                }
                
                // Send permission data to API
                return fetch(`${baseApiUrl}/content_manager`, {
                    method: 'POST',
                    credentials: 'include',
                    headers: {
                        'Content-Type': 'application/json',
                        'Accept': 'application/json'
                    },
                    body: JSON.stringify(permissionData)
                });
            })
            .then(response => {
                if (!response.ok) {
                    throw new Error('권한 추가에 실패했습니다.');
                }
                return response.json();
            })
            .then(data => {
                // Add new permission to table
                addPermissionToTable(data);
                
                // Clear form
                managerInput.value = '';
                validationMessage.textContent = '담당자 ID를 입력하거나 소속 정보를 통해 선택하세요';
                validationMessage.className = 'validation-message';
                
                // Clear user selection comboboxes
                resetUserSelectionComboboxes();
                
                // Success message
                alert('담당자 권한이 추가되었습니다.');
            })
            .catch(error => {
                errorMessage.textContent = error.message;
            });
    }

    // Add permission to table
    function addPermissionToTable(permission) {
        const row = document.createElement('tr');
        
        // Get user name
        fetchUserName(permission.user_id)
            .then(userName => {
                // Split path components for display
                let folderParts = ['', '', '', ''];
                let fileName = '';
                
                if (contentHierarchy) {
                    if (permission.type === 'channel' || permission.type === 'folder') {
                        const path = getPathInHierarchy(permission.type, permission.folder_id);
                        if (path) {
                            const parts = path.split('/');
                            for (let i = 0; i < Math.min(parts.length, 4); i++) {
                                folderParts[i] = parts[i] || '';
                            }
                        }
                    } else if (permission.type === 'file' && permission.file_id) {
                        const path = getPathInHierarchy(permission.type, permission.file_id);
                        if (path) {
                            const parts = path.split('/');
                            // Last part is the file name
                            if (parts.length > 0) {
                                fileName = parts.pop() || '';
                            }
                            // Remaining parts are folder path
                            for (let i = 0; i < Math.min(parts.length, 4); i++) {
                                folderParts[i] = parts[i] || '';
                            }
                        }
                    }
                }
                
                // Add cells
                row.innerHTML = `
                    <td>${permission.type}</td>
                    <td>${folderParts[0] || ''}</td>
                    <td class="folder-col folder1-col">${folderParts[1] || ''}</td>
                    <td class="folder-col folder2-col">${folderParts[2] || ''}</td>
                    <td class="folder-col folder3-col">${folderParts[3] || ''}</td>
                    <td class="file-col">${fileName || ''}</td>
                    <td class="manager-col">${userName || permission.user_id}</td>
                    <td>
                        <button class="delete-btn" data-id="${permission.id}">삭제</button>
                    </td>
                `;
                
                // Add row to table
                permissionsListBody.appendChild(row);
                
                // Apply column visibility rules to the new row
                updateColumnsVisibility();
                
                // Add event listener to delete button
                row.querySelector('.delete-btn').addEventListener('click', function() {
                    deletePermission(this.dataset.id, row);
                });
            })
            .catch(error => {
                console.error('Error adding permission to table:', error);
            });
    }

    // Fetch user name
    function fetchUserName(userId) {
        return fetch(`${baseApiUrl}/users/${userId}`, {
            method: 'GET',
            credentials: 'include',
            headers: {
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            }
        })
        .then(response => {
            if (!response.ok) {
                return '';
            }
            return response.json();
        })
        .then(data => {
            return data.name || '';
        })
        .catch(() => {
            return '';
        });
    }

    // Delete permission
    function deletePermission(permissionId, row) {
        if (confirm('이 권한을 삭제하시겠습니까?')) {
            fetch(`${baseApiUrl}/content_manager/${permissionId}`, {
                method: 'DELETE',
                credentials: 'include',
                headers: {
                    'Content-Type': 'application/json',
                    'Accept': 'application/json'
                }
            })
            .then(response => {
                if (!response.ok) {
                    throw new Error('권한 삭제에 실패했습니다.');
                }
                
                // Remove row from table
                row.remove();
                
                // Success message
                alert('권한이 삭제되었습니다.');
            })
            .catch(error => {
                console.error('Error deleting permission:', error);
                errorMessage.textContent = error.message;
            });
        }
    }

    // Load company options for user selection
    function loadCompanyOptions() {
        fetch(`${baseApiUrl}/user/companies`, {
            method: 'GET',
            credentials: 'include',
            headers: {
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            }
        })
        .then(response => {
            if (!response.ok) {
                throw new Error('Failed to fetch company options');
            }
            return response.json();
        })
        .then(data => {
            // Clear existing options except the first placeholder
            companySelect.innerHTML = '<option value="">회사명</option>';
            
            // Add new options
            data.forEach(company => {
                const option = document.createElement('option');
                option.value = company;
                option.textContent = company;
                companySelect.appendChild(option);
            });
        })
        .catch(error => {
            console.error('Error loading company options:', error);
        });
    }

    // Load department options based on selected company
    function loadDepartmentOptions(company) {
        fetch(`${baseApiUrl}/user/departments?company=${encodeURIComponent(company)}`, {
            method: 'GET',
            credentials: 'include',
            headers: {
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            }
        })
        .then(response => {
            if (!response.ok) {
                throw new Error('Failed to fetch department options');
            }
            return response.json();
        })
        .then(data => {
            // Clear existing options except the first placeholder
            departmentSelect.innerHTML = '<option value="">부서</option>';
            positionSelect.innerHTML = '<option value="">직책</option>';
            nameSelect.innerHTML = '<option value="">이름</option>';
            
            // Add new options
            data.forEach(department => {
                const option = document.createElement('option');
                option.value = department;
                option.textContent = department;
                departmentSelect.appendChild(option);
            });
        })
        .catch(error => {
            console.error('Error loading department options:', error);
        });
    }

    // Load position options based on selected company and department
    function loadPositionOptions(company, department) {
        fetch(`${baseApiUrl}/user/positions?company=${encodeURIComponent(company)}&department=${encodeURIComponent(department)}`, {
            method: 'GET',
            credentials: 'include',
            headers: {
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            }
        })
        .then(response => {
            if (!response.ok) {
                throw new Error('Failed to fetch position options');
            }
            return response.json();
        })
        .then(data => {
            // Clear existing options except the first placeholder
            positionSelect.innerHTML = '<option value="">직책</option>';
            nameSelect.innerHTML = '<option value="">이름</option>';
            
            // Add new options
            data.forEach(position => {
                const option = document.createElement('option');
                option.value = position;
                option.textContent = position;
                positionSelect.appendChild(option);
            });
        })
        .catch(error => {
            console.error('Error loading position options:', error);
        });
    }

    // Load name options based on selected company, department, and position
    function loadNameOptions(company, department, position) {
        fetch(`${baseApiUrl}/user/names?company=${encodeURIComponent(company)}&department=${encodeURIComponent(department)}&position=${encodeURIComponent(position)}`, {
            method: 'GET',
            credentials: 'include',
            headers: {
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            }
        })
        .then(response => {
            if (!response.ok) {
                throw new Error('Failed to fetch name options');
            }
            return response.json();
        })
        .then(data => {
            // Clear existing options except the first placeholder
            nameSelect.innerHTML = '<option value="">이름</option>';
            
            // Add new options
            data.forEach(user => {
                const option = document.createElement('option');
                option.value = user.id;
                option.textContent = user.name;
                nameSelect.appendChild(option);
            });
        })
        .catch(error => {
            console.error('Error loading name options:', error);
        });
    }

    // Reset user selection comboboxes
    function resetUserSelectionComboboxes() {
        companySelect.innerHTML = '<option value="">회사명</option>';
        departmentSelect.innerHTML = '<option value="">부서</option>';
        positionSelect.innerHTML = '<option value="">직책</option>';
        nameSelect.innerHTML = '<option value="">이름</option>';
        
        // Reload company options
        loadCompanyOptions();
    }

    // Validate user ID input
    function validateUserID(userId) {
        if (!userId) {
            validationMessage.textContent = '담당자 ID를 입력하거나 소속 정보를 통해 선택하세요';
            validationMessage.className = 'validation-message';
            return;
        }
        
        fetch(`${baseApiUrl}/user/verify?id=${encodeURIComponent(userId)}`, {
            method: 'GET',
            credentials: 'include',
            headers: {
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            }
        })
        .then(response => {
            if (!response.ok) {
                validationMessage.textContent = 'ID를 찾을 수 없습니다';
                validationMessage.className = 'validation-message error';
                return null;
            }
            return response.json();
        })
        .then(data => {
            if (data && data.exists) {
                const user = data.user;
                validationMessage.textContent = `올바른 ID입니다(${user.company} ${user.department} ${user.name} ${user.position})`;
                validationMessage.className = 'validation-message success';
            }
        })
        .catch(error => {
            console.error('Error validating user ID:', error);
            validationMessage.textContent = 'ID 검증에 실패했습니다';
            validationMessage.className = 'validation-message error';
        });
    }

    // Event listeners for permission scope radio buttons
    permissionScopeRadios.forEach(radio => {
        radio.addEventListener('change', updateColumnsVisibility);
    });

    // Event listener for channel select
    channelSelect.addEventListener('change', function() {
        if (this.value) {
            // Load folders with depth 2 under the selected channel
            loadFolderOptions('channel', this.value, folder1Select, 1);
        }
    });

    // Event listener for folder1 select
    folder1Select.addEventListener('change', function() {
        if (this.value) {
            console.log(`Folder1 selected: ${this.value}`);
            
            // Load folders with depth 3 under the selected folder
            loadFolderOptions('folder', this.value, folder2Select, 2);
            
            // Try to load files immediately - if this is a leaf folder, it will get files
            try {
                loadFileOptions(this.value);
            } catch (error) {
                console.error("Error loading files for folder1:", error);
            }
        } else {
            // Clear dependent selects
            folder2Select.innerHTML = '<option value="">선택</option>';
            folder3Select.innerHTML = '<option value="">선택</option>';
            fileSelect.innerHTML = '<option value="">선택</option>';
        }
    });

    // Event listener for folder2 select
    folder2Select.addEventListener('change', function() {
        if (this.value) {
            console.log(`Folder2 selected: ${this.value}`);
            
            // Load folders with depth 4 under the selected folder
            loadFolderOptions('folder', this.value, folder3Select, 3);
            
            // Try to load files immediately - if this is a leaf folder, it will get files
            try {
                loadFileOptions(this.value);
            } catch (error) {
                console.error("Error loading files for folder2:", error);
            }
        } else {
            // Clear dependent selects
            folder3Select.innerHTML = '<option value="">선택</option>';
            fileSelect.innerHTML = '<option value="">선택</option>';
        }
    });

    // Event listener for folder3 select
    folder3Select.addEventListener('change', function() {
        if (this.value) {
            console.log(`Folder3 selected: ${this.value}`);
            
            // Load files under the selected folder
            try {
                loadFileOptions(this.value);
            } catch (error) {
                console.error("Error loading files for folder3:", error);
            }
        } else {
            // Clear file select
            fileSelect.innerHTML = '<option value="">선택</option>';
        }
    });

    // Event listener for company select
    companySelect.addEventListener('change', function() {
        if (this.value) {
            loadDepartmentOptions(this.value);
        } else {
            departmentSelect.innerHTML = '<option value="">부서</option>';
            positionSelect.innerHTML = '<option value="">직책</option>';
            nameSelect.innerHTML = '<option value="">이름</option>';
        }
    });

    // Event listener for department select
    departmentSelect.addEventListener('change', function() {
        if (this.value && companySelect.value) {
            loadPositionOptions(companySelect.value, this.value);
        } else {
            positionSelect.innerHTML = '<option value="">직책</option>';
            nameSelect.innerHTML = '<option value="">이름</option>';
        }
    });

    // Event listener for position select
    positionSelect.addEventListener('change', function() {
        if (this.value && companySelect.value && departmentSelect.value) {
            loadNameOptions(companySelect.value, departmentSelect.value, this.value);
        } else {
            nameSelect.innerHTML = '<option value="">이름</option>';
        }
    });

    // Event listener for name select
    nameSelect.addEventListener('change', function() {
        if (this.value) {
            // Set the selected user's ID in the manager input field
            managerInput.value = this.value;
            validateUserID(this.value);
        }
    });

    // Event listener for manager input
    managerInput.addEventListener('input', function() {
        validateUserID(this.value.trim());
    });

    // Event listener for add button
    addBtn.addEventListener('click', addPermission);

    // Initialize view
    updateColumnsVisibility();
    fetchContentHierarchy(); // This will load channel options after fetching
    loadPermissions();
    loadCompanyOptions();
    
    // Force refresh the column visibility
    setTimeout(updateColumnsVisibility, 100);
});

// Add event listener to open the manager admin popup from main page
if (window.opener) {
    // If this window was opened by another window (popup mode)
    document.title = '담당자 관리';
}

// Process and normalize the hierarchy data to ensure it has the expected format
function normalizeHierarchyData(data) {
    if (!data || !data.channels) {
        console.error('Invalid hierarchy data:', data);
        return data;
    }
    
    console.log('Normalizing hierarchy data structure');
    
    // Process each channel
    data.channels.forEach(channel => {
        console.log(`Processing channel ${channel.id}: ${channel.name}`);
        
        if (!channel.folders) {
            console.log(`Channel ${channel.id} has no folders array, creating empty array`);
            channel.folders = [];
        }
        
        // Process each folder
        channel.folders.forEach(folder => {
            normalizeFolder(folder);
        });
    });
    
    // Debug output
    let folderStats = [];
    data.channels.forEach(channel => {
        let channelStats = { 
            channelId: channel.id, 
            channelName: channel.name,
            folderCount: channel.folders ? channel.folders.length : 0,
            leafFolders: []
        };
        
        if (channel.folders && channel.folders.length > 0) {
            channel.folders.forEach(folder => {
                collectLeafFolders(folder, channelStats.leafFolders);
            });
        }
        
        folderStats.push(channelStats);
    });
    
    console.log('Hierarchy leaf folder stats:', folderStats);
    
    return data;
}

// Recursively normalize folder structure
function normalizeFolder(folder) {
    if (!folder) return;
    
    console.log(`Processing folder ${folder.id}: ${folder.name}`);
    
    // Ensure subfolders array exists
    if (!folder.subfolders) {
        console.log(`Folder ${folder.id} has no subfolders array, creating empty array`);
        folder.subfolders = [];
    }
    
    // Ensure pages array exists
    if (!folder.pages) {
        console.log(`Folder ${folder.id} has no pages array, creating empty array`);
        folder.pages = [];
    } else {
        console.log(`Folder ${folder.id} has ${folder.pages.length} pages`);
    }
    
    // Process each subfolder recursively
    folder.subfolders.forEach(subfolder => {
        normalizeFolder(subfolder);
    });
}

// Helper function to collect leaf folders for debugging
function collectLeafFolders(folder, leafFolders) {
    if (!folder.subfolders || folder.subfolders.length === 0) {
        leafFolders.push({
            id: folder.id,
            name: folder.name,
            pageCount: folder.pages ? folder.pages.length : 0
        });
    } else {
        folder.subfolders.forEach(subfolder => {
            collectLeafFolders(subfolder, leafFolders);
        });
    }
}

// Helper function to find a folder by ID in the entire hierarchy
function findSelectedFolder(folderId) {
    // First ensure contentHierarchy is defined
    if (typeof contentHierarchy === 'undefined' || !contentHierarchy || !contentHierarchy.channels) {
        console.error('Content hierarchy is not available', typeof contentHierarchy);
        return null;
    }
    
    for (const channel of contentHierarchy.channels) {
        if (!channel.folders) continue;
        
        const folder = findFolderById(channel.folders, folderId);
        if (folder) return folder;
    }
    
    return null;
} 