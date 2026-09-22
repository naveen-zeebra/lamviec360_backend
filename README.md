# Job Portal Multi-Gateway API Platform (`new-api-setup`)

A high-performance, modular Python backend platform featuring **three dedicated FastAPI gateway servers** sharing a unified SQLAlchemy core, Pydantic schemas, and security infrastructure.

---

## 🏛️ Architecture Overview

```
                      ┌─────────────────────────────────┐
                      │          Shared Layer           │
                      │  SQLAlchemy 2.0 / Pydantic /    │
                      │  JWT / Bcrypt / SQLite/Postgres │
                      └──────────────┬──────────────────┘
                                     │
           ┌─────────────────────────┼─────────────────────────┐
           ▼                         ▼                         ▼
┌─────────────────────┐   ┌─────────────────────┐   ┌─────────────────────┐
│ Job Seeker Gateway  │   │   Company Gateway   │   │ Super Admin Gateway │
│     Port: 8001      │   │     Port: 8002      │   │     Port: 8003      │
│                     │   │                     │   │                     │
│ • Candidate Auth    │   │ • Recruiter Auth    │   │ • Super Admin Auth  │
│ • Resume & Profile  │   │ • Company Profile   │   │ • User & Role RBAC  │
│ • Job Discovery     │   │ • Job Postings      │   │ • Company Moderation│
│ • Applications      │   │ • ATS Pipeline      │   │ • Job Approval      │
│ • Saved Jobs        │   │ • Candidate Review  │   │ • Audit Logs & Stats│
└─────────────────────┘   └─────────────────────┘   └─────────────────────┘
```

---

## 🚀 Port & Documentation Directory

| Service | Port | Base URL | Interactive Docs (Swagger UI) |
| :--- | :--- | :--- | :--- |
| **Job Seeker Gateway** | `8001` | `http://localhost:8001/api/v1/jobseeker` | [http://localhost:8001/docs](http://localhost:8001/docs) |
| **Company Gateway** | `8002` | `http://localhost:8002/api/v1/company` | [http://localhost:8002/docs](http://localhost:8002/docs) |
| **Super Admin Gateway** | `8003` | `http://localhost:8003/api/v1/admin` | [http://localhost:8003/docs](http://localhost:8003/docs) |

---

## 🔑 Default Seeded Accounts

The database automatically seeds the following accounts on first startup:

| Account Type | Email | Password | Role / Capabilities |
| :--- | :--- | :--- | :--- |
| **Super Administrator** | `admin@jobportal.com` | `Admin@123` | Full access, RBAC, Moderation, Logs |
| **Company Recruiter** | `company@techcorp.com` | `Company@123` | TechCorp HR, Job Postings, ATS Pipeline |
| **Job Seeker** | `seeker@example.com` | `Seeker@123` | Candidate Profile, Job Search, Applications |

---

## 📦 Installation & Quickstart

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Database Setup (SQLite vs PostgreSQL)

By default, the project uses **SQLite** (`sqlite:///./jobportal.db`) for instant zero-configuration local execution.

To switch to **PostgreSQL**:
1. Edit [.env](file:///d:/Project/BolierPlate%20Setup/Reactjs/new-api-setup/.env):
   ```ini
   DB_ENGINE=postgres
   POSTGRES_USER=postgres
   POSTGRES_PASSWORD=your_password
   POSTGRES_HOST=localhost
   POSTGRES_PORT=5432
   POSTGRES_DB=jobportal_db
   
   # Or set direct connection string:
   DATABASE_URL=postgresql://postgres:your_password@localhost:5432/jobportal_db
   ```
2. (Optional) Auto-create the database if it doesn't exist yet:
   ```bash
   python create_postgres_db.py
   ```

### 3. Run All 3 Gateways Concurrently
```bash
python run.py
```

### 3. Or Run Gateways Individually
```bash
# Job Seeker Gateway (Port 8001)
python run_jobseeker.py

# Company Gateway (Port 8002)
python run_company.py

# Super Admin Gateway (Port 8003)
python run_admin.py
```

### 4. Production Process Manager (PM2)
```bash
pm2 start ecosystem.config.js
```

---

## 📂 Directory Structure

```
new-api-setup/
├── .env                     # Local environment settings
├── .env.example             # Template environment variables
├── requirements.txt         # Project dependencies
├── run.py                   # Multi-gateway concurrent orchestrator
├── run_jobseeker.py         # Job Seeker Gateway runner (port 8001)
├── run_company.py           # Company Gateway runner (port 8002)
├── run_admin.py             # Super Admin Gateway runner (port 8003)
├── ecosystem.config.js      # PM2 configuration
│
├── shared/                  # Common domain core
│   ├── database/            # Engine, session, Base, seeder
│   │   ├── base.py          # TimestampMixin, SoftDeleteMixin
│   │   ├── session.py       # SessionLocal, get_db, init_db
│   │   └── seed.py          # Auto-seeder
│   ├── models/              # SQLAlchemy 2.0 models
│   │   ├── user.py          # Unified User model
│   │   ├── role.py          # Roles, Permissions, UserRoles
│   │   ├── company.py       # CompanyProfile
│   │   ├── jobseeker.py     # JobSeekerProfile, SavedJob
│   │   ├── job.py           # JobPosting
│   │   ├── application.py   # JobApplication (ATS)
│   │   └── audit_log.py     # AuditLog
│   ├── schemas/             # Pydantic schemas
│   │   ├── auth.py          # Auth requests & responses
│   │   ├── user.py          # User schemas
│   │   ├── role.py          # Role & permission schemas
│   │   ├── company.py       # Company schemas
│   │   ├── jobseeker.py     # Job Seeker schemas
│   │   ├── job.py           # Job posting schemas
│   │   └── application.py   # Application schemas
│   └── utils/               # JWT, password hashing, rate limiting, logging
│
└── services/                # Dedicated API Gateways
    ├── jobseeker_service/   # Candidate gateway (8001)
    │   └── app/
    │       ├── main.py
    │       ├── routes_manager.py
    │       └── api/ (auth, profile, jobs, applications)
    ├── company_service/     # Employer gateway (8002)
    │   └── app/
    │       ├── main.py
    │       ├── routes_manager.py
    │       └── api/ (auth, profile, jobs, applicants)
    └── admin_service/       # Platform moderation gateway (8003)
        └── app/
            ├── main.py
            ├── routes_manager.py
            └── api/ (auth, dashboard, users, roles, companies, jobs, audit_logs)
```
