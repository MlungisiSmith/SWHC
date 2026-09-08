"""Test the exact flow the dashboard uses."""

import os
from SwitchhealthStatuscheck import detect_vendor, get_switch_health

USERNAME = os.getenv("SWITCH_USERNAME", "networks")
PASSWORD = os.getenv("SWITCH_PASSWORD", "w00Lw0rTh$")
ENABLE_SECRET = os.getenv("SWITCH_ENABLE_SECRET", "w00Lw0rTh$")

print("=" * 60)
print("TEST 1: Direct detect_vendor call with 'auto'")
print("=" * 60)
vendor, error = detect_vendor("192.168.101.212", "auto")
print(f"Vendor: {vendor}")
print(f"Error: {error}")

print("\n" + "=" * 60)
print("TEST 2: Full get_switch_health with 'auto'")
print("=" * 60)
metrics, device, error = get_switch_health("192.168.101.212", "auto")
print(f"Device: {device}")
print(f"Error: {error}")
print(f"Metrics: {list(metrics.keys()) if metrics else None}")

print("\n" + "=" * 60)
print("TEST 3: Direct detect_vendor call with 'cisco'")
print("=" * 60)
vendor, error = detect_vendor("192.168.101.212", "cisco")
print(f"Vendor: {vendor}")
print(f"Error: {error}")

print("\n" + "=" * 60)
print("TEST 4: Full get_switch_health with 'cisco'")
print("=" * 60)
metrics, device, error = get_switch_health("192.168.101.212", "cisco")
print(f"Device: {device}")
print(f"Error: {error}")
print(f"Metrics: {list(metrics.keys()) if metrics else None}")
