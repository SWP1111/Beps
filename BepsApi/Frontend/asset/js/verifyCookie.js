async function checkLoginStatus() {
    try{
        const url = `${baseUrl}user/token_check`;
        const response = await fetch(url, {
            method: "GET",
            credentials: "include",
        })

        if(response.ok){
            const data = await response.json();
            console.log("checkLoginStatus: ", data);
            localStorage.setItem("username", data.user);    
            if(window.location.pathname.endsWith("main.html") == false)      
                window.location.href = "main.html";           
        }
        else
        {
            if(window.location.pathname.endsWith("login.html") == false)
                window.location.href = "login.html";
        }
        
    }catch(error){
        console.error(error);
        if(window.location.pathname.endsWith("login.html") == false)
            window.location.href = "login.html";
    }
}