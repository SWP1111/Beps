import { setupUI } from "./progress_admin_search.js";
import { activeUser, getTopUserConnectionDuration, getTopDepartmentConnectionDuration, getTopCompanyConnectionDuration } from "./progress_admin_active_user.js";
import { initMap, lookupIP } from "./progress_admin_map.js";
import { initTrafficGaugeChart} from "./progress_admin_traffic.js";
import { initPeriod, setOnSelectPeriodCallback, setOnSelectFilterCallback } from "./progress_admin_period.js";
import { setLoginData, formatSecondsToHHMMSS } from "./progress_admin_login.js";

document.addEventListener('DOMContentLoaded', async() => {
  
  const yearStart = new Date().getFullYear();
  const today = new Date().toISOString().split('T')[0];
  
  let period_type = "year";
  let period_value = `${yearStart}`;
  let filter_type = "all";
  let filter_value = "all";

  //기간 설정 Init
  initPeriod();

  // 검색 영역 Init
  const container = document.getElementById('container');
  setupUI(container);

  // 동시 접속 영역 Init
  activeUser(period_type, period_value);

  // 지도 영역 Init
  initMap();
  document.getElementById("ipInput").addEventListener("keydown", (event) => {
    if(event.key === "Enter") {
      const ip = document.getElementById("ipInput").value.trim();
      if (!ip) return alert("IP 주소를 입력하세요.");
      lookupIP(ip);
    }     
  });
  document.getElementById("ipInput-icon").addEventListener("click", () => {
    const ip = document.getElementById("ipInput").value.trim();
    if (!ip) return alert("IP 주소를 입력하세요.");
    lookupIP(ip);
  });

  // 트래픽 게이지 차트 Init
  initTrafficGaugeChart(0);
  
  getTopUserConnectionDuration(period_type, period_value)
  .then(data => {
    displayUserTopBottom(data);
  });

  getTopDepartmentConnectionDuration(period_type, period_value)
  .then(data => {
    displayDipartmentTopBottom(data);
  });

  getTopCompanyConnectionDuration(period_type, period_value)
  .then(data => {
    displayCompanyTopBottom(data);
  });


  setOnSelectPeriodCallback(async() =>
  {
    period_type = sessionStorage.getItem("period_type");
    period_value = sessionStorage.getItem("period_value");

    activeUser(period_type, period_value);

    setLoginData(period_type, period_value, filter_type, filter_value);

    getTopUserConnectionDuration(period_type, period_value)
    .then(data => {
      displayUserTopBottom(data);
    });

    getTopDepartmentConnectionDuration(period_type, period_value)
    .then(data => {
      displayDipartmentTopBottom(data);
    });

    getTopCompanyConnectionDuration(period_type, period_value)
    .then(data => {
      displayCompanyTopBottom(data);
    });


    getTotalPoint();
    getRankPoint();
    getCategoryLearingRate();
    getTopViewdPages();
    getMemoRank();
  });

  setOnSelectFilterCallback(async({type, company, department, user}) =>
  {
    filter_type = type;
    filter_value = (type === "user") ? user.userId : (type === "department") ? `${company}||${department}` : company;
    setLoginData(period_type, period_value, filter_type, filter_value);

    getTotalPoint();
    getRankPoint();
    getCategoryLearingRate();
    getTopViewdPages();
    getMemoRank();
  });


  async function getTotalPoint()
  {
    const totalPoint = document.getElementById("total-point");
    let url = `${window.baseUrl}leaning/point?period_value=${period_value}`
    if(period_type != null)
      url += `&period_type=${period_type}`;
    if(filter_type != null)
      url += `&filter_type=${filter_type}`;
    if(filter_value != null)
      url += `&filter_value=${encodeURIComponent(filter_value)}`
    const response = await fetch(url);
    const getPoint = await response.json();
    if(response.ok)
    {
      totalPoint.textContent = `총 포인트 : ${getPoint.total_points} P`;
    }
  }

  async function getRankPoint()
  {
    const TopPoint = document.getElementById("top-point");
    const BottomPoint = document.getElementById("bottom-point");
    let url = `${window.baseUrl}leaning/point/rank?period_value=${period_value}`
    if(period_type != null)
      url += `&period_type=${period_type}`;
    if(filter_type != null)
      url += `&filter_type=all`; // filter_type은 all로 고정(department, company 사용 가능, user는 사용 불가)

    const response = await fetch(url);
    const getResult = await response.json();
    if(response.ok)
    {
      if(getResult.top != null && getResult.top.length > 0)
      {
        TopPoint.textContent = `최상위 포인트(전직원 기준) : ${getResult.top[0].total_points} P (${getResult.top[0].name}`;
        if(getResult.top.length > 1)
          TopPoint.textContent += `외 ${getResult.top.length - 1}명)`;
        else
          TopPoint.textContent += `)`;
      }

      if(getResult.bottom != null && getResult.bottom.length > 0)
      {
        BottomPoint.textContent = `전체 최하위 포인트(전직원 기준) : ${getResult.bottom[0].total_points} P (${getResult.bottom[0].name}`;
        if(getResult.bottom.length > 1)
          BottomPoint.textContent += `외 ${getResult.bottom.length - 1}명)`;
        else
          BottomPoint.textContent += `)`;
      }
    }
  }

  async function getCategoryLearingRate() {
    const categorArea = document.getElementById("category_area");
    categorArea.innerHTML = ""; // Clear previous content

    const element = document.createElement("span");
    element.className = "category-item";
    element.textContent = `카테고리 학습 현황`;
    categorArea.appendChild(element);

    let url = `${window.baseUrl}leaning/category_progress?period_value=${period_value}`;
    if(period_type != null)
      url += `&period_type=${period_type}`;
    if(filter_type != null)
      url += `&filter_type=${filter_type}`;
    if(filter_value != null)
      url += `&filter_value=${encodeURIComponent(filter_value)}`;

    const response = await fetch(url);
    const getCategory = await response.json();
    
    if(response.ok)
    {
      getCategory.progress.sort((a,b)=> {
        if (a.folder_name < b.folder_name) return -1;
        if (a.folder_name > b.folder_name) return 1;
        return 0;
      });

      for(let i = 0; i < getCategory.progress.length; i++)
      {
        const element = document.createElement("span");
        element.className = "category-item";
        element.textContent = `${getCategory.progress[i].folder_name.replace(/^\d+_/, '')} : ${getCategory.progress[i].percentage}% (${getCategory.progress[i].duration})`;
        categorArea.appendChild(element);
      }
    }
  }

  async function getTopViewdPages() {
    const topViewdPages = document.getElementById("top_viewed_pages");
    topViewdPages.innerHTML = ""; // Clear previous content

    const element = document.createElement("span");
    element.className = "category-item";
    element.textContent = `많이 본 페이지 순위`;
    topViewdPages.appendChild(element);

    let url= `${window.baseUrl}leaning/top_viewed_pages?period_value=${period_value}`;
    if(period_type != null)
      url += `&period_type=${period_type}`;
    if(filter_type != null)
      url += `&filter_type=${filter_type}`;
    if(filter_value != null)
      url += `&filter_value=${encodeURIComponent(filter_value)}`;

    const response = await fetch(url);
    const getTopViewdPages = await response.json();
    if(response.ok)
    {
      for(let i = 0; i < getTopViewdPages.top_viewd_pages.length; i++)
      {
        const element = document.createElement("span");
        element.className = "category-item";
        element.textContent = `${i+1}위: ${getTopViewdPages.top_viewd_pages[i].file_name.replace(/^\d+_/, '')} (${getTopViewdPages.top_viewd_pages[i].view_count}회)`;
        topViewdPages.appendChild(element);
      }
    }
  }

  async function getMemoRank() {
    const memoRank = document.getElementById("memo_rank");
    memoRank.innerHTML = ""; // Clear previous content

    const element = document.createElement("span");
    element.className = "category-item";
    element.textContent = `메모 랭킹`;
    memoRank.appendChild(element);

    let url = `${window.baseUrl}leaning/memo_rank?period_value=${period_value}`;
    if(period_type != null)
      url += `&period_type=${period_type}`;
    if(filter_type != null)
      url += `&filter_type=${filter_type}`;
    if(filter_value != null)
      url += `&filter_value=${encodeURIComponent(filter_value)}`;

    const response = await fetch(url);
    const getMemoRank = await response.json();
    if(response.ok)
    {
      const data = getMemoRank.data;

      for(let i = 0; i < data.length; i++)
      {
        const element = document.createElement("span");
        element.className = "category-item";
        const path = data[i].path.split("/").pop().replace(/^\d+_/, '').replace(/\.[^.]+$/, ''); // 마지막 파일명 추출. 숫자 제거. 확장자 제거거
        element.textContent = `${i+1}위: ${path} (${data[i].cnt}회)`;
        memoRank.appendChild(element);
      }
    }
  }

  async function displayUserTopBottom(data)
  {
    const userRankTopFirst = document.getElementById("user-rank-top-first");
    const userRankTopSecond = document.getElementById("user-rank-top-second");
    const userRankTopThird = document.getElementById("user-rank-top-third");
    const userRankBottonFirst = document.getElementById("user-rank-bottom-first");
    const userRankBottonSecond = document.getElementById("user-rank-bottom-second");
    const userRankBottonThird = document.getElementById("user-rank-bottom-third");
    
    userRankTopFirst.textContent = `개인 상위 Top3 : ${data.data.top[0][1]} (${formatSecondsToHHMMSS(data.data.top[0][2])})`;
    userRankTopSecond.textContent = `, ${data.data.top[1][1]} (${formatSecondsToHHMMSS(data.data.top[1][2])})`;
    userRankTopThird.textContent = `, ${data.data.top[2][1]} (${formatSecondsToHHMMSS(data.data.top[2][2])})`;

    userRankBottonFirst.textContent = `개인 하위 Top3 : ${data.data.bottom[0][1]} (${formatSecondsToHHMMSS(data.data.bottom[0][2])})`;
    userRankBottonSecond.textContent = `, ${data.data.bottom[1][1]} (${formatSecondsToHHMMSS(data.data.bottom[1][2])})`;
    userRankBottonThird.textContent = `, ${data.data.bottom[2][1]} (${formatSecondsToHHMMSS(data.data.bottom[2][2])})`;
  }

  async function displayDipartmentTopBottom(data)
  {
    const departmentRankTopFirst = document.getElementById("team-rank-top-first");
    const departmentRankTopSecond = document.getElementById("team-rank-top-second");
    const departmentRankTopThird = document.getElementById("team-rank-top-third");

    const departmentRankBottonFirst = document.getElementById("team-rank-bottom-first");
    const departmentRankBottonSecond = document.getElementById("team-rank-bottom-second");
    const departmentRankBottonThird = document.getElementById("team-rank-bottom-third");

    departmentRankTopFirst.textContent = `부서 상위 Top3 : ${data.data.top[0][1]} (${formatSecondsToHHMMSS(data.data.top[0][2])})`;
    departmentRankTopSecond.textContent = `, ${data.data.top[1][1]} (${formatSecondsToHHMMSS(data.data.top[1][2])})`;
    departmentRankTopThird.textContent = `, ${data.data.top[2][1]} (${formatSecondsToHHMMSS(data.data.top[2][2])})`;

    departmentRankBottonFirst.textContent = `부서 하위 Top3 : ${data.data.bottom[0][1]} (${formatSecondsToHHMMSS(data.data.bottom[0][2])})`;
    departmentRankBottonSecond.textContent = `, ${data.data.bottom[1][1]} (${formatSecondsToHHMMSS(data.data.bottom[1][2])})`;
    departmentRankBottonThird.textContent = `, ${data.data.bottom[2][1]} (${formatSecondsToHHMMSS(data.data.bottom[2][2])})`;
  }

  async function displayCompanyTopBottom(data)
  {
    const companyRankTopFirst = document.getElementById("company-rank-top-first");
    const companyRankTopSecond = document.getElementById("company-rank-top-second");
    const companyRankTopThird = document.getElementById("company-rank-top-third");

    const companyRankBottonFirst = document.getElementById("company-rank-bottom-first");
    const companyRankBottonSecond = document.getElementById("company-rank-bottom-second");
    const companyRankBottonThird = document.getElementById("company-rank-bottom-third");

    companyRankTopFirst.textContent = `회사 상위 Top3 : ${data.data.top[0][0]} (${formatSecondsToHHMMSS(data.data.top[0][1])})`;
    companyRankTopSecond.textContent = `, ${data.data.top[1][0]} (${formatSecondsToHHMMSS(data.data.top[1][1])})`;
    if(data.data.top.length > 2)
      companyRankTopThird.textContent = `, ${data.data.top[2][0]} (${formatSecondsToHHMMSS(data.data.top[2][1])})`;

    companyRankBottonFirst.textContent = `회사 하위 Top3 : ${data.data.bottom[0][0]} (${formatSecondsToHHMMSS(data.data.bottom[0][1])})`;
    companyRankBottonSecond.textContent = `, ${data.data.bottom[1][0]} (${formatSecondsToHHMMSS(data.data.bottom[1][1])})`;
    if(data.data.top.length > 2)
      companyRankBottonThird.textContent = `, ${data.data.bottom[2][0]} (${formatSecondsToHHMMSS(data.data.bottom[2][1])})`;
  }

});





  
  