console.log("opinion.js");

const { createApp, ref, reactive, computed, onMounted } = Vue;

const url = typeof baseUrl != "undefined" ? baseUrl : "http://172.16.8.208:20000/";

// User cache to avoid repeated API failures
const userCache = {};

createApp({
    setup() {
        const memoList = ref([]);
        const currentPage = ref(1);
        const totalPages = ref(1);
        const pageSize = 10;

        // Search filters
        const searchContent = ref('');
        const searchStartDate = ref('');
        const searchEndDate = ref('');
        
        // URL params for file_id and folder_id
        const urlParams = new URLSearchParams(window.location.search);
        const fileId = urlParams.get('file_id');
        const folderId = urlParams.get('folder_id');
        const path = urlParams.get('path');

        // Current user data
        const currentUser = ref({});

        const isAdmin = computed(() => {
            const userInfo = JSON.parse(localStorage.getItem("loggedInUser"));
            return userInfo.user.role_id == 1;
        });

        const visiblePages = computed(() => {
            let pages = [];
        
            if (totalPages.value <= 7) {
                return Array.from({ length: totalPages.value }, (_, i) => i + 1);
            }
        
            let startPage, endPage;
        
            if (currentPage.value <= 4) {
                startPage = 1;
                endPage = 5;
            } else if (currentPage.value >= totalPages.value - 3) {
                startPage = totalPages.value - 4;
                endPage = totalPages.value;
            } else {
                startPage = currentPage.value - 2;
                endPage = currentPage.value + 2;
            }
        
            pages = Array.from({ length: endPage - startPage + 1 }, (_, i) => startPage + i);
        
            if (pages[0] !== 1) {
                pages.unshift(1);
                if (pages[1] !== 2) {
                    pages.splice(1, 0, "..."); 
                }
            }
        
            if (pages[pages.length - 1] !== totalPages.value) {
                if (pages[pages.length - 1] !== totalPages.value - 1) {
                    pages.push("...");
                }
                pages.push(totalPages.value);
            }
        
            return pages;
        });

        const formatStatus = (status) => {
            switch(status) {
                case 0: return '대기';
                case 1: return '처리중';
                case 2: return '완료';
                default: return '알 수 없음';
            }
        };

        const formatMemoPath = (path) => {
            if (!path) return '';
            
            // Remove the first '/'
            let formatted = path.startsWith('/') ? path.substring(1) : path;
            
            // Remove all instances of '###_' patterns
            formatted = formatted.replace(/\d+_/g, '');
            
            // Remove file extensions
            formatted = formatted.replace(/\.[^/.]+$/, '');
            
            return formatted;
        };

        const formatDate = (dateString) => {
            if (!dateString) return '';
            const date = new Date(dateString);
            return date.toLocaleString('ko-KR', {
                year: 'numeric',
                month: '2-digit',
                day: '2-digit',
                hour: '2-digit',
                minute: '2-digit'
            }).replace(/\./g, '-');
        };

        const loadCurrentUser = () => {
            try {
                const loggedInUser = JSON.parse(localStorage.getItem("loggedInUser"));
                if (loggedInUser && loggedInUser.user) {
                    currentUser.value = {
                        id: loggedInUser.user.id,
                        name: loggedInUser.user.name || '',
                        position: loggedInUser.user.position || '',
                        company: loggedInUser.user.company || '',
                        department: loggedInUser.user.department || ''
                    };
                } else {
                    // Redirect to login if no user data found
                    window.top.location.href = "login.html";
                }
            } catch (error) {
                console.error("Error loading current user data:", error);
                window.top.location.href = "login.html";
            }
        };

        const loadMemoData = (page = 1) => {
            if (page < 1 || (page > totalPages.value && totalPages.value > 0)) {
                return;
            }
            
            currentPage.value = page;
            
            // Build URL with query parameters
            let fetchUrl = `${url}memo/`;
            let queryParams = [];
            
            if (fileId) {
                queryParams.push(`file_id=${fileId}`);
            }
            
            if (folderId) {
                queryParams.push(`folder_id=${folderId}`);
            }
            
            if (path) {
                queryParams.push(`path=${encodeURIComponent(path)}`);
            }
            
            if (queryParams.length > 0) {
                fetchUrl += `?${queryParams.join('&')}`;
            }
            
            fetch(fetchUrl, {
                method: "GET",
                credentials: "include",
                headers: {
                    "Accept": "application/json",
                    "Content-Type": "application/json"
                }
            })
            .then(response => {
                if (!response.ok) {
                    throw new Error('Network response was not ok');
                }
                return response.json();
            })
            .then(data => {
                // Apply filters if any
                let filteredData = data;
                
                if (searchContent.value) {
                    filteredData = filteredData.filter(memo => 
                        memo.content && memo.content.toLowerCase().includes(searchContent.value.toLowerCase())
                    );
                }
                
                if (searchStartDate.value) {
                    const startDate = new Date(searchStartDate.value);
                    filteredData = filteredData.filter(memo => 
                        memo.modified_at && new Date(memo.modified_at) >= startDate
                    );
                }
                
                if (searchEndDate.value) {
                    const endDate = new Date(searchEndDate.value);
                    endDate.setHours(23, 59, 59); // End of the day
                    filteredData = filteredData.filter(memo => 
                        memo.modified_at && new Date(memo.modified_at) <= endDate
                    );
                }
                
                // Since the backend returns an array directly, we need to handle pagination on the client side
                const start = (page - 1) * pageSize;
                const end = start + pageSize;

                // Get user information for each memo
                const promises = filteredData.map(async memo => {
                    if (memo.user_id) {
                        // Try to get current user info from localStorage if it's the same user
                        try {
                            const loggedInUser = JSON.parse(localStorage.getItem("loggedInUser"));
                            if (loggedInUser && loggedInUser.user && loggedInUser.user.id === memo.user_id) {
                                console.log("Using logged in user data for user_id:", memo.user_id);
                                // Store in cache for future use
                                userCache[memo.user_id] = {
                                    company: loggedInUser.user.company || '-',
                                    department: loggedInUser.user.department || '-',
                                    name: loggedInUser.user.name || '-',
                                    position: loggedInUser.user.position || ''
                                };
                                return {
                                    ...memo,
                                    user: userCache[memo.user_id],
                                    status_text: formatStatus(memo.status)
                                };
                            }
                        } catch (error) {
                            console.error("Error retrieving user data from localStorage:", error);
                        }

                        // Check if user is already in cache
                        if (userCache[memo.user_id]) {
                            console.log("Using cached user data for user_id:", memo.user_id);
                            return {
                                ...memo,
                                user: userCache[memo.user_id],
                                status_text: formatStatus(memo.status)
                            };
                        }

                        // If not the current user, try the API
                        try {
                            const userResponse = await fetch(`${url}users/${memo.user_id}`, {
                                method: "GET",
                                credentials: "include",
                                headers: {
                                    "Accept": "application/json",
                                    "Content-Type": "application/json"
                                }
                            });
                            
                            if (!userResponse.ok) {
                                if (userResponse.status === 401) {
                                    window.top.location.href = "login.html";
                                    throw new Error("로그인이 필요합니다. 로그인 페이지로 이동합니다.");
                                }
                                // If response is not OK but not a 401, just return memo without user data
                                return {
                                    ...memo,
                                    user: { 
                                        company: '-', 
                                        department: '-', 
                                        name: '-',
                                        position: '' 
                                    },
                                    status_text: formatStatus(memo.status)
                                };
                            }
                            
                            // Check content type to avoid parsing HTML as JSON
                            const contentType = userResponse.headers.get('content-type');
                            if (contentType && contentType.includes('application/json')) {
                                const userData = await userResponse.json();
                                return {
                                    ...memo,
                                    user: userData,
                                    status_text: formatStatus(memo.status)
                                };
                            } else {
                                console.error("Received non-JSON response for user ID", memo.user_id);
                                
                                // Cache the failure to avoid repeated attempts
                                if (!userCache[memo.user_id]) {
                                    userCache[memo.user_id] = {
                                        company: '-',
                                        department: '-',
                                        name: '-',
                                        position: ''
                                    };
                                }
                                
                                return {
                                    ...memo,
                                    user: userCache[memo.user_id],
                                    status_text: formatStatus(memo.status)
                                };
                            }
                        } catch (error) {
                            console.error(`Error fetching user data for user ID ${memo.user_id}:`, error);
                            return {
                                ...memo,
                                user: userCache[memo.user_id] || { 
                                    company: '-', 
                                    department: '-', 
                                    name: '-',
                                    position: '' 
                                },
                                status_text: formatStatus(memo.status)
                            };
                        }
                    }
                    
                    return {
                        ...memo,
                        user: { 
                            company: '-', 
                            department: '-', 
                            name: '-',
                            position: '' 
                        },
                        status_text: formatStatus(memo.status)
                    };
                });
                
                Promise.all(promises)
                    .then(memoWithUserData => {
                        memoList.value = memoWithUserData.slice(start, end);
                        totalPages.value = Math.ceil(filteredData.length / pageSize);
                        console.log("Loaded memo data:", memoList.value);
                    })
                    .catch(error => {
                        console.error("Error processing user data:", error);
                    });
            })
            .catch(error => {
                console.error("Error loading memo data:", error);
            });
        };

        const replyToMemo = (memo) => {
            // Open a new popup window
            const width = 800;
            const height = 600;
            const left = (window.screen.width - width) / 2;
            const top = (window.screen.height - height) / 2;
            
            // Store the selected memo in localStorage for access from the popup
            localStorage.setItem('replyMemo', JSON.stringify(memo));
            
            // Open popup window
            const popupWindow = window.open(
                'memo_reply.html',
                'replyPopup',
                `width=${width},height=${height},left=${left},top=${top},resizable=yes,scrollbars=yes`
            );
            
            if (popupWindow) {
                popupWindow.focus();
            } else {
                alert('팝업 창이 차단되었습니다. 팝업 차단을 해제해주세요.');
            }
        };

        onMounted(() => {
            loadCurrentUser();
            loadMemoData();
        });

        return {
            memoList,
            currentPage,
            totalPages,
            visiblePages,
            isAdmin,
            searchContent,
            searchStartDate,
            searchEndDate,
            currentUser,
            loadMemoData,
            replyToMemo,
            formatStatus,
            formatDate,
            formatMemoPath
        };
    }
}).mount("#app");