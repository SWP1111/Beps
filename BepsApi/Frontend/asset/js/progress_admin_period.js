import { setOnSelectCallback, SELECTION_TYPE } from "./progress_admin_search.js";

let onSelectPeriodCallback = null;
let onSelectFilterCallback = null;

export function setOnSelectPeriodCallback(callback) {
    onSelectPeriodCallback = callback;
}

export function setOnSelectFilterCallback(callback) {
    onSelectFilterCallback = callback;
}

export function initPeriod()
{
    const currentYear = new Date().getFullYear();
    const yearStart = `${new Date().getFullYear()}-01-01`;
    let today = new Date().toISOString().split('T')[0];

    let period_type = "day";
    let period_value = `${yearStart}~${today}`;
    const selectedPeriod = document.getElementById("selected-period");

    //적용
    const applyBtn = document.getElementById("apply-button");
    applyBtn.addEventListener("click", (e) => {
        
        sessionStorage.setItem("period_type", period_type);
        sessionStorage.setItem("period_value", period_value);
        
        onSelectPeriodCallback();
    });

    // 기간 선택_날짜 지정
    const statpicker = flatpickr('#start-date', {
        dateFormat: "Y-m-d",
        locale: "ko",
        onChange: function(selectedDates, dateStr, instance) {
            dropdownBtn.classList.remove("active");
            btnYear.classList.remove("active");
            dropdownBtnQuarter.classList.remove("active");
            
            endpicker.set('minDate', dateStr);
            period_type = "day";
            period_value = `${dateStr}~${endpicker.input.value}`;
        }
    });
    const endpicker = flatpickr('#end-date',{
        dateFormat: "Y-m-d",
        locale: "ko", 
        onChange: function(selectedDates, dateStr, instance) {
            dropdownBtn.classList.remove("active");
            btnYear.classList.remove("active");
            dropdownBtnQuarter.classList.remove("active");

            statpicker.set('maxDate', dateStr);
            period_type = "day";
            period_value = `${statpicker.input.value}~${dateStr}`;
        }
    });

    // 기간 선택 드롭다운 동작_연간
    const dropdownBtnYear = document.getElementById("year");
    const dropdownMenuYear = document.getElementById("year-list");
    const dropdownLabelYear = document.getElementById("year-label");
    const btnYear = document.getElementById("year-button");

    for (let year = 2025; year <= currentYear; year++) {
        const div = document.createElement("div");
        const dropdownItem = document.createElement("button");
        dropdownItem.className = "dropdown-item";
        dropdownItem.textContent = `${year}`;
        div.appendChild(dropdownItem);
        dropdownMenuYear.appendChild(div);
    }
    
    dropdownLabelYear.textContent = `${currentYear}년도`;
    btnYear.classList.add("active");
    period_type = "year";
    period_value = dropdownLabelYear.textContent.replace("년도", "").trim();
    selectedPeriod.textContent = `전체 (${period_value}년)`;
    statpicker.setDate(`${period_value}-01-01`);
    endpicker.setDate(`${period_value}-12-31`);

    sessionStorage.setItem("period_type", period_type);
    sessionStorage.setItem("period_value", period_value);

    btnYear.addEventListener("click", (e) => {
        btnYear.classList.add("active");

        period_type = "year";
        period_value = dropdownLabelYear.textContent.replace("년도","").trim();

        statpicker.set('maxDate', null);
        endpicker.set('minDate', null);

        statpicker.setDate(`${period_value}-01-01`);
        endpicker.setDate(`${period_value}-12-31`);

        dropdownBtn.classList.remove("active");
        dropdownLabel.textContent = "반기";
        dropdownBtnQuarter.classList.remove("active");
        dropdownLabelQuarter.textContent = "분기";
    });

    dropdownBtnYear.addEventListener("click", (e) => {
        dropdownMenuYear.classList.toggle("show");
    });

    dropdownMenuYear.addEventListener("click", (e) => {   
        if(e.target.classList.contains("dropdown-item")) {
        dropdownLabelYear.textContent = `${e.target.textContent}년도`;
        dropdownMenuYear.classList.remove("show");
        } 
    });

    // 기간 선택 드롭다운 동작_반기
    const dropdownBtn = document.getElementById("half-year");
    const dropdownMenu = document.getElementById("half-year-list");
    const dropdownLabel = document.getElementById("half-year-label");

    dropdownBtn.addEventListener("click", (e) => {
        dropdownMenu.classList.toggle("show");
    });

    dropdownMenu.addEventListener("click", (e) => {
        if(e.target.classList.contains("dropdown-item")) {
            dropdownLabel.textContent = e.target.textContent;
            dropdownMenu.classList.remove("show");
            dropdownBtn.classList.add("active");

            const selectedYear = dropdownLabelYear.textContent.replace("년도","").trim();

            period_type = "half";
            period_value = selectedYear;

            statpicker.set('maxDate', null);
            endpicker.set('minDate', null);

            if(dropdownLabel.textContent === "상반기")
            {
                period_value += '-H1';
                
                statpicker.setDate(`${selectedYear}-01-01`);
                endpicker.setDate(`${selectedYear}-06-30`);
            }
            else if(dropdownLabel.textContent === "하반기")
            {
                period_value += '-H2';

                statpicker.setDate(`${selectedYear}-07-01`);
                endpicker.setDate(`${selectedYear}-12-31`);
            }

            dropdownBtnQuarter.classList.remove("active");
            dropdownLabelQuarter.textContent = "분기";
            btnYear.classList.remove("active");
        }
    });

    // 기간 선택 드롭다운 동작_분기
    const dropdownBtnQuarter = document.getElementById("quarter");
    const dropdownMenuQuarter = document.getElementById("quarter-list");
    const dropdownLabelQuarter = document.getElementById("quarter-label");

    dropdownBtnQuarter.addEventListener("click", (e) => {
        dropdownMenuQuarter.classList.toggle("show");
    });

    dropdownMenuQuarter.addEventListener("click", (e) => {
        if(e.target.classList.contains("dropdown-item")) {
            dropdownLabelQuarter.textContent = e.target.textContent;
            dropdownMenuQuarter.classList.remove("show");
            dropdownBtnQuarter.classList.add("active");

            const selectedYear = dropdownLabelYear.textContent.replace("년도","").trim();

            period_type = "quarter";
            period_value = selectedYear;

            statpicker.set('maxDate', null);
            endpicker.set('minDate', null);

            if(dropdownLabelQuarter.textContent === "1분기") {
                period_value += '-Q1';
                statpicker.setDate(`${selectedYear}-01-01`);
                endpicker.setDate(`${selectedYear}-03-31`);
            }
            else if(dropdownLabelQuarter.textContent === "2분기") {
                period_value += '-Q2';
                statpicker.setDate(`${selectedYear}-04-01`);
                endpicker.setDate(`${selectedYear}-06-30`);
            }
            else if(dropdownLabelQuarter.textContent === "3분기") {
                period_value += '-Q3';
                statpicker.setDate(`${selectedYear}-07-01`);
                endpicker.setDate(`${selectedYear}-09-30`);
            }
            else if(dropdownLabelQuarter.textContent === "4분기") {
                period_value += '-Q4';
                statpicker.setDate(`${selectedYear}-10-01`);
                endpicker.setDate(`${selectedYear}-12-31`);
            }

            dropdownBtn.classList.remove("active");
            dropdownLabel.textContent = "반기";
            btnYear.classList.remove("active");
        }
    });

    // 클릭 이벤트
    document.addEventListener("click", (event) => {
        if(!dropdownBtn.contains(event.target) && !dropdownMenu.contains(event.target)) {
            dropdownMenu.classList.remove("show");
        }
        if(!dropdownBtnQuarter.contains(event.target) && !dropdownMenuQuarter.contains(event.target)) {
            dropdownMenuQuarter.classList.remove("show");
        }
        if(!dropdownBtnYear.contains(event.target) && !dropdownMenuYear.contains(event.target)) {
            dropdownMenuYear.classList.remove("show");
        }
    });
        
    // 키보드 입력 이벤트
    document.addEventListener("keydown", (event) => {
        if(event.key === "Escape") {
            dropdownMenu.classList.remove("show");
            dropdownMenuQuarter.classList.remove("show");
            dropdownMenuYear.classList.remove("show");
        }
    });


    setOnSelectCallback(({type, company, department, user}) => {
        switch(type){
            case SELECTION_TYPE.ALL:
                selectedPeriod.textContent = `전체 (${period_value}년)`;
                break;
            case SELECTION_TYPE.COMPANY:
                selectedPeriod.textContent = `${company} (${currentYear}년)`;
                break;
            case SELECTION_TYPE.DEPARTMENT:
                selectedPeriod.textContent = `${department} (${currentYear}년)`;
                break;
            case SELECTION_TYPE.USER:
                selectedPeriod.textContent = `${user.userName} ${user.position} (${currentYear}년)`;
                break;
            default:
                break;
        }

        onSelectFilterCallback({
            type: type.toLowerCase(),
            company: company,
            department: department,
            user: user
        });
  });

}

