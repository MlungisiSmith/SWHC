const $ = (selector) => document.querySelector(selector);
const $$ = (selector) => document.querySelectorAll(selector);

const statusLabels = { healthy: "Nominal", warning: "Review", critical: "Action needed", unknown: "Awaiting data" };
const statusWords = { healthy: "All clear", warning: "Review needed", critical: "Needs attention", unknown: "Awaiting telemetry" };
const componentIcons = { cpu: "◈", memory: "▤", fans: "◌", power: "ϟ", thermal: "⌁" };

let selectedComponent = "cpu";
let visibleComponents = {};
let chassisOpen = false;
let currentDeviceModel = null;

// Real switch chassis representations
const chassisModels = {
  auto: { 
    name: "NETWORK SWITCH", 
    spec: "24-PORT PLATFORM",
    width: 400,
    height: 300,
    ports: 24
  },
  cisco: { 
    name: "C9200L", 
    spec: "24 × 1G · 4 × 10GE SFP",
    width: 480,
    height: 320,
    ports: 24,
    illustration: "cisco-c9200l"
  },
  huawei: { 
    name: "S5735L-24P4X-A1", 
    spec: "24 × GE · 4 × 10GE",
    width: 480,
    height: 320,
    ports: 24,
    illustration: "huawei-s5735l"
  }
};

// Component positions inside chassis (normalized 0-100)
const componentPositions = {
  cpu: { x: 10, y: 20, w: 25, h: 20, color: "#FF6B6B" },
  memory: { x: 40, y: 20, w: 20, h: 20, color: "#4ECDC4" },
  fans: { x: 70, y: 20, w: 25, h: 20, color: "#95E1D3" },
  power: { x: 10, y: 55, w: 35, h: 25, color: "#FFE66D" },
  thermal: { x: 50, y: 60, w: 40, h: 20, color: "#A8E6CF" }
};

function waitingComponent(key) {
  const labels = { cpu: "Processor", memory: "Memory", fans: "Cooling fans", power: "Power supply", thermal: "Thermal sensors" };
  return { key, label: labels[key], status: "unknown", value: "Waiting", detail: "Connect to a switch to read this component." };
}

function formatTime(iso) {
  if (!iso) return "No completed health check";
  return new Intl.DateTimeFormat([], { hour: "2-digit", minute: "2-digit", second: "2-digit" }).format(new Date(iso));
}

function showConnectMessage(message = "") {
  const element = $("#connect-error");
  element.hidden = !message;
  element.textContent = message;
}

async function readDashboardJson(response) {
  const body = await response.text();
  try {
    return JSON.parse(body);
  } catch {
    throw new Error("The dashboard service needs a restart. Stop it, then run switch_health_dashboard.py again.");
  }
}

function setScreen(connected) {
  $("#connect-screen").hidden = connected;
  $("#dashboard").hidden = !connected;
}

function setChassis(open) {
  chassisOpen = open;
  const toggle = $("#chassis-toggle");
  const interior = $("#switch-interior");
  
  toggle.setAttribute("aria-expanded", String(open));
  interior.style.display = open ? "block" : "none";
  
  $("#model-caption").textContent = open
    ? "Inside the chassis: click components to inspect their live status."
    : "Click the chassis to open and inspect components.";
}

// Draw interactive chassis interior
function drawChassisInterior(vendorKey) {
  const canvas = $("#chassis-canvas");
  if (!canvas) return;
  
  const ctx = canvas.getContext("2d");
  const width = canvas.width;
  const height = canvas.height;
  
  // Clear canvas
  ctx.fillStyle = "#1a2332";
  ctx.fillRect(0, 0, width, height);
  
  // Draw circuit board pattern
  ctx.strokeStyle = "#2a4466";
  ctx.lineWidth = 0.5;
  for (let i = 0; i < width; i += 20) {
    ctx.beginPath();
    ctx.moveTo(i, 0);
    ctx.lineTo(i, height);
    ctx.stroke();
  }
  for (let i = 0; i < height; i += 20) {
    ctx.beginPath();
    ctx.moveTo(0, i);
    ctx.lineTo(width, i);
    ctx.stroke();
  }
  
  // Draw components
  Object.entries(componentPositions).forEach(([key, pos]) => {
    const component = visibleComponents[key] || waitingComponent(key);
    const x = (pos.x / 100) * width;
    const y = (pos.y / 100) * height;
    const w = (pos.w / 100) * width;
    const h = (pos.h / 100) * height;
    
    // Component background
    ctx.fillStyle = pos.color;
    ctx.globalAlpha = component.status === "healthy" ? 0.8 : component.status === "warning" ? 0.6 : 0.4;
    ctx.fillRect(x, y, w, h);
    ctx.globalAlpha = 1;
    
    // Component border
    ctx.strokeStyle = "#fff";
    ctx.lineWidth = 2;
    ctx.strokeRect(x, y, w, h);
    
    // Component label
    ctx.fillStyle = "#fff";
    ctx.font = "bold 12px monospace";
    ctx.textAlign = "center";
    ctx.fillText(component.label, x + w / 2, y + h / 2 - 5);
    ctx.font = "10px monospace";
    ctx.fillText(component.status.toUpperCase(), x + w / 2, y + h / 2 + 8);
  });
}

function renderRail(history) {
  const rail = $("#health-rail");
  rail.replaceChildren();
  const recent = history.slice(-12);
  const blanks = Math.max(0, 12 - recent.length);
  for (let index = 0; index < blanks; index += 1) {
    rail.append(Object.assign(document.createElement("span"), { className: "rail-node", ariaLabel: "No check recorded" }));
  }
  recent.forEach((check, index) => {
    const node = document.createElement("span");
    node.className = `rail-node ${check.overall}${index === recent.length - 1 ? " latest" : ""}`;
    node.setAttribute("aria-label", `${statusLabels[check.overall]} check at ${formatTime(check.timestamp)}`);
    rail.append(node);
  });
}

function renderNodes() {
  $$(".component-node").forEach((node) => {
    const key = node.dataset.component;
    const component = visibleComponents[key] || waitingComponent(key);
    node.classList.remove("healthy", "warning", "critical", "unknown");
    node.classList.add(component.status);
    node.setAttribute("aria-pressed", String(key === selectedComponent));
    node.setAttribute("aria-label", `${component.label}: ${component.value}. Select for details.`);
    node.disabled = !chassisOpen;
  });
}

function renderSelectedDetail(lastCheck) {
  const component = visibleComponents[selectedComponent] || waitingComponent(selectedComponent);
  $("#detail-icon").textContent = componentIcons[selectedComponent];
  $("#detail-label").textContent = component.label;
  if (!chassisOpen) {
    $("#detail-value").textContent = "Closed";
    const badge = $("#detail-status");
    badge.className = "detail-status unknown";
    badge.textContent = "Open chassis";
    $("#detail-copy").textContent = "Click the switch chassis to reveal its interior components.";
    $("#last-checked").textContent = lastCheck ? `Last checked ${formatTime(lastCheck)}` : "No completed health check";
    return;
  }
  $("#detail-value").textContent = component.value;
  const badge = $("#detail-status");
  badge.className = `detail-status ${component.status}`;
  badge.textContent = statusLabels[component.status];
  $("#detail-copy").textContent = component.detail;
  $("#last-checked").textContent = lastCheck ? `Last checked ${formatTime(lastCheck)}` : "No completed health check";
}

function render(payload) {
  setScreen(payload.connected);
  if (!payload.connected) return;

  const device = payload.device || { hostname: "Connecting…", vendor: "Detecting vendor", vendor_key: "auto" };
  const latest = payload.latest;
  visibleComponents = Object.fromEntries(
    ["cpu", "memory", "fans", "power", "thermal"].map((key) => [
      key,
      latest?.components?.[key] || waitingComponent(key),
    ])
  );
  currentDeviceModel = device.vendor_key;
  
  $("#device-name").textContent = device.hostname;
  $("#vendor-name").textContent = device.vendor;
  $("#vendor-lockup").dataset.vendor = device.vendor_key;
  $("#vendor-lockup").setAttribute("aria-label", `${device.vendor} switch`);
  $("#switch-model").dataset.vendor = device.vendor_key;
  
  const stencil = chassisModels[device.vendor_key] || chassisModels.auto;
  $("#chassis-model-name").textContent = stencil.name;
  $("#chassis-model-spec").textContent = stencil.spec;

  const status = latest?.overall || "unknown";
  $("#health-word").textContent = statusWords[status];
  $("#health-word").style.color = status === "healthy" ? "var(--green)" : status === "warning" ? "var(--amber)" : status === "critical" ? "var(--red)" : "var(--muted)";
  
  const pollState = $("#poll-state");
  pollState.textContent = payload.checking ? "Checking switch" : latest?.error ? "Check incomplete" : "Monitor active";
  pollState.className = `poll-state ${latest?.error ? "alert" : payload.checking ? "" : "online"}`;
  
  $("#check-button").disabled = payload.checking;
  $("#check-button").textContent = payload.checking ? "Checking…" : "Run check";
  $("#check-cadence").textContent = `Polling cadence: ${payload.interval_seconds}s`;
  
  setChassis(chassisOpen);
  renderNodes();
  renderSelectedDetail(payload.last_check);
  renderRail(payload.history || []);
  
  // Draw chassis interior if open
  if (chassisOpen) {
    drawChassisInterior(device.vendor_key);
  }

  const alert = $("#dashboard-alert");
  alert.hidden = !latest?.error;
  alert.textContent = latest?.error || "";
}

async function refresh() {
  try {
    const response = await fetch("/api/status", { cache: "no-store" });
    if (!response.ok) throw new Error("The local dashboard is unavailable.");
    render(await readDashboardJson(response));
  } catch (error) {
    showConnectMessage(error.message);
  }
}

$("#connect-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  showConnectMessage();
  const button = $("#connect-button");
  button.disabled = true;
  button.textContent = "Connecting…";
  try {
    const response = await fetch("/api/connect", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ address: $("#switch-address").value.trim(), vendor: $("#vendor-preference").value }),
    });
    const result = await readDashboardJson(response);
    if (!response.ok) throw new Error(result.message || "Unable to start the switch connection.");
    $("#switch-address").value = "";
    setChassis(false);
    await refresh();
  } catch (error) {
    showConnectMessage(error.message);
  } finally {
    button.disabled = false;
    button.innerHTML = "Connect to switch <span aria-hidden=\"true\">→</span>";
  }
});

$("#check-button").addEventListener("click", async () => {
  await fetch("/api/check", { method: "POST" });
  refresh();
});

$("#disconnect-button").addEventListener("click", async () => {
  await fetch("/api/disconnect", { method: "POST" });
  setScreen(false);
  setChassis(false);
  showConnectMessage();
  $("#switch-address").focus();
});

// Component nodes - clickable to select
$$(".component-node").forEach((node) => {
  node.addEventListener("click", () => {
    selectedComponent = node.dataset.component;
    setChassis(true);
    renderNodes();
    renderSelectedDetail(null);
  });
});

// Canvas click to open chassis
const chassisToggle = $("#chassis-toggle");
if (chassisToggle) {
  chassisToggle.addEventListener("click", () => {
    setChassis(!chassisOpen);
    if (chassisOpen) {
      drawChassisInterior(currentDeviceModel);
    }
    renderNodes();
    renderSelectedDetail(null);
  });
}

// Component detail click handler for interactive inspection
$$(".detail-title").forEach(title => {
  title.addEventListener("click", () => {
    // Could open a modal with more detailed component info
    console.log(`Inspecting component: ${selectedComponent}`);
  });
});

refresh();
window.setInterval(refresh, 2500);
