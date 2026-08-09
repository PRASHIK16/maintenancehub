# MaintenanceHub

**Smart Maintenance & Service Request Management Platform**

A production-quality, multi-tenant SaaS application for managing maintenance requests, assets, and preventive maintenance schedules across colleges, hostels, apartments, and office buildings.

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Django 5.2 LTS + Django REST Framework |
| Frontend | Django Templates + HTMX + Tailwind CSS v4 |
| Database | PostgreSQL (SQLite in dev) |
| Cache / Queue | Redis + Celery + Django Celery Beat |
| Real-time | Django Channels + WebSockets |
| Auth | Custom email-based User model, session auth |
| Static files | WhiteNoise (CompressedManifest in production) |
| Containers | Docker + Docker Compose + Nginx |

**No React, Next.js, Vue, TypeScript, or JavaScript frameworks.**

---

## Features

### Multi-tenant SaaS
- Single deployment supports multiple organizations (colleges, apartments, offices)
- All data isolated by `organization` foreign key
- Sub-domain or path-based routing ready

### Role-Based Access Control (RBAC)
| Role | Capabilities |
|------|-------------|
| Super Admin | Cross-org administration |
| Org Admin | Full org management, user management |
| Manager | Ticket assignment, analytics, team management |
| Maintenance Staff | Work on assigned tickets, update status |
| User / Resident | Submit tickets, track progress, rate service |

### Ticket Lifecycle (10 States)
```
submitted → triaged → assigned → in_progress → on_hold
         ↓                                        ↓
    verification_pending ← resolved ← on_hold   closed
         ↓
      closed / reopened
```

### SLA Management
- Per-organization SLA rules by priority (Critical/High/Medium/Low)
- Automatic response and resolution due date calculation
- SLA breach detection with dashboard alerts
- SLA compliance tracking in analytics

### Asset Registry
- Track physical assets (HVAC, elevators, generators, etc.)
- Status tracking: Active / Under Maintenance / Retired
- Warranty expiry alerts
- Maintenance history linkage

### Preventive Maintenance
- Scheduled maintenance plans with frequency (daily to annual)
- Checklist-driven work orders
- Team assignment and duration estimates
- Overdue detection

### Analytics Dashboard
- KPI cards: total/open/closed/overdue tickets, resolution rate, SLA rate
- Chart.js visualizations: daily trend, by-priority donut, by-status bar
- Staff performance table
- 7/30/90-day period filtering with HTMX partial refresh

### Real-time Features
- WebSocket-powered live notifications via Django Channels
- HTMX-driven partial updates (no page reloads for comments, assignments, filters)
- Live stat card refresh in admin dashboard

---

## Quick Start

### Prerequisites
- Python 3.11+
- PostgreSQL 15+ (or use SQLite for dev)
- Redis 7+ (optional in dev — LocMemCache fallback)

### 1. Clone and Setup

```bash
git clone https://github.com/PRASHIK16/maintenancehub.git
cd maintenancehub

python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements/development.txt
```

### 2. Configure Environment

```bash
cp .env.example .env
# Edit .env with your database credentials
```

Key variables:
```env
DEBUG=True
SECRET_KEY=your-secret-key-here
DATABASE_URL=postgres://user:pass@localhost:5432/maintenancehub
REDIS_URL=redis://localhost:6379/0
```

### 3. Initialize Database

```bash
python manage.py migrate
python manage.py createsuperuser
```

### 4. Load Demo Data

```bash
python manage.py seed_demo
```

Creates **Green Valley Apartments** with:
- **52 users**: 1 admin, 3 managers, 8 maintenance staff, 40 residents
- **100 tickets** across all status states with realistic data
- **24 locations**, **8 categories**, **3 teams**

Demo credentials:
| Role | Email | Password |
|------|-------|----------|
| Admin | `admin@greenvalley.in` | `Demo@1234` |
| Manager | `vikram.sharma@greenvalley.in` | `Demo@1234` |
| Staff | `ramesh.kumar@greenvalley.in` | `Demo@1234` |
| Resident | `arjun.verma@gmail.com` | `Demo@1234` |

### 5. Run Development Server

```bash
python manage.py runserver
```

Visit: http://localhost:8000

---

## Project Structure

```
maintenancehub/
├── apps/
│   ├── accounts/       # Custom User model, auth views, RBAC mixins
│   ├── analytics/      # KPI aggregation, Chart.js data APIs
│   ├── assets/         # Asset registry (CRUD + status)
│   ├── audit/          # Immutable AuditLog, middleware
│   ├── core/           # Health checks, landing page, template tags
│   ├── maintenance/    # Preventive maintenance schedules
│   ├── notifications/  # Real-time + email notifications
│   ├── organizations/  # Org, Location (hierarchy), Team, TeamMembership
│   └── tickets/        # Full ticket lifecycle + SLA + comments + attachments
├── config/
│   ├── settings/
│   │   ├── base.py         # Shared settings
│   │   ├── development.py  # Dev overrides (SQLite, LocMemCache)
│   │   └── production.py   # Production (PostgreSQL, Redis, WhiteNoise)
│   ├── urls.py
│   ├── wsgi.py
│   └── asgi.py
├── templates/          # All Django templates (no JS framework)
├── static/             # CSS, JS, images
├── docker-compose.yml
├── Dockerfile
└── manage.py
```

---

## REST API

Base URL: `/api/`

### Tickets
| Method | URL | Description |
|--------|-----|-------------|
| GET | `/api/tickets/` | List tickets (paginated, filterable) |
| POST | `/api/tickets/` | Create ticket |
| GET | `/api/tickets/<id>/` | Ticket detail |
| PATCH | `/api/tickets/<id>/` | Update ticket (staff+) |
| GET | `/api/tickets/<id>/comments/` | List comments |
| POST | `/api/tickets/<id>/comments/` | Add comment |

### Accounts
| Method | URL | Description |
|--------|-----|-------------|
| GET | `/api/accounts/me/` | My profile |
| PATCH | `/api/accounts/me/` | Update my profile |
| GET | `/api/accounts/users/` | List org users (manager+) |

Authentication: Django session (same cookie as web UI).

---

## Docker Deployment

```bash
# Build and start all services
docker-compose up --build -d

# Run migrations
docker-compose exec web python manage.py migrate

# Load demo data
docker-compose exec web python manage.py seed_demo

# Access app
open http://localhost
```

Services: `web` (Django/Gunicorn), `nginx`, `postgres`, `redis`, `celery`, `celery-beat`.

---

## Health Endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /health/` | Liveness — returns 200 if Django is running |
| `GET /health/ready/` | Readiness — checks DB + cache connectivity |

---

## License

MIT
