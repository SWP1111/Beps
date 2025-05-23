window.onload = checkLoginStatus;    // Check login status when page is loaded

document.addEventListener("DOMContentLoaded", () => {

    const loggedInUser = localStorage.getItem("username");
    if(loggedInUser)
        document.getElementById("user_name").textContent = loggedInUser;
    else
        window.location.href = "login.html";

    const userInfo = JSON.parse(localStorage.getItem("loggedInUser"));
    const user_role = userInfo && userInfo.user ? userInfo.user.role_id : null;

    const buttons = document.querySelectorAll(".nav-button");
    const contentArea = document.getElementById("content-area");

    if(user_role == 5 || user_role == 6 || user_role == null) { // 일반사용자 또는 외부사용자
        document.getElementById("contents-button").style.display = "none"; // 학습 버튼 숨김
        document.getElementById("opinion-button").style.display = "none"; // 의견 버튼 숨김
        document.getElementById("manager-admin-button").style.display = "none";
    }

    if(user_role == 1 || user_role == 2 || user_role == 999) // 통합관리자 또는 개발관리자
        loadContent("progress_admin.html");
    else
        loadContent("progress.html");

    buttons.forEach(button => {
        button.addEventListener("click", () => {
            // 모든 버튼에서 'active' 클래스 제거
            buttons.forEach(btn => btn.classList.remove("active"));

            // 클릭한 버튼에 'active' 클래스 추가
            button.classList.add("active");
            
            if(button.id == "learning-button" && (user_role == 1 || user_role == 2))
                loadContent("progress_admin.html");
            else
                loadContent(button.dataset.content);
        });
    });

    const logoutButton = document.getElementById("logout-button");
    if(logoutButton)
    {
        logoutButton.addEventListener("click", logout);
    } 
    
    const managerAdminButton = document.getElementById("manager-admin-button");
    if(managerAdminButton) {
        managerAdminButton.addEventListener("click", openManagerAdmin);
    }
});

function openManagerAdmin() {
    // Remove active class from all nav buttons
    const navButtons = document.querySelectorAll(".nav-button");
    navButtons.forEach(btn => btn.classList.remove("active"));
    
    // Load manager admin page in the content frame
    loadContent("manager_admin.html");
}

async function logout(){
    try{
        
        // 로그아웃 요청
        const url = `${baseUrl}user/logout`;
        const response = await fetch(url, {
            method: "GET",
            credentials: "include",
            headers: {
                "Content-Type": "application/json",
            },
        });

        // localStorage 초기화
        localStorage.removeItem("username");
        localStorage.removeItem("loggedInUser");
        localStorage.removeItem("isLoggedIn");

        // 쿠키 삭제
        document.cookie.split(";").forEach(cookie => {
            document.cookie = 
            cookie.replace(/^ +/, "").replace(/=.*/, `=;expires=Thu, 01 Jun 1970 00:00:00 GMP; path=/`);
        });

        // 로그인 페이지로 이동
        window.location.href = "login.html";

    }catch(error){
        console.error(error);
    }
}


function loadContent(page) {
    if(page != undefined){
    
        fetch(page)
        .then(response => response.text())
        .then(data => {
            //document.getElementById("content-frame").src = page;
            const iframe = document.getElementById("content-frame");
            iframe.style.height = window.innerHeight + 'px';
            iframe.src = page;
            console.log("page: ", page);
        })
        .catch(error => {
            contentArea.innerHTML = "페이지를 불러오는 중 오류가 발생했습니다.";
            console.error(error);
        });
    }
    else
    {
        document.getElementById("content-frame").src = "about:blank";
    }
}
