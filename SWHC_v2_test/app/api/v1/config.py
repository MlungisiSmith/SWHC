"""Configuration management endpoints."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Optional

from app.services.templates import (
    get_template_list, 
    render_template,
    get_template
)

router = APIRouter()


# --- Pydantic Models ---

class Template(BaseModel):
    name: str
    label: str
    description: str
    purpose: str


class ConfigPreviewRequest(BaseModel):
    vendor: str
    template: str
    parameters: Dict[str, str]


class ConfigPreviewResponse(BaseModel):
    config: str
    template: str
    vendor: str


# --- Endpoints ---

@router.get("/templates")
async def list_templates(vendor: str = "cisco") -> Dict:
    """Get available templates for a vendor."""
    if vendor not in ["cisco_ios", "cisco", "huawei"]:
        raise HTTPException(status_code=400, detail="Invalid vendor")
    
    # Normalize vendor name
    vendor_key = "cisco" if vendor in ["cisco", "cisco_ios"] else vendor
    
    templates = get_template_list(vendor_key)
    return {
        "vendor": vendor_key,
        "templates": templates,
        "count": len(templates)
    }


@router.post("/preview", response_model=ConfigPreviewResponse)
async def preview_configuration(request: ConfigPreviewRequest):
    """Preview configuration without applying it."""
    # Validate vendor
    if request.vendor not in ["cisco", "huawei"]:
        raise HTTPException(status_code=400, detail="Invalid vendor")
    
    # Validate template exists
    template = get_template(request.vendor, request.template)
    if not template:
        raise HTTPException(status_code=400, detail="Template not found")
    
    # Render template
    config = render_template(request.vendor, request.template, request.parameters)
    if not config:
        raise HTTPException(status_code=400, detail="Failed to render template")
    
    return {
        "config": config,
        "template": request.template,
        "vendor": request.vendor
    }


@router.get("/templates/{vendor}/{template_name}")
async def get_template_details(vendor: str, template_name: str):
    """Get detailed information about a template."""
    if vendor not in ["cisco", "huawei"]:
        raise HTTPException(status_code=400, detail="Invalid vendor")
    
    template = get_template(vendor, template_name)
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    
    return {
        "name": template_name,
        "label": template.get("name"),
        "description": template.get("description"),
        "purpose": template.get("purpose"),
        "parameters": template.get("parameters"),
        "template": template.get("template")
    }
