import sys
import csv
import os
from pathlib import Path
from datetime import datetime, timedelta, timezone

# Ensure root backend directory is in sys.path
SCRIPT_DIR = Path(__file__).resolve().parent
BACKEND_ROOT = SCRIPT_DIR.parent.parent
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

# Ensure stdout supports UTF-8 on Windows
if sys.stdout.encoding.lower() != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

from sqlalchemy.orm import Session
from shared.database.session import SessionLocal, init_db
from shared.models import Role, User, CompanyProfile, CompanyUser, JobPosting
from shared.utils.password import hash_password
from shared.utils.logger import get_logger

logger = get_logger("dev_company_seeder")


def seed_companies_and_jobs(db: Session = None):
    should_close = False
    if db is None:
        init_db()
        db = SessionLocal()
        should_close = True

    try:
        print("=" * 60)
        print("🚀 Starting Developer Seed: 20 Companies & 100 Jobs")
        print("=" * 60)

        # 1. Get or create Company role
        company_role = db.query(Role).filter_by(code="company").first()
        if not company_role:
            company_role = Role(
                name="Company Recruiter",
                code="company",
                description="Employer account for posting jobs and hiring",
                is_system=True,
            )
            db.add(company_role)
            db.flush()
            logger.info("Created missing 'company' role")

        # Paths to reference CSV files
        companies_csv_path = SCRIPT_DIR / "companies.csv"
        jobs_csv_path = SCRIPT_DIR / "jobs.csv"

        if not companies_csv_path.exists() or not jobs_csv_path.exists():
            raise FileNotFoundError(f"CSV reference files not found in {SCRIPT_DIR}")

        # 2. Seed Companies
        companies_seeded = 0
        company_map = {}  # company_name -> CompanyProfile object

        with open(companies_csv_path, mode="r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                c_name = row["company_name"].strip()
                c_email = row["contact_email"].strip().lower()
                c_industry = row["industry"].strip()

                # Check if user exists
                user = db.query(User).filter_by(email=c_email).first()
                if not user:
                    user = User(
                        email=c_email,
                        hashed_password=hash_password("Company123!"),
                        full_name=f"{c_name} HR Team",
                        role_type="company",
                        is_active=True,
                        is_verified=True,
                    )
                    if company_role and company_role not in user.roles:
                        user.roles.append(company_role)
                    db.add(user)
                    db.flush()

                # Check if company profile exists
                profile = db.query(CompanyProfile).filter_by(user_id=user.id).first()
                if not profile:
                    profile = db.query(CompanyProfile).filter_by(company_name=c_name).first()

                is_feat = row["is_featured"].strip().lower() in ["true", "1", "yes"]
                founded = int(row["founded_year"]) if row["founded_year"].strip().isdigit() else None

                if not profile:
                    profile = CompanyProfile(
                        user_id=user.id,
                        company_name=c_name,
                        legal_name=row.get("legal_name", c_name),
                        industry=c_industry,
                        company_size=row.get("company_size"),
                        city=row.get("city"),
                        country=row.get("country", "Vietnam"),
                        website=row.get("website"),
                        founded_year=founded,
                        contact_email=c_email,
                        contact_phone=row.get("contact_phone"),
                        address=row.get("address"),
                        tax_code=row.get("tax_code"),
                        subscription_tier=row.get("subscription_tier", "Enterprise"),
                        verification_status=row.get("verification_status", "verified"),
                        is_featured=is_feat,
                        about=row.get("about"),
                        benefits=row.get("benefits"),
                    )
                    db.add(profile)
                    db.flush()
                    companies_seeded += 1
                    logger.info(f"Seeded Company #{companies_seeded}: {c_name}")
                else:
                    # Update fields if missing
                    profile.industry = c_industry
                    profile.verification_status = "verified"

                company_map[c_name] = profile

                # Ensure CompanyUser relationship exists
                c_user = db.query(CompanyUser).filter_by(company_id=profile.id, email=c_email).first()
                if not c_user:
                    c_user = CompanyUser(
                        company_id=profile.id,
                        email=c_email,
                        password_hash=user.password_hash,
                        first_name=user.first_name,
                        last_name=user.last_name,
                        role="company_admin",
                        is_active=True,
                        is_verified=True,
                    )
                    db.add(c_user)

        db.commit()
        print(f"✅ Companies Seeded/Verified: {len(company_map)} companies.")

        # 3. Seed Jobs
        jobs_seeded = 0
        now = datetime.now(timezone.utc)
        expires = now + timedelta(days=60)

        with open(jobs_csv_path, mode="r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                c_name = row["company_name"].strip()
                j_title = row["title"].strip()

                company_profile = company_map.get(c_name)
                if not company_profile:
                    company_profile = db.query(CompanyProfile).filter_by(company_name=c_name).first()

                if not company_profile:
                    print(f"⚠️ Warning: Company '{c_name}' not found for job '{j_title}'. Skipping.")
                    continue

                # Check if job already exists for this company
                existing_job = (
                    db.query(JobPosting)
                    .filter_by(company_id=company_profile.id, title=j_title)
                    .first()
                )

                if not existing_job:
                    s_min = float(row["salary_min"]) if row.get("salary_min") else None
                    s_max = float(row["salary_max"]) if row.get("salary_max") else None
                    is_neg = row.get("is_negotiable", "").strip().lower() in ["true", "1", "yes"]

                    job = JobPosting(
                        company_id=company_profile.id,
                        title=j_title,
                        description=row.get("description"),
                        requirements=row.get("requirements"),
                        benefits=row.get("benefits"),
                        job_type=row.get("job_type", "Full-time"),
                        workplace_type=row.get("workplace_type", "On-site"),
                        experience_level=row.get("experience_level", "Mid-level"),
                        city=row.get("city", company_profile.city),
                        country=row.get("country", "Vietnam"),
                        salary_min=s_min,
                        salary_max=s_max,
                        salary_currency=row.get("salary_currency", "VND"),
                        is_negotiable=is_neg,
                        required_skills=row.get("required_skills"),
                        status=row.get("status", "published"),
                        moderation_status="approved",
                        views_count=50 + (jobs_seeded * 3),
                        applications_count=5 + (jobs_seeded % 10),
                        expires_at=expires,
                    )
                    db.add(job)
                    jobs_seeded += 1

        db.commit()
        print(f"✅ Jobs Seeded: {jobs_seeded} new job postings created.")
        print("=" * 60)
        print("🎉 Database successfully seeded with 20 Companies & 100 Jobs!")
        print("=" * 60)

    except Exception as e:
        db.rollback()
        logger.error(f"Error during developer company seeding: {e}", exc_info=True)
        print(f"❌ Seeding failed: {e}")
        raise e
    finally:
        if should_close:
            db.close()


if __name__ == "__main__":
    seed_companies_and_jobs()
