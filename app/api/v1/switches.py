"""Switch management endpoints."""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.database import get_db, Switch
from app.services.health_check import get_switch_health
from typing import Optional, List

router = APIRouter()


# --- Pydantic Models ---

class SwitchCreate(BaseModel):
    hostname: str
    ip_address: str
    vendor: str
    location: Optional[str] = None
    description: Optional[str] = None


class SwitchResponse(BaseModel):
    id: int
    hostname: str
    ip_address: str
    vendor: str
    status: str
    location: Optional[str]
    description: Optional[str]
    
    class Config:
        from_attributes = True


class HealthCheckRequest(BaseModel):
    ip_address: str
    vendor: str = "auto"


class HealthCheckResponse(BaseModel):
    hostname: str
    vendor: str
    status: str
    metrics: dict


# --- Endpoints ---

@router.get("/", response_model=List[SwitchResponse])
async def list_switches(db: AsyncSession = Depends(get_db)):
    """List all registered switches."""
    result = await db.execute(select(Switch).filter(Switch.is_active == True))
    switches = result.scalars().all()
    return switches


@router.post("/", response_model=SwitchResponse)
async def create_switch(switch: SwitchCreate, db: AsyncSession = Depends(get_db)):
    """Register a new switch."""
    new_switch = Switch(
        hostname=switch.hostname,
        ip_address=switch.ip_address,
        vendor=switch.vendor,
        location=switch.location,
        description=switch.description,
        status="offline"
    )
    db.add(new_switch)
    await db.commit()
    await db.refresh(new_switch)
    return new_switch


@router.get("/{switch_id}", response_model=SwitchResponse)
async def get_switch(switch_id: int, db: AsyncSession = Depends(get_db)):
    """Get switch details."""
    result = await db.execute(select(Switch).filter(Switch.id == switch_id))
    switch = result.scalars().first()
    if not switch:
        raise HTTPException(status_code=404, detail="Switch not found")
    return switch


@router.post("/check-health")
async def check_switch_health(request: HealthCheckRequest):
    """Perform ad-hoc health check on a switch."""
    metrics, identity, error = await get_switch_health(request.ip_address, request.vendor)
    
    if error:
        raise HTTPException(status_code=400, detail=error)
    
    return {
        "hostname": identity.get("hostname"),
        "vendor": identity.get("vendor"),
        "ip_address": identity.get("ip_address"),
        "status": "online" if metrics else "offline",
        "metrics": metrics
    }
