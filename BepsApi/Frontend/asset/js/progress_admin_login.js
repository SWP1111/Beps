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

    const total_duration = value.total_duration ?? "00:00:00";
    const worktime_duration_value = value.worktime_duration ?? "00:00:00";
    const offhour_duration_value = value.offhour_duration ?? "00:00:00";
    const internal_count_value = value.internal_count ?? 0;
    const external_count_value = value.external_count ?? 0;
    const total_login_count_value = internal_count_value + external_count_value;

    totalLoginTime.textContent = `총 접속 시간: ${total_duration} (${durationToHours(total_duration)} 시간)`;
    worktime_duration.textContent = `근무 시간 내: ${worktime_duration_value} (${durationToHours(worktime_duration_value)} 시간)`;
    offhour_duration.textContent = `근무 시간 외: ${offhour_duration_value} (${durationToHours(offhour_duration_value)} 시간)`;
    total_login_count.textContent = `총 접속 횟수: ${total_login_count_value}`;
    internal_count.textContent = `내부 접속 횟수: ${internal_count_value}`;
    external_count.textContent = `외부 접속 횟수: ${external_count_value}`;
}

function durationToHours(durationStar) {
    if (durationStar == undefined || durationStar == "00:00:00") return 0;

    const [hms, factional = '0' ] = durationStar.split('.');
    const [h, m, s] = hms.split(':').map(Number);
    const fractionalSeconds = parseFloat('0.'+factional);

    const totalHours = h + (m / 60) + ((s + fractionalSeconds) / 3600);
    return totalHours.toFixed(2);
}