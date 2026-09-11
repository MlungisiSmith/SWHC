"""Configuration templates for network switches."""

CONFIG_TEMPLATES = {
    "cisco_ios": {
        "base_vlan": {
            "name": "Base VLAN Configuration",
            "description": "Create VLANs for network segmentation",
            "purpose": "Network Segmentation",
            "template": """configure terminal
vlan {vlan_id}
  name {vlan_name}
  description {vlan_description}
exit
end
""",
            "parameters": {
                "vlan_id": {"type": "int", "min": 1, "max": 4094, "default": 10, "label": "VLAN ID"},
                "vlan_name": {"type": "string", "default": "VLAN10", "label": "VLAN Name"},
                "vlan_description": {"type": "string", "default": "Production VLAN", "label": "Description"},
            }
        },
        "port_config": {
            "name": "Port Configuration",
            "description": "Configure access or trunk ports",
            "purpose": "Port Management",
            "template": """configure terminal
interface {interface}
  description {description}
  switchport mode {mode}
  switchport access vlan {vlan_id}
  no shutdown
exit
end
""",
            "parameters": {
                "interface": {"type": "string", "default": "GigabitEthernet0/0/1", "label": "Interface"},
                "description": {"type": "string", "default": "Access Port", "label": "Description"},
                "mode": {"type": "select", "options": ["access", "trunk"], "default": "access", "label": "Mode"},
                "vlan_id": {"type": "int", "min": 1, "max": 4094, "default": 10, "label": "VLAN ID"},
            }
        },
        "stp_config": {
            "name": "Spanning Tree Configuration",
            "description": "Configure Spanning Tree Protocol",
            "purpose": "Loop Prevention",
            "template": """configure terminal
spanning-tree mode rapid-pvst
spanning-tree vlan {vlan_id} priority {priority}
end
""",
            "parameters": {
                "vlan_id": {"type": "int", "min": 1, "max": 4094, "default": 1, "label": "VLAN ID"},
                "priority": {"type": "select", "options": ["0", "4096", "8192", "12288", "16384", "20480", "24576", "28672"], "default": "24576", "label": "Priority"},
            }
        },
        "snmp_config": {
            "name": "SNMP Configuration",
            "description": "Configure SNMP for monitoring",
            "purpose": "Device Monitoring",
            "template": """configure terminal
snmp-server community {community_string} RO
snmp-server trap-source {trap_source}
snmp-server enable traps snmp
end
""",
            "parameters": {
                "community_string": {"type": "string", "default": "public", "label": "Community String"},
                "trap_source": {"type": "string", "default": "0.0.0.0", "label": "Trap Source IP"},
            }
        },
        "acl_config": {
            "name": "Access Control List",
            "description": "Configure basic ACL",
            "purpose": "Traffic Control",
            "template": """configure terminal
ip access-list standard {acl_name}
  permit {source_ip} {wildcard}
  deny any
exit
end
""",
            "parameters": {
                "acl_name": {"type": "string", "default": "ALLOW_SUBNET", "label": "ACL Name"},
                "source_ip": {"type": "string", "default": "10.0.0.0", "label": "Source IP"},
                "wildcard": {"type": "string", "default": "0.0.0.255", "label": "Wildcard Mask"},
            }
        }
    },
    "huawei": {
        "base_vlan": {
            "name": "Base VLAN Configuration",
            "description": "Create VLANs for network segmentation",
            "purpose": "Network Segmentation",
            "template": """system-view
vlan {vlan_id}
  name {vlan_name}
  description {vlan_description}
quit
return
""",
            "parameters": {
                "vlan_id": {"type": "int", "min": 1, "max": 4094, "default": 10, "label": "VLAN ID"},
                "vlan_name": {"type": "string", "default": "VLAN10", "label": "VLAN Name"},
                "vlan_description": {"type": "string", "default": "Production VLAN", "label": "Description"},
            }
        },
        "port_config": {
            "name": "Port Configuration",
            "description": "Configure access or trunk ports",
            "purpose": "Port Management",
            "template": """system-view
interface {interface}
  description {description}
  port link-type {mode}
  port default vlan {vlan_id}
  undo shutdown
quit
return
""",
            "parameters": {
                "interface": {"type": "string", "default": "GigabitEthernet0/0/1", "label": "Interface"},
                "description": {"type": "string", "default": "Access Port", "label": "Description"},
                "mode": {"type": "select", "options": ["access", "trunk"], "default": "access", "label": "Mode"},
                "vlan_id": {"type": "int", "min": 1, "max": 4094, "default": 10, "label": "VLAN ID"},
            }
        },
        "stp_config": {
            "name": "Spanning Tree Configuration",
            "description": "Configure STP for loop prevention",
            "purpose": "Loop Prevention",
            "template": """system-view
stp mode rstp
stp priority {priority}
quit
return
""",
            "parameters": {
                "priority": {"type": "select", "options": ["0", "4096", "8192", "12288", "16384", "20480", "24576"], "default": "20480", "label": "Priority"},
            }
        },
        "snmp_config": {
            "name": "SNMP Configuration",
            "description": "Configure SNMP for monitoring",
            "purpose": "Device Monitoring",
            "template": """system-view
snmp-agent community read {community_string}
snmp-agent trapsource {trap_source}
snmp-agent trap enable
quit
return
""",
            "parameters": {
                "community_string": {"type": "string", "default": "public", "label": "Community String"},
                "trap_source": {"type": "string", "default": "0.0.0.0", "label": "Trap Source IP"},
            }
        }
    }
}


def get_templates_for_vendor(vendor: str) -> dict:
    """Get all templates for a vendor."""
    return CONFIG_TEMPLATES.get(vendor, {})


def get_template(vendor: str, template_name: str) -> dict:
    """Get a specific template."""
    templates = get_templates_for_vendor(vendor)
    return templates.get(template_name)


def render_template(vendor: str, template_name: str, parameters: dict) -> str:
    """Render a template with parameters."""
    template = get_template(vendor, template_name)
    if not template:
        return None
    
    config_text = template["template"]
    for key, value in parameters.items():
        config_text = config_text.replace(f"{{{key}}}", str(value))
    
    return config_text.strip()


def get_template_list(vendor: str) -> list:
    """Get list of available templates for a vendor."""
    templates = get_templates_for_vendor(vendor)
    return [
        {
            "name": name,
            "label": info["name"],
            "description": info["description"],
            "purpose": info["purpose"],
        }
        for name, info in templates.items()
    ]
