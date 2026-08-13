# MaintenanceHub

**Multi-tenant Maintenance & Service Request Management Platform**

A production-ready SaaS application for managing maintenance requests, assets, and preventive maintenance schedules across colleges, hostels, apartments, and office buildings. Built with Django 5.2 LTS, deployed on Railway.

[![CI](https://github.com/PRASHIK16/maintenancehub/actions/workflows/ci.yml/badge.svg)](https://github.com/PRASHIK16/maintenancehub/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/Python-3.12-blue)](https://www.python.org/)
[![Django](https://img.shields.io/badge/Django-5.2_LTS-green)](https://www.djangoproject.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

🚀 **Live Demo:** https://web-production-78782.up.railway.app/

---

## Overview

MaintenanceHub eliminates paper-based and email-driven maintenance workflows. Residents or users submit tickets through a clean web interface; maintenance staff get notified in real time, track work on a Kanban board, and managers monitor SLA compliance through an analytics dashboard — all in one application.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Django 5.2 LTS + Django REST Framework 3.15 |
| Frontend | Django Templates + HTMX + Tailwind CSS v4 |
| Real-time | Django Channels 4.1 + WebSockets (Daphne ASGI) |
| Task Queue | Celery 5.4 + Django Celery Beat + Redis |
| Database | PostgreSQL (SQLite in local dev) |
| Cache | Redis / LocMemCache fallback |
| Auth | Custom email-based User model + session auth + JWT |
| Static Files | WhiteNoise 6.8 (compressed manifest in production) |
| Storage | Local filesystem (S3-ready via django-storages + boto3) |
| Deployment | Docker + Railway (Dockerfile builder) |
| CI | GitHub Actions (tests + migrations check + flake8) |

---

## Key Features

### Multi-Tenant Architecture
- Single deployment serves multiple organizations
- All data isolated by `organization` foreign key — zero cross-tenant data leakage
- Per-organization SLA rules, teams, locations, and user bases

### Role-Based Access Control (RBAC)

| Role | What they can do |
|---|---|
| **Super Admin** | Cross-organization administration |
| **Org Admin** | Full org management, user management |
| **Manager** | Ticket assignment, analytics, team management |
| **Maintenance Staff** | Work on assigned tickets, update status |
| **User / Resident** | Submit tickets, track progress, rate service |

### Ticket Lifecycle — 10 States
```
submitted → triaged → assigned → in_progress → on_hold
                                                   ↓
             closed ← verification_pending ← resolved
                              ↓
                          reopened
```

### SLA Management
- Per-organization rules by priority (Critical / High / Medium / Low)
- Automatic response and resolution due-date calculation at ticket creation
- SLA breach detection with dashboard alerts and overdue counters
- Full SLA compliance metrics in analytics

### Asset Registry
- Track physical assets (HVAC, elevators, generators, fixtures, etc.)
- Status tracking: Active / Under Maintenance / Retired
- Warranty expiry dates and maintenance history linked to tickets

### Preventive Maintenance
- Scheduled maintenance plans with configurable frequency (daily → annual)
- Checklist-driven work orders
- Team assignment, estimated duration, and overdue detection

### Analytics Dashboard
- KPI cards: total / open / closed / overdue tickets, resolution rate, SLA compliance %
- Charts: daily ticket trend (14-day), by-priority donut, by-status bar, per-location breakdown
- Staff performance table (assigned vs. resolved, overdue)
- HTMX partial refresh on period change (7 / 30 / 90 days or custom date range)
- CSV export for all analytics data

### Real-time & UX
- WebSocket-powered live notifications (Django Channels + Redis)
- HTMX-driven partial updates — no full page reloads for comments, assignments, or filters
- Kanban board view for ticket management
- Audit log: every state change and action recorded with actor + timestamp
- Responsive design (desktop + mobile)

---

## Project Structure

```
maintenancehub/
├── apps/
│   ├── accounts/           # Custom User model, auth views, RBAC mixins, JWT + session auth
│   ├── analytics/          # KPI aggregation, SLA reports, CSV export, Chart.js data APIs
│   ├── assets/             # Asset registry — CRUD + status + history
│   ├── audit/              # Immutable AuditLog model + audit middleware
│   ├── core/               # Health checks, landing page, WebSocket consumers, template tags
│   ├── maintenance/        # Preventive maintenance schedules + work orders
│   ├── notifications/      # Real-time + email notifications, Celery tasks
│   ├── organizations/      # Organization, Location hierarchy, Team, TeamMembership
│   └── tickets/            # Full ticket lifecycle, SLA, comments, attachments, REST API
├── config/
│   ├── settings/
│   │   ├── base.py         # Shared settings for all environments
│   │   ├── development.py  # Dev overrides (SQLite, LocMemCache, DEBUG=True)
│   │   ├── production.py   # Production (PostgreSQL, Redis, WhiteNoise, Sentry)
│   │   └── test.py         # CI test settings (in-memory DB + cache, eager Celery)
│   ├── asgi.py             # ASGI + WebSocket routing
│   ├── celery.py           # Celery app config
│   ├── urls.py             # Root URL configuration
│   └── wsgi.py             # WSGI fallback
├── templates/              # Django HTML templates (no JS framework)
│   ├── layout/             # app.html — main authenticated shell
│   ├── partials/           # sidebar.html, topbar.html
│   ├── tickets/            # Ticket list, detail, kanban, create, partials
│   ├── analytics/          # Analytics dashboard + HTMX stat partials
│   ├── dashboard/          # Role-specific dashboards (admin / staff / user)
│   ├── emails/             # Transactional email templates
│   └── errors/             # 403, 404, 500 error pages
├── static/
│   ├── css/main.css        # Hand-written design system (~3,700 lines, CSS custom properties)
│   └── js/app.js           # Sidebar toggle, HTMX helpers, WebSocket client
├── docker/                 # Nginx config for local Docker Compose setup
├── requirements/
│   ├── base.txt            # Core production dependencies
│   ├── production.txt      # Production-only additions (gunicorn)
│   └── development.txt     # Dev/test tools (debug-toolbar, factory-boy, pytest)
├── .github/workflows/      # GitHub Actions CI pipeline
├── Dockerfile              # Production image (python:3.12-slim)
├── docker-compose.yml      # Local development stack
├── railway.toml            # Railway deployment config
├── render.yaml             # Render.com deployment config
├── Procfile                # Heroku/Render process declarations
└── manage.py
```

---

## Local Development

### Prerequisites

- Python 3.12+
- PostgreSQL 15+ (or use SQLite — zero config)
- Redis 7+ (optional — falls back to LocMemCache)

### Setup

```bash
git clone https://github.com/PRASHIK16/maintenancehub.git
cd maintenancehub

python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\Activate.ps1
pip install -r requirements/development.txt

cp .env.example .env
# Edit .env — minimum required: SECRET_KEY and DATABASE_URL
```

Minimum `.env` for local dev:
```env
DEBUG=True
SECRET_KEY=any-long-random-string-for-dev
DATABASE_URL=sqlite:///db.sqlite3
```

```bash
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Visit: **http://localhost:8000**

### Load Demo Data

```bash
python manage.py seed_demo
```

Seeds **Green Valley Apartments** with realistic data:
- 52 users (1 admin · 3 managers · 8 staff · 40 residents)
- 100 tickets across all statuses
- 24 locations · 8 categories · 3 teams · SLA rules

| Role | Email | Password |
|---|---|---|
| Admin | `admin@greenvalley.in` | `Demo@1234` |
| Manager | `vikram.sharma@greenvalley.in` | `Demo@1234` |
| Staff | `ramesh.kumar@greenvalley.in` | `Demo@1234` |
| Resident | `arjun.verma@gmail.com` | `Demo@1234` |

### Docker Compose (full local stack)

```bash
docker-compose up --build -d
docker-compose exec web python manage.py migrate
docker-compose exec web python manage.py seed_demo
```

Services: Django (Daphne) · Nginx · PostgreSQL · Redis · Celery worker · Celery Beat

---

## REST API

Base URL: `/api/`  
Authentication: Django session cookie (same as web UI) or JWT.

### Tickets

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/tickets/` | List tickets (paginated, filterable by status/priority/assignee) |
| `POST` | `/api/tickets/` | Create ticket |
| `GET` | `/api/tickets/<id>/` | Ticket detail |
| `PATCH` | `/api/tickets/<id>/` | Update ticket (staff+) |
| `GET` | `/api/tickets/<id>/comments/` | List comments |
| `POST` | `/api/tickets/<id>/comments/` | Add comment |

### Accounts

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/accounts/me/` | Current user profile |
| `PATCH` | `/api/accounts/me/` | Update profile |
| `GET` | `/api/accounts/users/` | List org users (manager+) |

### JWT

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/token/` | Obtain JWT access + refresh token |
| `POST` | `/api/token/refresh/` | Refresh access token |

---

## Health Checks

| Endpoint | Description |
|---|---|
| `GET /health/` | Liveness — returns 200 if Django is responding |
| `GET /health/ready/` | Readiness — checks DB + cache connectivity |

---

## Deployment — Railway

The project ships with `railway.toml` for one-command Railway deploys.

### Environment Variables (set in Railway → Variables)

| Variable | Value |
|---|---|
| `DJANGO_SETTINGS_MODULE` | `config.settings.production` |
| `SECRET_KEY` | Long random string |
| `ALLOWED_HOSTS` | `your-app.up.railway.app` |
| `DATABASE_URL` | Auto-linked from Railway PostgreSQL |
| `REDIS_URL` | Auto-linked from Railway Redis |
| `CELERY_BROKER_URL` | Same as `REDIS_URL` |
| `DEBUG` | `false` |

The `startCommand` in `railway.toml` automatically runs `migrate` and `collectstatic` before starting Daphne:

```
python manage.py migrate --noinput
python manage.py collectstatic --noinput
daphne -b 0.0.0.0 -p $PORT config.asgi:application
```

### Render.com

`render.yaml` is included for Render Blueprint deployment. See environment variable requirements above — same set applies.

---

## CI / Continuous Integration

GitHub Actions runs on every push to `main` or `develop`:

- **Test job**: PostgreSQL + Redis services, migrations, full test suite
- **Lint job**: flake8 over `apps/` and `config/` (max line length 120, migrations excluded)
- **Migration check**: verifies no unapplied migrations exist

---

## Security Highlights

- `SECRET_KEY` never committed — always from environment variable
- `DEBUG=False` enforced in production settings
- CSRF protection enabled on all state-changing views
- `SECURE_SSL_REDIRECT`, HSTS, and secure cookie flags in production
- Rate limiting on login/register via `django-ratelimit`
- Organization-scoped querysets — users can only see their own org's data
- Immutable audit log records every action with actor identity
- Sentry error tracking (optional — set `SENTRY_DSN`)

---

## License

MIT — see [LICENSE](LICENSE).
