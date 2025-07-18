const userName = document.getElementById("user-name");
const updateList = document.getElementById("update-list");
const dayIconContainer = document.getElementById("day-icon-container");
const chartContainer = document.getElementById("chart-container");

const myAvgLearningMinutes = document.querySelectorAll(".my-avg-learning-minutes");
const percentChangeValue = document.getElementById("percent-change-value");
const percentChangeText = document.getElementById("percent-change-text");
const allAvgLearningMinutes = document.getElementById("all-avg-learning-minutes");
const comparePercentValue = document.getElementById("compare-percent-value");
const comparePercentText = document.getElementById("compare-percent-text");

const contentsProgressContainer = document.getElementById("contents-progress-container");

const summaryCalendarButton = document.getElementById("summary-calendar-button");
const contentsDataButton = document.getElementById("contents-data-button");
const [start, end] = getWeekRange(new Date());

const updateContentsUnviewedCount = document.getElementById("update-contents-unviewed-count");
const pushMessageContainer = document.getElementById("push-message-container");
const pushMessageCount = document.getElementById("push-message-count");
const updateListBtn = document.getElementById('update-list-btn');

let userInfoMemoValueCount;
let userInfoLevelValueLevel;
let userInfoRankValueRank;
let userInfoProgressValueProgress;

let updateContentsData = null; // 업데이트 콘텐츠 데이터를 저장할 전역 변수
let updateContentsWindow = null; // 업데이트 창 참조를 저장할 전역 변수
let pushMessageData = null;
let pushMessageWindow = null; // 푸시 메시지 창 참조를 저장할 전역 변수

const fpSummary = flatpickr("#summary-date", {
    mode: "range",
    dateFormat: "y-m-d",
    locale: "ko",
    defaultDate: [start, end],  // ✅ 이번 주 기본 선택
    onChange: function(selectedDates, dateStr, instance) {
        if (selectedDates.length === 1) {
            const [start, end] = getWeekRange(selectedDates[0]);

            // 프로그램적으로 range 선택
            instance.setDate([start, end], true);
             // 달력 닫기!
            instance.close();

            (async() => {
                const learningData = await getLearningTimeByWeek(start, end);
    
                // 지난 주 날짜 계산 (원본 날짜를 변경하지 않도록 새로운 Date 객체 생성)
                const lastWeekStart = new Date(start);
                lastWeekStart.setDate(start.getDate() - 7);
                const lastWeekEnd = new Date(end);
                lastWeekEnd.setDate(end.getDate() - 7);
                const lastLearningData = await getLearningTimeByWeek(lastWeekStart, lastWeekEnd);    // 지난 주간의 학습 시간 데이터

                await configureLearningDays(start, end, learningData);
                await configureLearningChart(learningData);
            })();
        }
    }
});

const fpContents = flatpickr("#contents-date", {
    mode: "range",
    dateFormat: "y-m-d",
    locale: "ko",
    defaultDate: [start, end],  // ✅ 이번 주 기본 선택
    onChange: function(selectedDates, dateStr, instance) {
        if (selectedDates.length === 1) {
            const [start, end] = getWeekRange(selectedDates[0]);

            // 프로그램적으로 range 선택
            instance.setDate([start, end], true);
             // 달력 닫기!
            instance.close();
        }
    }
});

const loggedInUser = JSON.parse(localStorage.getItem("loggedInUser"));

pushMessageContainer.addEventListener("click", () => {
    // 데이터가 없으면 먼저 로드
    if (!pushMessageData || pushMessageData.length === 0) {
        alert('메시지 데이터를 먼저 불러오고 있습니다. 잠시 후 다시 시도해주세요.');
        return;
    }
    
    // 이미 열린 창이 있고 닫히지 않았다면 포커스만 주기
    if (pushMessageWindow && !pushMessageWindow.closed) {
        pushMessageWindow.focus();
        return;
    }
    
    // 새 창 열기
    pushMessageWindow = window.open('push_message_list.html', '_blank', 'width=500,height=400,scrollbars=yes,resizable=yes');
    
    // 새 창이 로드된 후 데이터 전달
    pushMessageWindow.addEventListener('load', function() {
        // 새 창의 전역 함수 호출하여 데이터 전달
        if (pushMessageWindow.setPushMessageData) {
            pushMessageWindow.setPushMessageData(pushMessageData);
        }
    });
    
    // 창이 닫힐 때 참조 정리
    pushMessageWindow.addEventListener('beforeunload', function() {
        pushMessageWindow = null;
    });
});

// 업데이트 리스트 버튼 클릭 이벤트 추가
if (updateListBtn) {
    updateListBtn.addEventListener('click', function() {
        // 데이터가 없으면 먼저 로드
        if (!updateContentsData) {
            alert('업데이트 데이터를 먼저 불러오고 있습니다. 잠시 후 다시 시도해주세요.');
            return;
        }
        
        // 이미 열린 창이 있고 닫히지 않았다면 포커스만 주기
        if (updateContentsWindow && !updateContentsWindow.closed) {
            updateContentsWindow.focus();
            return;
        }
        
        // 새 창 열기
        updateContentsWindow = window.open('update_contents_list.html', '_blank', 'width=500,height=435,scrollbars=yes,resizable=yes');
        
        // 새 창이 로드된 후 데이터 전달
        updateContentsWindow.addEventListener('load', function() {
            // 새 창의 전역 함수 호출하여 데이터 전달
            if (updateContentsWindow.setUpdateContentsData) {
                updateContentsWindow.setUpdateContentsData(updateContentsData);
            }
        });
        
        // 창이 닫힐 때 참조 정리
        updateContentsWindow.addEventListener('beforeunload', function() {
            updateContentsWindow = null;
        });
    });
}

if(loggedInUser !== null)
    userName.textContent = loggedInUser.user.name;

(async() =>
{
    await configureUserLearningStatus();
    
    // 오늘 날짜를 YYYY-MM-DD 형식으로 생성
    const today = new Date();
    const todayStr = formatDate(today);
    
    await configureContinuousLearningDays(todayStr);

    // 학습 데이터를 한 번만 가져와서 여러 함수에서 사용
    const learningData = await getLearningTimeByWeek(start, end);   //선택한 주간의 학습 시간 데이터
    
    // 지난 주 날짜 계산 (원본 날짜를 변경하지 않도록 새로운 Date 객체 생성)
    const lastWeekStart = new Date(start);
    lastWeekStart.setDate(start.getDate() - 7);
    const lastWeekEnd = new Date(end);
    lastWeekEnd.setDate(end.getDate() - 7);
    const lastLearningData = await getLearningTimeByWeek(lastWeekStart, lastWeekEnd);    // 지난 주간의 학습 시간 데이터
    
    await configureLearningDays(start, end, learningData);
    await configureLearningChart(learningData);
    updateLearningSummary(lastLearningData, learningData, start, end);

    await configureContentsProgress();

    await getUpdateContents();
    await loadPushMessage();
})();

summaryCalendarButton.addEventListener("click", () => {
    fpSummary.open();
});

contentsDataButton.addEventListener("click", () => {
    fpContents.open();
});

/**
 * 사용자 학습 상태 정보 구성(의견서 개수, 레벨 등등)
 */
async function configureUserLearningStatus()
{
    const user = JSON.parse(localStorage.getItem("loggedInUser"));

    let memoCount = 0;
    let level = 0;
    let rank = 0;
    let progress = 0;

    if(user !== null) {
        const id = user.user.id;
        memoCount = await getCountOfMemo(id);
    }

    const items = [
        { icon: "memo", type: "count", value: memoCount, unit: "개", unitPosition:"after", label:"의견서"},
        { icon: "level", type: "level", value: level, unit:"LV.", unitPosition:"before", label:"레벨"},
        { icon: "rank", type: "rank", value: rank, unit:"위", unitPosition:"after", label:"랭킹"},
        { icon: "progress", type: "progress", value: progress, unit:"%", unitPosition:"after", label:"진도율" }
    ]

    items.forEach((item, index) => {
        const valueId = `user-${item.icon}-value-${item.type}`;
        let valueSpan = `<span id=${valueId} style="font-size: 25px; font-weight: bold; font-family:'Noto Sans KR'; color: #fff;">${item.value}</span>`;
        let unitSpan = `<span style="font-size: 10px; font-weight: bold; font-family:'Noto Sans KR'; color: #fff; align-self:flex-end; margin-bottom: 5px;" >${item.unit}</span>`;
        let valueBlock = "";

        if(item.unitPosition === "before") {
            valueBlock = `${unitSpan}${valueSpan}`;
        }
        else if(item.unitPosition === "after") {
            valueBlock = `${valueSpan}${unitSpan}`;
        }

        const html = `
            <div class="rectangle" style="margin-right: 1rem;">
                <div>
                    <div style="margin-top: 5px;">
                        <svg width="37" height="40">
                            <use href="asset/images/images.svg#${item.icon}" />
                        </svg>
                    </div>
                    <div style="flex-direction: row;">
                        ${valueBlock}
                    </div>
                    <div>
                        <span style="font-size: 15px; font-weight: bold; font-family:'Noto Sans KR'; color: #fff;">${item.label}</span>
                    </div>
                </div>
            </div>
        `;

        if(index < 2) {
            document.getElementById("user-info-rect-top").insertAdjacentHTML("beforeend", html);
        } else {
            document.getElementById("user-info-rect-bottom").insertAdjacentHTML("beforeend", html);
        }
        
    });

    userInfoMemoValueCount = document.getElementById("user-memo-value-count");
    userInfoLevelValueLevel = document.getElementById("user-level-value-level");
    userInfoRankValueRank = document.getElementById("user-rank-value-rank");
    userInfoProgressValueProgress = document.getElementById("user-progress-value-progress");

    var loggedInUser = JSON.parse(localStorage.getItem("loggedInUser"));
    if(loggedInUser) {
        userInfoMemoValueCount.textContent = await getCountOfMemo(loggedInUser.user.id);
        userInfoRankValueRank.textContent = await getUserRank();
        userInfoProgressValueProgress.textContent = await getUserLearningRate(loggedInUser.user.id);
    }
}

/**
 * 연속 학습일 구성
 * @param {string} referenceData 
 */
async function configureContinuousLearningDays(referenceData) {
    try {
        const response = await fetch(`${window.baseUrl}leaning/continuous_learning_days?reference_date=${referenceData}`);
        const data = await response.json();
        
        if (response.ok) {
            // 성공시 연속 학습일 표시 업데이트
            const continueLearningDaysElement = document.getElementById("continue-learning-days");
            if (continueLearningDaysElement) {
                continueLearningDaysElement.textContent = `${data.continuous_days || 0}일`;
            }
            console.log(`Continuous learning days: ${data.continuous_days} (reference: ${referenceData})`);
        } else {
            console.error("Error fetching continuous learning days:", data.error);
            // 에러시 기본값으로 0일 표시
            const continueLearningDaysElement = document.getElementById("continue-learning-days");
            if (continueLearningDaysElement) {
                continueLearningDaysElement.textContent = "0일";
            }
        }
    } catch (e) {
        console.error("Error in configureContinuousLearningDays:", e);
        // 에러시 기본값으로 0일 표시
        const continueLearningDaysElement = document.getElementById("continue-learning-days");
        if (continueLearningDaysElement) {
            continueLearningDaysElement.textContent = "0일";
        }
    }
}

/**
 * 사용자의 학습 요일 아이콘 구성
 */
async function configureLearningDays(start, end, learningData)
{
    const today = new Date();
    today.setHours(0, 0, 0, 0); // 시간 초기화

    // 오늘 날짜를 YYYY-MM-DD 형식으로 생성
    const todayStr = formatDate(today);

    let todayIndex = null;
    if (today >= start && today <= end) {
        const day = today.getDay();
        todayIndex = day === 0 ? 6 : day - 1; // 일요일(0)이면 6, 그 외는 (day - 1)
    }

    // 사용자의 학습한 날짜들을 Set으로 저장
    const learningDates = new Set();
    if (learningData && learningData.user_daily_total) {
        learningData.user_daily_total.forEach(item => {
            if (item.total_duration_minutes > 0) {
                learningDates.add(item.date);
            }
        });
    }

    const days = [
        { day: "월", active: false },
        { day: "화", active: false },
        { day: "수", active: false },
        { day: "목", active: false },
        { day: "금", active: false },
        { day: "토", active: false },
        { day: "일", active: false }
    ];

    // 주간 날짜별로 학습 여부 확인하여 active 설정
    console.log('Week range:', start, 'to', end);
    console.log('Learning dates found:', Array.from(learningDates));
    for (let i = 0; i < 7; i++) {
        const currentDate = new Date(start);
        currentDate.setDate(start.getDate() + i);
        // 로컬 날짜 문자열 사용 (UTC 변환 방지)
        const dateStr = formatDate(currentDate);
        
        console.log(`Day ${i} (${['월','화','수','목','금','토','일'][i]}): ${dateStr}, has learning: ${learningDates.has(dateStr)}`);
        
        if (learningDates.has(dateStr)) {
            days[i].active = true;
            
            if(dateStr === todayStr){
                const todayLearningTime = learningData.user_daily_total.find(item => item.date === dateStr)?.total_duration_minutes || 0;
                document.getElementById("learning-time-today").textContent = Math.round(todayLearningTime);
            }
        }
    }

    dayIconContainer.innerHTML = ""; // 기존 아이콘 제거
    
    days.forEach((day, index) => {
        const wrapper = document.createElement("div");
        wrapper.style.display = "flex";
        wrapper.style.flexDirection = "column";
        wrapper.style.alignItems = "center";
        wrapper.style.position = "relative";

        const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
        svg.setAttribute("width", "44");
        svg.setAttribute("height", "44");

        const use = document.createElementNS("http://www.w3.org/2000/svg", "use");
        const symbolId = day.active ? "enabled-fire" : "disabled-fire";
        use.setAttributeNS("http://www.w3.org/1999/xlink", "xlink:href", `asset/images/images.svg#${symbolId}`);
        svg.appendChild(use);

        const label = document.createElement("span");
        label.textContent = day.day;
        label.style.fontSize = "12px";
        label.style.color = index === todayIndex ? "#FF7700" : "#000";

        if(todayIndex !== null && index === todayIndex) {
            const svgCircle = document.createElementNS("http://www.w3.org/2000/svg", "svg");
            svgCircle.setAttribute("width", "7");
            svgCircle.setAttribute("height", "7");
            svgCircle.style.position = "absolute";
            svgCircle.style.top = "0";
            svgCircle.style.left = "85%";

            const circle = document.createElementNS("http://www.w3.org/2000/svg", "circle");
            circle.setAttribute("cx", "3.5");
            circle.setAttribute("cy", "3.5");
            circle.setAttribute("r", "3.5");
            circle.style.fill = "#FF7700";

            svgCircle.appendChild(circle);
            wrapper.appendChild(svgCircle);
        }
        wrapper.appendChild(svg);
        wrapper.appendChild(label);

        dayIconContainer.appendChild(wrapper);
    });
}

/**
 * 학습 차트 구성
 */
async function configureLearningChart(learningData = null)
{
    var myChart = echarts.init(chartContainer, null, {
      renderer: 'canvas',
      useDirtyRect: false
    });

    // 기본값 설정 (데이터가 없을 때)
    let myData = [0, 0, 0, 0, 0, 0, 0];
    let averageData = [0, 0, 0, 0, 0, 0, 0];

    // 학습 데이터가 있을 때 차트 데이터 구성
    if (learningData) {
        console.log('Learning data received:', learningData);
        
        // 데이터 초기화
        myData = [0, 0, 0, 0, 0, 0, 0];
        averageData = [0, 0, 0, 0, 0, 0, 0];

        // 현재 선택된 주간 범위 가져오기
        const startDate = fpSummary.selectedDates[0];
        const endDate = fpSummary.selectedDates[1];
        
        if (startDate && endDate) {
            // 사용자 데이터를 날짜별로 매핑
            const userDataMap = {};
            if (learningData.user_daily_total) {
                console.log('Raw user_daily_total:', learningData.user_daily_total);
                learningData.user_daily_total.forEach(item => {
                    console.log('Processing user item:', item);
                    userDataMap[item.date] = item.total_duration_minutes || 0;
                });
            }
            
            // 전체 사용자 평균 데이터를 날짜별로 매핑
            const avgDataMap = {};
            if (learningData.all_users_daily_average) {
                console.log('Raw all_users_daily_average:', learningData.all_users_daily_average);
                learningData.all_users_daily_average.forEach(item => {
                    console.log('Processing avg item:', item);
                    avgDataMap[item.date] = item.avg_duration_minutes || 0;
                });
            }
            
            console.log('=== CHART DATA MAPPING DEBUG ===');
            console.log('Selected week range:', 
                       formatDate(startDate), 
                       'to', 
                       formatDate(endDate));
            console.log('User data map:', userDataMap);
            console.log('Average data map:', avgDataMap);
            
            // 주간 범위의 각 날짜를 요일별로 매핑
            for (let i = 0; i < 7; i++) {
                const currentDate = new Date(startDate);
                currentDate.setDate(startDate.getDate() + i);
                const dateStr = formatDate(currentDate);
                
                const userValue = userDataMap[dateStr] || 0;
                const avgValue = avgDataMap[dateStr] || 0;
                
                myData[i] = Math.round(userValue);
                averageData[i] = Math.round(avgValue);
                
                console.log(`Chart Day ${i} (${['월','화','수','목','금','토','일'][i]}): ${dateStr} -> User: ${userValue}, Avg: ${avgValue}`);
            }
        }
        
        console.log('Chart myData:', myData);
        console.log('Chart averageData:', averageData);
    }

    // 동적 Y축 최대값 계산
    const allData = [...myData, ...averageData];
    const maxValue = Math.max(...allData);
    const dynamicMax = Math.max(60, Math.ceil(maxValue / 10) * 10); // 최소 60, 10의 배수로 올림
    console.log('Chart dynamic max:', dynamicMax, 'from max data:', maxValue);

    var option = {
        grid: {
            top: 30,
            bottom: 50,
        },
        xAxis: {
            type: 'category',
            data: ['월', '화', '수', '목', '금', '토', '일']
        },
        yAxis: {
            type: 'value',
            interval: 10,
            min: 0,
            max: dynamicMax  // 동적 최대값
        },
        legend: {
            data: ['나의 학습시간', '전체 학습자 평균 학습시간'],
            bottom: 0,  // 💡 아래쪽에 고정
            icon: 'circle',
            left: '8%',
        },
        series: [
            {
                name: '나의 학습시간',
                data: myData,
                barWidth: 30,
                type: 'bar',
                itemStyle: {
                    color: '#3CB043',
                    barBorderRadius:[40,40,40,40]
                },
                label: {
                    show: true,
                    position: 'inside',
                    fontWeight: 'bold',
                    formatter: function(params) {
                        return params.value === 0? '' : params.value;
                    }
                }
            },
            {
                name: '전체 학습자 평균 학습시간',
                data: averageData,
                type: 'bar',
                barWidth: 30,
                itemStyle: {
                    color: '#FFCC66',
                    barBorderRadius:[40,40,40,40]
                },
                label: {
                    show: true,
                    position: 'inside',
                    fontWeight: 'bold',
                    formatter: function(params) {
                        return params.value === 0? '' : params.value;
                    }
                }
            }
        ]
    };

    myChart.setOption(option);

    window.addEventListener('resize', function() {
        myChart.resize();
    });
}

/**
 * 학습 통계 요약 업데이트 함수
 */
async function updateLearningSummary(lastWeekData, currentWeekData, start, end) {
    
    // 현재 주 나의 학습 데이터에서 하루 평균 학습시간 계산
    let totalMinutes = 0;
    let totalDays = 0;
    
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    
    // 현재 주의 각 날짜를 확인하여 계산
    for (let i = 0; i < 7; i++) {
        const currentDate = new Date(start);
        currentDate.setDate(start.getDate() + i);
        
        // 오늘 이후의 날짜는 제외
        if (currentDate > today) {
            break;
        }
        
        totalDays++; // 실제 지나간 날 수 카운트
        
        const dateStr = formatDate(currentDate);
        
        // 해당 날짜의 학습 시간 찾기
        let dailyMinutes = 0;
        if (currentWeekData && currentWeekData.user_daily_total) {
            const dayData = currentWeekData.user_daily_total.find(item => item.date === dateStr);
            if (dayData && dayData.total_duration_minutes > 0) {
                dailyMinutes = dayData.total_duration_minutes;
            }
        }
        totalMinutes += dailyMinutes; // 학습시간이 0인 날도 0으로 포함
    }
    
    // 하루 평균 학습시간 (분 단위) - 지나간 모든 날로 나누기
    const avgMinutesPerDay = totalDays > 0 ? Math.round(totalMinutes / totalDays) : 0;
    
    // 모든 .my-avg-learning-minutes 요소에 평균 학습시간 설정
    myAvgLearningMinutes.forEach(span => {
        span.textContent = avgMinutesPerDay.toString().padStart(2, '0');
    });

    percentChangeValue.textContent = "00";
    percentChangeText.textContent = "% 내렸습니다.";

    allAvgLearningMinutes.textContent = "00";
    comparePercentValue.textContent = "00";
    comparePercentText.textContent = "% 높습니다.";
}

/**
 * 콘텐츠 진도율 구성
 */
async function configureContentsProgress() {
    const categories = [
        { title: "A_BIM/DX", progress: 0, total: 23 },
        { title: "B_천지인", progress: 0, total: 7 },
        { title: "C_설계도서 검토", progress: 0, total: 41 },
        { title: "D_모델제작과 OBS", progress: 0, total: 17 },
        { title: "E_시공상세도", progress: 0, total: 13 },
        { title: "F_공사관리", progress: 0, total: 1 },
        { title: "G_안전관리", progress: 0, total: 8 },
        { title: "H_품질 및 환경관리", progress: 0, total: 7 },
        { title: "I_공정 및 기성관리", progress: 0, total: 5 },
        { title: "J_보상 및 민원", progress: 0, total: 3 },
        { title: "K_준공 및 운영", progress: 0, total: 13 },
        { title: "L_DfMA", progress: 0, total: 2 }
    ];

    const categoryDetails = {
        "A_BIM/DX": [
            { page: "개요", start: "2025. 3. 6. 오전 10:59:58", end: "2025. 3. 6. 오전 11:00:26", duration: "27초", ip: "172.16.8.127" },
            { page: "개요", start: "2025. 3. 6. 오전 10:59:58", end: "2025. 3. 6. 오전 11:00:26", duration: "27초", ip: "172.16.8.127" },
            { page: "개요", start: "2025. 3. 6. 오전 10:59:58", end: "2025. 3. 6. 오전 11:00:26", duration: "27초", ip: "172.16.8.127" },
            { page: "개요", start: "2025. 3. 6. 오전 10:59:58", end: "2025. 3. 6. 오전 11:00:26", duration: "27초", ip: "172.16.8.127" },
            { page: "개요", start: "2025. 3. 6. 오전 10:59:58", end: "2025. 3. 6. 오전 11:00:26", duration: "27초", ip: "172.16.8.127" },
            { page: "개요", start: "2025. 3. 6. 오전 10:59:58", end: "2025. 3. 6. 오전 11:00:26", duration: "27초", ip: "172.16.8.127" },
            { page: "개요", start: "2025. 3. 6. 오전 10:59:58", end: "2025. 3. 6. 오전 11:00:26", duration: "27초", ip: "172.16.8.127" },
            { page: "DX 목표/실행요건", start: "2025. 3. 6. 오전 11:01:00", end: "2025. 3. 6. 오전 11:02:00", duration: "1분", ip: "192.168.0.1" },
            { page: "DX 목표/실행요건", start: "2025. 3. 6. 오전 11:01:00", end: "2025. 3. 6. 오전 11:02:00", duration: "1분", ip: "192.168.0.1" },
            { page: "DX 목표/실행요건", start: "2025. 3. 6. 오전 11:01:00", end: "2025. 3. 6. 오전 11:02:00", duration: "1분", ip: "192.168.0.1" },
            { page: "DX 목표/실행요건", start: "2025. 3. 6. 오전 11:01:00", end: "2025. 3. 6. 오전 11:02:00", duration: "1분", ip: "192.168.0.1" },
            { page: "DX 목표/실행요건", start: "2025. 3. 6. 오전 11:01:00", end: "2025. 3. 6. 오전 11:02:00", duration: "1분", ip: "192.168.0.1" },
            { page: "DX 목표/실행요건", start: "2025. 3. 6. 오전 11:01:00", end: "2025. 3. 6. 오전 11:02:00", duration: "1분", ip: "192.168.0.1" },
            { page: "DX 목표/실행요건", start: "2025. 3. 6. 오전 11:01:00", end: "2025. 3. 6. 오전 11:02:00", duration: "1분", ip: "192.168.0.1" },
            { page: "DX 목표/실행요건", start: "2025. 3. 6. 오전 11:01:00", end: "2025. 3. 6. 오전 11:02:00", duration: "1분", ip: "192.168.0.1" },
            { page: "정부 건설정책 추진 현황", start: "2025. 3. 6. 오전 11:01:00", end: "2025. 3. 6. 오전 11:02:00", duration: "1분", ip: "192.168.0.1" },
            { page: "정부 건설정책 추진 현황", start: "2025. 3. 6. 오전 11:01:00", end: "2025. 3. 6. 오전 11:02:00", duration: "1분", ip: "192.168.0.1" },
            { page: "정부 건설정책 추진 현황", start: "2025. 3. 6. 오전 11:01:00", end: "2025. 3. 6. 오전 11:02:00", duration: "1분", ip: "192.168.0.1" },
            { page: "정부 건설정책 추진 현황", start: "2025. 3. 6. 오전 11:01:00", end: "2025. 3. 6. 오전 11:02:00", duration: "1분", ip: "192.168.0.1" },
            { page: "정부 건설정책 추진 현황", start: "2025. 3. 6. 오전 11:01:00", end: "2025. 3. 6. 오전 11:02:00", duration: "1분", ip: "192.168.0.1" },
            { page: "정부 건설정책 추진 현황", start: "2025. 3. 6. 오전 11:01:00", end: "2025. 3. 6. 오전 11:02:00", duration: "1분", ip: "192.168.0.1" },
            { page: "정부 건설정책 추진 현황", start: "2025. 3. 6. 오전 11:01:00", end: "2025. 3. 6. 오전 11:02:00", duration: "1분", ip: "192.168.0.1" },
            { page: "정부 건설정책 추진 현황", start: "2025. 3. 6. 오전 11:01:00", end: "2025. 3. 6. 오전 11:02:00", duration: "1분", ip: "192.168.0.1" },
            { page: "정부 건설정책 추진 현황", start: "2025. 3. 6. 오전 11:01:00", end: "2025. 3. 6. 오전 11:02:00", duration: "1분", ip: "192.168.0.1" },
            { page: "국내의 BIM/DX 실태", start: "2025. 3. 6. 오전 11:01:00", end: "2025. 3. 6. 오전 11:02:00", duration: "1분", ip: "192.168.0.1" },
            { page: "국내의 BIM/DX 실태", start: "2025. 3. 6. 오전 11:01:00", end: "2025. 3. 6. 오전 11:02:00", duration: "1분", ip: "192.168.0.1" },
            { page: "국내의 BIM/DX 실태", start: "2025. 3. 6. 오전 11:01:00", end: "2025. 3. 6. 오전 11:02:00", duration: "1분", ip: "192.168.0.1" },
            { page: "국내의 BIM/DX 실태", start: "2025. 3. 6. 오전 11:01:00", end: "2025. 3. 6. 오전 11:02:00", duration: "1분", ip: "192.168.0.1" },
            { page: "국내의 BIM/DX 실태", start: "2025. 3. 6. 오전 11:01:00", end: "2025. 3. 6. 오전 11:02:00", duration: "1분", ip: "192.168.0.1" },
            { page: "국내의 BIM/DX 실태", start: "2025. 3. 6. 오전 11:01:00", end: "2025. 3. 6. 오전 11:02:00", duration: "1분", ip: "192.168.0.1" },
            { page: "국내의 BIM/DX 실태", start: "2025. 3. 6. 오전 11:01:00", end: "2025. 3. 6. 오전 11:02:00", duration: "1분", ip: "192.168.0.1" },
            { page: "국내의 BIM/DX 실태", start: "2025. 3. 6. 오전 11:01:00", end: "2025. 3. 6. 오전 11:02:00", duration: "1분", ip: "192.168.0.1" },
            { page: "국내의 BIM/DX 실태", start: "2025. 3. 6. 오전 11:01:00", end: "2025. 3. 6. 오전 11:02:00", duration: "1분", ip: "192.168.0.1" },
            { page: "국내의 BIM/DX 실태", start: "2025. 3. 6. 오전 11:01:00", end: "2025. 3. 6. 오전 11:02:00", duration: "1분", ip: "192.168.0.1" },
            { page: "국내의 BIM/DX 실태", start: "2025. 3. 6. 오전 11:01:00", end: "2025. 3. 6. 오전 11:02:00", duration: "1분", ip: "192.168.0.1" },
            { page: "외부 제시의견", start: "2025. 3. 6. 오전 11:01:00", end: "2025. 3. 6. 오전 11:02:00", duration: "1분", ip: "192.168.0.1" },
            { page: "외부 제시의견", start: "2025. 3. 6. 오전 11:01:00", end: "2025. 3. 6. 오전 11:02:00", duration: "1분", ip: "192.168.0.1" },
            { page: "외부 제시의견", start: "2025. 3. 6. 오전 11:01:00", end: "2025. 3. 6. 오전 11:02:00", duration: "1분", ip: "192.168.0.1" },
            { page: "외부 제시의견", start: "2025. 3. 6. 오전 11:01:00", end: "2025. 3. 6. 오전 11:02:00", duration: "1분", ip: "192.168.0.1" },
            { page: "외부 제시의견", start: "2025. 3. 6. 오전 11:01:00", end: "2025. 3. 6. 오전 11:02:00", duration: "1분", ip: "192.168.0.1" },
            { page: "외부 제시의견", start: "2025. 3. 6. 오전 11:01:00", end: "2025. 3. 6. 오전 11:02:00", duration: "1분", ip: "192.168.0.1" },
            { page: "외부 제시의견", start: "2025. 3. 6. 오전 11:01:00", end: "2025. 3. 6. 오전 11:02:00", duration: "1분", ip: "192.168.0.1" },
            { page: "외부 제시의견", start: "2025. 3. 6. 오전 11:01:00", end: "2025. 3. 6. 오전 11:02:00", duration: "1분", ip: "192.168.0.1" },
            { page: "전면 BIM설계 도입의 한계", start: "2025. 3. 6. 오전 11:01:00", end: "2025. 3. 6. 오전 11:02:00", duration: "1분", ip: "192.168.0.1" },
            { page: "전면 BIM설계 도입의 한계", start: "2025. 3. 6. 오전 11:01:00", end: "2025. 3. 6. 오전 11:02:00", duration: "1분", ip: "192.168.0.1" },
            { page: "전면 BIM설계 도입의 한계", start: "2025. 3. 6. 오전 11:01:00", end: "2025. 3. 6. 오전 11:02:00", duration: "1분", ip: "192.168.0.1" },
            { page: "전면 BIM설계 도입의 한계", start: "2025. 3. 6. 오전 11:01:00", end: "2025. 3. 6. 오전 11:02:00", duration: "1분", ip: "192.168.0.1" },
            { page: "전면 BIM설계 도입의 한계", start: "2025. 3. 6. 오전 11:01:00", end: "2025. 3. 6. 오전 11:02:00", duration: "1분", ip: "192.168.0.1" },
            { page: "전면 BIM설계 도입의 한계", start: "2025. 3. 6. 오전 11:01:00", end: "2025. 3. 6. 오전 11:02:00", duration: "1분", ip: "192.168.0.1" },
            { page: "전면 BIM설계 도입의 한계", start: "2025. 3. 6. 오전 11:01:00", end: "2025. 3. 6. 오전 11:02:00", duration: "1분", ip: "192.168.0.1" },
            { page: "전면 BIM설계 도입의 한계", start: "2025. 3. 6. 오전 11:01:00", end: "2025. 3. 6. 오전 11:02:00", duration: "1분", ip: "192.168.0.1" },
            { page: "전면 BIM설계 도입의 한계", start: "2025. 3. 6. 오전 11:01:00", end: "2025. 3. 6. 오전 11:02:00", duration: "1분", ip: "192.168.0.1" },
            { page: "전면 BIM설계 도입의 한계", start: "2025. 3. 6. 오전 11:01:00", end: "2025. 3. 6. 오전 11:02:00", duration: "1분", ip: "192.168.0.1" },
            { page: "전면 BIM설계 도입의 한계", start: "2025. 3. 6. 오전 11:01:00", end: "2025. 3. 6. 오전 11:02:00", duration: "1분", ip: "192.168.0.1" },
            { page: "전면 BIM설계 도입의 한계", start: "2025. 3. 6. 오전 11:01:00", end: "2025. 3. 6. 오전 11:02:00", duration: "1분", ip: "192.168.0.1" },
            { page: "전면 BIM설계 도입의 한계", start: "2025. 3. 6. 오전 11:01:00", end: "2025. 3. 6. 오전 11:02:00", duration: "1분", ip: "192.168.0.1" },
            { page: "전면 BIM설계 도입의 한계", start: "2025. 3. 6. 오전 11:01:00", end: "2025. 3. 6. 오전 11:02:00", duration: "1분", ip: "192.168.0.1" },
            { page: "전면 BIM설계 도입의 한계", start: "2025. 3. 6. 오전 11:01:00", end: "2025. 3. 6. 오전 11:02:00", duration: "1분", ip: "192.168.0.1" },
            { page: "전면 BIM설계 도입의 한계", start: "2025. 3. 6. 오전 11:01:00", end: "2025. 3. 6. 오전 11:02:00", duration: "1분", ip: "192.168.0.1" },
            { page: "전면 BIM설계 도입의 한계", start: "2025. 3. 6. 오전 11:01:00", end: "2025. 3. 6. 오전 11:02:00", duration: "1분", ip: "192.168.0.1" },
            { page: "전면 BIM설계 도입의 한계", start: "2025. 3. 6. 오전 11:01:00", end: "2025. 3. 6. 오전 11:02:00", duration: "1분", ip: "192.168.0.1" },
            { page: "전면 BIM설계 도입의 한계", start: "2025. 3. 6. 오전 11:01:00", end: "2025. 3. 6. 오전 11:02:00", duration: "1분", ip: "192.168.0.1" },
            { page: "전면 BIM설계 도입의 한계", start: "2025. 3. 6. 오전 11:01:00", end: "2025. 3. 6. 오전 11:02:00", duration: "1분", ip: "192.168.0.1" },           
        ],
        "B_천지인": [
            { page: "개요", start: "2025. 3. 7. 오전 9:00:00", end: "2025. 3. 7. 오전 9:30:00", duration: "30분", ip: "192.168.0.2" }
        ]
    }

    categories.forEach(category => {
        const row = document.createElement("div");
        row.style.display = "flex";
        row.style.flexDirection = "row";
        row.style.padding = "17px";
        row.style.alignItems = "center";

        // 제목
        const titleSpan = document.createElement("span");
        titleSpan.className = "contents-title-flex";
        titleSpan.textContent = category.title;

        // 진행률 바
        const progressBar = document.createElement("div");
        progressBar.className = "progress-bar";
        progressBar.style.marginLeft = "50px";
        progressBar.style.marginRight = "50px";

        const progressFill = document.createElement("div");
        progressFill.className = "progress-fill";

        const percent = Math.round((category.progress / category.total) * 100);
        progressFill.style.width = `${percent}%`;

        const progressText = document.createElement("span");
        progressText.className = "progress-text";
        progressText.textContent = `${category.progress} / ${category.total}`;

        progressBar.appendChild(progressFill);
        progressBar.appendChild(progressText);

        // 퍼센트 span
        const percentSpan = document.createElement("span");
        percentSpan.textContent = `${percent}%`;

        row.appendChild(titleSpan);
        row.appendChild(progressBar);
        row.appendChild(percentSpan);

        contentsProgressContainer.appendChild(row);

        row.addEventListener("click", () =>
        {
            const next = row.nextElementSibling;
            
            // 이미 열려있으면 (즉, row 바로 뒤에 expander-container가 있으면)
            if (next && next.classList.contains("expander-container")) {
                next.remove();
                return; // ✅ 여기서 끝 → 다시 클릭 시 닫힘
            }

            const existing = document.querySelector(".expander-container");
            if (existing) existing.remove();

            const details = categoryDetails[category.title];
            if (!details || details.length === 0) return;

            const expander = document.createElement("div");
            expander.className = "expander-container";
            expander.style.width = "98%";
            expander.style.margin = "0 0 0 0";
            expander.style.border = "none";

            expander.appendChild(createDetailTable(details));

            row.insertAdjacentElement("afterend", expander);
        });
    });
}

// ✅ 테이블 생성 함수
function createDetailTable(data) {
    const table = document.createElement("table");
    table.className = "my-table";

    table.innerHTML = `
        <thead>
            <tr>
                <th>페이지</th>
                <th>시작 시간</th>
                <th>종료 시간</th>
                <th>학습 시간</th>
                <th>IP</th>
            </tr>
        </thead>
    `;

    const tbody = document.createElement("tbody");

    const grouped = {};
    data.forEach(item => {
        if (!grouped[item.page]) {
            grouped[item.page] = [];
        }
        grouped[item.page].push(item);
    });

    Object.keys(grouped).forEach(pageName => {
        const items = grouped[pageName];
        items.forEach((item, idx) => {
            const tr = document.createElement("tr");

            if (idx === 0) {
                const tdPage = document.createElement("td");
                tdPage.innerText = pageName;
                tdPage.rowSpan = items.length;
                tdPage.className = "page-cell";
                tr.appendChild(tdPage);
            }

            const tdStart = document.createElement("td");
            tdStart.innerText = item.start;

            const tdEnd = document.createElement("td");
            tdEnd.innerText = item.end;

            const tdDuration = document.createElement("td");
            tdDuration.innerText = item.duration;

            const tdIp = document.createElement("td");
            tdIp.innerText = item.ip;

            tr.appendChild(tdStart);
            tr.appendChild(tdEnd);
            tr.appendChild(tdDuration);
            tr.appendChild(tdIp);

            tbody.appendChild(tr);
        });
    });

    table.appendChild(tbody);
    return table;
}

/**
 * 사용자의 의견서 개수를 가져오는 함수  
 * @param {string} userId - 사번
 * @returns {Promise<number>} - 의견서 개수
 * 0 if an error occurs.
 */
async function getCountOfMemo(userId) {
    try{
        const response = await fetch(`${window.baseUrl}memo/?user_id=${userId}`);
        const data = await response.json();
        if(response.ok) 
        {
            return data.length;
        }
    }
    catch(e) {
        console.error("Error fetching memo count:", e);
    }
    return 0;
}

/**
 * 사용자의 랭킹을 가져오는 함수
 * @returns {Promise<number>} - 사용자의 랭킹
 */
async function getUserRank() {
    try {
        const response = await fetch(`${window.baseUrl}leaning/my_learning_rank`);
        const data = await response.json();

        if(response.ok) {
            return data.rank;
        }
    }
    catch(e) {
        console.error("Error fetching user rank:", e);
    }
    return 0;
}

/**
 * 사용자 학습률을 가져오는 함수
 * @param {string} id - 사용자 ID
 * @returns {Promise<number>} - 사용자 학습률
 */
async function getUserLearningRate(id) {
    try {
        var period_type = 'day';
        var period_value = `2025-01-01 ~ ${formatDate(new Date())}`; // 현재 날짜까지의 범위
        const response = await fetch(`${window.baseUrl}leaning/completion-rate?filter_type=user&filter_value=${id}&period_type=${period_type}&period_value=${period_value}`);
        const data = await response.json();

        if(response.ok) {
            return data.completion_rate;
        }
    }
    catch(e) {
        console.error("Error fetching user learning rate:", e);
    }
    return 0;
}

async function getLearningTimeByWeek(start_date, end_date) {
    try {
        
        const startDateStr = formatDate(start_date);
        const endDateStr = formatDate(end_date);

        const response = await fetch(`${window.baseUrl}leaning/learning_time_by_week?start_date=${startDateStr}&end_date=${endDateStr}`);
        const data = await response.json();

        if(response.ok) {
            return data;
        }
    }
    catch(e) {
        console.error("Error fetching learning time by week:", e);
    }
    return [];
}

async function getUpdateContents(daysAgo = 14) {
    try {
        const response = await fetch(`${window.baseUrl}leaning/get_updated_contents?days=${daysAgo}`);
        const data = await response.json();

        if(response.ok) {
            // 데이터 저장
            updateContentsData = data.contents || [];
            
            updateList.innerHTML = ""; // 기존 내용 초기화
            
            if (data.contents && data.contents.length > 0) {
                var unviewedCount = 0;
                data.contents.forEach(content => {
                    const tr = document.createElement("tr");
                    
                    // 업데이트 날짜 포맷팅 (월/일 형식)
                    const updateDate = new Date(content.updated_at);
                    const dateStr = `${updateDate.getMonth() + 1}/${updateDate.getDate()}`;
                    
                    // 파일 이름에서 000_ 형식의 접두사와 확장자 제거
                    const cleanedName = content.name.replace(/^\d+_/, '').replace(/\.[^/.]+$/, '');
                    
                    // 업데이트 확인 안한 건은 파란색 텍스트
                    const textColor = content.viewed_after_update ? "#000" : "#007bff";
                    unviewedCount += content.viewed_after_update ? 0 : 1;

                    tr.innerHTML = `
                        <td style="padding: 8px; font-size: 13px; color: ${textColor}; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;" title="${cleanedName}">
                            ${cleanedName}
                        </td>
                        <td style="padding: 8px; font-size: 13px; color: ${textColor}; text-align: center;">
                            ${dateStr}
                        </td>
                    `;
                    
                    updateList.appendChild(tr);

                    updateContentsUnviewedCount.textContent = unviewedCount || 0; // 업데이트 확인 안한 콘텐츠 개수 표시
                });
            } else {
                // 데이터가 없을 때
                const tr = document.createElement("tr");
                tr.innerHTML = `
                    <td colspan="2" style="text-align: center; padding: 20px; color: #888; font-size: 13px;">
                        최근 ${daysAgo}일 동안 업데이트된 콘텐츠가 없습니다.
                    </td>
                `;
                updateList.appendChild(tr);
            }
        }
    }
    catch(e) {
        console.error("Error fetching update contents:", e);
        updateContentsData = null;
        const tr = document.createElement("tr");
        tr.innerHTML = `
            <td colspan="2" style="text-align: center; padding: 20px; color: #dc3545; font-size: 13px;">
                업데이트 콘텐츠를 불러오는 중 오류가 발생했습니다.
            </td>
        `;
        updateList.appendChild(tr);
    }
}

async function loadPushMessage() {
    const response = await fetch(`${window.baseUrl}leaning/push/load`);
    const data = await response.json();
    if (response.ok) {
        pushMessageCount.textContent = data.messages.length || 0; // 메시지 개수 표시

        if(pushMessageData === null)
            pushMessageData = data.messages; // 메시지 데이터 저장
        else
            pushMessageData.push(...data.messages); // 기존 데이터에 추가
    } else {
        console.error("Failed to load push messages:", data.error);
    }
    
}

// ✅ 공통 함수로 분리
function getWeekRange(date) {
    const start = new Date(date);
    start.setHours(0, 0, 0, 0); // 시간 초기화

    const day = start.getDay();
    const diff = (day === 0 ? -6 : 1) - day;
    start.setDate(start.getDate() + diff);

    const end = new Date(start);
    end.setHours(23, 59, 59, 999); // 시간 초기화
    end.setDate(start.getDate() + 6);

    return [start, end];
}

/**
 * 날짜를 YYYY-MM-DD 형식으로 포맷팅
 * @param {Date} date - 포맷팅할 날짜 객체
 * @returns {string} - YYYY-MM-DD 형식의 문자열
 */
function formatDate(date) {
    return date.getFullYear() + '-' + 
           String(date.getMonth() + 1).padStart(2, '0') + '-' + 
           String(date.getDate()).padStart(2, '0');
}

/**
 * 오늘을 기준으로 연속 학습일 계산
 * @param {Set} learningDates - 학습한 날짜들의 Set (YYYY-MM-DD 형식)
 * @returns {number} - 연속 학습일 수
 */
function calculateContinuousLearningDays(learningDates) {
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    
    let continuousDays = 0;
    let currentDate = new Date(today);
    
    // 오늘부터 거꾸로 확인하여 연속 학습일 계산
    while (true) {
        const dateStr = formatDate(currentDate);
        
        if (learningDates.has(dateStr)) {
            continuousDays++;
            // 하루 전으로 이동
            currentDate.setDate(currentDate.getDate() - 1);
        } else {
            break;
        }
    }
    
    return continuousDays;
}
