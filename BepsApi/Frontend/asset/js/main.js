window.onload = checkLoginStatus;    // Check login status when page is loaded

document.addEventListener("DOMContentLoaded", () => {

    const loggedInUser = localStorage.getItem("username");
    if(loggedInUser)
        document.getElementById("user_name").textContent = loggedInUser;
    else
        window.location.href = "login.html";

    const userInfo = JSON.parse(localStorage.getItem("loggedInUser"));
    const isAdmin = userInfo.user.role_id == 1;// || userInfo.user.role_id == null;

    const buttons = document.querySelectorAll(".nav-button");
    const contentArea = document.getElementById("content-area");
   
    if(isAdmin)
        loadContent("progress_admin.html");
    else
        loadContent("progress.html");

    buttons.forEach(button => {
        button.addEventListener("click", () => {
            // 모든 버튼에서 'active' 클래스 제거
            buttons.forEach(btn => btn.classList.remove("active"));

            // 클릭한 버튼에 'active' 클래스 추가
            button.classList.add("active");

            if(button.id == "learning-button" && isAdmin)
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
});


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
            document.getElementById("content-frame").src = page;
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
