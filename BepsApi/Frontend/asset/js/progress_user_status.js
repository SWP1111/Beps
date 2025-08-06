 const contentsProgressContainer = document.getElementById("contents-progress-container");
const contentsDataButton = document.getElementById("contents-data-button");

let [start, end] = getWeekRange(new Date());

const fpContents = flatpickr("#contents-date", {
    mode: "range",
    dateFormat: "y-m-d",
    locale: "ko",
    defaultDate: [start, end],  // ✅ 이번 주 기본 선택
    onChange: function(selectedDates, dateStr, instance) {
        if (selectedDates.length === 1) {
            [start, end] = getWeekRange(selectedDates[0]);

            // 프로그램적으로 range 선택
            instance.setDate([start, end], true);
             // 달력 닫기!
            instance.close();

            const existing = document.querySelector(".expander-container");
            if (existing) existing.remove();
        }
    }
});

contentsDataButton.addEventListener("click", () => {
    fpContents.open();
});


contentsProgressContainer.addEventListener("click", async (event) => 
{
    const row = event.target.closest(".progress-row");
    if (!row) return; // 클릭한 요소가 progress-row가 아니면 무시

    const channelId = row.dataset.channelId;
    const next = row.nextElementSibling;
        
    // 이미 열려있으면 (즉, row 바로 뒤에 expander-container가 있으면)
    if (next && next.classList.contains("expander-container")) {
        next.remove();
        return; // ✅ 여기서 끝 → 다시 클릭 시 닫힘
    }

    const existing = document.querySelector(".expander-container");
    if (existing) existing.remove();

    const expander = document.createElement("div");
    expander.className = "expander-container";
    expander.style.width = "98%";
    expander.style.margin = "0 0 0 0";
    expander.style.border = "none";

    const details = await LoadLearningHistoryPerChannel(channelId, formatDate(start), formatDate(end));
    if (!details || details.length === 0) {
        expander.appendChild(createNoDataMessage());
    }
    else {
        expander.appendChild(createDetailTable(details));
    }

    row.insertAdjacentElement("afterend", expander);
});

/**
 * 콘텐츠 진도율 구성
 */
export async function configureContentsProgress(data) {

    contentsProgressContainer.innerHTML = ""; // 기존 내용 초기화

    const categories = data.map(category => ({
        title: category.channel_name,
        id: category.channel_id,
        progress: category.completed_pages,
        total: category.total_pages,
        rate: category.progress_rate
    })).sort((a,b) => a.id - b.id); // ID 순으로 정렬;

    categories.forEach(category => {
        const row = createCategoryRow(category, categories.length);
        contentsProgressContainer.appendChild(row);
    });
}

function createCategoryRow(category, totalCategories) {

    const row = document.createElement("div");
    row.className = "progress-row";
    // 🔹 간격 조정 - 부모 높이에 맞춰 균등 분할
    row.style.display = "flex";
    row.style.flexDirection = "row";
    row.style.alignItems = "center";
    row.style.height = `${100 / totalCategories}%`; // 🔹 height 대신 flex-basis 사용
    row.style.minHeight = "50px"; // 🔹 최소 높이 설정
    row.style.padding = "0 0 0 15px"; // 🔹 패딩 추가
    row.style.cursor = "pointer"; // 🔹 클릭 가능하게
    row.dataset.channelId = category.id;

    // 제목
    const titleSpan = document.createElement("span");
    titleSpan.className = "contents-title-flex";
    titleSpan.textContent = convertChannelName(category.title);

    // 진행률 바
    const progressBar = document.createElement("div");
    progressBar.className = "progress-bar";
    progressBar.style.flex = "1"; // 🔹 남은 공간 모두 사용
    progressBar.style.marginLeft = "20px";
    progressBar.style.marginRight = "20px";

    const progressFill = document.createElement("div");
    progressFill.className = "progress-fill";

    const percent = Math.round(category.rate);
    progressFill.style.width = `${percent}%`;

    const progressText = document.createElement("span");
    progressText.className = "progress-text";
    progressText.textContent = `${category.progress} / ${category.total}`;

    progressBar.appendChild(progressFill);
    progressBar.appendChild(progressText);

    // 퍼센트 span
    const percentSpan = document.createElement("span");
    percentSpan.style.flex = "0 0 60px"; // 🔹 고정 너비 60px
    percentSpan.style.textAlign = "right";
    percentSpan.textContent = `${percent}%`;

    row.appendChild(titleSpan);
    row.appendChild(progressBar);
    row.appendChild(percentSpan);

    return row;
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
        if (!grouped[item.file_name]) {
            grouped[item.file_name] = [];
        }
        grouped[item.file_name].push(item);
    });

    Object.keys(grouped).forEach(fileName => {
        const items = grouped[fileName];
        items.forEach((item, idx) => {
            const tr = document.createElement("tr");

            if (idx === 0) {
                const tdPage = document.createElement("td");
                tdPage.innerText = convertPageName(fileName);
                tdPage.rowSpan = items.length;
                tdPage.className = "page-cell";
                tr.appendChild(tdPage);
            }

            const tdStart = document.createElement("td");
            const utcStart = new Date(item.start_time);
            tdStart.innerText = utcStart.toLocaleString();

            const tdEnd = document.createElement("td");
            const utcEnd = new Date(item.end_time);
            tdEnd.innerText = utcEnd.toLocaleString();

            const tdDuration = document.createElement("td");
            tdDuration.innerText = item.stay_duration.split(".")[0]; // 초 단위로 표시

            const tdIp = document.createElement("td");
            tdIp.innerText = item.ip_address;

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

async function LoadLearningHistoryPerChannel(channel_id, start_date, end_date) {
    try {
        const response = await fetch(`${window.baseUrl}leaning/date_per_channels?channel_id=${channel_id}&start_date=${start_date}&end_date=${end_date}`);
        const data = await response.json();
        if (response.ok) {
            return data.data;
        }
    } catch (error) {
        console.error("Error fetching learning history:", error);
    }

    return [];
}

// 🔹 데이터 없을 때 메시지 생성 함수
function createNoDataMessage() {
    const messageDiv = document.createElement("div");
    messageDiv.style.textAlign = "center";
    messageDiv.style.padding = "20px 10px";
    messageDiv.style.color = "#666";
    messageDiv.style.fontSize = "14px";
    messageDiv.style.backgroundColor = "#f9f9f9";
    messageDiv.style.border = "1px solid #e0e0e0";
    messageDiv.style.borderRadius = "4px";
    
    //이미지 링크: https://icon-sets.iconify.design/fluent-emoji-flat/page-8.html
    //fluent-emoji-flat:confounded-face
    messageDiv.innerHTML = `
        <div style="margin-bottom: 10px;">
           <svg xmlns="http://www.w3.org/2000/svg" width="32" height="32" viewBox="0 0 32 32">
                <g fill="none"><path fill="#ffb02e" d="M15.999 29.998c9.334 0 13.999-6.268 13.999-14c0-7.73-4.665-13.998-14-13.998C6.665 2 2 8.268 2 15.999s4.664 13.999 13.999 13.999"/><path fill="#000" d="M8.106 13.553a1 1 0 0 1 1.341-.448l4 2a1 1 0 0 1 0 1.79l-4 2a1 1 0 1 1-.894-1.79L10.763 16l-2.21-1.106a1 1 0 0 1-.447-1.341m15.789 0a1 1 0 0 0-1.342-.448l-4 2a1 1 0 0 0 0 1.79l4 2a1 1 0 1 0 .894-1.79L21.237 16l2.21-1.106a1 1 0 0 0 .448-1.341m-10.188 6.74a1 1 0 0 0-1.414 0L10 22.586l-1.293-1.293a1 1 0 0 0-1.414 1.414l2 2a1 1 0 0 0 1.414 0L13 22.414l2.293 2.293a1 1 0 0 0 1.414 0L19 22.414l2.293 2.293a1 1 0 0 0 1.414 0l2-2a1 1 0 0 0-1.414-1.414L22 22.586l-2.293-2.293a1 1 0 0 0-1.414 0L16 22.586z"/></g>
            </svg>
        </div>
        <div style="font-weight: bold; margin-bottom: 5px;">해당 기간에는 학습 내역이 없습니다.</div>
    `;
    
    return messageDiv;
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

function convertChannelName(name) {
    const match = name.match(/^(\d{3})_(.+)$/);
    if(!match) return name; // 형식이 맞지 않으면 그대로 반환

    const num = parseInt(match[1], 10);
    if (num < 1 || num > 26) return name; // A~Z까지만
    const letter = String.fromCharCode(64 + num); // 1 → A, 2 → B ...

    return `${letter}_${match[2]}`;
}

function convertPageName(name) {
    const match = name.match(/^(\d{3})_(.+?)\.[^/.]+$/);
    if(!match) return name; // 형식이 맞지 않으면 그대로 반환

    return `${match[2]}`;
}