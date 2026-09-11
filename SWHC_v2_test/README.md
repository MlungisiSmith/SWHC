# SWHC Enterprise v2.0

Enterprise-grade Switch Health Check and Configuration Management System.

## Features

- **Async FastAPI** - Modern async/await architecture with high concurrency
- **Multi-vendor Support** - Cisco IOS and Huawei VRP
- **Real-time Health Monitoring** - CPU, Memory, Fans, Power, Temperature
- **Configuration Management** - Pre-built templates with parameter validation
- **Persistent Storage** - SQLite async database with audit logs
- **Redis Caching** - Performance optimization with async Redis support
- **Docker Ready** - Multi-stage builds, health checks, non-root user

## Quick Start

```bash
cd SWHC_v2_test
docker-compose up --build -d
```

Access:
- **API Docs**: http://localhost:8000/docs
- **Health**: http://localhost:8000/api/v1/health

## Architecture

```
SWHC_v2_test/
├── app/
│   ├── main.py                 # FastAPI app
│   ├── config.py               # Settings
│   ├── database.py             # SQLAlchemy async models
│   ├── api/v1/
│   │   ├── health.py           # Health endpoints
│   │   ├── switches.py         # Switch CRUD
│   │   └── config.py           # Configuration templates
│   ├── services/
│   │   ├── health_check.py     # Switch health collection
│   │   └── templates.py        # Template rendering
│   └── utils/
├── Dockerfile
├── docker-compose.yml
└── requirements.txt
```

## API Endpoints

### Health
- `GET /api/v1/health/` - Health check
- `GET /api/v1/health/ready` - Readiness check

### Switches
- `GET /api/v1/switches/` - List switches
- `POST /api/v1/switches/` - Register switch
- `POST /api/v1/switches/check-health` - Ad-hoc health check

### Configuration
- `GET /api/v1/config/templates?vendor=cisco` - List templates
- `POST /api/v1/config/preview` - Preview config
- `GET /api/v1/config/templates/{vendor}/{template_name}` - Template details

## Environment Variables

```
SWITCH_USERNAME=networks
SWITCH_PASSWORD=w00Lw0rTh$
SWITCH_ENABLE_SECRET=w00Lw0rTh$
DATABASE_URL=sqlite+aiosqlite:///./data/swch.db
REDIS_URL=redis://swhc-v2-redis:6379/0
SECRET_KEY=change-me-in-production
```

## Database Models

- **Switch** - Registered switches with metadata
- **HealthMetric** - Time-series health snapshots
- **ConfigAudit** - Configuration change audit trail

## Testing

```bash
# List templates
curl http://localhost:8000/api/v1/config/templates?vendor=cisco

# Check health
curl -X POST http://localhost:8000/api/v1/switches/check-health \
  -H "Content-Type: application/json" \
  -d '{"ip_address":"192.168.101.212","vendor":"cisco"}'

# Preview config
curl -X POST http://localhost:8000/api/v1/config/preview \
  -H "Content-Type: application/json" \
  -d '{
    "vendor":"cisco",
    "template":"base_vlan",
    "parameters":{"vlan_id":"100","vlan_name":"TEST","vlan_description":"Test VLAN"}
  }'
```

## Next Steps

1. Add web UI (React/Vue)
2. Implement configuration apply endpoint
3. Add Redis caching for health metrics
4. Setup Kubernetes deployment manifests
5. Add comprehensive logging and monitoring

## Version

2.0.0 - FastAPI + Async Architecture
