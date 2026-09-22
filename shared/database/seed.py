import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from sqlalchemy.orm import Session
from shared.database.session import SessionLocal, init_db
from shared.models import Role, RolePermission, User, CompanyProfile, JobSeekerProfile, JobPosting
from shared.utils.password import hash_password
from shared.utils.logger import get_logger

logger = get_logger("seeder")

MODULES = ["DASHBOARD", "USERS", "ROLES", "COMPANIES", "JOBSEEKERS", "JOBS", "APPLICATIONS", "AUDIT_LOGS"]

def seed_database(db: Session = None):
    should_close = False
    if db is None:
        init_db()
        db = SessionLocal()
        should_close = True

    try:
        # 1. Seed Roles
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

        # 2. Seed Permissions per Role
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

        # 3. Seed Default Super Admin
        admin_email = "admin@jobportal.com"
        admin_user = db.query(User).filter_by(email=admin_email).first()
        if not admin_user:
            admin_user = User(
                email=admin_email,
                hashed_password=hash_password("Admin@123"),
                full_name="Super Administrator",
                user_type="super_admin",
                is_superuser=True,
                is_verified=True,
                is_active=True,
                roles=[role_map["super_admin"]],
            )
            db.add(admin_user)
            db.flush()
            logger.info("Created default super admin: admin@jobportal.com")

        # 4. Seed Demo Company
        company_email = "company@techcorp.com"
        company_user = db.query(User).filter_by(email=company_email).first()
        company_profile = None
        if not company_user:
            company_user = User(
                email=company_email,
                hashed_password=hash_password("Company@123"),
                full_name="TechCorp HR",
                user_type="company",
                is_superuser=False,
                is_verified=True,
                is_active=True,
                roles=[role_map["company"]],
            )
            db.add(company_user)
            db.flush()
            
            company_profile = CompanyProfile(
                user_id=company_user.id,
                company_name="TechCorp Global",
                legal_name="TechCorp Innovations Ltd",
                industry="Software & IT",
                company_size="100-500 employees",
                about="Leading software technology firm providing cloud architecture and digital transformation services.",
                website="https://techcorp.example.com",
                city="Ho Chi Minh City",
                country="Vietnam",
                verification_status="verified",
                is_featured=True,
            )
            db.add(company_profile)
            db.flush()
            logger.info("Created demo company: company@techcorp.com")
        else:
            company_profile = company_user.company_profile

        # 5. Seed Demo Job Seeker
        seeker_email = "seeker@example.com"
        seeker_user = db.query(User).filter_by(email=seeker_email).first()
        if not seeker_user:
            seeker_user = User(
                email=seeker_email,
                hashed_password=hash_password("Seeker@123"),
                full_name="Nguyen Van A",
                user_type="jobseeker",
                is_superuser=False,
                is_verified=True,
                is_active=True,
                roles=[role_map["jobseeker"]],
            )
            db.add(seeker_user)
            db.flush()

            seeker_profile = JobSeekerProfile(
                user_id=seeker_user.id,
                headline="Senior Full Stack Engineer (Python / React)",
                bio="Experienced engineer with 5+ years of building resilient backend microservices and modern React applications.",
                skills="Python, FastAPI, React, TypeScript, PostgreSQL, Docker",
                experience_years=5.0,
                expected_salary=3000.0,
                city="Ho Chi Minh City",
                country="Vietnam",
                github_url="https://github.com",
                linkedin_url="https://linkedin.com",
            )
            db.add(seeker_profile)
            db.flush()
            logger.info("Created demo job seeker: seeker@example.com")

        # 6. Seed Demo Jobs if company exists and has no jobs
        if company_profile:
            existing_jobs = db.query(JobPosting).filter_by(company_id=company_profile.id).count()
            if existing_jobs == 0:
                demo_job_1 = JobPosting(
                    company_id=company_profile.id,
                    title="Senior Python / FastAPI Backend Engineer",
                    description="We are seeking an experienced Backend Engineer to architect and scale our microservices.",
                    requirements="Solid knowledge of Python 3.11+, FastAPI, SQLAlchemy, PostgreSQL, Docker, and RESTful API design.",
                    benefits="Competitive salary ($2500 - $3500), 13th month salary, hybrid work, MacBook Pro provided.",
                    job_type="Full-time",
                    workplace_type="Hybrid",
                    experience_level="Senior",
                    city="Ho Chi Minh City",
                    country="Vietnam",
                    salary_min=2500.0,
                    salary_max=3500.0,
                    salary_currency="USD",
                    required_skills="Python, FastAPI, SQLAlchemy, Docker, Redis",
                    status="active",
                    moderation_status="approved",
                )
                demo_job_2 = JobPosting(
                    company_id=company_profile.id,
                    title="Lead Frontend Engineer (React & TypeScript)",
                    description="Join our product team to design and build world-class user interfaces using React, Redux Toolkit, and Tailwind CSS.",
                    requirements="Deep understanding of React 19, TypeScript, state management, modern CSS, and web performance.",
                    benefits="Competitive salary ($2200 - $3200), flexible hours, annual health check, stock options.",
                    job_type="Full-time",
                    workplace_type="Remote",
                    experience_level="Lead",
                    city="Da Nang",
                    country="Vietnam",
                    salary_min=2200.0,
                    salary_max=3200.0,
                    salary_currency="USD",
                    required_skills="React, TypeScript, TailwindCSS, Vite, Redux",
                    status="active",
                    moderation_status="approved",
                )
                db.add_all([demo_job_1, demo_job_2])
                db.flush()
                logger.info("Created demo job postings")

        db.commit()
        logger.info("Database seeding completed successfully.")
    except Exception as e:
        db.rollback()
        logger.error(f"Error during database seeding: {str(e)}")
        raise
    finally:
        if should_close:
            db.close()

if __name__ == "__main__":
    seed_database()
