"""Real component images and Cisco/Huawei stencil data."""

from __future__ import annotations

# SVG icons for components (can be replaced with actual images)
COMPONENT_SVGS = {
    "processor": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">
      <defs><linearGradient id="procGrad" x1="0%" y1="0%" x2="100%" y2="100%">
        <stop offset="0%" style="stop-color:#FF6B6B;stop-opacity:1" />
        <stop offset="100%" style="stop-color:#CC5555;stop-opacity:1" />
      </linearGradient></defs>
      <rect x="10" y="10" width="80" height="80" fill="url(#procGrad)" rx="5"/>
      <rect x="25" y="25" width="15" height="15" fill="#FFD700" opacity="0.7"/>
      <rect x="45" y="25" width="15" height="15" fill="#FFD700" opacity="0.7"/>
      <rect x="65" y="25" width="15" height="15" fill="#FFD700" opacity="0.7"/>
      <rect x="25" y="45" width="15" height="15" fill="#FFD700" opacity="0.7"/>
      <rect x="45" y="45" width="15" height="15" fill="#FFD700" opacity="0.7"/>
      <rect x="65" y="45" width="15" height="15" fill="#FFD700" opacity="0.7"/>
      <rect x="25" y="65" width="15" height="15" fill="#FFD700" opacity="0.7"/>
      <rect x="45" y="65" width="15" height="15" fill="#FFD700" opacity="0.7"/>
      <rect x="65" y="65" width="15" height="15" fill="#FFD700" opacity="0.7"/>
      <text x="50" y="90" text-anchor="middle" font-size="8" fill="white" font-weight="bold">CPU</text>
    </svg>""",
    
    "memory": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">
      <defs><linearGradient id="memGrad" x1="0%" y1="0%" x2="100%" y2="100%">
        <stop offset="0%" style="stop-color:#4ECDC4;stop-opacity:1" />
        <stop offset="100%" style="stop-color:#3DA9A0;stop-opacity:1" />
      </linearGradient></defs>
      <rect x="15" y="15" width="70" height="70" fill="url(#memGrad)" rx="3"/>
      <rect x="25" y="25" width="8" height="50" fill="#00D9FF" opacity="0.8"/>
      <rect x="38" y="25" width="8" height="50" fill="#00D9FF" opacity="0.8"/>
      <rect x="51" y="25" width="8" height="50" fill="#00D9FF" opacity="0.8"/>
      <rect x="64" y="25" width="8" height="50" fill="#00D9FF" opacity="0.8"/>
      <circle cx="50" cy="85" r="4" fill="white"/>
      <text x="50" y="95" text-anchor="middle" font-size="8" fill="white" font-weight="bold">RAM</text>
    </svg>""",
    
    "fan": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">
      <defs><linearGradient id="fanGrad" x1="0%" y1="0%" x2="100%" y2="100%">
        <stop offset="0%" style="stop-color:#95E1D3;stop-opacity:1" />
        <stop offset="100%" style="stop-color:#5FC5B5;stop-opacity:1" />
      </linearGradient></defs>
      <circle cx="50" cy="50" r="40" fill="url(#fanGrad)"/>
      <circle cx="50" cy="50" r="30" fill="#061018" opacity="0.3"/>
      <polygon points="50,20 65,40 50,35" fill="#00D9FF"/>
      <polygon points="80,50 60,65 65,50" fill="#00D9FF"/>
      <polygon points="50,80 35,60 50,65" fill="#00D9FF"/>
      <polygon points="20,50 40,35 35,50" fill="#00D9FF"/>
      <circle cx="50" cy="50" r="8" fill="white"/>
      <text x="50" y="92" text-anchor="middle" font-size="8" fill="white" font-weight="bold">FAN</text>
    </svg>""",
    
    "power": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">
      <defs><linearGradient id="pwrGrad" x1="0%" y1="0%" x2="100%" y2="100%">
        <stop offset="0%" style="stop-color:#FFE66D;stop-opacity:1" />
        <stop offset="100%" style="stop-color:#FFC700;stop-opacity:1" />
      </linearGradient></defs>
      <rect x="12" y="20" width="76" height="60" fill="url(#pwrGrad)" rx="4"/>
      <rect x="20" y="28" width="15" height="15" fill="#FF6B6B" opacity="0.8"/>
      <rect x="40" y="28" width="15" height="15" fill="#FF6B6B" opacity="0.8"/>
      <rect x="60" y="28" width="15" height="15" fill="#FF6B6B" opacity="0.8"/>
      <circle cx="27.5" cy="60" r="4" fill="#00D9FF"/>
      <circle cx="47.5" cy="60" r="4" fill="#00D9FF"/>
      <circle cx="67.5" cy="60" r="4" fill="#00D9FF"/>
      <text x="50" y="92" text-anchor="middle" font-size="8" fill="white" font-weight="bold">PSU</text>
    </svg>""",
    
    "thermal": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">
      <defs><linearGradient id="thermGrad" x1="0%" y1="100%" x2="0%" y2="0%">
        <stop offset="0%" style="stop-color:#A8E6CF;stop-opacity:1" />
        <stop offset="50%" style="stop-color:#FFE66D;stop-opacity:1" />
        <stop offset="100%" style="stop-color:#FF6B6B;stop-opacity:1" />
      </linearGradient></defs>
      <rect x="40" y="15" width="20" height="65" fill="url(#thermGrad)" rx="10"/>
      <circle cx="50" cy="85" r="8" fill="url(#thermGrad)"/>
      <rect x="43" y="45" width="14" height="20" fill="white" opacity="0.6"/>
      <text x="50" y="92" text-anchor="middle" font-size="8" fill="white" font-weight="bold">TEMP</text>
    </svg>"""
}

def get_component_svg(component_type: str) -> str:
    """Get SVG representation of a component."""
    return COMPONENT_SVGS.get(component_type, COMPONENT_SVGS.get("processor", ""))

# Cisco Catalyst stencil data (simplified SVG representation)
CISCO_C9200L_STENCIL = {
    "name": "Catalyst 9200L",
    "dimensions": {"width": 440, "height": 88, "depth": 310},
    "ports": {
        "gigabit": 24,
        "ten_gigabit": 4,
        "mgmt": 1,
        "console": 1
    },
    "power_consumption": "300W",
    "internal_components": {
        "cpu": {"name": "Intel Atom", "position": "center-left", "width": 45, "height": 45},
        "memory": {"name": "8GB DRAM + 32GB Flash", "position": "center", "width": 40, "height": 40},
        "fans": {"name": "3x Cooling Fans", "position": "center-right", "width": 50, "height": 40},
        "psu": {"name": "Dual PSU (N+1)", "position": "bottom", "width": 200, "height": 25},
        "thermal": {"name": "Multi-zone Sensors", "position": "top", "width": 200, "height": 15}
    }
}

HUAWEI_S5735L_STENCIL = {
    "name": "S5735L-24P4X-A1",
    "dimensions": {"width": 440, "height": 88, "depth": 280},
    "ports": {
        "gigabit": 24,
        "ten_gigabit": 4,
        "mgmt": 1,
        "console": 1
    },
    "power_consumption": "350W",
    "internal_components": {
        "cpu": {"name": "Huawei Processor", "position": "center-left", "width": 45, "height": 45},
        "memory": {"name": "4GB DRAM + 16GB Storage", "position": "center", "width": 40, "height": 40},
        "fans": {"name": "2x Smart Fans", "position": "center-right", "width": 50, "height": 40},
        "psu": {"name": "Dual PSU", "position": "bottom", "width": 200, "height": 25},
        "thermal": {"name": "Smart Cooling", "position": "top", "width": 200, "height": 15}
    }
}

def get_stencil_data(vendor: str) -> dict:
    """Get stencil data for a vendor."""
    if vendor.lower() == "cisco":
        return CISCO_C9200L_STENCIL
    elif vendor.lower() == "huawei":
        return HUAWEI_S5735L_STENCIL
    return {}
