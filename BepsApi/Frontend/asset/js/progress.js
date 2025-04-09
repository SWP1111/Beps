console.log("progress.js");

const { createApp, ref, reactive, computed, onMounted } = Vue;

const url = typeof baseUrl != "undefined" ? baseUrl : "http://172.16.8.208:20000/";

createApp({
    setup() {
        const progressList = ref([]);
        const searchUserId = ref("");
        const searchFileName = ref("");
        const searchStartDate = ref("");
        const searchEndDate = ref("");
        const currentPage = ref(1);
        const totalPages = ref(1);
        const pageSize = 19;    // 변경되지 않는 값
        const csvDataCount = ref(0);

        const isAdmin = computed(() => {
            const userInfo = JSON.parse(localStorage.getItem("loggedInUser"));
            return userInfo.user.role_id == 1;// || userInfo.user.role_id == null;
        });

        const searchUserType = ref("all");
        const searchUserPlaceholder = computed(()=> {
            return searchUserType.value == "user_id" ? "사번"
            : searchUserType.value == "user_name"? "이름"
            : "전체";
        });

        const filteredProgressList = computed(() => {
            return progressList.value.filter(item => {
                const itemDate = new Date(item.start_time).toISOString().split("T")[0];
                return (!searchUserId.value || item.user_id.includes(searchUserId.value)) &&
                    (!searchFileName.value || item.file_name.includes(searchFileName.value)) &&
                    (!searchStartDate.value || itemDate >= searchStartDate.value) &&
                    (!searchEndDate.value || itemDate <= searchEndDate.value);
            });
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
        
            console.log("Visible Pages:", pages); // 디버깅용
            return pages;
        });
        

        const loadProgressData = (page = 1) => {
            currentPage.value = page;

            // 사용자 검색
            let userQuery ="";
            if(isAdmin.value ==  false){
                userQuery = `&user_id=${JSON.parse(localStorage.getItem("loggedInUser")).user.id}`;
            }
            else if(searchUserType.value != "all" && searchUserId.value.trim())
                userQuery = `&${searchUserType.value}=${encodeURIComponent(searchUserId.value)}`;

            // 파일 검색
            const fileQuery = searchFileName.value ? `&file_name=${encodeURIComponent(searchFileName.value)}` : "";

            // 기간 검색
            const dateQuery =
                searchStartDate.value && searchEndDate.value
                ? `&start_date=${searchStartDate.value}&end_date=${searchEndDate.value}`
                : "";

                
            const fullUrl = `${url}leaning/data?page_size=${pageSize}&page=${page}${userQuery}${fileQuery}${dateQuery}`;

            fetch(fullUrl, {
                method: "GET",
                credentials: "include",
            })
            .then(response => {
                if(!response.ok) {
                    if(response.status == 401){
                        window.top.location.href = "login.html";
                        throw new Error("로그인이 필요합니다. 로그인 페이지로 이동합니다.");
                    }
                }
                return response.json()
            })
            .then(data => {
                progressList.value = data.data.map(item => ({
                    ...item,
                    file_name: item.file_name.replace(/^\d+_/,''),  // 파일 이름에서 숫자_ 제거
                    start_time: formatDateTime(item.start_time),
                    end_time: formatDateTime(item.end_time),
                    stay_duration: formatDuration(item.stay_duration),
                }));       
                if(data.csv_count != null && data.csv_count != undefined)
                    this.csvDataCount = data.csv_count;
                console.log("db_count:", data.db_count);
                console.log("csvDataCount:", this.csvDataCount);
                console.log("totalPages:", totalPages.value);   
                totalPages.value = Math.ceil((data.db_count + this.csvDataCount) / pageSize);
                //Math.ceil(data.total_count / pageSize);   
            })
            .catch(error => console.error(error));
        };

        const formatDate = date => new Date(date).toISOString().split("T")[0];  // YYYY-MM-DD 형식 변환
        const formatDateTime = dateTime => dateTime ? new Date(dateTime).toLocaleString("ko-KR", { timeZone: "Asia/Seoul" }) : "-";
        const formatDuration = duration => {
            const [time, millis] = duration.split('.'); // "시간:분:초.밀리세컨드"에서 밀리세컨드 분리
            const [hours, minutes, seconds] = time.split(':').map(Number); // 시간, 분, 초를 숫자로 변환
            
            if (hours > 0) {
                return `${hours}시간 ${minutes}분 ${seconds}초`;
            } else if (minutes > 0) {
                return `${minutes}분 ${seconds}초`;
            } else {
                return `${seconds}초`;
            }
        };

        onMounted(() => {
            const today = new Date();
            const oneWeekAgo = new Date(today.getTime() - 7 * 24 * 60 * 60 * 1000);
            searchStartDate.value = formatDate(oneWeekAgo);
            searchEndDate.value = formatDate(today);
            loadProgressData();
        });

        return {
            url,
            progressList,
            searchUserId,
            searchFileName,
            searchStartDate,
            searchEndDate,
            currentPage,
            totalPages,
            filteredProgressList,  
            loadProgressData,
            formatDate,
            formatDateTime,
            formatDuration,
            
            searchUserType,
            searchUserPlaceholder,

            visiblePages,
            csvDataCount,
            isAdmin
        };
    }
}).mount("#app");