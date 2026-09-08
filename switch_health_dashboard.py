"""Local interactive Cisco and Huawei switch health dashboard.

Run with: python switch_health_dashboard.py
Open:     http://127.0.0.1:8787
"""

from __future__ import annotations

import ipaddress
import json
import os
import re
import threading
import time
from collections import deque
from datetime import datetime
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from SwitchhealthStatuscheck import INTERVAL_SECONDS, get_switch_health, extract_fan_rpm, extract_power_watts, extract_temperature_celsius
from switch_configs import get_template_list, get_template, render_template
from switch_models import get_all_models
try:
    from netmiko import ConnectHandler
except ImportError:
    ConnectHandler = None

import paramiko
from io import StringIO


HOST = os.getenv("SWITCH_DASHBOARD_HOST", "127.0.0.1")
PORT = int(os.getenv("SWITCH_DASHBOARD_PORT", "8787"))
CHECK_INTERVAL = max(10, INTERVAL_SECONDS)
HISTORY_SIZE = 36
WEB_ROOT = Path(__file__).with_name("switch_health_web")
COMPONENTS = ("cpu", "memory", "fans", "power", "thermal")
USERNAME = "networks"
PASSWORD = "w00Lw0rTh$"
ENABLE_SECRET = "w00Lw0rTh$"

state_lock = threading.Lock()
history: deque[dict[str, Any]] = deque(maxlen=HISTORY_SIZE)
state: dict[str, Any] = {
    "checking": False,
    "target": None,
    "vendor_preference": "auto",
    "device": None,
    "last_check": None,
    "latest": None,
}


def extract_cpu(raw_value: str | None) -> float | None:
    if not raw_value:
        return None
    patterns = (
        r"CPU\s+Usage\s*:?\s*(\d+(?:\.\d+)?)%",
        r"System\s+CPU\s+Using\s+Percentage\s*:\s*(\d+(?:\.\d+)?)%",
        r"CPU\s+utilization\s+for\s+(?:five|ten)\s+seconds\s*:\s*(\d+(?:\.\d+)?)%",
    )
    for pattern in patterns:
        match = re.search(pattern, raw_value, re.IGNORECASE)
        if match:
            return float(match.group(1))
    return None


def extract_memory(raw_value: str | None) -> float | None:
    if not raw_value:
        return None
    total_match = re.search(r"Processor Pool Total:\s*(\d+)", raw_value, re.IGNORECASE)
    used_match = re.search(r"\bUsed:\s*(\d+)", raw_value, re.IGNORECASE)
    if total_match and used_match and int(total_match.group(1)):
        return round((int(used_match.group(1)) / int(total_match.group(1))) * 100, 1)

    patterns = (
        r"Memory\s+Using\s+Percentage\s+Is\s*:\s*(\d+(?:\.\d+)?)%",
        r"Memory\s+(?:Usage|Utilization)(?:\s+Percentage)?\s*:?\s*(\d+(?:\.\d+)?)%",
    )
    for pattern in patterns:
        match = re.search(pattern, raw_value, re.IGNORECASE)
        if match:
            return float(match.group(1))
    return None


def metric_status(value: float | None, warning_at: float, critical_at: float) -> str:
    if value is None:
        return "unknown"
    if value >= critical_at:
        return "critical"
    if value >= warning_at:
        return "warning"
    return "healthy"


def text_status(raw_value: str | None) -> str:
    """Classify command text without returning its content to the browser."""
    if not raw_value:
        return "unknown"
    text = raw_value.lower()
    rejected = ("% invalid input", "% incomplete command", "% ambiguous command", "unrecognized command", "not support")
    if any(term in text for term in rejected):
        return "unknown"
    critical = ("critical", "fault", "failed", "failure", "shutdown", "temperature state: red", "state: abnormal", "not running")
    warning = ("warning", "yellow", "minor", "marginal", "degraded")
    if any(term in text for term in critical):
        return "critical"
    if any(term in text for term in warning):
        return "warning"
    return "healthy"


def component(key: str, status: str, value: str, detail: str) -> dict[str, str]:
    labels = {
        "cpu": "Processor",
        "memory": "Memory",
        "fans": "Cooling fans",
        "power": "Power supply",
        "thermal": "Thermal sensors",
    }
    return {"key": key, "label": labels[key], "status": status, "value": value, "detail": detail}


def environment_component(key: str, raw_value: str | None) -> dict[str, str]:
    status_text = text_status(raw_value)
    
    if key == "fans":
        value, detail = extract_fan_rpm(raw_value)
        if value is None:
            return component(key, "unknown", "0", "No fan data available")
        return component(key, "healthy" if detail == "Normal" else "warning", f"{int(value)}", f"{detail} - {int(value)} RPM")
    
    elif key == "power":
        value, detail = extract_power_watts(raw_value)
        if value is None:
            return component(key, "unknown", "0", "No power data available")
        return component(key, "healthy" if detail == "Normal" else "warning" if detail == "Degraded" else "critical", f"{int(value)}", f"{detail} - {int(value)}W")
    
    elif key == "thermal":
        value, detail = extract_temperature_celsius(raw_value)
        if value is None:
            return component(key, "unknown", "0", "No temperature data available")
        return component(key, "healthy" if detail == "Normal" else "warning" if detail == "Elevated" else "critical", f"{int(value)}", f"{detail} - {int(value)}°C")
    
    return component(key, status_text, "N/A", "Data unavailable")


def empty_components() -> dict[str, dict[str, str]]:
    return {key: component(key, "unknown", "Waiting", "Connect to a switch to read this component.") for key in COMPONENTS}


def overall_status(components: dict[str, dict[str, str]], error: str | None) -> str:
    if error:
        return "critical"
    statuses = [item["status"] for item in components.values()]
    if "critical" in statuses:
        return "critical"
    if "warning" in statuses:
        return "warning"
    if "unknown" in statuses:
        return "unknown"
    return "healthy"


def make_snapshot(metrics: dict[str, str] | None, error: str | None) -> dict[str, Any]:
    if error or not metrics:
        components = empty_components()
        detail = error or "No health data was returned."
        for item in components.values():
            item["detail"] = detail
            item["value"] = "Unavailable"
        return {
            "timestamp": datetime.now().astimezone().isoformat(timespec="seconds"),
            "overall": "critical" if error else "unknown",
            "components": components,
            "error": error,
        }

    cpu_value = extract_cpu(metrics.get("cpu"))
    memory_value = extract_memory(metrics.get("memory"))
    cpu_status = metric_status(cpu_value, 70, 90)
    memory_status = metric_status(memory_value, 75, 90)
    components = {
        "cpu": component(
            "cpu",
            cpu_status,
            f"{cpu_value:g}%" if cpu_value is not None else "Unavailable",
            "Five- or ten-second CPU utilization." if cpu_value is not None else "The switch did not return a readable CPU value.",
        ),
        "memory": component(
            "memory",
            memory_status,
            f"{memory_value:g}%" if memory_value is not None else "Unavailable",
            "Current memory utilization." if memory_value is not None else "The switch did not return a readable memory value.",
        ),
        "fans": environment_component("fans", metrics.get("fans")),
        "power": environment_component("power", metrics.get("power")),
        "thermal": environment_component("thermal", metrics.get("thermal")),
    }
    return {
        "timestamp": datetime.now().astimezone().isoformat(timespec="seconds"),
        "overall": overall_status(components, None),
        "components": components,
        "error": None,
    }


def run_check(target: str, vendor_preference: str) -> None:
    """Poll one configured switch without returning target or raw CLI output."""
    try:
        metrics, device, error = get_switch_health(target, vendor_preference)
        snapshot = make_snapshot(metrics, error)
    except Exception:
        device, snapshot = None, make_snapshot(None, "The health check could not be completed.")

    with state_lock:
        if state["target"] != target:
            return
        if device and state["target"] == target:
            state["device"] = device
        history.append({"timestamp": snapshot["timestamp"], "overall": snapshot["overall"]})
        state.update(checking=False, last_check=snapshot["timestamp"], latest=snapshot)


def begin_check() -> bool:
    with state_lock:
        if state["checking"] or not state["target"]:
            return False
        target = state["target"]
        vendor_preference = state["vendor_preference"]
        state["checking"] = True
    threading.Thread(target=run_check, args=(target, vendor_preference), name="switch-health-check", daemon=True).start()
    return True


def configure_target(address: str, vendor_preference: str) -> tuple[bool, str | None]:
    try:
        ipaddress.ip_address(address)
    except ValueError:
        return False, "Enter a valid switch IP address."
    if vendor_preference not in ("auto", "cisco", "huawei"):
        return False, "Choose Cisco, Huawei, or automatic vendor detection."

    with state_lock:
        state.update(
            checking=False,
            target=address,
            vendor_preference=vendor_preference,
            device=None,
            last_check=None,
            latest=None,
        )
        history.clear()
    begin_check()
    return True, None


def clear_target() -> None:
    with state_lock:
        state.update(checking=False, target=None, vendor_preference="auto", device=None, last_check=None, latest=None)
        history.clear()


def monitor_forever() -> None:
    while True:
        begin_check()
        time.sleep(CHECK_INTERVAL)


def apply_switch_config(target: str, vendor_key: str, config_commands: str) -> dict[str, Any]:
    """Apply configuration commands to a switch."""
    try:
        if not ConnectHandler:
            return {"success": False, "error": "Netmiko not available"}
        
        device_type = "cisco_ios" if vendor_key == "cisco" else "huawei"
        net_connect = ConnectHandler(
            host=target,
            username=USERNAME,
            password=PASSWORD,
            secret=ENABLE_SECRET,
            device_type=device_type,
            timeout=20,
            auth_timeout=15
        )
        
        if vendor_key == "cisco":
            net_connect.enable()
        
        output = net_connect.send_config_set(config_commands.split('\n'))
        net_connect.disconnect()
        
        return {
            "success": True,
            "message": "Configuration applied successfully",
            "output": output[-500:] if len(output) > 500 else output
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Configuration failed: {str(e)[:100]}"
        }


def discover_topology(target: str, vendor_preference: str) -> dict[str, Any]:
    """Discover network topology using LLDP/CDP."""
    devices = []
    links = []

    try:
        print(f"[TOPOLOGY] Starting discovery for {target}, vendor preference: {vendor_preference}")
        
        if vendor_preference in ("auto", "cisco"):
            print(f"[TOPOLOGY] Using Cisco mode")
            return discover_topology_cisco(target, devices, links)
        else:
            print(f"[TOPOLOGY] Using Huawei mode")
            return discover_topology_huawei(target, devices, links)

    except Exception as e:
        print(f"[TOPOLOGY] Fatal discovery error: {e}")
        import traceback
        traceback.print_exc()
        return {"devices": [], "links": [], "error": str(e)}


def discover_topology_huawei(target: str, devices: list, links: list) -> dict[str, Any]:
    """Discover Huawei switch topology using direct SSH."""
    try:
        print(f"[TOPOLOGY] Connecting to Huawei switch {target}")
        
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(
            target,
            username=USERNAME,
            password=PASSWORD,
            timeout=20,
            auth_timeout=15,
            banner_timeout=15
        )
        
        print(f"[TOPOLOGY] SSH connected successfully")
        
        shell = ssh.invoke_shell()
        shell.settimeout(10)
        
        import time
        time.sleep(1)
        output = shell.recv(4096).decode('utf-8')
        print(f"[TOPOLOGY] Initial prompt: {output[:100]}")
        
        hostname = "Huawei-Switch"
        shell.send("display current-configuration | include sysName\n")
        time.sleep(0.5)
        output = shell.recv(4096).decode('utf-8')
        print(f"[TOPOLOGY] Hostname output: {output[:200]}")
        if "sysName" in output:
            parts = output.split()
            for i, part in enumerate(parts):
                if "sysName" in part and i + 1 < len(parts):
                    hostname = parts[i + 1]
                    break
        
        print(f"[TOPOLOGY] Device hostname: {hostname}")
        
        devices.append({
            "hostname": hostname,
            "name": hostname,
            "ipAddress": target,
            "vendor": "Huawei",
            "model": "Huawei VRP",
            "type": "core",
            "bandwidth": "10G",
            "status": "up"
        })
        
        print(f"[TOPOLOGY] Querying LLDP neighbors")
        shell.send("display lldp neighbor\n")
        time.sleep(1)
        output = shell.recv(8192).decode('utf-8', errors='ignore')
        print(f"[TOPOLOGY] LLDP output:\n{output}")
        
        lines = output.split("\n")
        for line in lines:
            line = line.strip()
            if not line or "Local" in line or "---" in line or "Neighbor" in line:
                continue
            
            parts = line.split()
            if len(parts) >= 3:
                try:
                    local_port = parts[0]
                    neighbor_id = parts[1]
                    neighbor_port = parts[2]
                    
                    print(f"[TOPOLOGY] Found link: {local_port} -> {neighbor_id} ({neighbor_port})")
                    
                    devices.append({
                        "hostname": neighbor_id,
                        "name": neighbor_id,
                        "vendor": "Unknown",
                        "model": "Network Device",
                        "type": "access",
                        "bandwidth": "1G",
                        "status": "up"
                    })
                    links.append({
                        "from": hostname,
                        "to": neighbor_id,
                        "fromPort": local_port,
                        "toPort": neighbor_port,
                        "bandwidth": "1000Mbps",
                        "utilization": 25,
                        "status": "up"
                    })
                except Exception as e:
                    print(f"[TOPOLOGY] Error parsing line '{line}': {e}")
        
        shell.close()
        ssh.close()
        
        print(f"[TOPOLOGY] Discovery complete: {len(devices)} devices, {len(links)} links")
        return {"devices": devices, "links": links}
        
    except Exception as e:
        print(f"[TOPOLOGY] Huawei discovery failed: {e}")
        import traceback
        traceback.print_exc()
        return {"devices": devices, "links": links, "error": str(e)}


def discover_topology_cisco(target: str, devices: list, links: list) -> dict[str, Any]:
    """Discover Cisco switch topology using Netmiko."""
    try:
        if not ConnectHandler:
            return {"devices": [], "links": [], "error": "Netmiko not available"}
        
        print(f"[TOPOLOGY] Connecting to Cisco switch {target}")
        
        net_connect = ConnectHandler(
            host=target,
            username=USERNAME,
            password=PASSWORD,
            secret=ENABLE_SECRET,
            device_type="cisco_ios",
            timeout=20,
            auth_timeout=15
        )
        
        print(f"[TOPOLOGY] Connected to Cisco")
        
        hostname = "Cisco-Switch"
        try:
            output = net_connect.send_command("show run | include hostname")
            if output:
                hostname = output.split()[-1]
            print(f"[TOPOLOGY] Cisco hostname: {hostname}")
        except Exception as e:
            print(f"[TOPOLOGY] Failed to get hostname: {e}")
        
        model = "Cisco Catalyst 9200L"
        try:
            output = net_connect.send_command("show version | include Model number")
            if output:
                model = output.split(":")[-1].strip()
        except:
            pass
        
        devices.append({
            "hostname": hostname,
            "name": hostname,
            "ipAddress": target,
            "vendor": "Cisco",
            "model": model,
            "type": "core",
            "bandwidth": "10G",
            "status": "up"
        })
        
        print(f"[TOPOLOGY] Querying LLDP neighbors")
        try:
            output = net_connect.send_command("show lldp neighbors")
            print(f"[TOPOLOGY] LLDP output length: {len(output)}")
            
            lines = output.split("\n")
            for line in lines[1:]:
                line = line.strip()
                if not line:
                    continue
                parts = line.split()
                if len(parts) >= 4:
                    try:
                        neighbor_hostname = parts[0]
                        local_port = parts[1]
                        neighbor_port = parts[2]
                        
                        print(f"[TOPOLOGY] Found Cisco neighbor: {neighbor_hostname} on {local_port}")
                        
                        devices.append({
                            "hostname": neighbor_hostname,
                            "name": neighbor_hostname,
                            "vendor": "Unknown",
                            "model": "Network Device",
                            "type": "access",
                            "bandwidth": "1G",
                            "status": "up"
                        })
                        links.append({
                            "from": hostname,
                            "to": neighbor_hostname,
                            "fromPort": local_port,
                            "toPort": neighbor_port,
                            "bandwidth": "1000Mbps",
                            "utilization": 45,
                            "status": "up"
                        })
                    except Exception as e:
                        print(f"[TOPOLOGY] Error parsing Cisco line: {e}")
        except Exception as e:
            print(f"[TOPOLOGY] Cisco LLDP query failed: {e}")
        
        net_connect.disconnect()
        print(f"[TOPOLOGY] Cisco discovery complete: {len(devices)} devices, {len(links)} links")
        return {"devices": devices, "links": links}
        
    except Exception as e:
        print(f"[TOPOLOGY] Cisco discovery fatal error: {e}")
        import traceback
        traceback.print_exc()
        return {"devices": devices, "links": links, "error": str(e)}


def dashboard_payload() -> dict[str, Any]:
    """Return only safe-to-display data; target addresses stay server-side."""
    with state_lock:
        return {
            "connected": bool(state["target"]),
            "checking": state["checking"],
            "device": state["device"],
            "last_check": state["last_check"],
            "interval_seconds": CHECK_INTERVAL,
            "latest": state["latest"],
            "history": list(history),
        }


class DashboardHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:  # noqa: N802
        request_path = urlparse(self.path).path
        if request_path == "/api/status":
            self.respond_json(HTTPStatus.OK, dashboard_payload())
            return
        if request_path == "/api/topology":
            with state_lock:
                target = state["target"]
                vendor_preference = state["vendor_preference"]
            if not target:
                self.respond_json(HTTPStatus.BAD_REQUEST, {"error": "No switch connected"})
                return
            topology_data = discover_topology(target, vendor_preference)
            self.respond_json(HTTPStatus.OK, topology_data)
            return
        if request_path == "/api/models":
            self.respond_json(HTTPStatus.OK, {"models": get_all_models()})
            return
        if request_path == "/api/config/templates":
            with state_lock:
                vendor_key = state["device"].get("vendor_key") if state["device"] else "cisco"
            templates = get_template_list(vendor_key)
            self.respond_json(HTTPStatus.OK, {"templates": templates})
            return
        if request_path in ("/", "/index.html"):
            self.respond_file(WEB_ROOT / "index.html", "text/html; charset=utf-8")
            return
        if request_path == "/app.css":
            self.respond_file(WEB_ROOT / "app.css", "text/css; charset=utf-8")
            return
        if request_path == "/app.js":
            self.respond_file(WEB_ROOT / "app.js", "application/javascript; charset=utf-8")
            return
        if request_path == "/greystone-logo.png":
            self.respond_file(WEB_ROOT / "greystone-logo.png", "image/png")
            return
        self.send_error(HTTPStatus.NOT_FOUND, "Nothing is served at this address.")

    def do_POST(self) -> None:  # noqa: N802
        request_path = urlparse(self.path).path
        if request_path == "/api/connect":
            payload = self.request_json()
            if payload is None:
                return
            success, message = configure_target(str(payload.get("address", "")).strip(), str(payload.get("vendor", "auto")).lower())
            self.respond_json(HTTPStatus.ACCEPTED if success else HTTPStatus.BAD_REQUEST, {"started": success, "message": message or "Connection started."})
            return
        if request_path == "/api/check":
            started = begin_check()
            self.respond_json(HTTPStatus.ACCEPTED if started else HTTPStatus.CONFLICT, {"started": started, "message": "Health check started." if started else "Connect to a switch or wait for the active check."})
            return
        if request_path == "/api/disconnect":
            clear_target()
            self.respond_json(HTTPStatus.OK, {"disconnected": True})
            return
        if request_path == "/api/config/templates":
            with state_lock:
                vendor_key = state["device"].get("vendor_key") if state["device"] else "cisco"
            templates = get_template_list(vendor_key)
            self.respond_json(HTTPStatus.OK, {"templates": templates})
            return
        if request_path == "/api/config/preview":
            payload = self.request_json()
            if payload is None:
                return
            with state_lock:
                vendor_key = state["device"].get("vendor_key") if state["device"] else None
            if not vendor_key:
                self.respond_json(HTTPStatus.BAD_REQUEST, {"error": "No switch connected"})
                return
            template_name = str(payload.get("template", "")).strip()
            parameters = payload.get("parameters", {})
            config = render_template(vendor_key, template_name, parameters)
            if not config:
                self.respond_json(HTTPStatus.BAD_REQUEST, {"error": "Invalid template or parameters"})
                return
            self.respond_json(HTTPStatus.OK, {"config": config, "template": template_name})
            return
        if request_path == "/api/config/apply":
            payload = self.request_json()
            if payload is None:
                return
            with state_lock:
                target = state["target"]
                vendor_key = state["device"].get("vendor_key") if state["device"] else None
            if not target or not vendor_key:
                self.respond_json(HTTPStatus.BAD_REQUEST, {"error": "No switch connected"})
                return
            template_name = str(payload.get("template", "")).strip()
            parameters = payload.get("parameters", {})
            config = render_template(vendor_key, template_name, parameters)
            if not config:
                self.respond_json(HTTPStatus.BAD_REQUEST, {"error": "Invalid template or parameters"})
                return
            result = apply_switch_config(target, vendor_key, config)
            self.respond_json(HTTPStatus.OK if result["success"] else HTTPStatus.BAD_REQUEST, result)
            return
        self.send_error(HTTPStatus.NOT_FOUND, "Nothing is served at this address.")

    def request_json(self) -> dict[str, Any] | None:
        try:
            size = int(self.headers.get("Content-Length", "0"))
            if size <= 0 or size > 1024:
                raise ValueError
            payload = json.loads(self.rfile.read(size).decode("utf-8"))
            if not isinstance(payload, dict):
                raise ValueError
            return payload
        except (ValueError, json.JSONDecodeError, UnicodeDecodeError):
            self.respond_json(HTTPStatus.BAD_REQUEST, {"started": False, "message": "Enter a valid switch IP address."})
            return None

    def respond_json(self, status: HTTPStatus, data: dict[str, Any]) -> None:
        body = json.dumps(data).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def respond_file(self, path: Path, content_type: str) -> None:
        try:
            body = path.read_bytes()
        except FileNotFoundError:
            self.send_error(HTTPStatus.NOT_FOUND, "Dashboard asset is missing.")
            return
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type)
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args: Any) -> None:
        return


def main() -> None:
    threading.Thread(target=monitor_forever, name="switch-health-monitor", daemon=True).start()
    server = ThreadingHTTPServer((HOST, PORT), DashboardHandler)
    print(f"Switch Health Console is running at http://{HOST}:{PORT}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nDashboard stopped.")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
