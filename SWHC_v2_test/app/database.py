from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy import Column, Integer, String, Text, DateTime, Float, Boolean, JSON
from datetime import datetime
from app.config import settings

Base = declarative_base()

# Database engine
engine = None


async def init_db():
    """Initialize database and create tables."""
    global engine
    engine = create_async_engine(
        settings.DATABASE_URL,
        echo=settings.APP_DEBUG,
        pool_pre_ping=True
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_db():
    """Get database session."""
    async_session = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    async with async_session() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


# --- Database Models ---

class Switch(Base):
    """Network Switch model."""
    __tablename__ = "switches"
    
    id = Column(Integer, primary_key=True)
    hostname = Column(String(255), unique=True, nullable=False)
    ip_address = Column(String(45), nullable=False)
    vendor = Column(String(50), nullable=False)  # cisco, huawei, etc.
    model = Column(String(255))
    status = Column(String(50), default="offline")  # online, offline, warning, critical
    location = Column(String(255))
    description = Column(Text)
    is_active = Column(Boolean, default=True)
    last_check = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)


class HealthMetric(Base):
    """Health metrics snapshot."""
    __tablename__ = "health_metrics"
    
    id = Column(Integer, primary_key=True)
    switch_id = Column(Integer, nullable=False)
    cpu_usage = Column(Float)
    memory_usage = Column(Float)
    fan_rpm = Column(Float)
    power_watts = Column(Float)
    temperature_celsius = Column(Float)
    overall_status = Column(String(50))  # healthy, warning, critical
    raw_data = Column(JSON)
    recorded_at = Column(DateTime, default=datetime.utcnow)


class ConfigAudit(Base):
    """Configuration change audit log."""
    __tablename__ = "config_audits"
    
    id = Column(Integer, primary_key=True)
    switch_id = Column(Integer, nullable=False)
    template_name = Column(String(255), nullable=False)
    parameters = Column(JSON)
    config_text = Column(Text)
    status = Column(String(50))  # pending, applied, failed
    applied_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
