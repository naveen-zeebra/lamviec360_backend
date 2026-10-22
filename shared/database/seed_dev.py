import sys
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Ensure UTF-8 output on Windows terminals
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Ensure backend root is in sys.path
SCRIPT_DIR = Path(__file__).resolve().parent
BACKEND_ROOT = SCRIPT_DIR.parent.parent
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from sqlalchemy.orm import Session
from shared.database.session import SessionLocal, init_db
from shared.models import (
    Role,
    RolePermission,
    User,
    CompanyProfile,
    JobSeekerProfile,
    JobPosting,
    JobApplication,
    AdminUser,
    AdminRole,
    AdminRolePermission,
    CompanyUser,
    CompanyInvitation,
)
from shared.utils.password import hash_password
from shared.utils.logger import get_logger

logger = get_logger("dev_seeder")

MODULES = ["DASHBOARD", "USERS", "ROLES", "COMPANIES", "JOBSEEKERS", "JOBS", "APPLICATIONS", "AUDIT_LOGS"]

ADMIN_MODULES = [
    "DASHBOARD", "ANALYTICS", "TENANTS", "USERS", "COMMERCIAL",
    "GOVERNANCE", "CONFIGURATION", "ADMIN_MANAGEMENT", "ACCOUNT"
]

DEFAULT_REJECTION_TEMPLATES = [
    {
        "id": "RT-1",
        "title": "Experience Mismatch",
        "body": "Thank you for your interest in our company. After careful review, we have decided to move forward with candidates whose specific experience more closely aligns with our current requirements.",
    },
    {
        "id": "RT-2",
        "title": "Position Filled",
        "body": "Thank you for taking the time to interview with us. This position has now been filled. We were very impressed by your background and would like to stay connected for future opportunities.",
    },
    {
        "id": "RT-3",
        "title": "Skills Alignment",
        "body": "We appreciate your application. For this particular role, we are prioritizing candidates with deeper hands-on expertise in the primary tech stack specified in the job description.",
    },
]

def make_tenant_settings(company_name: str) -> str:
    return json.dumps({
        "notifications": {
            "newApplications": True,
            "interviewReminders": True,
            "teamActivity": True,
            "billing": True,
            "marketing": False,
        },
        "security": {"twoFactor": False},
        "pipeline": {
            "autoRejectEmail": True,
            "delayRejectionEmail": False,
            "rejectionTemplates": DEFAULT_REJECTION_TEMPLATES,
        },
        "privacy": {
            "contactVisibility": "always",
            "maskEmail": False,
            "maskPhone": False,
        },
        "retention": {
            "candidateDataMonths": 12,
            "autoPurge": False,
            "purgeRejectedMonths": 6,
        },
    })


def seed_roles_and_permissions(db: Session):
    roles_data = [
        ("Super Administrator", "super_admin", "Complete platform superuser access", True),
        ("Platform Administrator", "admin", "Platform administrator with moderation rights", False),
        ("Company Recruiter", "company", "Employer account for posting jobs and hiring", True),
        ("Job Seeker", "jobseeker", "Candidate account for finding and applying to jobs", True),
    ]

    role_map = {}
    for name, code, desc, is_sys in roles_data:
        role = db.query(Role).filter_by(code=code).first()
        if not role:
            role = Role(name=name, code=code, description=desc, is_system=is_sys)
            db.add(role)
            db.flush()
        role_map[code] = role

    for code, role in role_map.items():
        existing_modules = {p.module_key for p in role.permissions}
        for mod in MODULES:
            if mod not in existing_modules:
                if code == "super_admin":
                    perm = RolePermission(role_id=role.id, module_key=mod, can_view=True, can_create=True, can_edit=True, can_delete=True)
                elif code == "admin":
                    perm = RolePermission(role_id=role.id, module_key=mod, can_view=True, can_create=True, can_edit=True, can_delete=(mod in ["JOBS", "COMPANIES"]))
                elif code == "company":
                    can_v = mod in ["DASHBOARD", "JOBS", "APPLICATIONS"]
                    can_c = mod in ["JOBS"]
                    can_e = mod in ["JOBS", "APPLICATIONS"]
                    perm = RolePermission(role_id=role.id, module_key=mod, can_view=can_v, can_create=can_c, can_edit=can_e, can_delete=(mod == "JOBS"))
                else:  # jobseeker
                    can_v = mod in ["JOBS", "APPLICATIONS"]
                    can_c = mod in ["APPLICATIONS"]
                    perm = RolePermission(role_id=role.id, module_key=mod, can_view=can_v, can_create=can_c, can_edit=False, can_delete=False)
                db.add(perm)
    db.flush()
    return role_map


def seed_admin_roles_and_permissions(db: Session):
    admin_roles_data = [
        ("Super Admin", "super_admin", "Complete platform root superuser access with all privileges"),
        ("Operations Admin", "operations_admin", "Tenant moderation, job management, and operational workflows"),
        ("Compliance Officer", "compliance_officer", "Platform compliance, legal review, and data governance"),
        ("Billing Manager", "billing_manager", "Commercial plan management, billing tiers, and revenue oversight"),
        ("Read-Only Auditor", "read_only_auditor", "Read-only access across all platform modules"),
    ]

    admin_role_map = {}
    for name, code, desc in admin_roles_data:
        arole = db.query(AdminRole).filter_by(code=code).first()
        if not arole:
            arole = AdminRole(name=name, code=code, description=desc, is_system=True)
            db.add(arole)
            db.flush()
        admin_role_map[code] = arole

        existing_admin_mods = {p.module_key for p in arole.permissions}
        for amod in ADMIN_MODULES:
            if amod not in existing_admin_mods:
                if code == "super_admin":
                    perm = AdminRolePermission(role_id=arole.id, module_key=amod, can_view=True, can_create=True, can_edit=True, can_delete=True)
                elif code == "operations_admin":
                    can_write = amod in ["TENANTS", "USERS", "GOVERNANCE"]
                    perm = AdminRolePermission(role_id=arole.id, module_key=amod, can_view=True, can_create=can_write, can_edit=can_write, can_delete=False)
                elif code == "compliance_officer":
                    can_write = amod in ["GOVERNANCE", "TENANTS"]
                    perm = AdminRolePermission(role_id=arole.id, module_key=amod, can_view=True, can_create=can_write, can_edit=can_write, can_delete=False)
                elif code == "billing_manager":
                    can_write = amod in ["COMMERCIAL", "TENANTS"]
                    perm = AdminRolePermission(role_id=arole.id, module_key=amod, can_view=True, can_create=can_write, can_edit=can_write, can_delete=False)
                else:  # read_only_auditor
                    perm = AdminRolePermission(role_id=arole.id, module_key=amod, can_view=True, can_create=False, can_edit=False, can_delete=False)
                db.add(perm)
    db.flush()
    return admin_role_map


def seed_super_admins(db: Session, admin_role_map: dict, default_pwd: str = "Password123!"):
    super_admins_data = [
        ("admin.super@yopmail.com", "Nguyen", "Van An", "+84 901 234 567", "super_admin"),
        ("admin.ops@yopmail.com", "Tran", "Thi Mai", "+84 912 345 678", "operations_admin"),
        ("admin.compliance@yopmail.com", "Le", "Hoang Nam", "+84 933 456 789", "compliance_officer"),
        ("admin.billing@yopmail.com", "Pham", "Minh Duc", "+84 944 567 890", "billing_manager"),
        ("admin.auditor@yopmail.com", "Vu", "Thi Lan", "+84 955 678 901", "read_only_auditor"),
    ]

    hashed = hash_password(default_pwd)
    seeded_admins = []

    for email, fname, lname, phone, rcode in super_admins_data:
        adm = db.query(AdminUser).filter_by(email=email).first()
        role_obj = admin_role_map.get(rcode)
        if not adm:
            adm = AdminUser(
                email=email,
                password_hash=hashed,
                first_name=fname,
                last_name=lname,
                phone=phone,
                role_id=role_obj.id if role_obj else None,
                role_name=role_obj.name if role_obj else "Super Admin",
                is_active=True,
            )
            db.add(adm)
            db.flush()
            logger.info(f"Created dedicated admin user: {email} ({rcode})")
        else:
            adm.password_hash = hashed
            adm.is_active = True
            adm.is_deleted = False
            if role_obj:
                adm.role_id = role_obj.id
                adm.role_name = role_obj.name
        seeded_admins.append(adm)

    # Legacy User table fallback for Super Admin portal
    legacy_admin = db.query(User).filter_by(email="admin.super@yopmail.com").first()
    if not legacy_admin:
        legacy_admin = User(
            email="admin.super@yopmail.com",
            hashed_password=hashed,
            full_name="Nguyen Van An",
            user_type="super_admin",
            phone="+84 901 234 567",
            is_active=True,
            is_verified=True,
        )
        db.add(legacy_admin)
        db.flush()

    return seeded_admins


def seed_companies_and_employees(db: Session, role_map: dict, default_pwd: str = "Password123!"):
    companies_data = [
        {
            "key": "techcorp",
            "company_name": "TechCorp Solutions Vietnam",
            "legal_name": "TechCorp Solutions Vietnam Co., Ltd",
            "primary_email": "company.techcorp@yopmail.com",
            "contact_person": "David Nguyen (VP of Engineering)",
            "contact_phone": "+84 28 3910 2122",
            "industry": "Information Technology & Software",
            "company_size": "201–500 employees",
            "city": "Ho Chi Minh City",
            "address": "Level 15, Saigon Centre Tower 2, 67 Le Loi Boulevard, District 1",
            "website": "https://techcorp.example.com",
            "tax_code": "0315891234",
            "founded_year": 2016,
            "subscription_tier": "Enterprise",
            "about": "TechCorp Solutions is a premier software engineering firm delivering enterprise cloud platforms, AI integrations, and digital products for enterprise clients across APAC and North America.",
            "benefits": "13th month bonus + annual performance bonus (up to 3 months), Premium Bao Viet healthcare, 18 annual leave days, Hybrid work model, MacBook Pro M3 Max.",
            "employees": [
                ("techcorp.admin@yopmail.com", "David", "Nguyen", "+84 28 3910 2122", "company_admin"),
                ("techcorp.recruiter@yopmail.com", "Sarah", "Jenkins", "+84 28 3910 2123", "recruiter"),
                ("techcorp.hiring@yopmail.com", "Alex", "Wong", "+84 28 3910 2124", "hiring_manager"),
            ],
            "jobs": [
                {
                    "title": "Senior Backend Engineer (Python & FastAPI)",
                    "description": "We are seeking a Senior Backend Engineer to architect, optimize, and scale backend microservices behind our enterprise recruitment platform. You will lead database design, API resilience, and Redis cache strategies.",
                    "requirements": "5+ years backend development in Python, FastAPI or Django, PostgreSQL, Redis, Docker, and REST API design.",
                    "benefits": "Competitive salary ($2500 - $3500), 13th month bonus, Bao Viet premium health insurance, MacBook Pro.",
                    "job_type": "Full-time",
                    "workplace_type": "Hybrid",
                    "experience_level": "Senior",
                    "city": "Ho Chi Minh City",
                    "salary_min": 35000000.0,
                    "salary_max": 55000000.0,
                    "required_skills": "Python, FastAPI, PostgreSQL, Redis, Docker",
                },
                {
                    "title": "Lead Frontend Engineer (React 19 & TypeScript)",
                    "description": "Join our frontend engineering team to architect modern single-page applications and design system component libraries using React 19, TypeScript, and modern styling solutions.",
                    "requirements": "Deep expertise in React, TypeScript, state management, web performance optimization, and responsive design systems.",
                    "benefits": "Attractive salary ($2200 - $3200), flexible hours, stock options, luxury annual team retreat.",
                    "job_type": "Full-time",
                    "workplace_type": "Hybrid",
                    "experience_level": "Lead",
                    "city": "Ho Chi Minh City",
                    "salary_min": 32000000.0,
                    "salary_max": 50000000.0,
                    "required_skills": "React 19, TypeScript, Next.js, TailwindCSS, State Management",
                },
            ],
        },
        {
            "key": "vinafintech",
            "company_name": "VinaFintech Digital Bank",
            "legal_name": "VinaFintech Digital Financial Technology JSC",
            "primary_email": "company.vinafintech@yopmail.com",
            "contact_person": "Lan Tran (Head of Talent Acquisition)",
            "contact_phone": "+84 24 3788 2678",
            "industry": "Financial Services & Fintech",
            "company_size": "101–200 employees",
            "city": "Hanoi",
            "address": "Floor 18, Keangnam Landmark 72, Pham Hung Road, Nam Tu Liem District",
            "website": "https://vinafintech.example.vn",
            "tax_code": "0108923456",
            "founded_year": 2019,
            "subscription_tier": "Enterprise",
            "about": "VinaFintech is an innovative digital banking and payments platform transforming financial inclusion with secure real-time microservices, AI fraud prevention, and seamless merchant checkout.",
            "benefits": "14 months guaranteed salary, comprehensive healthcare, flexible core hours (9:30-16:30), annual overseas team retreat, $1000/year learning budget.",
            "employees": [
                ("vinafintech.admin@yopmail.com", "Lan", "Tran", "+84 24 3788 2678", "company_admin"),
                ("vinafintech.recruiter@yopmail.com", "Tuan", "Nguyen", "+84 24 3788 2679", "recruiter"),
                ("vinafintech.interviewer@yopmail.com", "Duc", "Pham", "+84 24 3788 2680", "interviewer"),
            ],
            "jobs": [
                {
                    "title": "Core Banking Golang Microservices Specialist",
                    "description": "Design and build high-throughput, ACID-compliant banking transaction services with Go, gRPC, and PostgreSQL. Maintain zero-downtime ledger consistency under peak loads.",
                    "requirements": "4+ years experience with Go (Golang), distributed transaction handling, gRPC, Kafka, and PostgreSQL.",
                    "benefits": "Top-tier fintech compensation ($2600 - $4000), annual banking performance bonus, full premium coverage.",
                    "job_type": "Full-time",
                    "workplace_type": "On-site",
                    "experience_level": "Senior",
                    "city": "Hanoi",
                    "salary_min": 38000000.0,
                    "salary_max": 60000000.0,
                    "required_skills": "Go, Microservices, gRPC, PostgreSQL, Kafka",
                },
                {
                    "title": "Senior QA Automation Engineer (Playwright & API Security)",
                    "description": "Lead automated end-to-end quality assurance and financial security regression suites across our web and mobile applications using Playwright, TypeScript, and CI pipelines.",
                    "requirements": "Solid experience with Playwright or Cypress, TypeScript, REST & GraphQL API automation, and CI/CD security scanning.",
                    "benefits": "Attractive package (up to 42M VND), premium medical plan, annual luxury team trip, MacBook Pro.",
                    "job_type": "Full-time",
                    "workplace_type": "Hybrid",
                    "experience_level": "Senior",
                    "city": "Hanoi",
                    "salary_min": 28000000.0,
                    "salary_max": 42000000.0,
                    "required_skills": "Playwright, TypeScript, Cypress, CI/CD, Automated Testing",
                },
            ],
        },
        {
            "key": "nexus",
            "company_name": "Nexus E-Commerce Group",
            "legal_name": "Nexus Retail & Digital Commerce Vietnam Ltd",
            "primary_email": "company.nexus@yopmail.com",
            "contact_person": "Hoang Nam (Chief Operating Officer)",
            "contact_phone": "+84 28 7300 8899",
            "industry": "E-Commerce & Retail",
            "company_size": "201–500 employees",
            "city": "Ho Chi Minh City",
            "address": "Level 10, Bitexco Financial Tower, 2 Hai Trieu, District 1",
            "website": "https://nexus-commerce.example.com",
            "tax_code": "0316447788",
            "founded_year": 2018,
            "subscription_tier": "Professional",
            "about": "Nexus E-Commerce operates Southeast Asia's fastest-growing multi-brand omni-channel retail network, processing over 100,000 daily orders with real-time inventory intelligence.",
            "benefits": "13.5 months salary, quarterly store discounts, gym membership, annual health screening, sponsored technical certifications.",
            "employees": [
                ("nexus.admin@yopmail.com", "Hoang", "Nam", "+84 28 7300 8899", "company_admin"),
                ("nexus.recruiter@yopmail.com", "Mai", "Le", "+84 28 7300 8890", "recruiter"),
                ("nexus.hiring@yopmail.com", "Huy", "Tran", "+84 28 7300 8891", "hiring_manager"),
            ],
            "jobs": [
                {
                    "title": "Principal UI/UX & Design Systems Architect",
                    "description": "Lead the design direction and component system across consumer mobile apps and merchant admin dashboards. Shape frictionless discovery and checkout flows.",
                    "requirements": "5+ years in digital product design, mastery of Figma, design token governance, interactive prototyping, and user testing.",
                    "benefits": "Market-leading salary ($2200 - $3200), stock options, flexible hybrid working, wellness allowance.",
                    "job_type": "Full-time",
                    "workplace_type": "Hybrid",
                    "experience_level": "Lead",
                    "city": "Ho Chi Minh City",
                    "salary_min": 35000000.0,
                    "salary_max": 52000000.0,
                    "required_skills": "Figma, UI/UX Design, Design Systems, Prototyping, CSS3",
                },
                {
                    "title": "Full Stack Product Engineer (Next.js & Node.js)",
                    "description": "Develop customer-facing storefront features, high-converting product detail pages, and merchant analytics using Next.js, Node.js, and Redis caching.",
                    "requirements": "3+ years building full-stack web applications with React/Next.js, Node.js, relational databases, and REST/GraphQL APIs.",
                    "benefits": "Competitive compensation, flexible core hours, continuous learning stipend, modern gear.",
                    "job_type": "Full-time",
                    "workplace_type": "Hybrid",
                    "experience_level": "Mid-Senior",
                    "city": "Ho Chi Minh City",
                    "salary_min": 30000000.0,
                    "salary_max": 48000000.0,
                    "required_skills": "Next.js, React, Node.js, PostgreSQL, REST APIs",
                },
            ],
        },
        {
            "key": "greenlogistics",
            "company_name": "GreenLogistics Supply Chain",
            "legal_name": "GreenLogistics Vietnam Logistics JSC",
            "primary_email": "company.greenlogistics@yopmail.com",
            "contact_person": "Thanh Son (General Manager)",
            "contact_phone": "+84 236 3888 999",
            "industry": "Logistics & Supply Chain",
            "company_size": "51–100 employees",
            "city": "Da Nang",
            "address": "Floor 5, Software Park Da Nang, 02 Quang Trung, Hai Chau District",
            "website": "https://greenlogistics.example.vn",
            "tax_code": "0401993322",
            "founded_year": 2020,
            "subscription_tier": "Professional",
            "about": "GreenLogistics pioneers smart route optimization, IoT temperature monitoring, and low-carbon multi-modal freight tracking across Vietnam and cross-border corridors.",
            "benefits": "13th month bonus, generous Da Nang coastal living allowance, comprehensive family medical coverage, annual company retreat.",
            "employees": [
                ("greenlogistics.admin@yopmail.com", "Thanh", "Son", "+84 236 3888 999", "company_admin"),
                ("greenlogistics.recruiter@yopmail.com", "Kim", "Ngan", "+84 236 3888 991", "recruiter"),
                ("greenlogistics.interviewer@yopmail.com", "Bao", "Long", "+84 236 3888 992", "interviewer"),
            ],
            "jobs": [
                {
                    "title": "Senior Cloud DevOps & Kubernetes Engineer",
                    "description": "Own our cloud automation, multi-region Kubernetes deployments, and telemetry across AWS. Maintain infrastructure as code using Terraform and GitOps pipelines.",
                    "requirements": "Strong expertise in AWS, Kubernetes (EKS), Terraform, Docker, CI/CD automation, and Prometheus/Grafana monitoring.",
                    "benefits": "Excellent compensation ($2400 - $3600), comprehensive medical package, annual tech conference budget.",
                    "job_type": "Full-time",
                    "workplace_type": "Remote",
                    "experience_level": "Senior",
                    "city": "Da Nang",
                    "salary_min": 36000000.0,
                    "salary_max": 55000000.0,
                    "required_skills": "AWS, Kubernetes, Terraform, Docker, CI/CD",
                },
                {
                    "title": "Senior Mobile Engineer (Flutter & React Native)",
                    "description": "Build resilient mobile apps used daily by thousands of warehouse operators, freight drivers, and freight dispatchers across low-connectivity regions.",
                    "requirements": "4+ years mobile development experience in Flutter or React Native, offline-first SQLite sync, and native iOS/Android bridge integration.",
                    "benefits": "Full remote flexibility, annual tech gear upgrade, team wellness budget.",
                    "job_type": "Full-time",
                    "workplace_type": "Hybrid",
                    "experience_level": "Senior",
                    "city": "Da Nang",
                    "salary_min": 28000000.0,
                    "salary_max": 45000000.0,
                    "required_skills": "Flutter, Dart, React Native, iOS, Android",
                },
            ],
        },
        {
            "key": "cloudai",
            "company_name": "CloudAI Studio Labs",
            "legal_name": "CloudAI Artificial Intelligence & Cloud Solutions Co., Ltd",
            "primary_email": "company.cloudai@yopmail.com",
            "contact_person": "Viet Anh (Co-Founder & CTO)",
            "contact_phone": "+84 24 3999 1234",
            "industry": "Artificial Intelligence & Cloud",
            "company_size": "20–50 employees",
            "city": "Hanoi",
            "address": "Floor 12, CMC Tower, Duy Tan Street, Cau Giay District",
            "website": "https://cloudaistudio.example.ai",
            "tax_code": "0109887766",
            "founded_year": 2021,
            "subscription_tier": "Enterprise",
            "about": "CloudAI Studio Labs develops proprietary generative AI agents, vector retrieval pipelines, and enterprise automation infrastructure for finance and healthcare enterprises.",
            "benefits": "Equity options, 14 months salary, cutting-edge GPU compute access (H100 clusters), fully covered international research conference trips.",
            "employees": [
                ("cloudai.admin@yopmail.com", "Viet", "Anh", "+84 24 3999 1234", "company_admin"),
                ("cloudai.recruiter@yopmail.com", "Thao", "My", "+84 24 3999 1235", "recruiter"),
                ("cloudai.hiring@yopmail.com", "Quang", "Minh", "+84 24 3999 1236", "hiring_manager"),
            ],
            "jobs": [
                {
                    "title": "Senior AI / ML Research Engineer (PyTorch & LLMs)",
                    "description": "Architect and fine-tune large language models, retrieval-augmented generation (RAG) pipelines, and multimodal inference services for enterprise customers.",
                    "requirements": "4+ years in machine learning engineering, expertise in PyTorch, HuggingFace, LangChain/LlamaIndex, Vector DBs, and Triton inference server.",
                    "benefits": "Market-leading AI package ($3000 - $4800), high equity grant, direct compute access.",
                    "job_type": "Full-time",
                    "workplace_type": "Hybrid",
                    "experience_level": "Senior",
                    "city": "Hanoi",
                    "salary_min": 45000000.0,
                    "salary_max": 70000000.0,
                    "required_skills": "Python, PyTorch, LLMs, LangChain, Vector DBs",
                },
                {
                    "title": "Data Platform & Pipeline Engineer (Spark & Airflow)",
                    "description": "Design distributed ETL pipelines, real-time streaming architectures, and feature stores supporting continuous model training and analytics at petabyte scale.",
                    "requirements": "Solid experience with Apache Spark, Apache Airflow, Kafka, Delta Lake / Iceberg, and distributed SQL query engines.",
                    "benefits": "Top compensation, flexible hybrid schedule, learning budget, health package.",
                    "job_type": "Full-time",
                    "workplace_type": "Hybrid",
                    "experience_level": "Mid-Senior",
                    "city": "Hanoi",
                    "salary_min": 38000000.0,
                    "salary_max": 58000000.0,
                    "required_skills": "Python, Apache Spark, Airflow, SQL, Kafka",
                },
            ],
        },
    ]

    hashed = hash_password(default_pwd)
    seeded_companies = []
    all_seeded_jobs = []

    for c in companies_data:
        p_email = c["primary_email"]
        u = db.query(User).filter_by(email=p_email).first()
        if not u:
            u = User(
                email=p_email,
                hashed_password=hashed,
                full_name=c["contact_person"].split("(")[0].strip(),
                user_type="company",
                phone=c["contact_phone"],
                is_active=True,
                is_verified=True,
                roles=[role_map["company"]],
            )
            db.add(u)
            db.flush()
            logger.info(f"Created company owner user: {p_email}")
        else:
            u.hashed_password = hashed
            u.is_active = True
            u.is_verified = True
            if role_map["company"] not in u.roles:
                u.roles.append(role_map["company"])

        profile = db.query(CompanyProfile).filter_by(user_id=u.id).first()
        if not profile:
            profile = CompanyProfile(
                user_id=u.id,
                company_name=c["company_name"],
                legal_name=c["legal_name"],
                tax_code=c["tax_code"],
                contact_person=c["contact_person"],
                contact_email=p_email,
                contact_phone=c["contact_phone"],
                founded_year=c["founded_year"],
                industry=c["industry"],
                company_size=c["company_size"],
                about=c["about"],
                website=c["website"],
                address=c["address"],
                city=c["city"],
                country="Vietnam",
                benefits=c["benefits"],
                verification_status="verified",
                is_featured=True,
                subscription_tier=c["subscription_tier"],
                settings=make_tenant_settings(c["company_name"]),
            )
            db.add(profile)
            db.flush()
            logger.info(f"Created company profile: {c['company_name']}")
        else:
            profile.company_name = c["company_name"]
            profile.legal_name = c["legal_name"]
            profile.tax_code = c["tax_code"]
            profile.contact_person = c["contact_person"]
            profile.contact_email = p_email
            profile.contact_phone = c["contact_phone"]
            profile.founded_year = c["founded_year"]
            profile.industry = c["industry"]
            profile.company_size = c["company_size"]
            profile.about = c["about"]
            profile.website = c["website"]
            profile.address = c["address"]
            profile.city = c["city"]
            profile.benefits = c["benefits"]
            profile.verification_status = "verified"
            profile.is_featured = True
            profile.subscription_tier = c["subscription_tier"]
            if not profile.settings:
                profile.settings = make_tenant_settings(c["company_name"])
            db.flush()

        seeded_companies.append(profile)

        # Seed 3 dedicated CompanyUser records
        for emp_email, fname, lname, phone, role in c["employees"]:
            cu = db.query(CompanyUser).filter_by(company_id=profile.id, email=emp_email).first()
            if not cu:
                cu = CompanyUser(
                    company_id=profile.id,
                    email=emp_email,
                    password_hash=hashed,
                    first_name=fname,
                    last_name=lname,
                    phone=phone,
                    role=role,
                    is_active=True,
                    is_verified=True,
                )
                db.add(cu)
                db.flush()
                logger.info(f"Created CompanyUser for {c['company_name']}: {emp_email} ({role})")
            else:
                cu.password_hash = hashed
                cu.first_name = fname
                cu.last_name = lname
                cu.phone = phone
                cu.role = role
                cu.is_active = True
                cu.is_verified = True
                cu.is_deleted = False

        # Seed demo pending invitation
        inv_email = f"candidate.interviewer@{c['key']}.yopmail.com"
        inv_token = f"yopmail-dev-invite-{c['key']}-token"
        inv = db.query(CompanyInvitation).filter_by(invite_token=inv_token).first()
        if not inv:
            inv = db.query(CompanyInvitation).filter_by(company_id=profile.id, email=inv_email).first()
        if not inv:
            admin_cu = db.query(CompanyUser).filter_by(company_id=profile.id, role="company_admin").first()
            inv = CompanyInvitation(
                company_id=profile.id,
                email=inv_email,
                role="interviewer",
                invite_token=inv_token,
                message=f"Welcome to {c['company_name']} talent acquisition team!",
                status="pending",
                invited_by_id=admin_cu.id if admin_cu else None,
                expires_at=datetime.now(timezone.utc) + timedelta(days=14),
            )
            db.add(inv)
            db.flush()
        else:
            inv.company_id = profile.id
            inv.email = inv_email
            inv.role = "interviewer"
            inv.status = "pending"

        # Seed Exactly 2 Jobs per Company
        now = datetime.now(timezone.utc)
        expires = now + timedelta(days=60)
        company_jobs = []

        for j_spec in c["jobs"]:
            job = db.query(JobPosting).filter_by(company_id=profile.id, title=j_spec["title"], is_deleted=False).first()
            if not job:
                job = JobPosting(
                    company_id=profile.id,
                    title=j_spec["title"],
                    description=j_spec["description"],
                    requirements=j_spec["requirements"],
                    benefits=j_spec["benefits"],
                    job_type=j_spec["job_type"],
                    workplace_type=j_spec["workplace_type"],
                    experience_level=j_spec["experience_level"],
                    city=j_spec["city"],
                    country="Vietnam",
                    salary_min=j_spec["salary_min"],
                    salary_max=j_spec["salary_max"],
                    salary_currency="VND",
                    required_skills=j_spec["required_skills"],
                    status="published",
                    moderation_status="approved",
                    views_count=75 + (len(company_jobs) * 20),
                    applications_count=3,
                    expires_at=expires,
                )
                db.add(job)
                db.flush()
                logger.info(f"Created Job for {c['company_name']}: {j_spec['title']}")
            else:
                job.description = j_spec["description"]
                job.requirements = j_spec["requirements"]
                job.benefits = j_spec["benefits"]
                job.salary_min = j_spec["salary_min"]
                job.salary_max = j_spec["salary_max"]
                job.status = "published"
                job.moderation_status = "approved"
            company_jobs.append(job)
            all_seeded_jobs.append(job)

    db.flush()
    return seeded_companies, all_seeded_jobs


def seed_jobseekers(db: Session, role_map: dict, default_pwd: str = "Password123!"):
    seekers_data = [
        (
            "seeker.python.dev@yopmail.com",
            "Nguyen",
            "Van An",
            "+84 908 111 201",
            "Senior Python & FastAPI Backend Architect",
            "Backend engineer with 6+ years designing resilient microservices, high-concurrency Redis caching, and async Python APIs in production.",
            "Python, FastAPI, Django, PostgreSQL, Redis, Docker, RabbitMQ",
            6.0,
            45000000.0,
            "Ho Chi Minh City",
            "open_to_work",
        ),
        (
            "seeker.frontend.lead@yopmail.com",
            "Tran",
            "Thi Mai",
            "+84 919 222 333",
            "Lead Frontend React & TypeScript Specialist",
            "UI architect with 7 years crafting high-performance design systems, React 19 SPAs, Next.js web applications, and web vital optimizations.",
            "React 19, TypeScript, Next.js, TailwindCSS, Redux Toolkit, Webpack, Vite",
            7.0,
            50000000.0,
            "Ho Chi Minh City",
            "open_to_work",
        ),
        (
            "seeker.fullstack.dev@yopmail.com",
            "Le",
            "Hoang Nam",
            "+84 938 333 444",
            "Full Stack Next.js & Python Web Engineer",
            "Versatile engineer with 4 years building customer-facing digital platforms using Next.js on the client and Python FastAPI on the backend.",
            "Next.js, React, Python, FastAPI, Node.js, PostgreSQL, Docker",
            4.0,
            35000000.0,
            "Hanoi",
            "open_to_work",
        ),
        (
            "seeker.devops.cloud@yopmail.com",
            "Pham",
            "Minh Duc",
            "+84 944 444 555",
            "Senior Cloud DevOps & Kubernetes Architect",
            "Infrastructure and platform engineer specializing in AWS EKS, Terraform infrastructure as code, zero-downtime CI/CD, and Grafana telemetry.",
            "AWS, Kubernetes, Terraform, Docker, Helm, GitHub Actions, Prometheus, Grafana",
            5.5,
            48000000.0,
            "Hanoi",
            "open_to_opportunities",
        ),
        (
            "seeker.qa.automation@yopmail.com",
            "Vu",
            "Thi Lan",
            "+84 955 555 666",
            "Senior QA Automation Engineer (Playwright/CI)",
            "Quality assurance leader specializing in modern Playwright / Cypress frameworks, automated API test suites, and CI/CD quality gates.",
            "Playwright, Cypress, TypeScript, Python, Jest, Postman, CI/CD, Selenium",
            5.0,
            32000000.0,
            "Da Nang",
            "open_to_work",
        ),
        (
            "seeker.uiux.designer@yopmail.com",
            "Dang",
            "Quang Huy",
            "+84 966 666 777",
            "Principal UI/UX & Design Systems Lead",
            "Human-centered product designer with 6.5 years designing accessible web/mobile experiences, design token frameworks, and high-converting checkout flows.",
            "Figma, Design Systems, Wireframing, User Research, Prototyping, CSS3, Storybook",
            6.5,
            40000000.0,
            "Ho Chi Minh City",
            "open_to_opportunities",
        ),
        (
            "seeker.mobile.flutter@yopmail.com",
            "Hoang",
            "Thu Trang",
            "+84 977 777 888",
            "Senior Mobile Engineer (Flutter & React Native)",
            "Mobile specialist with 4.5 years developing cross-platform iOS and Android apps with offline caching, push notifications, and native performance.",
            "Flutter, Dart, React Native, TypeScript, iOS, Android, SQLite, Firebase",
            4.5,
            36000000.0,
            "Hanoi",
            "open_to_work",
        ),
        (
            "seeker.data.engineer@yopmail.com",
            "Doan",
            "Van Binh",
            "+84 988 888 999",
            "Senior Data Engineer (ETL, Spark & Airflow)",
            "Data platform specialist with 5 years designing high-volume data ingestions, Delta Lake pipelines, Apache Spark transformations, and DBT models.",
            "Python, Apache Spark, Airflow, SQL, Kafka, Snowflake, Delta Lake, Docker",
            5.0,
            42000000.0,
            "Ho Chi Minh City",
            "open_to_work",
        ),
        (
            "seeker.ai.ml.engineer@yopmail.com",
            "Bui",
            "Thanh Tung",
            "+84 909 000 111",
            "AI / Machine Learning Specialist (PyTorch/LLMs)",
            "Applied machine learning engineer building production RAG pipelines, fine-tuning LLMs, vector database embeddings, and Triton inference services.",
            "Python, PyTorch, HuggingFace, LangChain, LlamaIndex, Qdrant, Docker, FastAPI",
            3.5,
            46000000.0,
            "Hanoi",
            "open_to_opportunities",
        ),
        (
            "seeker.golang.backend@yopmail.com",
            "Ngo",
            "Quoc Anh",
            "+84 912 111 333",
            "High-Throughput Go & Distributed Systems Dev",
            "Backend engineer focusing on low-latency microservices in Go, gRPC service meshes, Kafka event streaming, and PostgreSQL query tuning.",
            "Go, Golang, gRPC, Kafka, PostgreSQL, Redis, Kubernetes, Linux",
            4.0,
            38000000.0,
            "Ho Chi Minh City",
            "not_looking",
        ),
    ]

    hashed = hash_password(default_pwd)
    seeded_profiles = []

    for email, fname, lname, phone, headline, bio, skills, exp, sal, city, availability in seekers_data:
        full_name = f"{fname} {lname}"
        u = db.query(User).filter_by(email=email).first()
        if not u:
            u = User(
                email=email,
                hashed_password=hashed,
                first_name=fname,
                last_name=lname,
                user_type="jobseeker",
                phone=phone,
                is_active=True,
                is_verified=True,
                roles=[role_map["jobseeker"]],
            )
            db.add(u)
            db.flush()
            logger.info(f"Created job seeker user: {email}")
        else:
            u.hashed_password = hashed
            u.first_name = fname
            u.last_name = lname
            u.phone = phone
            u.is_active = True
            u.is_verified = True
            if role_map["jobseeker"] not in u.roles:
                u.roles.append(role_map["jobseeker"])

        prof = db.query(JobSeekerProfile).filter_by(user_id=u.id).first()
        if not prof:
            prof = JobSeekerProfile(
                user_id=u.id,
                headline=headline,
                bio=bio,
                skills=skills,
                experience_years=exp,
                expected_salary=sal,
                city=city,
                country="Vietnam",
                resume_url=f"/uploads/resumes/{fname}_{lname}_CV.pdf",
                github_url="https://github.com",
                linkedin_url="https://linkedin.com",
                is_visible=True,
                visibility="public",
                job_availability=availability,
            )
            db.add(prof)
            db.flush()
            logger.info(f"Created job seeker profile for {full_name} ({availability})")
        else:
            prof.headline = headline
            prof.bio = bio
            prof.skills = skills
            prof.experience_years = exp
            prof.expected_salary = sal
            prof.city = city
            prof.is_visible = True
            prof.visibility = "public"
            prof.job_availability = availability
        seeded_profiles.append(prof)

    db.flush()
    return seeded_profiles


def seed_applications(db: Session, job_list: list, seeker_profiles: list):
    """
    Distribute the 10 jobseekers across the 10 seeded jobs in multiple ATS pipeline stages.
    """
    if len(job_list) < 10 or len(seeker_profiles) < 10:
        logger.warning("Not enough jobs or profiles to link all 10 applications.")
        return

    # Matrix: (seeker_idx, job_idx, status, rating, cover_letter, notes)
    application_matrix = [
        (0, 0, "interviewing", 5, "I am passionate about building resilient FastAPI microservices and would love to bring my backend architecture expertise to TechCorp.", "Strong performance in round 1 technical interview. Recommended for system design round."),
        (1, 1, "shortlisted", 5, "My UI component libraries and design system background allows me to ensure rock-solid user experiences across modern React platforms.", "Excellent portfolio and clean TypeScript code sample. Shortlisted by lead architect."),
        (9, 2, "applied", 4, "I have built high-throughput microservices using Go and gRPC, and would love to contribute to VinaFintech's real-time core banking systems.", "Resume received, matches required Go concurrency requirements."),
        (4, 3, "interviewing", 5, "With 5 years automating end-to-end regression suites in Playwright, I can bring automated banking quality gates to VinaFintech.", "Passed automated coding test with flying colors. Scheduled for round 2."),
        (5, 4, "shortlisted", 5, "I love crafting scalable design systems in Figma and would be thrilled to lead UI/UX architecture for Nexus omni-channel products.", "Exceptional design tokens portfolio and prototype showcase."),
        (2, 5, "applied", 4, "Excited about Nexus retail growth in Vietnam. I have built multiple Next.js + Node.js e-commerce modules with high conversion rates.", "Candidate has solid Next.js experience. Resume assigned to hiring team."),
        (3, 6, "interviewing", 5, "My Kubernetes and Terraform automation background enables high availability across multi-region logistics operations.", "Strong DevOps track record. Scheduled for cloud architecture review."),
        (6, 7, "applied", 4, "I have 4.5 years developing offline-first Flutter and React Native logistics applications for field teams.", "Strong offline caching and mobile background."),
        (8, 8, "shortlisted", 5, "Excited by CloudAI Studio's RAG and LLM agent research. I have deployed high-throughput PyTorch model inference in production.", "Profile shortlisted by AI Research Director."),
        (7, 9, "applied", 4, "I specialize in large-scale Apache Spark and Airflow pipelines supporting high-throughput feature stores.", "Strong data platform credentials."),
    ]

    for s_idx, j_idx, status, rating, cover, notes in application_matrix:
        seeker = seeker_profiles[s_idx]
        job = job_list[j_idx]

        existing_app = db.query(JobApplication).filter_by(job_id=job.id, jobseeker_id=seeker.id).first()
        if not existing_app:
            app = JobApplication(
                job_id=job.id,
                jobseeker_id=seeker.id,
                status=status,
                rating=rating,
                resume_url=seeker.resume_url,
                resume_name=f"{seeker.user.first_name}_{seeker.user.last_name}_CV.pdf",
                cover_letter=cover,
                recruiter_notes=notes,
                consent=True,
            )
            db.add(app)
            logger.info(f"Created application: {seeker.user.email} -> {job.title} ({status})")
        else:
            existing_app.status = status
            existing_app.rating = rating
            existing_app.recruiter_notes = notes

    db.flush()


def print_summary_card(default_pwd: str):
    divider = "=" * 80
    print("\n" + divider)
    print(" 🎉 DEVELOPER DATABASE SEED COMPLETED SUCCESSFULLY! (YOPMAIL ENVIRONMENT)")
    print(divider)
    print(f" Uniform Password for All Seeded Accounts:  {default_pwd}")
    print(f" Disposable Webmail Client:                 https://yopmail.com")
    print("-" * 80)
    print(" 👑 SUPER ADMIN & PLATFORM GOVERNANCE (Super Admin Portal: http://localhost:3003)")
    print("   * admin.super@yopmail.com       -> Role: Super Admin (Root Access)")
    print("   * admin.ops@yopmail.com         -> Role: Operations Admin (Tenant Moderation)")
    print("   * admin.compliance@yopmail.com  -> Role: Compliance Officer")
    print("   * admin.billing@yopmail.com     -> Role: Billing Manager")
    print("   * admin.auditor@yopmail.com     -> Role: Read-Only Auditor")
    print("-" * 80)
    print(" 🏢 5 VERIFIED COMPANIES (Employer Portal: http://localhost:3002)")
    print("   1) TechCorp Solutions Vietnam")
    print("      - techcorp.admin@yopmail.com     (Company Admin - VP Engineering)")
    print("      - techcorp.recruiter@yopmail.com (Recruiter)")
    print("      - techcorp.hiring@yopmail.com    (Hiring Manager)")
    print("      Jobs: [1] Senior Backend (Python)  [2] Lead Frontend (React 19)")
    print("   2) VinaFintech Digital Bank")
    print("      - vinafintech.admin@yopmail.com     (Company Admin)")
    print("      - vinafintech.recruiter@yopmail.com (Recruiter)")
    print("      - vinafintech.interviewer@yopmail.com (Interviewer)")
    print("      Jobs: [1] Core Banking Golang      [2] Senior QA Automation")
    print("   3) Nexus E-Commerce Group")
    print("      - nexus.admin@yopmail.com        (Company Admin - COO)")
    print("      - nexus.recruiter@yopmail.com    (Recruiter)")
    print("      - nexus.hiring@yopmail.com       (Hiring Manager)")
    print("      Jobs: [1] Principal UI/UX Architect [2] Full Stack Product Engineer")
    print("   4) GreenLogistics Supply Chain")
    print("      - greenlogistics.admin@yopmail.com     (Company Admin)")
    print("      - greenlogistics.recruiter@yopmail.com (Recruiter)")
    print("      - greenlogistics.interviewer@yopmail.com (Interviewer)")
    print("      Jobs: [1] Senior Cloud DevOps      [2] Senior Mobile Engineer")
    print("   5) CloudAI Studio Labs")
    print("      - cloudai.admin@yopmail.com      (Company Admin - CTO)")
    print("      - cloudai.recruiter@yopmail.com  (Recruiter)")
    print("      - cloudai.hiring@yopmail.com     (Hiring Manager)")
    print("      Jobs: [1] Senior AI / ML Research   [2] Data Platform Engineer")
    print("-" * 80)
    print(" 👤 10 JOB SEEKERS (Job Seeker Portal: http://localhost:3001)")
    print("   1) seeker.python.dev@yopmail.com      - Nguyen Van An (Senior Python Backend)")
    print("   2) seeker.frontend.lead@yopmail.com   - Tran Thi Mai (Lead Frontend React)")
    print("   3) seeker.fullstack.dev@yopmail.com   - Le Hoang Nam (Full Stack Next.js)")
    print("   4) seeker.devops.cloud@yopmail.com    - Pham Minh Duc (Senior Cloud DevOps)")
    print("   5) seeker.qa.automation@yopmail.com   - Vu Thi Lan (Senior QA Automation)")
    print("   6) seeker.uiux.designer@yopmail.com   - Dang Quang Huy (Principal UI/UX)")
    print("   7) seeker.mobile.flutter@yopmail.com  - Hoang Thu Trang (Senior Mobile)")
    print("   8) seeker.data.engineer@yopmail.com   - Doan Van Binh (Senior Data Engineer)")
    print("   9) seeker.ai.ml.engineer@yopmail.com  - Bui Thanh Tung (AI / ML Engineer)")
    print("  10) seeker.golang.backend@yopmail.com  - Ngo Quoc Anh (High-Throughput Go)")
    print(divider + "\n")


def seed_dev_database(db: Session = None, password: str = "Password123!"):
    """
    Main developer database seeder function.
    """
    should_close = False
    if db is None:
        init_db()
        db = SessionLocal()
        should_close = True

    try:
        print("\n🚀 Initializing Developer Seed with Yopmail Accounts...")
        
        # 1. Platform Roles & Permissions
        role_map = seed_roles_and_permissions(db)
        print("  ✓ Platform roles and module permissions verified.")

        # 2. Admin Roles & Permissions
        admin_role_map = seed_admin_roles_and_permissions(db)
        print("  ✓ Admin roles and governance permissions verified.")

        # 3. Super Admins
        seed_super_admins(db, admin_role_map, default_pwd=password)
        print("  ✓ 5 Super Admin & Platform Administrator accounts seeded.")

        # 4. 5 Companies + 3 Employees each + 2 Jobs each
        companies, jobs = seed_companies_and_employees(db, role_map, default_pwd=password)
        print(f"  ✓ 5 Companies seeded with 15 Company Employees and {len(jobs)} Published Jobs.")

        # 5. 10 Job Seekers
        seekers = seed_jobseekers(db, role_map, default_pwd=password)
        print("  ✓ 10 Job Seeker user accounts and candidate profiles seeded.")

        # 6. ATS Applications
        seed_applications(db, jobs, seekers)
        print("  ✓ Pre-seeded candidate applications across ATS pipeline stages.")

        db.commit()
        print_summary_card(password)
        return True

    except Exception as e:
        db.rollback()
        logger.error(f"Error during developer database seeding: {str(e)}", exc_info=True)
        print(f"\n❌ Error during developer seeding: {e}\n")
        raise
    finally:
        if should_close:
            db.close()


if __name__ == "__main__":
    pwd = sys.argv[1] if len(sys.argv) > 1 else "Password123!"
    seed_dev_database(password=pwd)
