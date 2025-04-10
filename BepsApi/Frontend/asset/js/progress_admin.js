import { setupUI } from "./progress_admin_search.js";
import { activeUser } from "./progress_admin_active_user.js";

document.addEventListener('DOMContentLoaded', async() => {

    const container = document.getElementById('container');
    setupUI(container);
    activeUser();
  });