# LàmViệc360 - Python FastAPI Backend

FastAPI backend powering both the **LàmViệc360 Main Portal** (`lamviec360_7278_new`) and the **Super Admin Platform** (`Job-super-admin`).

## Features

- **Isolated Auth Pipelines**:
  - **Job Seeker Auth** (`/api/v1/auth/seeker`): Registration, email verification, login, Google SSO.
  - **Company / Employer Auth** (`/api/v1/auth/company`): Registration (pending approval), 2FA OTP login, employee invitation activation.
  - **Super Admin Auth** (`/api/v1/auth/admin`): Isolated login with strict platform-level role verification.
- **Tenant Management & Governance**:
  - Company approval, rejection with reasons, suspension, and reactivation.
  - Plan assignment (`Freemium`, `Professional`, `Enterprise`).
  - Quota enforcement on active job postings.
- **Job Board & Candidate Pipeline**:
  - Public job search and filtering.
  - Employer recruitment Kanban/stages (`Applied`, `Screening`, `Shortlisted`, `Interview Scheduled`, `Offer Sent`, `Hired`, `Rejected`).
  - Multi-round interview scheduling with video meeting links.
  - Seeker profile completeness tracking and CV storage.
- **Moderation & Audit**:
  - Automated keyword moderation queue for reported jobs and companies.
  - Platform audit trail logging administrative actions.
  - Compliance data retention purge for rejected candidates.

## Getting Started

### 1. Prerequisites
- Python 3.10+
- Virtual environment tool (`venv`)

### 2. Setup & Installation
```bash
# Navigate to backend directory
cd lamviec360_backend

# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Windows (PowerShell):
.\venv\Scripts\Activate.ps1
# On macOS / Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Database Migrations (Alembic)

Alembic manages schema migrations for both PostgreSQL and SQLite.

```bash
# Apply all pending migrations to head
alembic upgrade head

# Generate a new auto-detected migration after model changes
alembic revision --autogenerate -m "describe_changes"

# Check current migration revision
alembic current

# Check if there is any unmigrated schema drift
alembic check

# Rollback one migration
alembic downgrade -1
```

### 4. Run Development Server
```bash
uvicorn app.main:app --reload --port 8000
```

> **Note:** On startup, the server will automatically initialize the database schema and seed the initial Super Admin, plans, demo companies, jobs, and candidates.

### 5. Interactive Documentation (Swagger UI)
Open your browser to:
- **Swagger UI**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **ReDoc**: [http://localhost:8000/redoc](http://localhost:8000/redoc)


## Default Seed Accounts (for Testing)

| Role | Email | Password | 2FA Code (Dev) |
|---|---|---|---|
| **Super Admin** | `admin@lamviec360.vn` | `password123` | N/A |
| **Company Admin** (ABC Tech) | `lan.tran@abctech.vn` | `password123` | `123456` |
| **HR / Recruiter** (ABC Tech) | `huy.nguyen@abctech.vn` | `password123` | `123456` |
| **Pending Company Admin** | `hoa.le@vantix.vn` | `password123` | `123456` |
| **Job Seeker** | `minh.tran@example.com` | `password123` | `123456` |

## Running Automated Tests

```bash
pytest
```
