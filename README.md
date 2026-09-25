# Route 53 Clone

A Route 53-inspired DNS management console I built for this assignment with Next.js, FastAPI, and SQLite. It manages hosted zones and DNS records through an AWS-console-style UI backed by a real REST API and a file-based database. It stores DNS configuration data only; it does not perform actual DNS resolution.

## Demo

Live demo: https://frontend-btfwf41jz-ishvajeetsingh.vercel.app
API docs: https://route53-clone-production-5b4c.up.railway.app/api/docs

## What works

- Mock login/logout with a persistent browser session
- Hosted zone create, view, edit, delete
- Hosted zone search and pagination
- DNS record create, view, edit, delete per zone
- Record search, type filter, and pagination
- A, AAAA, CNAME, TXT, MX, NS, PTR, SRV, and CAA records (SOA is also present as a system record)
- New zones automatically get apex NS and SOA records
- Validation that adapts to the record type
- Delete confirmations and success/error notifications
- SQLite persistence across backend restarts
- Route 53-style console layout: dark header, service sidebar, dense tables, breadcrumbs

## Screenshots

- Dashboard: `screenshots/dashboard.png` (to be added)
- Hosted zones: `screenshots/hosted-zones.png` (to be added)
- Zone detail with records: `screenshots/records.png` (to be added)
- Create record dialog: `screenshots/create-record.png` (to be added)

## Tech stack

Frontend:

- Next.js 14 (App Router), React 18, TypeScript

Backend:

- FastAPI, SQLAlchemy, Pydantic (v2), Uvicorn

Database:

- SQLite (file-based, path configurable)

Testing:

- pytest with FastAPI TestClient (backend)
- ESLint, `tsc --noEmit`, and `next build` (frontend)

## Project structure

```
route53-clone/
  README.md
  backend/
    requirements.txt
    requirements-dev.txt
    .env.example
    app/
      main.py            # app setup, CORS, router wiring, seed on startup
      config.py          # env-based settings
      database.py        # engine, session, Base
      models/dns.py      # HostedZone, DNSRecord tables
      schemas/dns.py     # Pydantic models + DNS validation
      routers/
        auth.py          # mock login/logout/session
        hosted_zones.py  # zone CRUD, search, pagination
        records.py       # record CRUD scoped to a zone
        stats.py         # account summary for the dashboard
      services/
        auth.py          # in-memory token sessions
        seed.py          # demo zone on first run
        validation.py    # shared value validation
    tests/               # pytest suite (isolated test database)
  frontend/
    .env.example
    app/
      login/             # sign-in page
      dashboard/         # landing page with live counts
      hosted-zones/      # zone list
      hosted-zones/[id]/ # zone detail + records
      traffic-policies/ health-checks/ resolver/ profiles/  # placeholders
    components/          # AppShell, modals, toasts, pagination
    lib/                 # API client, auth context, formatters
    types/               # shared TypeScript types
```

## How it works

The browser talks to the Next.js frontend, which calls the FastAPI REST API, which reads and writes SQLite through SQLAlchemy. The frontend keeps no hardcoded zone or record data; everything on screen comes from the API.

Creating a hosted zone also creates its apex NS and SOA records, the same way Route 53 starts every zone with them. Deleting a hosted zone deletes all of its records through a foreign-key cascade, and the delete dialog says so explicitly.

## Database

Two tables:

- **HostedZone** — `id` (Route 53-style `Z...` string), `name`, `description`, `type` (Public/Private), `created_at`, `updated_at`.
- **DNSRecord** — `id`, `zone_id` (FK to HostedZone with `ON DELETE CASCADE`), `name`, `type`, `values` (JSON list), `ttl`, `routing_policy`, `description`, `created_at`, `updated_at`.

One zone has many records. Record counts shown in the UI are computed per zone. The demo zone is seeded only when the database is completely empty, so deleting it does not bring it back on restart.

## API

Interactive docs are served at `/api/docs`. All endpoints except login, logout, and health require a `Bearer` token from the mock login.

| Method | Endpoint | Purpose |
| ------ | -------- | ------- |
| POST | `/api/auth/login` | Mock login, returns token + user |
| POST | `/api/auth/logout` | Invalidate the token |
| GET | `/api/auth/me` | Current session |
| GET | `/api/health` | Health check |
| GET | `/api/stats/summary` | Zone and record counts for the dashboard |
| GET | `/api/hosted-zones` | List/search zones (`q`, `page`, `page_size`) |
| POST | `/api/hosted-zones` | Create a zone (also creates NS + SOA) |
| GET | `/api/hosted-zones/{zone_id}` | Zone detail with record count |
| PATCH | `/api/hosted-zones/{zone_id}` | Edit description/type |
| DELETE | `/api/hosted-zones/{zone_id}` | Delete zone and its records |
| GET | `/api/hosted-zones/{zone_id}/records` | List/search records (`q`, `record_type`, `page`, `page_size`) |
| POST | `/api/hosted-zones/{zone_id}/records` | Create a record |
| GET | `/api/hosted-zones/{zone_id}/records/{record_id}` | Single record |
| PATCH | `/api/hosted-zones/{zone_id}/records/{record_id}` | Edit a record |
| DELETE | `/api/hosted-zones/{zone_id}/records/{record_id}` | Delete a record (apex NS/SOA return 400) |

## DNS record validation

The backend is authoritative for validation; the frontend form shows per-type placeholders and hints. A few examples of what the backend enforces:

- A -> valid IPv4 address (checked with the `ipaddress` module)
- AAAA -> valid IPv6 address
- MX -> `priority mail-host`, e.g. `10 mail.example.com`
- SRV -> `priority weight port target`, e.g. `10 5 443 sip.example.com`
- CAA -> `flags tag value`, e.g. `0 issue "letsencrypt.org"`

CNAME/NS/PTR values must be hostnames, CNAME is limited to a single value, TXT values are length-checked, and record names accept apex (`@`), wildcards, and service labels like `_sip._tcp`.

## Running locally

### Backend

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

API at http://localhost:8000, docs at http://localhost:8000/api/docs.

### Frontend

```bash
cd frontend
npm install
cp .env.example .env.local
npm run dev
```

App at http://localhost:3000. Sign in with any username and password.

## Environment variables

| Variable | Where | Purpose |
| -------- | ----- | ------- |
| `DATABASE_URL` | backend `.env` | SQLite location, e.g. `sqlite:///./route53.db`. An absolute path works for persistent volumes. |
| `ALLOWED_ORIGINS` | backend `.env` | Comma-separated CORS origins for the frontend. |
| `NEXT_PUBLIC_API_URL` | frontend `.env.local` | Base URL of the backend API. |

No secrets are needed to run this project.

## Tests

Backend (62 tests, isolated test database, dev database untouched):

```bash
cd backend
pip install -r requirements-dev.txt
python -m pytest tests -q
```

Frontend:

```bash
cd frontend
npm run lint
npx tsc --noEmit
npm run build
```

Current status: 62 backend tests passing, lint clean, TypeScript check clean, production build succeeds. I also clicked through login, zone CRUD, record CRUD, validation errors, search/filter, and persistence manually in the browser; there is no automated browser suite.

## A few implementation decisions

- For this assignment, I kept authentication intentionally simple: mock login, token in `localStorage`, verified against `/api/auth/me` on load. No real credentials are checked or stored.
- I store timestamps in UTC and convert them to the browser's local timezone for display. The API always serializes datetimes with an explicit `+00:00` offset.
- Creating a hosted zone also creates its apex NS and SOA records. These records can be edited but not deleted from the UI.
- A hosted zone's `updated_at` also advances when one of its records changes, since the detail page labels it "Last updated".
- Backend validation is authoritative even though the frontend provides form guidance, so bad input is rejected with a 422 even if sent directly to the API.

## Deployment

The frontend (Vercel) and backend (Railway, SQLite on a persistent volume at `DATABASE_URL=sqlite:////data/route53.db`) deploy separately: Next.js to any Node host, FastAPI to any Python host with `uvicorn app.main:app --host 0.0.0.0 --port $PORT`. Because the assignment requires SQLite, the backend host needs a persistent disk or volume, with `DATABASE_URL` pointed at it. Point `NEXT_PUBLIC_API_URL` at the backend URL and add the frontend origin to `ALLOWED_ORIGINS`. Live URLs: https://frontend-btfwf41jz-ishvajeetsingh.vercel.app, docs: https://route53-clone-production-5b4c.up.railway.app/api/docs. Repository: https://github.com/Ishvajeetsingh/route53-clone.

## Limitations

- No real DNS resolution; this is a management console for DNS data.
- Authentication is intentionally mocked, not IAM.
- Traffic Policies, Health Checks, Resolver, and Profiles are navigation placeholders.
- Nothing here connects to AWS APIs.
