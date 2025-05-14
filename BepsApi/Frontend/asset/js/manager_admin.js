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

    // Base API URL from config
    const apiUrl = config.apiUrl;

    // Function to toggle visibility of columns based on selected permission scope
    function updateColumnsVisibility() {
        const selectedScope = document.querySelector('input[name="permission-scope"]:checked').value;
        
        if (selectedScope === 'channel') {
            // Hide folder and file columns
            folderCols.forEach(col => col.classList.add('hidden'));
            fileCol.classList.add('hidden');
        } else if (selectedScope === 'folder') {
            // Show folder columns, hide file column
            folderCols.forEach(col => col.classList.remove('hidden'));
            fileCol.classList.add('hidden');
        } else if (selectedScope === 'file') {
            // Show all columns
            folderCols.forEach(col => col.classList.remove('hidden'));
            fileCol.classList.remove('hidden');
        }
    }

    // Load channel options (depth = 1)
    function loadChannelOptions() {
        fetch(`${apiUrl}/folders?depth=1`, {
            method: 'GET',
            credentials: 'include',
            headers: {
                'Content-Type': 'application/json'
            }
        })
        .then(response => {
            if (!response.ok) {
                throw new Error('Failed to fetch channel options');
            }
            return response.json();
        })
        .then(data => {
            // Clear existing options except the first placeholder
            channelSelect.innerHTML = '<option value="">선택</option>';
            
            // Add new options
            data.forEach(channel => {
                const option = document.createElement('option');
                option.value = channel.folder_id;
                option.textContent = channel.folder_name;
                channelSelect.appendChild(option);
            });
        })
        .catch(error => {
            console.error('Error loading channel options:', error);
            errorMessage.textContent = '채널 정보를 불러오는데 실패했습니다.';
        });
    }

    // Load folder options based on parent folder id and depth
    function loadFolderOptions(parentId, selectElement, depth) {
        fetch(`${apiUrl}/folders?parent_id=${parentId}&depth=${depth}`, {
            method: 'GET',
            credentials: 'include',
            headers: {
                'Content-Type': 'application/json'
            }
        })
        .then(response => {
            if (!response.ok) {
                throw new Error(`Failed to fetch folders with depth ${depth}`);
            }
            return response.json();
        })
        .then(data => {
            // Clear existing options except the first placeholder
            selectElement.innerHTML = '<option value="">선택</option>';
            
            // Add new options
            data.forEach(folder => {
                const option = document.createElement('option');
                option.value = folder.folder_id;
                option.textContent = folder.folder_name;
                selectElement.appendChild(option);
            });
        })
        .catch(error => {
            console.error(`Error loading folder options with depth ${depth}:`, error);
            errorMessage.textContent = '폴더 정보를 불러오는데 실패했습니다.';
        });
    }

    // Load file options based on parent folder id
    function loadFileOptions(folderId) {
        fetch(`${apiUrl}/files?folder_id=${folderId}`, {
            method: 'GET',
            credentials: 'include',
            headers: {
                'Content-Type': 'application/json'
            }
        })
        .then(response => {
            if (!response.ok) {
                throw new Error('Failed to fetch files');
            }
            return response.json();
        })
        .then(data => {
            // Clear existing options except the first placeholder
            fileSelect.innerHTML = '<option value="">선택</option>';
            
            // Add new options
            data.forEach(file => {
                const option = document.createElement('option');
                option.value = file.file_id;
                option.textContent = file.file_name;
                fileSelect.appendChild(option);
            });
        })
        .catch(error => {
            console.error('Error loading file options:', error);
            errorMessage.textContent = '파일 정보를 불러오는데 실패했습니다.';
        });
    }

    // Load existing permissions
    function loadPermissions() {
        fetch(`${apiUrl}/content_manager`, {
            method: 'GET',
            credentials: 'include',
            headers: {
                'Content-Type': 'application/json'
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

    // Verify user exists
    function verifyUser(userId) {
        return fetch(`${apiUrl}/users/${userId}`, {
            method: 'GET',
            credentials: 'include',
            headers: {
                'Content-Type': 'application/json'
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
                return fetch(`${apiUrl}/content_manager`, {
                    method: 'POST',
                    credentials: 'include',
                    headers: {
                        'Content-Type': 'application/json'
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
        
        // Fetch additional data if needed (folder/file names)
        Promise.all([
            permission.folder_id ? fetchFolderPath(permission.folder_id) : null,
            permission.file_id ? fetchFileName(permission.file_id) : null,
            fetchUserName(permission.user_id)
        ])
        .then(([folderPath, fileName, userName]) => {
            let folderParts = folderPath ? folderPath.split('/').filter(Boolean) : ['', '', '', ''];
            
            // Add cells
            row.innerHTML = `
                <td>${permission.type}</td>
                <td>${folderParts[0] || ''}</td>
                <td>${folderParts[1] || ''}</td>
                <td>${folderParts[2] || ''}</td>
                <td>${folderParts[3] || ''}</td>
                <td>${fileName || ''}</td>
                <td>${userName || permission.user_id}</td>
                <td>
                    <button class="delete-btn" data-id="${permission.id}">삭제</button>
                </td>
            `;
            
            // Add row to table
            permissionsListBody.appendChild(row);
            
            // Add event listener to delete button
            row.querySelector('.delete-btn').addEventListener('click', function() {
                deletePermission(this.dataset.id, row);
            });
        })
        .catch(error => {
            console.error('Error adding permission to table:', error);
        });
    }

    // Fetch folder path
    function fetchFolderPath(folderId) {
        return fetch(`${apiUrl}/folders/${folderId}/path`, {
            method: 'GET',
            credentials: 'include',
            headers: {
                'Content-Type': 'application/json'
            }
        })
        .then(response => {
            if (!response.ok) {
                return '';
            }
            return response.json();
        })
        .then(data => {
            return data.path || '';
        })
        .catch(() => {
            return '';
        });
    }

    // Fetch file name
    function fetchFileName(fileId) {
        return fetch(`${apiUrl}/files/${fileId}`, {
            method: 'GET',
            credentials: 'include',
            headers: {
                'Content-Type': 'application/json'
            }
        })
        .then(response => {
            if (!response.ok) {
                return '';
            }
            return response.json();
        })
        .then(data => {
            return data.file_name || '';
        })
        .catch(() => {
            return '';
        });
    }

    // Fetch user name
    function fetchUserName(userId) {
        return fetch(`${apiUrl}/users/${userId}`, {
            method: 'GET',
            credentials: 'include',
            headers: {
                'Content-Type': 'application/json'
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
            fetch(`${apiUrl}/content_manager/${permissionId}`, {
                method: 'DELETE',
                credentials: 'include',
                headers: {
                    'Content-Type': 'application/json'
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

    // Event listeners for permission scope radio buttons
    permissionScopeRadios.forEach(radio => {
        radio.addEventListener('change', updateColumnsVisibility);
    });

    // Event listener for channel select
    channelSelect.addEventListener('change', function() {
        if (this.value) {
            // Load folders with depth 2 under the selected channel
            loadFolderOptions(this.value, folder1Select, 2);
            
            // Clear other dropdowns
            folder2Select.innerHTML = '<option value="">선택</option>';
            folder3Select.innerHTML = '<option value="">선택</option>';
            fileSelect.innerHTML = '<option value="">선택</option>';
        }
    });

    // Event listener for folder1 select
    folder1Select.addEventListener('change', function() {
        if (this.value) {
            // Load folders with depth 3 under the selected folder
            loadFolderOptions(this.value, folder2Select, 3);
            
            // Clear other dropdowns
            folder3Select.innerHTML = '<option value="">선택</option>';
            fileSelect.innerHTML = '<option value="">선택</option>';
        }
    });

    // Event listener for folder2 select
    folder2Select.addEventListener('change', function() {
        if (this.value) {
            // Load folders with depth 4 under the selected folder
            loadFolderOptions(this.value, folder3Select, 4);
            
            // Clear file dropdown
            fileSelect.innerHTML = '<option value="">선택</option>';
        }
    });

    // Event listener for folder3 select
    folder3Select.addEventListener('change', function() {
        if (this.value) {
            // Load files under the selected folder
            loadFileOptions(this.value);
        }
    });

    // Event listener for add button
    addBtn.addEventListener('click', addPermission);

    // Initialize view
    updateColumnsVisibility();
    loadChannelOptions();
    loadPermissions();
});

// Add event listener to open the manager admin popup from main page
if (window.opener) {
    // If this window was opened by another window (popup mode)
    document.title = '담당자 관리';
} 