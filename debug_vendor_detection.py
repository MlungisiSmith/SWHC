"""Debug script to test vendor detection and switch connectivity."""

from __future__ import annotations

import os
import sys
from netmiko import SSHDetect, ConnectHandler
from netmiko.exceptions import (
    NetmikoAuthenticationException,
    NetmikoTimeoutException,
)

# Load credentials from environment
USERNAME = os.getenv("SWITCH_USERNAME", "networks")
PASSWORD = os.getenv("SWITCH_PASSWORD", "w00Lw0rTh$")
ENABLE_SECRET = os.getenv("SWITCH_ENABLE_SECRET", "w00Lw0rTh$")
CONNECTION_TIMEOUT = 15

def test_ssh_connectivity(host: str) -> bool:
    """Test basic SSH connectivity."""
    print(f"\n[*] Testing SSH connectivity to {host}...")
    try:
        import socket
        sock = socket.create_connection((host, 22), timeout=5)
        sock.close()
        print(f"[OK] SSH port 22 is open on {host}")
        return True
    except Exception as e:
        print(f"[FAIL] SSH port 22 unreachable: {e}")
        return False

def test_vendor_detection(host: str) -> None:
    """Test netmiko vendor detection."""
    print(f"\n[*] Attempting vendor autodetection...")
    try:
        detector = SSHDetect(
            device_type="autodetect",
            host=host,
            username=USERNAME,
            password=PASSWORD,
            secret=ENABLE_SECRET,
            conn_timeout=CONNECTION_TIMEOUT,
            banner_timeout=CONNECTION_TIMEOUT,
            auth_timeout=CONNECTION_TIMEOUT,
        )
        detected_type = detector.autodetect()
        print(f"[OK] Detected device type: {detected_type}")
        
        if detected_type in ["cisco_ios", "cisco_xe", "cisco_xr"]:
            print(f"[OK] This is a Cisco device!")
            return
        elif detected_type == "huawei":
            print(f"[OK] This is a Huawei device!")
            return
        else:
            print(f"[FAIL] Detected type '{detected_type}' is not in supported list")
            print(f"    Supported: cisco_ios, cisco_xe, cisco_xr, huawei")
            
    except NetmikoAuthenticationException as e:
        print(f"[FAIL] Authentication failed: {e}")
        print(f"    Check username and password")
    except NetmikoTimeoutException as e:
        print(f"[FAIL] Connection timeout: {e}")
        print(f"    Check if host is reachable and SSH timeout is sufficient")
    except Exception as e:
        print(f"[FAIL] Autodetection failed: {type(e).__name__}: {e}")

def test_direct_connection(host: str, device_type: str) -> None:
    """Test direct connection with specific device type."""
    print(f"\n[*] Testing direct connection with device_type='{device_type}'...")
    try:
        net_connect = ConnectHandler(
            device_type=device_type,
            host=host,
            username=USERNAME,
            password=PASSWORD,
            secret=ENABLE_SECRET,
            conn_timeout=CONNECTION_TIMEOUT,
            banner_timeout=CONNECTION_TIMEOUT,
            auth_timeout=CONNECTION_TIMEOUT,
        )
        print(f"[OK] Successfully connected!")
        prompt = net_connect.find_prompt()
        print(f"[OK] Device prompt: {prompt}")
        
        # Try a simple command
        try:
            if device_type == "cisco_ios":
                output = net_connect.send_command("show version | include Version")
                print(f"[OK] Command output: {output[:100]}")
            elif device_type == "huawei":
                output = net_connect.send_command("display version | include Version")
                print(f"[OK] Command output: {output[:100]}")
        except Exception as e:
            print(f"[!] Command failed: {e}")
        
        net_connect.disconnect()
    except Exception as e:
        print(f"[FAIL] Connection failed: {type(e).__name__}: {e}")

def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: python debug_vendor_detection.py <switch_ip>")
        print("Example: python debug_vendor_detection.py 192.168.1.1")
        sys.exit(1)
    
    host = sys.argv[1]
    print(f"Debugging vendor detection for {host}")
    print(f"Using credentials: username={USERNAME}")
    
    # Test basic connectivity
    if not test_ssh_connectivity(host):
        print("\n[!] Cannot reach SSH. Check IP address, network, and firewall.")
        sys.exit(1)
    
    # Test autodetection
    test_vendor_detection(host)
    
    # Test direct Cisco connection
    test_direct_connection(host, "cisco_ios")
    
    # Test direct Huawei connection
    test_direct_connection(host, "huawei")
    
    print("\n[*] Debug complete. Check the output above for errors.")

if __name__ == "__main__":
    main()
