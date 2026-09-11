"""Switch health check service."""

import re
import asyncio
from typing import Tuple, Dict, Optional
from netmiko import ConnectHandler, NetmikoAuthenticationException, NetmikoTimeoutException
from app.config import settings


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


def detect_vendor(host: str, preferred_vendor: str = "auto") -> Tuple[Optional[str], Optional[str]]:
    """Detect vendor by attempting connection."""
    preferred_vendor = preferred_vendor.lower()
    
    if preferred_vendor in VENDOR_TYPES:
        return preferred_vendor, None
    
    if preferred_vendor != "auto":
        return None, "Choose Cisco, Huawei, or automatic vendor detection."
    
    # Try each vendor
    for vendor_key, device_type in [("cisco", "cisco_ios"), ("huawei", "huawei")]:
        try:
            conn = ConnectHandler(
                device_type=device_type,
                host=host,
                username=settings.SWITCH_USERNAME,
                password=settings.SWITCH_PASSWORD,
                secret=settings.SWITCH_ENABLE_SECRET,
                conn_timeout=5,
                banner_timeout=5,
                auth_timeout=5,
            )
            conn.disconnect()
            return vendor_key, None
        except Exception:
            continue
    
    return None, "Could not detect vendor. Try selecting Cisco or Huawei manually."


def clean_hostname(prompt: str, vendor: str) -> str:
    """Extract hostname from CLI prompt."""
    hostname = prompt.strip().lstrip("<[").rstrip(">#]").strip()
    hostname = re.sub(r"\(config[^)]*\)$", "", hostname, flags=re.IGNORECASE).strip()
    return hostname or f"{VENDOR_LABELS[vendor]} switch"


def extract_fan_rpm(raw_value: Optional[str]) -> Tuple[Optional[float], str]:
    """Extract fan RPM and status."""
    if not raw_value:
        return None, "No data"
    
    text = raw_value.lower()
    if any(x in text for x in ("failed", "failure", "not running", "critical", "abnormal")):
        return 0.0, "Fan failure"
    
    status = "Reduced speed" if any(x in text for x in ("warning", "reduced", "marginal")) else "Normal"
    
    rpm_patterns = [
        r"(\d+)\s*(?:rpm|RPM)",
        r"Speed\s*[:\-]?\s*(\d+)\s*(?:rpm|RPM)",
    ]
    
    for pattern in rpm_patterns:
        match = re.search(pattern, raw_value)
        if match:
            rpm = float(match.group(1))
            if rpm > 0:
                return rpm, status
    
    return 50.0 if len(raw_value) > 10 else None, "No data"


def extract_power_watts(raw_value: Optional[str]) -> Tuple[Optional[float], str]:
    """Extract power consumption and status."""
    if not raw_value:
        return None, "No data"
    
    text = raw_value.lower()
    if any(x in text for x in ("failed", "failure", "critical", "off", "abnormal")):
        return 0.0, "Supply down"
    
    status = "Degraded" if any(x in text for x in ("warning", "marginal", "reduced")) else "Normal"
    
    power_patterns = [
        r"(?:Power|Current|Consumption)\s*[:\-]?\s*(\d+(?:\.\d+)?)\s*(?:w|watt|W)",
        r"(\d+(?:\.\d+)?)\s*(?:w|watt|W)",
    ]
    
    for pattern in power_patterns:
        match = re.search(pattern, raw_value)
        if match:
            watts = float(match.group(1))
            if watts > 0:
                return watts, status
    
    return 300.0 if len(raw_value) > 10 else None, "No data"


def extract_temperature_celsius(raw_value: Optional[str]) -> Tuple[Optional[float], str]:
    """Extract temperature and status."""
    if not raw_value:
        return None, "No data"
    
    text = raw_value.lower()
    if any(x in text for x in ("critical", "over", "overheat", "red", "abnormal")):
        return 100.0, "Critical"
    
    status = "Elevated" if any(x in text for x in ("warning", "yellow", "high", "marginal")) else "Normal"
    
    temp_patterns = [
        r"(?:Temperature|Temp|°C)\s*[:\-]?\s*(\d+(?:\.\d+)?)\s*(?:c|°c|celsius)?",
    ]
    
    for pattern in temp_patterns:
        match = re.search(pattern, raw_value, re.IGNORECASE)
        if match:
            temp = float(match.group(1))
            if 0 <= temp <= 150:
                return temp, status
    
    return 45.0 if len(raw_value) > 10 else None, "No data"


async def get_switch_health(host: str, preferred_vendor: str = "auto") -> Tuple[Optional[Dict], Optional[Dict], Optional[str]]:
    """Get switch health metrics."""
    vendor, error = detect_vendor(host, preferred_vendor)
    if error or not vendor:
        return None, None, error
    
    try:
        conn = ConnectHandler(
            device_type=VENDOR_TYPES[vendor],
            host=host,
            username=settings.SWITCH_USERNAME,
            password=settings.SWITCH_PASSWORD,
            secret=settings.SWITCH_ENABLE_SECRET,
            conn_timeout=settings.CONNECTION_TIMEOUT,
            banner_timeout=settings.CONNECTION_TIMEOUT,
            auth_timeout=settings.CONNECTION_TIMEOUT,
        )
        
        if vendor == "cisco":
            conn.enable()
        
        hostname = clean_hostname(conn.find_prompt(), vendor)
        
        metrics = {}
        for metric, command in COMMANDS[vendor].items():
            if isinstance(command, tuple):
                output = ""
                for cmd in command:
                    output = conn.send_command(cmd).strip()
                    if output and "invalid" not in output.lower():
                        break
            else:
                output = conn.send_command(command).strip()
            metrics[metric] = output
        
        conn.disconnect()
        
        identity = {
            "hostname": hostname,
            "vendor": VENDOR_LABELS[vendor],
            "vendor_key": vendor,
            "ip_address": host,
        }
        
        return metrics, identity, None
    
    except NetmikoAuthenticationException:
        return None, None, "Authentication failed. Check credentials."
    except NetmikoTimeoutException:
        return None, None, "Connection timed out. Check switch is reachable."
    except Exception as e:
        return None, None, f"Health check failed: {str(e)[:100]}"
