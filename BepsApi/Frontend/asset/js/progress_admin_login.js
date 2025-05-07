import { getUserConnectionDuration } from "./progress_admin_active_user.js";

export async function setLoginData(period_type, period_value, filter_type, filter_value)
{
    const totalLoginTime = document.getElementById("total-login-time");
    const worktime_duration = document.getElementById("worktime-duration");
    const offhour_duration = document.getElementById("offhour-duration");
    const total_login_count = document.getElementById("total-login-count");
    const internal_count = document.getElementById("internal-count");
    const external_count = document.getElementById("external-count");

    const value = await getUserConnectionDuration(period_type, period_value, filter_type, filter_value);

    const total_duration = value.total_duration ?? "0";
    const worktime_duration_value = value.worktime_duration ?? "0";
    const offhour_duration_value = value.offhour_duration ?? "0";
    const internal_count_value = value.internal_count ?? 0;
    const external_count_value = value.external_count ?? 0;
    const total_login_count_value = internal_count_value + external_count_value;

    totalLoginTime.textContent = `총 접속 시간: ${formatSecondsToHHMMSS(total_duration)} (${formatSecondsToHoursFloat(total_duration)})`;
    worktime_duration.textContent = `근무 시간 내: ${formatSecondsToHHMMSS(worktime_duration_value)} (${formatSecondsToHoursFloat(worktime_duration_value)})`;
    offhour_duration.textContent = `근무 시간 외: ${formatSecondsToHHMMSS(offhour_duration_value)} (${formatSecondsToHoursFloat(offhour_duration_value)})`;
    total_login_count.textContent = `총 접속 횟수: ${total_login_count_value}`;
    internal_count.textContent = `내부 접속 횟수: ${internal_count_value}`;
    external_count.textContent = `외부 접속 횟수: ${external_count_value}`;
}

export function formatSecondsToHHMMSS(seconds) {
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    const secondsRemainder = Math.floor(seconds % 60);

    return `${String(hours).padStart(2, '0')}:${String(minutes).padStart(2, '0')}:${String(secondsRemainder).padStart(2, '0')}`;
}

function formatSecondsToHoursFloat(seconds) {
    const hours = Math.floor(seconds / 3600);
    return `${hours.toFixed(1)} 시간`;
}