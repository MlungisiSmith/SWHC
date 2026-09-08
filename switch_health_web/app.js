let metricHistory = { cpu: [], memory: [], tx: [], rx: [] };
let charts = {};
let currentConnectedSwitch = null;
let topologyData = { devices: [], links: [] };
let deviceLogs = [];
let configTemplates = [];
let selectedTemplate = null;
let templateParams = {};

const METRICS = [
    { id: 'cpu', name: 'CPU Usage', unit: '%', icon: '⚙️' },
    { id: 'memory', name: 'Memory', unit: '%', icon: '🧠' },
    { id: 'fans', name: 'Fan Status', unit: 'RPM', icon: '💨' },
    { id: 'power', name: 'Power', unit: 'W', icon: '⚡' },
    { id: 'thermal', name: 'Temperature', unit: '°C', icon: '🌡️' }
];

// Elements
const loginWrapper = document.getElementById('loginWrapper');
const dashboard = document.getElementById('dashboard');
const connectForm = document.getElementById('connectForm');
const disconnectBtn = document.getElementById('disconnectBtn');
const deviceName = document.getElementById('deviceName');
const deviceVendor = document.getElementById('deviceVendor');
const healthStatus = document.getElementById('healthStatus');
const metricsGrid = document.getElementById('metricsGrid');
const errorDisplay = document.getElementById('connect-error');

// Tab elements
const tabButtons = document.querySelectorAll('.tab-button');
const tabContents = document.querySelectorAll('.tab-content');

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    connectForm.addEventListener('submit', handleConnect);
    disconnectBtn.addEventListener('click', handleDisconnect);
    
    tabButtons.forEach(btn => {
        btn.addEventListener('click', () => switchTab(btn.dataset.tab));
    });

    // Log filter buttons
    document.querySelectorAll('.filter-btn').forEach(btn => {
        btn.addEventListener('click', (e) => {
            document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
            e.target.classList.add('active');
            filterLogs(e.target.dataset.filter);
        });
    });

    // Create metric cards
    METRICS.forEach(metric => {
        const card = document.createElement('div');
        card.style.cssText = 'background: rgba(30, 30, 30, 0.6); border: 2px solid rgba(200, 90, 82, 0.2); border-radius: 12px; padding: 24px; position: relative; overflow: hidden;';
        card.innerHTML = `
            <div style="font-size: 0.9rem; color: #a0a0a0; margin-bottom: 8px; display: flex; justify-content: space-between; align-items: center;">
                <span>${metric.icon} ${metric.name}</span>
                <span style="font-size: 0.75rem;">NORMAL</span>
            </div>
            <div id="value-${metric.id}" style="font-size: 2.5rem; font-weight: 800; color: #c85a52; margin-bottom: 12px;">--</div>
            <div style="height: 6px; background: rgba(200, 90, 82, 0.1); border-radius: 3px; overflow: hidden; margin-bottom: 8px;">
                <div id="fill-${metric.id}" style="height: 100%; background: linear-gradient(90deg, #c85a52, #a84738); width: 0%; transition: width 0.5s ease;"></div>
            </div>
            <div id="detail-${metric.id}" style="font-size: 0.85rem; color: #959d9f;">Waiting for data...</div>
        `;
        metricsGrid.appendChild(card);
    });

    initCharts();
    startPolling();
});

function handleConnect(e) {
    e.preventDefault();
    const ip = document.getElementById('switchIP').value;
    const vendor = document.getElementById('vendorType').value;

    fetch('/api/connect', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ address: ip, vendor })
    })
    .then(r => r.json())
    .then(data => {
        if (data.started) {
            currentConnectedSwitch = ip;
            deviceLogs = [];
            addLog('info', `Connected to switch ${ip}`);
            loginWrapper.classList.add('hidden');
            dashboard.classList.remove('hidden');
            setTimeout(() => {
                refreshData();
                discoverTopology();
                loadConfigTemplates();
            }, 1000);
        } else {
            showError(data.message || 'Connection failed');
            addLog('error', `Connection failed: ${data.message}`);
        }
    })
    .catch(e => {
        showError(e.message);
        addLog('error', `Connection error: ${e.message}`);
    });
}

function handleDisconnect() {
    fetch('/api/disconnect', { method: 'POST' })
        .then(() => {
            currentConnectedSwitch = null;
            addLog('info', 'Disconnected from switch');
            loginWrapper.classList.remove('hidden');
            dashboard.classList.add('hidden');
            document.getElementById('switchIP').value = '';
        });
}

function showError(msg) {
    errorDisplay.textContent = msg;
    errorDisplay.style.display = msg ? 'block' : 'none';
}

function switchTab(tabName) {
    tabButtons.forEach(btn => btn.classList.remove('active'));
    tabContents.forEach(content => content.classList.remove('active'));
    
    document.querySelector(`[data-tab="${tabName}"]`).classList.add('active');
    document.getElementById(tabName).classList.add('active');

    if (tabName === 'topology' && currentConnectedSwitch) {
        renderTopology();
    }
    
    if (tabName === 'config') {
        renderConfigUI();
    }
}

function loadConfigTemplates() {
    fetch('/api/config/templates')
        .then(r => r.json())
        .then(data => {
            configTemplates = data.templates || [];
            addLog('info', `Loaded ${configTemplates.length} configuration templates`);
        })
        .catch(e => addLog('error', `Failed to load templates: ${e.message}`));
}

function renderConfigUI() {
    const configTab = document.getElementById('config');
    if (!configTab) return;
    
    let html = `
        <div style="padding: 20px;">
            <!-- Configuration Selector -->
            <div class="config-controls">
                <div class="config-selector">
                    <label style="color: #c85a52; font-weight: 700; display: block; margin-bottom: 15px; font-size: 1rem;">📋 Choose Configuration Action</label>
                    <div style="display: flex; flex-direction: column; gap: 10px;">
    `;
    
    if (configTemplates.length === 0) {
        html += '<p style="color: #959d9f;">No templates available</p>';
    } else {
        configTemplates.forEach(template => {
            html += `
                <div style="padding: 12px; background: rgba(200, 90, 82, 0.1); border: 2px solid rgba(200, 90, 82, 0.2); border-radius: 8px; cursor: pointer; transition: all 0.3s;" class="template-option" data-template="${template.name}">
                    <div style="font-weight: 700; color: #c85a52; margin-bottom: 4px;">${template.label}</div>
                    <div style="font-size: 0.85rem; color: #a0a0a0; margin-bottom: 4px;">${template.description}</div>
                    <div style="font-size: 0.8rem; color: #959d9f;">📍 Purpose: ${template.purpose}</div>
                </div>
            `;
        });
    }
    
    html += `
                    </div>
                </div>
                
                <!-- Parameters Section -->
                <div id="paramsSection" style="display: none;">
                    <div style="margin-bottom: 20px;">
                        <div style="font-weight: 700; color: #c85a52; margin-bottom: 15px; font-size: 1rem;">⚙️ Configuration Parameters</div>
                        <div id="parametersContainer" style="display: flex; flex-direction: column; gap: 12px;"></div>
                    </div>
                    
                    <!-- Action Buttons -->
                    <div style="display: flex; gap: 10px; margin-bottom: 20px;">
                        <button id="backBtn" class="btn-config btn-preview" style="flex: 1;">⬅️ Back</button>
                        <button id="previewBtn" class="btn-config btn-preview" style="flex: 1;">👁️ Preview</button>
                        <button id="applyBtn" class="btn-config btn-apply" style="flex: 1;">✅ Apply</button>
                    </div>
                </div>
            </div>
            
            <!-- Output Section -->
            <div id="configOutput" class="config-output" style="display: none;"></div>
        </div>
    `;
    
    configTab.innerHTML = html;
    
    // Add event listeners
    document.querySelectorAll('.template-option').forEach(el => {
        el.addEventListener('click', () => selectTemplate(el.dataset.template));
        el.addEventListener('mouseover', () => el.style.background = 'rgba(200, 90, 82, 0.2)');
        el.addEventListener('mouseout', () => el.style.background = 'rgba(200, 90, 82, 0.1)');
    });
    
    document.getElementById('backBtn')?.addEventListener('click', resetConfig);
    document.getElementById('previewBtn')?.addEventListener('click', previewConfig);
    document.getElementById('applyBtn')?.addEventListener('click', applyConfig);
}

function selectTemplate(templateName) {
    selectedTemplate = templateName;
    const template = configTemplates.find(t => t.name === templateName);
    
    if (!template) return;
    
    // Hide template options, show parameters
    document.querySelector('.config-selector').style.display = 'none';
    document.getElementById('paramsSection').style.display = 'block';
    
    // Render parameters
    renderTemplateParameters(template);
}

function renderTemplateParameters(template) {
    const container = document.getElementById('parametersContainer');
    container.innerHTML = '';
    
    // Add template title
    const title = document.createElement('div');
    title.style.cssText = 'padding: 15px; background: rgba(200, 90, 82, 0.1); border: 2px solid rgba(200, 90, 82, 0.2); border-radius: 8px; margin-bottom: 15px;';
    title.innerHTML = `
        <div style="font-weight: 700; color: #c85a52; margin-bottom: 4px;">Selected: ${template.label}</div>
        <div style="font-size: 0.85rem; color: #a0a0a0;">${template.description}</div>
    `;
    container.appendChild(title);
    
    // Render parameters based on template
    const params = {
        'base_vlan': [
            { name: 'vlan_id', label: 'VLAN ID', type: 'number', default: '10', min: 1, max: 4094 },
            { name: 'vlan_name', label: 'VLAN Name', type: 'text', default: 'VLAN10' },
            { name: 'vlan_description', label: 'Description', type: 'text', default: 'Production VLAN' }
        ],
        'port_config': [
            { name: 'interface', label: 'Interface Name', type: 'text', default: 'GigabitEthernet0/0/1' },
            { name: 'description', label: 'Port Description', type: 'text', default: 'Access Port' },
            { name: 'mode', label: 'Port Mode', type: 'select', options: ['access', 'trunk'], default: 'access' },
            { name: 'vlan_id', label: 'VLAN ID', type: 'number', default: '10', min: 1, max: 4094 }
        ],
        'stp_config': [
            { name: 'vlan_id', label: 'VLAN ID', type: 'number', default: '1', min: 1, max: 4094 },
            { name: 'priority', label: 'Bridge Priority', type: 'select', options: ['0', '4096', '8192', '12288', '16384', '20480', '24576', '28672'], default: '24576' }
        ],
        'snmp_config': [
            { name: 'community_string', label: 'Community String', type: 'text', default: 'public' },
            { name: 'trap_source', label: 'Trap Source IP', type: 'text', default: '0.0.0.0' }
        ],
        'acl_config': [
            { name: 'acl_name', label: 'ACL Name', type: 'text', default: 'ALLOW_SUBNET' },
            { name: 'source_ip', label: 'Source IP', type: 'text', default: '10.0.0.0' },
            { name: 'wildcard', label: 'Wildcard Mask', type: 'text', default: '0.0.0.255' }
        ]
    };
    
    const templateParams = params[selectedTemplate] || [];
    templateParams.forEach(param => {
        const paramDiv = document.createElement('div');
        paramDiv.style.cssText = 'padding: 12px; background: rgba(30,30,30,0.6); border: 2px solid rgba(200,90,82,0.1); border-radius: 6px;';
        
        let inputHTML = '';
        if (param.type === 'select') {
            inputHTML = `<select id="param-${param.name}" style="width: 100%; padding: 8px; background: rgba(30,30,30,0.8); border: 2px solid rgba(200,90,82,0.2); color: #fff; border-radius: 4px; font-size: 0.9rem;">`;
            param.options.forEach(opt => {
                inputHTML += `<option value="${opt}" ${opt === param.default ? 'selected' : ''}>${opt}</option>`;
            });
            inputHTML += '</select>';
        } else if (param.type === 'number') {
            inputHTML = `<input type="number" id="param-${param.name}" value="${param.default}" min="${param.min}" max="${param.max}" style="width: 100%; padding: 8px; background: rgba(30,30,30,0.8); border: 2px solid rgba(200,90,82,0.2); color: #fff; border-radius: 4px; font-size: 0.9rem;">`;
        } else {
            inputHTML = `<input type="text" id="param-${param.name}" value="${param.default}" placeholder="${param.default}" style="width: 100%; padding: 8px; background: rgba(30,30,30,0.8); border: 2px solid rgba(200,90,82,0.2); color: #fff; border-radius: 4px; font-size: 0.9rem;">`;
        }
        
        paramDiv.innerHTML = `
            <label style="display: block; margin-bottom: 8px; color: #c85a52; font-weight: 600; font-size: 0.9rem;">${param.label}</label>
            ${inputHTML}
        `;
        container.appendChild(paramDiv);
    });
}

function resetConfig() {
    selectedTemplate = null;
    document.querySelector('.config-selector').style.display = 'block';
    document.getElementById('paramsSection').style.display = 'none';
    document.getElementById('configOutput').style.display = 'none';
}

function previewConfig() {
    if (!selectedTemplate) return;
    
    // Collect parameters
    const params = {};
    document.querySelectorAll('[id^="param-"]').forEach(input => {
        const key = input.id.replace('param-', '');
        params[key] = input.value;
    });
    
    fetch('/api/config/preview', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ template: selectedTemplate, parameters: params })
    })
    .then(r => r.json())
    .then(data => {
        if (data.error) {
            showConfigOutput('error', data.error);
        } else {
            showConfigOutput('preview', `<strong>Configuration Preview:</strong><br><br><pre style="color: #90EE90; background: rgba(0,0,0,0.5); padding: 10px; border-radius: 4px; overflow-x: auto;">${escapeHtml(data.config)}</pre>`);
        }
    })
    .catch(e => showConfigOutput('error', 'Preview failed: ' + e.message));
}

function applyConfig() {
    if (!selectedTemplate) return;
    
    if (!confirm('⚠️ Are you sure you want to apply this configuration to the switch?\n\nThis will make changes to your network switch.')) return;
    
    // Collect parameters
    const params = {};
    document.querySelectorAll('[id^="param-"]').forEach(input => {
        const key = input.id.replace('param-', '');
        params[key] = input.value;
    });
    
    fetch('/api/config/apply', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ template: selectedTemplate, parameters: params })
    })
    .then(r => r.json())
    .then(data => {
        if (data.success) {
            showConfigOutput('success', `<span style="color: #00ff00;">✅ Configuration applied successfully!</span><br><br><pre style="color: #90EE90; background: rgba(0,0,0,0.5); padding: 10px; border-radius: 4px; overflow-x: auto; font-size: 0.75rem;">${escapeHtml(data.output)}</pre>`);
            addLog('info', `Configuration "${selectedTemplate}" applied successfully`);
        } else {
            showConfigOutput('error', data.error || 'Configuration failed');
            addLog('error', `Configuration failed: ${data.error}`);
        }
    })
    .catch(e => {
        showConfigOutput('error', 'Apply failed: ' + e.message);
        addLog('error', 'Configuration apply error: ' + e.message);
    });
}

function showConfigOutput(type, message) {
    const output = document.getElementById('configOutput');
    output.style.display = 'block';
    if (type === 'error') {
        output.innerHTML = `<span style="color: #ff6b6b;">❌ ${message}</span>`;
    } else if (type === 'success') {
        output.innerHTML = message;
    } else {
        output.innerHTML = message;
    }
}

function escapeHtml(text) {
    const map = {
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        '"': '&quot;',
        "'": '&#039;'
    };
    return text.replace(/[&<>"']/g, m => map[m]);
}

function discoverTopology() {
    if (!currentConnectedSwitch) return;

    fetch('/api/topology', { cache: 'no-store' })
        .then(r => r.json())
        .then(data => {
            topologyData = data;
            if (data.devices && data.devices.length > 0) {
                addLog('info', `Discovered ${data.devices.length} devices and ${data.links?.length || 0} links`);
                renderTopology();
            } else {
                addLog('warning', 'No devices discovered in topology');
            }
        })
        .catch(e => {
            addLog('error', `Topology discovery failed: ${e.message}`);
        });
}

function getVendorIcon(vendor, type) {
    if (type === 'core') return '🖥️';
    if (!vendor) return '📱';
    
    const v = vendor.toLowerCase();
    if (v.includes('cisco')) return '🖥️';
    if (v.includes('huawei')) return '⚙️';
    if (v.includes('windows')) return '💻';
    if (v.includes('linux')) return '🐧';
    if (v.includes('printer')) return '🖨️';
    if (v.includes('camera')) return '📷';
    if (v.includes('ap') || v.includes('access point')) return '📡';
    if (v.includes('server')) return '🗄️';
    if (v.includes('workstation')) return '🖱️';
    return '📱';
}

function renderTopology() {
    const svg = document.getElementById('topoSVG');
    if (!svg) return;

    svg.innerHTML = '';
    
    if (!topologyData.devices || topologyData.devices.length === 0) {
        svg.innerHTML = '<text x="50%" y="50%" text-anchor="middle" fill="#a0a0a0">No topology data available</text>';
        return;
    }

    const width = svg.clientWidth;
    const height = svg.clientHeight;
    const nodeRadius = 50;
    const padding = 80;

    const coreDevices = topologyData.devices.filter(d => d.type === 'core');
    const accessDevices = topologyData.devices.filter(d => d.type === 'access');

    const positions = {};
    let y = padding;

    // Core devices - top center
    coreDevices.forEach((dev, i) => {
        const x = width / 2 + (i - (coreDevices.length - 1) / 2) * 200;
        positions[dev.hostname] = { x, y };
    });

    y += 250;

    // Access devices - distributed below
    accessDevices.forEach((dev, i) => {
        const x = padding + (i % Math.ceil(accessDevices.length / 2)) * (width - 2 * padding) / Math.max(Math.ceil(accessDevices.length / 2), 1);
        if (i > 0 && i % Math.ceil(accessDevices.length / 2) === 0) y += 200;
        positions[dev.hostname] = { x, y };
    });

    // Draw links with bandwidth info
    (topologyData.links || []).forEach(link => {
        const from = positions[link.from];
        const to = positions[link.to];
        if (from && to) {
            // Link line
            const line = document.createElementNS('http://www.w3.org/2000/svg', 'line');
            line.setAttribute('x1', from.x);
            line.setAttribute('y1', from.y);
            line.setAttribute('x2', to.x);
            line.setAttribute('y2', to.y);
            line.setAttribute('class', `topo-link ${link.status === 'up' ? 'up' : 'down'}`);
            line.setAttribute('stroke-width', link.utilization ? Math.max(2, link.utilization / 20) : 2);
            svg.appendChild(line);

            // Bandwidth label
            const midX = (from.x + to.x) / 2;
            const midY = (from.y + to.y) / 2;
            const label = document.createElementNS('http://www.w3.org/2000/svg', 'text');
            label.setAttribute('x', midX);
            label.setAttribute('y', midY - 15);
            label.setAttribute('class', 'topo-label');
            label.setAttribute('text-anchor', 'middle');
            label.setAttribute('fill', '#c85a52');
            label.setAttribute('font-weight', 'bold');
            label.textContent = link.bandwidth || 'Link';
            svg.appendChild(label);

            // Utilization label
            if (link.utilization) {
                const util = document.createElementNS('http://www.w3.org/2000/svg', 'text');
                util.setAttribute('x', midX);
                util.setAttribute('y', midY + 5);
                util.setAttribute('class', 'topo-label');
                util.setAttribute('text-anchor', 'middle');
                util.setAttribute('font-size', '10');
                util.textContent = `${link.utilization}% util`;
                svg.appendChild(util);
            }
        }
    });

    // Draw devices
    topologyData.devices.forEach(dev => {
        const pos = positions[dev.hostname];
        if (!pos) return;

        const group = document.createElementNS('http://www.w3.org/2000/svg', 'g');
        group.setAttribute('class', 'topo-node');

        // Device circle
        const circle = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
        circle.setAttribute('cx', pos.x);
        circle.setAttribute('cy', pos.y);
        circle.setAttribute('r', nodeRadius);
        circle.setAttribute('fill', dev.type === 'core' ? 'rgba(200, 90, 82, 0.2)' : 'rgba(200, 90, 82, 0.1)');
        circle.setAttribute('stroke', dev.status === 'up' ? '#00ff00' : '#ff0000');
        circle.setAttribute('stroke-width', '3');
        group.appendChild(circle);

        // Icon
        const iconText = document.createElementNS('http://www.w3.org/2000/svg', 'text');
        iconText.setAttribute('x', pos.x);
        iconText.setAttribute('y', pos.y - 8);
        iconText.setAttribute('text-anchor', 'middle');
        iconText.setAttribute('font-size', '24');
        iconText.setAttribute('fill', '#c85a52');
        iconText.textContent = getVendorIcon(dev.vendor, dev.type);
        group.appendChild(iconText);

        // Hostname with fallback
        const displayName = dev.hostname || dev.vendor || 'Unknown Device';
        const hostname = document.createElementNS('http://www.w3.org/2000/svg', 'text');
        hostname.setAttribute('x', pos.x);
        hostname.setAttribute('y', pos.y + nodeRadius + 25);
        hostname.setAttribute('text-anchor', 'middle');
        hostname.setAttribute('fill', '#fff');
        hostname.setAttribute('font-size', '13');
        hostname.setAttribute('font-weight', 'bold');
        hostname.textContent = displayName.substring(0, 20);
        group.appendChild(hostname);

        // Model/Vendor info
        const model = document.createElementNS('http://www.w3.org/2000/svg', 'text');
        model.setAttribute('x', pos.x);
        model.setAttribute('y', pos.y + nodeRadius + 42);
        model.setAttribute('text-anchor', 'middle');
        model.setAttribute('fill', '#959d9f');
        model.setAttribute('font-size', '10');
        model.textContent = (dev.model || dev.vendor || 'Network Device').substring(0, 25);
        group.appendChild(model);

        // Bandwidth label
        if (dev.bandwidth) {
            const bw = document.createElementNS('http://www.w3.org/2000/svg', 'text');
            bw.setAttribute('x', pos.x);
            bw.setAttribute('y', pos.y + nodeRadius + 56);
            bw.setAttribute('text-anchor', 'middle');
            bw.setAttribute('fill', '#c85a52');
            bw.setAttribute('font-size', '9');
            bw.setAttribute('font-weight', 'bold');
            bw.textContent = dev.bandwidth;
            group.appendChild(bw);
        }

        svg.appendChild(group);
    });

    // Update device list panel
    const deviceList = document.getElementById('deviceList');
    deviceList.innerHTML = topologyData.devices.map(dev => {
        const displayName = dev.hostname || dev.vendor || 'Unknown';
        return `
        <div class="device-entry">
            <div class="device-status-indicator ${dev.status === 'up' ? 'up' : 'down'}"></div>
            <div style="flex: 1;">
                <div style="font-weight: 600;">${displayName}</div>
                <div style="font-size: 0.75rem; color: #a0a0a0;">${dev.model || dev.vendor || 'Device'}</div>
            </div>
        </div>
    `}).join('');

    // Update links list panel
    const linkList = document.getElementById('linkList');
    linkList.innerHTML = (topologyData.links || []).map(link => `
        <div class="device-entry">
            <div class="device-status-indicator ${link.status === 'up' ? 'up' : 'down'}"></div>
            <div style="flex: 1;">
                <div style="font-weight: 600;">${link.from} ↔ ${link.to}</div>
                <div style="font-size: 0.75rem; color: #a0a0a0;">${link.fromPort} → ${link.toPort}</div>
                <div style="font-size: 0.75rem; color: #c85a52; margin-top: 2px;">📊 ${link.bandwidth}${link.utilization ? ` (${link.utilization}% util)` : ''}</div>
            </div>
        </div>
    `).join('');
}

function addLog(type, msg) {
    const timestamp = new Date().toLocaleTimeString();
    deviceLogs.push({ type, msg, timestamp });
    if (deviceLogs.length > 100) deviceLogs.shift();
    updateLogs();
}

function filterLogs(filter) {
    updateLogs(filter);
}

function updateLogs(filter = 'all') {
    const logsContent = document.getElementById('logsContent');
    logsContent.innerHTML = deviceLogs
        .filter(log => filter === 'all' || log.type === filter)
        .map(log => `
            <div class="log-entry ${log.type}">
                <div class="log-time">${log.timestamp}</div>
                <div class="log-msg">${log.msg}</div>
            </div>
        `)
        .join('');
    logsContent.scrollTop = logsContent.scrollHeight;
}

function updateMetrics(data) {
    const latest = data.latest || {};
    const components = latest.components || {};

    METRICS.forEach(metric => {
        const comp = components[metric.id] || {};
        let value = parseFloat(comp.value) || 0;

        metricHistory[metric.id] = metricHistory[metric.id] || [];
        metricHistory[metric.id].push(value);
        if (metricHistory[metric.id].length > 20) metricHistory[metric.id].shift();

        const valueEl = document.getElementById(`value-${metric.id}`);
        const fillEl = document.getElementById(`fill-${metric.id}`);
        const detailEl = document.getElementById(`detail-${metric.id}`);

        if (valueEl) valueEl.textContent = value.toFixed(1) + metric.unit;
        if (fillEl) fillEl.style.width = Math.min(value, 100) + '%';
        if (detailEl) detailEl.textContent = comp.detail || 'No data';
    });

    if (charts.cpu && metricHistory.cpu.length) {
        charts.cpu.data.datasets[0].data = metricHistory.cpu;
        charts.cpu.update('none');
    }
    if (charts.memory && metricHistory.memory.length) {
        charts.memory.data.datasets[0].data = metricHistory.memory;
        charts.memory.update('none');
    }
}

function initCharts() {
    const chartOptions = {
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { display: false } },
        scales: {
            y: { min: 0, max: 100, ticks: { color: '#a0a0a0' }, grid: { color: 'rgba(200, 90, 82, 0.05)' } },
            x: { ticks: { color: '#a0a0a0' }, grid: { color: 'rgba(200, 90, 82, 0.05)' } }
        }
    };

    const cpuCtx = document.getElementById('cpuChart')?.getContext('2d');
    if (cpuCtx) {
        charts.cpu = new Chart(cpuCtx, {
            type: 'line',
            data: {
                labels: Array(20).fill(''),
                datasets: [{ label: 'CPU %', data: Array(20).fill(0), borderColor: '#c85a52', backgroundColor: 'rgba(200, 90, 82, 0.1)', fill: true, tension: 0.4, pointRadius: 0, borderWidth: 2 }]
            },
            options: chartOptions
        });
    }

    const memCtx = document.getElementById('memoryChart')?.getContext('2d');
    if (memCtx) {
        charts.memory = new Chart(memCtx, {
            type: 'line',
            data: {
                labels: Array(20).fill(''),
                datasets: [{ label: 'Memory %', data: Array(20).fill(0), borderColor: '#a84738', backgroundColor: 'rgba(168, 71, 56, 0.1)', fill: true, tension: 0.4, pointRadius: 0, borderWidth: 2 }]
            },
            options: chartOptions
        });
    }

    const healthCtx = document.getElementById('healthChart')?.getContext('2d');
    if (healthCtx) {
        charts.health = new Chart(healthCtx, {
            type: 'line',
            data: {
                labels: Array(20).fill(''),
                datasets: [{ label: 'Health Score', data: Array(20).fill(95), borderColor: '#c85a52', backgroundColor: 'rgba(200, 90, 82, 0.1)', fill: true, tension: 0.4, pointRadius: 0, borderWidth: 2 }]
            },
            options: chartOptions
        });
    }

    const perfCtx = document.getElementById('performanceChart')?.getContext('2d');
    if (perfCtx) {
        charts.performance = new Chart(perfCtx, {
            type: 'radar',
            data: {
                labels: ['CPU', 'Memory', 'Fans', 'Power', 'Thermal'],
                datasets: [{ label: 'Performance', data: [85, 75, 90, 80, 70], borderColor: '#c85a52', backgroundColor: 'rgba(200, 90, 82, 0.15)' }]
            },
            options: { ...chartOptions, scales: { r: { ticks: { color: '#a0a0a0' } } } }
        });
    }
}

function refreshData() {
    fetch('/api/status', { cache: 'no-store' })
        .then(r => r.json())
        .then(data => {
            if (!data.connected) {
                loginWrapper.classList.remove('hidden');
                dashboard.classList.add('hidden');
                return;
            }

            const device = data.device || {};
            deviceName.textContent = device.hostname || 'Unknown Device';
            deviceVendor.textContent = device.vendor || 'Auto-detecting...';

            const latest = data.latest || {};
            const status = latest.overall || 'unknown';
            healthStatus.textContent = status === 'healthy' ? 'Healthy' : status === 'warning' ? 'Warning' : 'Critical';

            updateMetrics(data);
        })
        .catch(e => addLog('error', `Refresh failed: ${e.message}`));
}

function startPolling() {
    setInterval(refreshData, 2500);
}
