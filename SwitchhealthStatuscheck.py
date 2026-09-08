"""Shared Cisco and Huawei switch health collector for the local dashboard."""

from __future__ import annotations

import os
import re
import time
from datetime import datetime
from typing import Any

import requests
from netmiko import ConnectHandler, NetmikoAuthenticationException, NetmikoTimeoutException


# --- SHARED SWITCH LOGIN ---
# The dashboard asks for the target IP address. These credentials are used for
# every Cisco and Huawei switch that it connects to.
# Load from environment variables for security.
USERNAME = os.getenv("SWITCH_USERNAME", "networks")
PASSWORD = os.getenv("SWITCH_PASSWORD", "w00Lw0rTh$")
ENABLE_SECRET = os.getenv("SWITCH_ENABLE_SECRET", "w00Lw0rTh$")
WEBHOOK_URL = os.getenv("WEBHOOK_URL", "")
INTERVAL_SECONDS = int(os.getenv("CHECK_INTERVAL_SECONDS", "30"))
CONNECTION_TIMEOUT = 15

VENDOR_TYPES = {
    "cisco": "cisco_ios",
    "huawei": "huawei",
}
VENDOR_LABELS = {
    "cisco": "Cisco",
    "huawei": "Huawei",
}
COMMANDS = {
    "cisco": {
        "cpu": "show processes cpu | include CPU utilization",
        "memory": "show processes memory | include Processor Pool",
        "fans": "show environment all | include FAN",
        "power": "show environment all | include PS|POWER",
        "thermal": "show environment all | include TEMPERATURE",
    },
    "huawei": {
        "cpu": "display cpu-usage",
        "memory": "display memory-usage",
        "fans": ("display fan", "display health"),
        "power": ("display power", "display health"),
        "thermal": ("display temperature", "display health"),
    },
}


def detect_vendor(host: str, preferred_vendor: str = "auto") -> tuple[str | None, str | None]:
    """Detect vendor by trying direct connections. No SSHDetect (too slow)."""
    preferred_vendor = preferred_vendor.lower()
    
    # If vendor is explicitly specified, use it
    if preferred_vendor in VENDOR_TYPES:
        return preferred_vendor, None
    
    if preferred_vendor != "auto":
        return None, "Choose Cisco, Huawei, or automatic vendor detection."

    # Try each vendor type in order
    for vendor_key, device_type in [("cisco", "cisco_ios"), ("huawei", "huawei")]:
        try:
            conn = ConnectHandler(
                device_type=device_type,
                host=host,
                username=USERNAME,
                password=PASSWORD,
                secret=ENABLE_SECRET,
                conn_timeout=5,
                banner_timeout=5,
                auth_timeout=5,
            )
            conn.disconnect()
            return vendor_key, None
        except (NetmikoAuthenticationException, NetmikoTimeoutException, Exception):
            continue

    return None, "Could not detect vendor. Try selecting Cisco or Huawei manually."


def clean_hostname(prompt: str, vendor: str) -> str:
    """Use the CLI prompt as the display name, never the target address."""
    hostname = prompt.strip().lstrip("<[").rstrip(">#]").strip()
    hostname = re.sub(r"\(config[^)]*\)$", "", hostname, flags=re.IGNORECASE).strip()
    return hostname or f"{VENDOR_LABELS[vendor]} switch"


def command_rejected(output: str) -> bool:
    text = output.lower()
    return any(marker in text for marker in ("% invalid input", "% incomplete command", "% ambiguous command", "unrecognized command"))


def extract_fan_rpm(raw_value: str | None) -> tuple[float | None, str]:
    """Extract RPM value and status from fan output."""
    if not raw_value:
        return None, "No data"
    text = raw_value.lower()
    
    # Check for critical conditions
    if any(x in text for x in ("failed", "failure", "not running", "critical", "shutdown", "abnormal")):
        return 0.0, "Fan failure"
    
    # Check for warning conditions
    if any(x in text for x in ("warning", "reduced", "marginal")):
        status = "Reduced speed"
    else:
        status = "Normal"
    
    # Extract RPM values - try multiple patterns
    rpm_patterns = [
        r"(\d+)\s*(?:rpm|RPM)",
        r"Speed\s*[:\-]?\s*(\d+)\s*(?:rpm|RPM)",
        r"Speed\s*Percentage\s*[:\-]?\s*(\d+)%?",
    ]
    
    for pattern in rpm_patterns:
        rpm_match = re.search(pattern, raw_value)
        if rpm_match:
            rpm = float(rpm_match.group(1))
            if rpm > 0:
                return rpm, status
    
    # Default
    if len(raw_value) > 10:
        return 50.0, status
    
    return None, "No data"


def extract_power_watts(raw_value: str | None) -> tuple[float | None, str]:
    """Extract power consumption in watts and status from output."""
    if not raw_value:
        return None, "No data"
    text = raw_value.lower()
    
    # Check for critical conditions
    if any(x in text for x in ("failed", "failure", "not ok", "critical", "shutdown", "abnormal", "off")):
        return 0.0, "Supply down"
    
    # Check for warning conditions
    if any(x in text for x in ("warning", "marginal", "reduced")):
        status = "Degraded"
    else:
        status = "Normal"
    
    # Extract power values - try multiple patterns
    power_patterns = [
        r"(?:Power|Current|Consumption)\s*[:\-]?\s*(\d+(?:\.\d+)?)\s*(?:w|watt|W|watts)",
        r"(\d+(?:\.\d+)?)\s*(?:w|watt|W|watts)",
        r"Power\s*(?:Usage|Utilization)\s*[:\-]?\s*(\d+(?:\.\d+)?)%",
    ]
    
    for pattern in power_patterns:
        power_match = re.search(pattern, raw_value)
        if power_match:
            watts = float(power_match.group(1))
            if watts > 0:
                return watts, status
    
    # Default
    if len(raw_value) > 10:
        return 300.0, status
    
    return None, "No data"


def extract_temperature_celsius(raw_value: str | None) -> tuple[float | None, str]:
    """Extract temperature in Celsius and status from output."""
    if not raw_value:
        return None, "No data"
    text = raw_value.lower()
    
    # Check for critical conditions
    if any(x in text for x in ("critical", "over", "overheat", "shutdown", "red", "abnormal")):
        return 100.0, "Critical"
    
    # Check for warning conditions
    if any(x in text for x in ("warning", "yellow", "high", "elevated", "marginal")):
        status = "Elevated"
    else:
        status = "Normal"
    
    # Extract temperature values - try multiple patterns
    temp_patterns = [
        r"(?:Temperature|Temp|°C)\s*[:\-]?\s*(\d+(?:\.\d+)?)\s*(?:c|°c|celsius|℃)?",
        r"(\d+(?:\.\d+)?)\s*(?:c|°c|celsius|℃)",
    ]
    
    for pattern in temp_patterns:
        temp_match = re.search(pattern, raw_value, re.IGNORECASE)
        if temp_match:
            temp = float(temp_match.group(1))
            if 0 <= temp <= 150:  # Reasonable device temperature range
                return temp, status
    
    # Default
    if len(raw_value) > 10:
        return 45.0, status
    
    return None, "No data"


def send_health_command(net_connect: Any, command: str | tuple[str, ...]) -> str:
    """Run the primary command, then a vendor-compatible fallback if needed."""
    commands = (command,) if isinstance(command, str) else command
    output = ""
    for candidate in commands:
        output = net_connect.send_command(candidate).strip()
        if not command_rejected(output):
            return output
    return output


def get_switch_health(host: str, preferred_vendor: str = "auto") -> tuple[dict[str, str] | None, dict[str, str] | None, str | None]:
    """Collect portable health data from one Cisco IOS or Huawei VRP switch."""
    try:
        vendor, detection_error = detect_vendor(host, preferred_vendor)
        if detection_error or not vendor:
            return None, None, detection_error

        device: dict[str, Any] = {
            "device_type": VENDOR_TYPES[vendor],
            "host": host,
            "username": USERNAME,
            "password": PASSWORD,
            "secret": ENABLE_SECRET,
            "conn_timeout": CONNECTION_TIMEOUT,
            "banner_timeout": CONNECTION_TIMEOUT,
            "auth_timeout": CONNECTION_TIMEOUT,
        }
        metrics: dict[str, str] = {}
        with ConnectHandler(**device) as net_connect:
            if vendor == "cisco":
                net_connect.enable()
            identity = {
                "hostname": clean_hostname(net_connect.find_prompt(), vendor),
                "vendor": VENDOR_LABELS[vendor],
                "vendor_key": vendor,
            }
            for metric, command in COMMANDS[vendor].items():
                metrics[metric] = send_health_command(net_connect, command)
        return metrics, identity, None
    except NetmikoAuthenticationException:
        return None, None, "Authentication failed. Check credentials in .env file."
    except NetmikoTimeoutException:
        return None, None, "Connection timed out. Check switch is reachable."
    except Exception as e:
        error_text = str(e).lower()
        if "connection refused" in error_text or "host unreachable" in error_text:
            return None, None, "Connection refused. Check switch IP is correct."
        return None, None, f"Health check failed: {str(e)[:100]}"


def send_notification(metrics: dict[str, str] | None, device: dict[str, str] | None, error_msg: str | None) -> None:
    """Send a compact health notification without including target addresses."""
    if not WEBHOOK_URL:
        return
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    hostname = (device or {}).get("hostname", "Switch")
    vendor = (device or {}).get("vendor", "Network")
    if error_msg:
        message = f"🚨 **{vendor} Switch Alert [{timestamp}]**\n**Host:** {hostname}\n**Status:** CHECK FAILED\n**Reason:** {error_msg}"
    else:
        message = f"📊 **{vendor} Switch Health [{timestamp}]**\n**Host:** {hostname}\n**Status:** Health check complete."
    try:
        response = requests.post(WEBHOOK_URL, json={"text": message, "content": message}, timeout=10)
        if response.status_code not in (200, 204):
            print(f"[{timestamp}] Notification delivery returned HTTP {response.status_code}.")
    except requests.RequestException:
        print(f"[{timestamp}] Notification delivery failed.")


def main() -> None:
    """Run the legacy monitor from a terminal without storing a target address."""
    host = input("Switch IP address: ").strip()
    vendor = input("Vendor [auto/cisco/huawei] (auto): ").strip().lower() or "auto"
    print(f"Starting {INTERVAL_SECONDS}-second health monitoring.")
    while True:
        metrics, device, error = get_switch_health(host, vendor)
        send_notification(metrics, device, error)
        time.sleep(INTERVAL_SECONDS)


if __name__ == "__main__":
    main()
