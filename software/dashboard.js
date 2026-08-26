const $ = (id) => document.getElementById(id);
let selectedHours = 24;

function fmtTemp(value) {
  return value == null ? "—" : `${Number(value).toFixed(1)} °C`;
}
function fmtPercent(value) {
  return value == null ? "—" : `${Number(value).toFixed(0)}%`;
}
function fmtAge(seconds) {
  if (seconds == null) return "unknown";
  if (seconds < 60) return `${Math.round(seconds)} seconds ago`;
  if (seconds < 3600) return `${Math.round(seconds / 60)} minutes ago`;
  return `${(seconds / 3600).toFixed(1)} hours ago`;
}
function fmtDuration(seconds) {
  if (seconds == null) return "—";
  const days = Math.floor(seconds / 86400);
  const hours = Math.floor((seconds % 86400) / 3600);
  const mins = Math.floor((seconds % 3600) / 60);
  return days ? `${days}d ${hours}h ${mins}m` : `${hours}h ${mins}m`;
}
function statusClass(data) {
  if (!data.available || data.dashboard_status_stale) return "neutral";
  if (data.system_status === "HEALTHY") return "healthy";
  if (data.system_status === "ALARM") return "alarm";
  return "warning";
}
async function loadStatus() {
  try {
    const response = await fetch("/api/status", {cache: "no-store"});
    const data = await response.json();
    const cls = statusClass(data);
    const badge = $("connectionBadge");
    badge.className = `badge ${cls}`;
    badge.textContent = data.dashboard_status_stale ? "Monitor data stale" : "Live";
    const banner = $("statusBanner");
    banner.className = `status-banner ${cls}`;
    $("statusTitle").textContent = data.dashboard_status_stale
      ? "Monitor is not updating"
      : (data.status_message || data.system_status || "Unknown status");
    $("updatedText").textContent = `Updated ${fmtAge(data.dashboard_status_age_seconds)}`;
    $("returnWet").textContent = data.return_wet == null ? "—" : (data.return_wet ? "Detected" : "Not detected");

    const levelElement = $("reservoirLevel");
    levelElement.classList.remove("level-low", "level-ok");
    if (!data.low_level_sensor_enabled) {
      levelElement.textContent = "Disabled";
    } else if (data.reservoir_level_ok == null) {
      levelElement.textContent = "—";
    } else if (data.reservoir_level_ok) {
      levelElement.textContent = "Normal";
      levelElement.classList.add("level-ok");
    } else {
      levelElement.textContent = "LOW";
      levelElement.classList.add("level-low");
    }

    $("waterTemp").textContent = fmtTemp(data.reservoir_temp_c ?? data.water_temp_c);
    $("growPipeTemp").textContent = fmtTemp(data.grow_pipe_temp_c);
    $("growPipeDelta").textContent = fmtTemp(data.grow_pipe_minus_reservoir_c);
    const growProbe = $("growPipeProbe");
    growProbe.classList.remove("level-low", "level-ok");
    if (!data.grow_pipe_enabled) {
      growProbe.textContent = "Disabled";
    } else if (!data.grow_pipe_sensor_id) {
      growProbe.textContent = "Needs assignment";
      growProbe.classList.add("level-low");
    } else if (data.grow_pipe_temperature_sensor_fault) {
      growProbe.textContent = "No valid reading";
      growProbe.classList.add("level-low");
    } else if (data.grow_pipe_temp_c == null) {
      growProbe.textContent = "Checking";
    } else {
      growProbe.textContent = "Reporting";
      growProbe.classList.add("level-ok");
    }
    $("ambientTemp").textContent = fmtTemp(data.ambient_temp_c);
    $("humidity").textContent = fmtPercent(data.ambient_rh_percent);
    $("override").textContent = data.override_active ? "Inhibited" : "Normal";
    const alarmLabels = {
      "LOW_WATER": "Low reservoir water",
      "FLOW_LOSS": "Return flow lost",
      "TEMP_CRITICAL": "Temperature critical",
      "TEMP_SENSOR_FAULT": "Temperature sensor fault",
      "TEMP_WARNING": "Temperature warning"
    };
    $("activeAlarm").textContent = data.active_alarm
      ? (alarmLabels[data.active_alarm] || data.active_alarm)
      : "None";

    const notification = data.notifications || {};
    const notificationElement = $("phoneNotifications");
    notificationElement.classList.remove("level-low", "level-ok");
    if (!notification.enabled) {
      notificationElement.textContent = "Disabled";
    } else if (!notification.configured) {
      notificationElement.textContent = "Needs setup";
      notificationElement.classList.add("level-low");
    } else if (notification.last_error) {
      notificationElement.textContent = "Last send failed";
      notificationElement.classList.add("level-low");
      notificationElement.title = notification.last_error;
    } else {
      notificationElement.textContent = notification.worker_running ? "Ready" : "Starting";
      notificationElement.classList.add("level-ok");
      notificationElement.title = notification.last_success_at
        ? `Last sent ${notification.last_success_at}`
        : "Configured; no messages sent this session";
    }
    $("uptime").textContent = fmtDuration(data.monitor_uptime_seconds);
    $("cpuTemp").textContent = fmtTemp(data.pi_cpu_temp_c);
  } catch (error) {
    $("connectionBadge").className = "badge neutral";
    $("connectionBadge").textContent = "Dashboard error";
    $("statusBanner").className = "status-banner neutral";
    $("statusTitle").textContent = "Unable to read monitor";
    $("updatedText").textContent = String(error);
  }
}

function escapeHtml(value) {
  return String(value ?? "").replace(/[&<>"']/g, (char) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#039;"
  })[char]);
}

function pathFor(rows, key, x, y) {
  let path = "";
  let drawing = false;
  rows.forEach((row, index) => {
    const value = row[key];
    if (value == null) {
      drawing = false;
      return;
    }
    const command = drawing ? "L" : "M";
    path += `${command}${x(index).toFixed(2)},${y(Number(value)).toFixed(2)} `;
    drawing = true;
  });
  return path.trim();
}

function renderChart(element, rows, series, options = {}) {
  const width = Math.max(element.clientWidth || 800, 320);
  const height = 310;
  const margin = {left: 54, right: 18, top: 14, bottom: 36};
  const values = [];
  rows.forEach(row => series.forEach(item => {
    if (row[item.key] != null) values.push(Number(row[item.key]));
  }));
  if (!rows.length || !values.length) {
    element.innerHTML = `<svg viewBox="0 0 ${width} ${height}"><text class="empty" x="${width/2}" y="${height/2}">No readings in this period</text></svg>`;
    return;
  }
  let min = options.min != null ? options.min : Math.min(...values);
  let max = options.max != null ? options.max : Math.max(...values);
  if (max === min) { max += 1; min -= 1; }
  const padding = options.fixed ? 0 : Math.max((max - min) * 0.1, 0.5);
  min -= padding; max += padding;
  const plotW = width - margin.left - margin.right;
  const plotH = height - margin.top - margin.bottom;
  const x = index => margin.left + (rows.length === 1 ? plotW/2 : index * plotW/(rows.length-1));
  const y = value => margin.top + (max - value) * plotH/(max-min);
  const ticks = 5;
  let svg = `<svg viewBox="0 0 ${width} ${height}" preserveAspectRatio="none">`;
  for (let i = 0; i <= ticks; i++) {
    const yy = margin.top + i * plotH/ticks;
    const value = max - i * (max-min)/ticks;
    svg += `<line class="grid" x1="${margin.left}" y1="${yy}" x2="${width-margin.right}" y2="${yy}"/>`;
    svg += `<text class="axis-label" x="${margin.left-8}" y="${yy+4}" text-anchor="end">${value.toFixed(options.decimals ?? 1)}${options.suffix ?? ""}</text>`;
  }
  const dateIndices = [0, Math.floor((rows.length-1)/2), rows.length-1];
  [...new Set(dateIndices)].forEach(index => {
    const date = new Date(rows[index].timestamp);
    const label = date.toLocaleString([], {
      month: "short", day: "numeric",
      hour: selectedHours <= 48 ? "numeric" : undefined,
      minute: selectedHours <= 48 ? "2-digit" : undefined
    });
    svg += `<text class="axis-label" x="${x(index)}" y="${height-10}" text-anchor="${index === 0 ? "start" : index === rows.length-1 ? "end" : "middle"}">${escapeHtml(label)}</text>`;
  });
  series.forEach(item => {
    svg += `<path class="${item.className}" d="${pathFor(rows, item.key, x, y)}"/>`;
  });
  svg += "</svg>";
  element.innerHTML = svg;
}

async function loadHistory(hours = selectedHours) {
  selectedHours = hours;
  document.querySelectorAll("[data-hours]").forEach(button => {
    button.classList.toggle("active", Number(button.dataset.hours) === hours);
  });
  try {
    const response = await fetch(`/api/history?hours=${encodeURIComponent(hours)}&max_points=1200`, {cache: "no-store"});
    const data = await response.json();
    renderChart($("tempChart"), data.rows, [
      {key: "reservoir_temp_c", className: "line-water"},
      {key: "grow_pipe_temp_c", className: "line-grow-pipe"},
      {key: "ambient_temp_c", className: "line-ambient"}
    ], {decimals: 1, suffix: "°"});
    renderChart($("humidityChart"), data.rows, [
      {key: "ambient_rh_percent", className: "line-humidity"}
    ], {min: 0, max: 100, fixed: true, decimals: 0, suffix: "%"});
    $("historyNote").textContent = data.sampled
      ? `Showing ${data.returned_points.toLocaleString()} evenly sampled points from ${data.matching_points.toLocaleString()} readings.`
      : `${data.matching_points.toLocaleString()} readings in this period.`;
  } catch (error) {
    $("tempChart").textContent = `Unable to load history: ${error}`;
    $("humidityChart").textContent = "";
  }
}

async function loadEvents() {
  const query = $("eventQuery").value;
  const level = $("eventLevel").value;
  const params = new URLSearchParams({q: query, level, limit: "500"});
  try {
    const response = await fetch(`/api/events?${params}`, {cache: "no-store"});
    const data = await response.json();
    $("eventRows").innerHTML = data.events.length ? data.events.map(event => `
      <tr>
        <td>${escapeHtml(event.timestamp)}</td>
        <td class="level-${escapeHtml(event.level)}">${escapeHtml(event.level)}</td>
        <td>${escapeHtml(event.message)}</td>
      </tr>`).join("") : '<tr><td colspan="3">No matching events.</td></tr>';
  } catch (error) {
    $("eventRows").innerHTML = `<tr><td colspan="3">${escapeHtml(error)}</td></tr>`;
  }
}

document.querySelectorAll("[data-hours]").forEach(button => {
  button.addEventListener("click", () => loadHistory(Number(button.dataset.hours)));
});
$("eventSearch").addEventListener("submit", event => {
  event.preventDefault();
  loadEvents();
});
window.addEventListener("resize", () => loadHistory(selectedHours));

loadStatus();
loadHistory(24);
loadEvents();
setInterval(loadStatus, 5000);
setInterval(() => loadHistory(selectedHours), 60000);


function formatBytesGb(value) {
  return value == null ? "—" : `${Number(value).toFixed(2)} GB`;
}

function setProgress(id, percent) {
  const element = $(id);
  const safe = percent == null ? 0 : Math.max(0, Math.min(100, Number(percent)));
  element.style.width = `${safe}%`;
  element.classList.remove("warning", "alarm");
  if (safe >= 90) element.classList.add("alarm");
  else if (safe >= 75) element.classList.add("warning");
}

function setWifiProgress(id, percent) {
  const element = $(id);
  const safe = percent == null ? 0 : Math.max(0, Math.min(100, Number(percent)));
  element.style.width = `${safe}%`;
  element.classList.remove("warning", "alarm");
  if (safe < 30) element.classList.add("alarm");
  else if (safe < 55) element.classList.add("warning");
}

async function loadSystemInfo() {
  try {
    const response = await fetch("/api/system", {cache: "no-store"});
    const data = await response.json();

    $("sysPiModel").textContent = data.pi_model || "Unknown";
    $("sysHostname").textContent = data.hostname || "—";
    $("sysIp").textContent = (data.ipv4_addresses || []).join(", ") || "—";

    const wifiName = data.wifi?.ssid || data.wifi?.interface || "Not reported";
    const wifiQuality = data.wifi?.quality_percent;
    $("sysWifi").textContent = wifiQuality == null
      ? wifiName
      : `${wifiName} · ${Number(wifiQuality).toFixed(0)}%`;

    $("sysCpuUse").textContent = data.cpu_percent == null
      ? "—"
      : `${Number(data.cpu_percent).toFixed(1)}%`;
    $("sysCpuTemp").textContent = fmtTemp(data.cpu_temperature_c);

    const memory = data.memory || {};
    $("sysMemory").textContent = memory.used_percent == null
      ? "—"
      : `${Number(memory.used_percent).toFixed(1)}%`;
    $("sysMemoryDetail").textContent =
      memory.used_mb == null || memory.total_mb == null
        ? "—"
        : `${Number(memory.used_mb).toFixed(0)} MB of ${Number(memory.total_mb).toFixed(0)} MB`;
    setProgress("sysMemoryBar", memory.used_percent);

    const disk = data.disk || {};
    $("sysDisk").textContent = disk.used_percent == null
      ? "—"
      : `${Number(disk.used_percent).toFixed(1)}%`;
    $("sysDiskDetail").textContent =
      disk.used_gb == null || disk.total_gb == null
        ? "—"
        : `${formatBytesGb(disk.used_gb)} of ${formatBytesGb(disk.total_gb)} used · ${formatBytesGb(disk.free_gb)} free`;
    setProgress("sysDiskBar", disk.used_percent);

    $("sysUptime").textContent = fmtDuration(data.uptime_seconds);
    $("sysBoot").textContent = data.boot_time
      ? new Date(data.boot_time).toLocaleString()
      : "—";
    $("sysOs").textContent = data.os?.pretty_name || data.os?.name || "—";
    $("sysVersion").textContent = `Dashboard ${data.dashboard_version || "—"}`;

    $("sysRtcStatus").textContent = data.rtc?.available
      ? (data.rtc.driver_name || "Available")
      : "Not detected";
    $("sysRtcTime").textContent = data.rtc?.hardware_time_utc || "—";

    $("sysArch").textContent = data.architecture || "—";
    $("sysKernel").textContent = data.kernel || "—";
    $("sysPython").textContent = data.python_version || "—";
    $("sysLoad").textContent = Array.isArray(data.load_average)
      ? data.load_average.map(value => Number(value).toFixed(2)).join(" / ")
      : "—";

    $("sysWifiDetail").textContent = [
      data.wifi?.signal_dbm == null ? null : `${Number(data.wifi.signal_dbm).toFixed(0)} dBm`,
      data.wifi?.quality_percent == null ? null : `${Number(data.wifi.quality_percent).toFixed(0)}% estimated quality`
    ].filter(Boolean).join(" · ") || "—";
    setWifiProgress("sysWifiBar", data.wifi?.quality_percent);

    $("systemUpdated").textContent = data.generated_at
      ? `Updated ${new Date(data.generated_at).toLocaleTimeString()}`
      : "Updated";
  } catch (error) {
    $("systemUpdated").textContent = `Unable to load system information: ${error}`;
  }
}

document.querySelectorAll(".tab-button").forEach(button => {
  button.addEventListener("click", () => {
    document.querySelectorAll(".tab-button").forEach(item => item.classList.remove("active"));
    document.querySelectorAll(".tab-panel").forEach(panel => panel.classList.remove("active"));
    button.classList.add("active");
    $(button.dataset.tab).classList.add("active");
    if (button.dataset.tab === "systemTab") loadSystemInfo();
  });
});

loadSystemInfo();
setInterval(loadSystemInfo, 30000);


function humaniseKey(key) {
  const special = {
    "GPIO": "GPIO",
    "DS18B20": "DS18B20",
    "DHT22": "DHT22",
    "CSV": "CSV"
  };
  return String(key)
    .replace(/_/g, " ")
    .replace(/\b\w/g, letter => letter.toUpperCase())
    .replace(/\bGpio\b/g, special.GPIO)
    .replace(/\bDs18b20\b/g, special.DS18B20)
    .replace(/\bDht22\b/g, special.DHT22)
    .replace(/\bCsv\b/g, special.CSV);
}

function formatConfigurationValue(key, value) {
  if (value == null) return "—";
  if (typeof value === "boolean") return value ? "Yes" : "No";
  if (String(key).endsWith("_c")) return `${value} °C`;
  if (String(key).endsWith("_seconds")) return `${value} s`;
  if (String(key).includes("interval_seconds")) return `${value} s`;
  if (String(key).toLowerCase().includes("gpio")) return `GPIO ${value}`;
  if (typeof value === "object") return JSON.stringify(value);
  return String(value);
}

function renderDefinitionList(id, values) {
  const element = $(id);
  element.innerHTML = Object.entries(values || {}).map(([key, value]) => `
    <div>
      <dt>${escapeHtml(humaniseKey(key))}</dt>
      <dd>${escapeHtml(formatConfigurationValue(key, value))}</dd>
    </div>
  `).join("") || "<div><dt>No data</dt><dd>—</dd></div>";
}

async function loadConfiguration() {
  try {
    const response = await fetch("/api/configuration", {cache: "no-store"});
    const data = await response.json();

    renderDefinitionList("alarmConfig", data.alarm_thresholds);
    renderDefinitionList("loggingConfig", data.sampling_and_logging);
    renderDefinitionList("dashboardConfig", data.dashboard);
    renderDefinitionList("notificationConfig", data.notifications);
    renderDefinitionList("lowLevelConfig", data.low_level_sensor);
    renderDefinitionList("rtcConfig", data.rtc);
    renderDefinitionList("gpioConfig", data.gpio);
    renderDefinitionList("pathConfig", data.paths);
    renderDefinitionList("softwareConfig", data.software);

    $("configurationUpdated").textContent =
      `Loaded ${new Date().toLocaleTimeString()}`;
  } catch (error) {
    $("configurationUpdated").textContent =
      `Unable to load configuration: ${error}`;
  }
}

document.querySelectorAll(".tab-button").forEach(button => {
  button.addEventListener("click", () => {
    if (button.dataset.tab === "configurationTab") {
      loadConfiguration();
    }
  });
});

loadConfiguration();
