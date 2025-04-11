import { attachCustomScrollbar } from "./custom_vscroll.js";

export async function activeUser()
{
    const wrapper = document.querySelector(".listbox-container");
    const container = document.querySelector(".custom-listbox");
    const res = await fetch('custom_vscroll.html');
    const html = await res.text();
    wrapper.insertAdjacentHTML('beforeend', html);
    const scrollbar = wrapper.querySelector('.custom-scrollbar');
    const thumb = wrapper.querySelector('.custom-scrollbar-thumb');
    const {refresh} = attachCustomScrollbar(container, scrollbar, thumb);


    let currentUserMap = new Map();
    const allTotalDurationStr = await getTopUserConnectionDuration('day', '2025-04-09~2025-04-10');
    const allTotalDuration = parseDurationToSeconds(allTotalDurationStr);

    let websocketUrl = `${window.websocketUrl}`;
    const socket = new WebSocket(websocketUrl);
 
    socket.onopen = () => {};
    socket.onmessage = async(event) =>
    {
        const data = JSON.parse(event.data);
        if(data.type == "user_count")
        {
            const newUserIds = new Set(data.users.map(u => u.user_id));

            for (const [userId, element] of currentUserMap.entries()) {
                if (!newUserIds.has(userId)){
                    container.removeChild(element);
                    currentUserMap.delete(userId);
                }
            }

            for (const user of data.users) {
                if (!currentUserMap.has(user.user_id)) {
                    const info = await getUserInfo(user);
                    const userDurationStr = await getUserConnectionDuration('day', '2025-04-09~2025-04-10', 'user', user.user_id);
                    const userDuration = parseDurationToSeconds(userDurationStr);
                    
                    const userPercentage = ((userDuration / allTotalDuration) * 100).toFixed(2);

                    const item = document.createElement("div");
                    item.className = "listbox-item";

                    const name = document.createElement("span");
                    name.className = "user_text";
                    name.textContent = `${info.username}/${user.user_id}/${info.position}`;

                    const status = document.createElement("span");
                    if(userPercentage <= 20)
                        status.className = "yellow-RedBorder";
                    else
                        status.className = "yellow";

                    item.appendChild(name);
                    item.appendChild(status);
                    container.appendChild(item);

                    currentUserMap.set(user.user_id, item);
                }
            }

            refresh();
        }
    };
}


async function getUserInfo(user) {

    const apiURL = `${window.baseUrl}user/user_info?id=${user.user_id}`;
    const response = await fetch(apiURL);
    const userData = await response.json();

    if(response.ok) {
        return {
            username: userData.name,
            position: userData.position
        };
    }
}

async function getUserConnectionDuration(period_type=null, period_value, filter_type=null, filter_value=null) {
    let url = `${window.baseUrl}user/get_connection_duration?period_value=${period_value}`;

    if(period_type != null)
        url += `&period_type=${period_type}`;
    if(filter_type != null)
        url += `&filter_type=${filter_type}`;
    if(filter_value != null)
        url += `&filter_value=${filter_value}`;

    const response = await fetch(url);
    const getdurationInfo = await response.json();
    if(response.ok)
    {
        return getdurationInfo.total_duration;
    }
    return 0;
}

async function getTopUserConnectionDuration(period_type=null, period_value) {
    let url = `${window.baseUrl}user/get_top_user_duration?period_value=${period_value}`;
    if(period_type != null)
        url += `&period_type=${period_type}`;

    const response = await fetch(url);
    const getdurationInfo = await response.json();
    if(response.ok)
    {
        return getdurationInfo.duration;
    }
    return 0;
}

function parseDurationToSeconds(durationStr) {
    const [hms, fractioanl = '0'] = durationStr.split('.');
    const [hours, minutes, seconds] = hms.split(':').map(Number);
    const fractionalSeconds = parseFloat(`0.${fractioanl}`);
    return (hours * 3600) + (minutes * 60) + seconds + fractionalSeconds;
}