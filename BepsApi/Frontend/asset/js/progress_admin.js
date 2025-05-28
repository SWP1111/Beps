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

  setInterval(() => {
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

  }, 60*60*1000); // 1시간마다 업데이트


  const exportBtn = document.getElementById("export-button");
  exportBtn.addEventListener("click", () => {
    getStatisticsPreview();
  });

  const pushMessageButton = document.getElementById("push-message-button");
  pushMessageButton.addEventListener("click", async() => {
    const pointValue =document.getElementById("point-input").value;

    let title = "";  
    let message = `학습진도율 ${pointValue}% 미만 학습자에게 보내는 메시지입니다.`;
       
    const csrfToken = await getCookie();
    const url = `${window.baseUrl}leaning/push/send?filter_type=${filter_type}&filter_value=${filter_value}&title=${title}&message=${message}`;
    const response = await fetch(url,{
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-CSRF-Token": csrfToken,
      },
      body: JSON.stringify({
        filter_type,
        filter_value,
        title,
        message
      })
    });

    const data = await response.json();
    console.log(data);
  });

  async function getCookie() {
    const url = `${window.baseUrl}user/csrf_token`;
    const response =  await fetch(url)
    const data = await response.json();
    if(response.ok){
      return data.csrf_token;
    }
    else{
      return '';
    }
  }

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
    getCompletionRate();
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
    getCompletionRate();
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
      totalPoint.innerHTML = `총 포인트 : ${getPoint.total_points} P <br> 평균 포인트: ${Number(getPoint.average_points).toFixed(2)} P`;
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
    const categorArea = document.getElementById("category-chart");
    categorArea.innerHTML = ""; // Clear previous content

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
      echarts.dispose(categorArea); // 이전 인스턴스 제거 (optional but safe)
      const myChart = echarts.init(categorArea);
      const chartData = getCategory.progress.map((item, index) => {      
        const prefix = String.fromCharCode(65 + index); // A, B, C, ...
        const isSamll = item.percentage < 10;

        return {
          name: `${prefix}_${item.channel_name.replace(/^\d+_/, '')}`,
          value: item.percentage,
          time: item.duration,
          label: {
            show: item.percentage === 0? false : true,
            formatter: `${item.percentage}`,
            fontSize: 12,
            position: isSamll ? 'outside' : 'inside',
            fontFamily: 'Noto Sans KR',
            fontWeight: '700',
          },
          labelLine: {
            show: item.percentage > 0 && isSamll,
          }
        }       
      })

      const channelsOption = {
        color: [
          '#B7F362', '#FFA778', '#806FBC', '#170068', '#80CEC8', '#FFB0B0', '#FF6565',
          '#F3DE62', '#4D66E7', '#A59684', '#DA8EC7', '#BFABCC', '#FF4567', '#65ABCD', '#123456'
        ],
        legend: {
          orient: 'vertical',
          right: 13,
          top: 'top',
          textStyle: {
            fontWeight: '700',
            fontFamily: 'Noto Sans KR'
          },
          formatter: function (name) {
            return '  ' + name;
          }
        },
        series: [
          {
            name: 'Access From',
            type: 'pie',
            radius: '55%',
            center: ['33%', '45%'],
            data: chartData,
            emphasis: {
              itemStyle: {
                shadowBlur: 10,
                shadowOffsetX: 0,
                shadowColor: 'rgba(0, 0, 0, 0.5)'
              }
            }
          }
        ]
      };
      myChart.setOption(channelsOption);

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
    element.textContent = `의견서 순위`;
    memoRank.appendChild(element);

    let url = `${window.baseUrl}memo/memo_rank?period_value=${period_value}`;
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

  async function getCompletionRate() {
    let url = `${window.baseUrl}leaning/completion-rate?period_value=${period_value}`;
    if(period_type != null)
      url += `&period_type=${period_type}`;
    if(filter_type != null)
      url += `&filter_type=${filter_type}`;
    if(filter_value != null)
      url += `&filter_value=${encodeURIComponent(filter_value)}`;

    const response = await fetch(url);
    const data = await response.json();
    if(response.ok)
    {
      const completionRateElement = document.getElementById("completion-rate");
      completionRateElement.textContent = `학습 완료율: ${data.completion_rate}%`;
    }
  }

  let statisticsPopup = null;
  async function getStatisticsPreview() {
    let url = `progress_admin_statistics_preview.html?period_value=${period_value}`;
    if(period_type != null)
      url += `&period_type=${period_type}`;
    if(filter_type != null)
      url += `&filter_type=${filter_type}`;
    if(filter_value != null)
      url += `&filter_value=${encodeURIComponent(filter_value)}`;

    if(statisticsPopup == null || statisticsPopup.closed){
      const width = screen.availWidth;
      const height = screen.availHeight;

      statisticsPopup = window.open(url, `통계미리보기`,`width=${width},height=${height},resizable=yes,scrollbars=yes`);
    }
    else{
      statisticsPopup.location.href = url;
      statisticsPopup.focus();
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

  window.parent.postMessage({
    type: 'resize',
    height: document.documentElement.scrollHeight
  }, '*');

});





  
  