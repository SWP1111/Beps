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


    let websocketUrl = `${window.websocketUrl}`;
    const socket = new WebSocket(websocketUrl);

    let currentUserMap = new Map();

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

                    const item = document.createElement("div");
                    item.className = "listbox-item";

                    const name = document.createElement("span");
                    name.className = "user_text";
                    name.textContent = `${info.username}/${user.user_id}/${info.position}`;

                    const status = document.createElement("span");
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