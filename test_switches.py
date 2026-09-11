#!/usr/bin/env python
import asyncio
from app.services.health_check import get_switch_health

async def test_switches():
    switches = [
        ("192.168.101.212", "cisco"),
        ("192.168.101.101", "huawei")
    ]
    
    for ip, vendor in switches:
        print(f"\n{'='*60}")
        print(f"Testing {vendor.upper()} switch at {ip}")
        print('='*60)
        
        metrics, identity, error = await get_switch_health(ip, vendor)
        
        if error:
            print(f"❌ ERROR: {error}")
        elif identity:
            print(f"✅ CONNECTION SUCCESSFUL!")
            print(f"\nIdentity Information:")
            print(f"  Hostname: {identity['hostname']}")
            print(f"  Vendor: {identity['vendor']}")
            print(f"  IP Address: {identity['ip_address']}")
            print(f"  Vendor Key: {identity['vendor_key']}")
            
            if metrics:
                print(f"\nMetrics Collected ({len(metrics)} items):")
                for key, value in metrics.items():
                    preview = str(value)[:80] if value else "[empty]"
                    print(f"  {key}: {preview}...")
        else:
            print("⚠ No data returned")

if __name__ == "__main__":
    asyncio.run(test_switches())
