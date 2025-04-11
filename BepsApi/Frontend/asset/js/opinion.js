console.log("opinion.js");

const { createApp, ref, reactive, computed, onMounted } = Vue;

const url = typeof baseUrl != "undefined" ? baseUrl : "http://172.16.8.208:20000/";

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

        const loadMemoData = (page = 1) => {
            if (page < 1 || (page > totalPages.value && totalPages.value > 0)) {
                return;
            }
            
            currentPage.value = page;
            
            // Update the URL to match the backend API endpoint
            const fullUrl = `${url}memo/`;
            
            fetch(fullUrl, {
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
                memoList.value = filteredData.slice(start, end).map(memo => ({
                    ...memo,
                    status_text: formatStatus(memo.status)
                }));
                totalPages.value = Math.ceil(filteredData.length / pageSize);
                console.log("Loaded memo data:", memoList.value);
            })
            .catch(error => {
                console.error("Error loading memo data:", error);
            });
        };

        const replyToMemo = (memo) => {
            // This function will be implemented to handle replying to memos
            console.log("Reply to memo:", memo);
            // You can implement a modal or redirect to a reply page
            alert(`메모 ID ${memo.id}에 대한 답변 기능은 개발 중입니다.`);
        };

        onMounted(() => {
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
            loadMemoData,
            replyToMemo,
            formatStatus,
            formatDate,
            formatMemoContent
        };
    }
}).mount("#app"); 