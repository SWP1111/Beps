import { setupUI } from "./progress_admin_search.js";
import { activeUser } from "./progress_admin_active_user.js";
import { initMap, lookupIP } from "./progress_admin_map.js";

document.addEventListener('DOMContentLoaded', async() => {

    const container = document.getElementById('container');
    setupUI(container);

    let period_type = "day";
    let period_value = "2025-01-01~2025-04-10";
    activeUser(period_type, period_value);

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

  });



  
  