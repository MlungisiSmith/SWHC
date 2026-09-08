"""Detailed debug to trace vendor detection step-by-step."""

from __future__ import annotations

import os
import sys
from netmiko import ConnectHandler, SSHDetect
from netmiko.exceptions import NetmikoAuthenticationException, NetmikoTimeoutException

USERNAME = os.getenv("SWITCH_USERNAME", "networks")
PASSWORD = os.getenv("SWITCH_PASSWORD", "w00Lw0rTh$")
ENABLE_SECRET = os.getenv("SWITCH_ENABLE_SECRET", "w00Lw0rTh$")

def vendor_key_from_device_type(device_type: str | None) -> str | None:
    print(f"  vendor_key_from_device_type called with: {device_type}")
    if device_type in ("cisco_ios", "cisco_xe", "cisco_xr"):
        print(f"  -> Matched Cisco variant, returning 'cisco'")
        return "cisco"
    if device_type == "huawei":
        print(f"  -> Matched Huawei, returning 'huawei'")
        return "huawei"
    print(f"  -> No match, returning None")
    return None

def detect_vendor_debug(host: str, preferred_vendor: str = "auto") -> None:
    """Debug version of detect_vendor."""
    print(f"\n=== DETECT_VENDOR DEBUG ===")
    print(f"Host: {host}")
    print(f"Preferred vendor: {preferred_vendor}")
    
    preferred_vendor = preferred_vendor.lower()
    
    # Step 1: Check if preferred vendor is already specified
    if preferred_vendor in ("cisco", "huawei"):
        print(f"Step 1: Preferred vendor '{preferred_vendor}' is in VENDOR_TYPES, returning immediately")
        return preferred_vendor, None
    
    if preferred_vendor != "auto":
        print(f"Step 1: Preferred vendor '{preferred_vendor}' is NOT 'auto' and NOT in VENDOR_TYPES, returning error")
        return None, "Invalid vendor preference"
    
    print(f"Step 1: Preferred vendor is 'auto', proceeding with detection")
    
    # Step 2: Try quick connects
    print(f"\nStep 2: Trying quick direct connections...")
    for quick_try_type in ["cisco_ios", "huawei"]:
        print(f"  Attempt: {quick_try_type}")
        try:
            print(f"    Creating ConnectHandler...")
            test_device = ConnectHandler(
                device_type=quick_try_type,
                host=host,
                username=USERNAME,
                password=PASSWORD,
                secret=ENABLE_SECRET,
                conn_timeout=5,
                banner_timeout=5,
                auth_timeout=5,
            )
            print(f"    Connected! Disconnecting...")
            test_device.disconnect()
            vendor_result = "cisco" if quick_try_type == "cisco_ios" else "huawei"
            print(f"    SUCCESS: Returning {vendor_result}")
            return vendor_result, None
        except NetmikoAuthenticationException as e:
            print(f"    Auth failed: {e}")
            continue
        except NetmikoTimeoutException as e:
            print(f"    Timeout: {e}")
            continue
        except Exception as e:
            print(f"    Other error ({type(e).__name__}): {e}")
            continue
    
    print(f"\nStep 2: Quick attempts failed, trying SSHDetect...")
    try:
        print(f"  Creating SSHDetect...")
        detector = SSHDetect(
            device_type="autodetect",
            host=host,
            username=USERNAME,
            password=PASSWORD,
            secret=ENABLE_SECRET,
            conn_timeout=15,
            banner_timeout=15,
            auth_timeout=15,
        )
        print(f"  Calling autodetect()...")
        detected_type = detector.autodetect()
        print(f"  SSHDetect returned: {detected_type}")
        
        vendor = vendor_key_from_device_type(detected_type)
        if vendor:
            print(f"  vendor_key_from_device_type returned: {vendor}")
            return vendor, None
        
        print(f"  vendor_key_from_device_type returned None")
        return None, "Vendor detection did not identify a supported Cisco or Huawei switch."
    except NetmikoTimeoutException as e:
        print(f"  SSHDetect timeout: {e}")
        return None, "Connection timed out."
    except Exception as e:
        print(f"  SSHDetect error ({type(e).__name__}): {e}")
        return None, f"Vendor detection failed: {e}"

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python debug_vendor_detection_detailed.py <switch_ip>")
        sys.exit(1)
    
    host = sys.argv[1]
    vendor, error = detect_vendor_debug(host, "auto")
    print(f"\n=== RESULT ===")
    print(f"Vendor: {vendor}")
    print(f"Error: {error}")
