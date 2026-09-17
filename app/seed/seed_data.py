from datetime import datetime, timedelta
from app.core.database import SessionLocal, engine, Base
from app.core.security import get_password_hash
from app.models import (
    User,
    UserRole,
    UserStatus,
    Company,
    CompanyApprovalStatus,
    SeekerProfile,
    Job,
    JobStatus,
    Application,
    ApplicationStage,
    ApplicationTimeline,
    ApplicationNote,
    Interview,
    InterviewMode,
    InterviewStatus,
    SubscriptionPlan,
    ModerationItem,
    ModerationType,
    ModerationStatus,
    Notification,
    NotificationType,
)


def seed_database():
    print("Creating database tables...")
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        # 1. Seed Subscription Plans
        if db.query(SubscriptionPlan).count() == 0:
            print("Seeding Subscription Plans...")
            plans = [
                SubscriptionPlan(
                    id="Freemium",
                    name="Freemium",
                    tier="Freemium",
                    price="Free",
                    posting_limit=3,
                    retention_months=6,
                    ai_features=False,
                    blurb="For occasional hiring",
                    features=["Standard search visibility", "Email support"],
                    active=True,
                ),
                SubscriptionPlan(
                    id="Professional",
                    name="Professional",
                    tier="Professional",
                    price="2,900,000 VND / mo",
                    posting_limit=25,
                    retention_months=12,
                    ai_features=True,
                    blurb="For growing teams",
                    features=["AI job description assist", "Candidate pipeline tools", "Priority support"],
                    active=True,
                ),
                SubscriptionPlan(
                    id="Enterprise",
                    name="Enterprise",
                    tier="Enterprise",
                    price="Custom",
                    posting_limit=None,
                    retention_months=24,
                    ai_features=True,
                    blurb="For high-volume hiring",
                    features=["Advanced AI recruitment suite", "Dedicated account manager", "Custom data retention"],
                    active=True,
                ),
            ]
            db.add_all(plans)
            db.commit()

        # 2. Seed Super Admin User
        admin_email = "admin@lamviec360.vn"
        admin_user = db.query(User).filter(User.email == admin_email).first()
        if not admin_user:
            print(f"Seeding Super Admin ({admin_email})...")
            admin_user = User(
                email=admin_email,
                name="Admin Root",
                hashed_password=get_password_hash("password123"),
                role=UserRole.SUPER_ADMIN,
                status=UserStatus.ACTIVE,
                email_verified=True,
                two_factor_enabled=True,
            )
            db.add(admin_user)
            db.commit()

        # 3. Seed Verified Company (ABC Technologies)
        company = db.query(Company).filter(Company.name == "ABC Technologies").first()
        if not company:
            print("Seeding Company (ABC Technologies)...")
            company = Company(
                name="ABC Technologies",
                reg_number="0312345678",
                industry="Technology",
                size="51–200",
                website="https://abctech.vn",
                description="A Vietnamese software company building hiring and workforce products for the region.",
                logo="",
                approval_status=CompanyApprovalStatus.ACTIVE,
                verified=True,
                email_verified=True,
                plan_id="Professional",
                settings={
                    "notifications": {"newApplications": True, "interviewReminders": True, "teamActivity": True, "billing": True},
                    "security": {"twoFactor": True},
                    "pipeline": {"autoRejectEmail": True},
                },
            )
            db.add(company)
            db.commit()
            db.refresh(company)

            # Company Admin
            emp_admin = User(
                email="lan.tran@abctech.vn",
                name="Lan Tran",
                hashed_password=get_password_hash("password123"),
                role=UserRole.COMPANY_ADMIN,
                status=UserStatus.ACTIVE,
                email_verified=True,
                two_factor_enabled=True,
                company_id=company.id,
            )
            # Recruiter
            recruiter = User(
                email="huy.nguyen@abctech.vn",
                name="Huy Nguyen",
                hashed_password=get_password_hash("password123"),
                role=UserRole.COMPANY_HR,
                status=UserStatus.ACTIVE,
                email_verified=True,
                two_factor_enabled=True,
                company_id=company.id,
            )
            db.add_all([emp_admin, recruiter])
            db.commit()

        # 4. Seed Pending Company (Vantix Software)
        pending_comp = db.query(Company).filter(Company.name == "Vantix Software").first()
        if not pending_comp:
            print("Seeding Pending Company (Vantix Software)...")
            pending_comp = Company(
                name="Vantix Software",
                reg_number="0399887766",
                industry="Technology",
                size="11–50",
                website="https://vantix.vn",
                description="High-growth enterprise software studio.",
                approval_status=CompanyApprovalStatus.PENDING,
                verified=False,
                email_verified=True,
                plan_id="Freemium",
            )
            db.add(pending_comp)
            db.commit()
            db.refresh(pending_comp)

            pending_admin = User(
                email="hoa.le@vantix.vn",
                name="Le Thi Hoa",
                hashed_password=get_password_hash("password123"),
                role=UserRole.COMPANY_ADMIN,
                status=UserStatus.PENDING,
                email_verified=True,
                two_factor_enabled=True,
                company_id=pending_comp.id,
            )
            db.add(pending_admin)
            db.commit()

        # 5. Seed Jobs for ABC Technologies
        if db.query(Job).filter(Job.company_id == company.id).count() == 0:
            print("Seeding Jobs...")
            jobs = [
                Job(
                    id="JOB-2001",
                    company_id=company.id,
                    title="Senior Backend Engineer",
                    department="Engineering",
                    type="Full-time",
                    location="Ho Chi Minh City",
                    salary_min="25000000",
                    salary_max="40000000",
                    negotiable=False,
                    jd="We are looking for a Senior Backend Engineer to design and scale the services behind our hiring platform. You will own core APIs, mentor engineers and drive technical decisions.",
                    skills=["Python", "FastAPI", "PostgreSQL", "AWS"],
                    experience="5",
                    education="Bachelor's Degree",
                    deadline=datetime.utcnow() + timedelta(days=21),
                    vacancies=2,
                    documents=["CV / Resume", "Cover Letter"],
                    status=JobStatus.PUBLISHED,
                    ai_generated=False,
                ),
                Job(
                    id="JOB-2002",
                    company_id=company.id,
                    title="Product Designer (UI/UX)",
                    department="Design",
                    type="Full-time",
                    location="Remote — Vietnam",
                    salary_min="18000000",
                    salary_max="28000000",
                    negotiable=True,
                    jd="Own the end-to-end design of key product areas, from research through polished UI. Partner closely with product and engineering.",
                    skills=["Figma", "Design systems", "Prototyping", "User research"],
                    experience="3",
                    education="Bachelor's Degree",
                    deadline=datetime.utcnow() + timedelta(days=12),
                    vacancies=1,
                    documents=["CV / Resume", "Portfolio"],
                    status=JobStatus.PUBLISHED,
                    ai_generated=True,
                ),
                Job(
                    id="JOB-2003",
                    company_id=company.id,
                    title="HR Operations Specialist",
                    department="People",
                    type="Full-time",
                    location="Hanoi",
                    salary_min="14000000",
                    salary_max="20000000",
                    negotiable=False,
                    jd="Support the full employee lifecycle: onboarding, records, payroll coordination.",
                    skills=["Onboarding", "Labour law", "HRIS"],
                    experience="2",
                    education="Bachelor's Degree",
                    deadline=datetime.utcnow() + timedelta(days=30),
                    vacancies=1,
                    documents=["CV / Resume"],
                    status=JobStatus.DRAFT,
                    ai_generated=False,
                ),
            ]
            db.add_all(jobs)
            db.commit()

        # 6. Seed Job Seeker (Minh Tran)
        seeker_email = "minh.tran@example.com"
        seeker = db.query(User).filter(User.email == seeker_email).first()
        if not seeker:
            print(f"Seeding Job Seeker ({seeker_email})...")
            seeker = User(
                email=seeker_email,
                name="Minh Tran",
                hashed_password=get_password_hash("password123"),
                role=UserRole.JOB_SEEKER,
                status=UserStatus.ACTIVE,
                email_verified=True,
                two_factor_enabled=False,
            )
            db.add(seeker)
            db.commit()
            db.refresh(seeker)

            profile = SeekerProfile(
                user_id=seeker.id,
                phone="090 123 4567",
                location="Ho Chi Minh City",
                title="Frontend Engineer",
                experience_years="3-5",
                industry="Technology",
                skills=["React", "TypeScript", "Node.js", "CSS"],
                languages=["Vietnamese", "English"],
                education=[{"degree": "B.Sc. Computer Science", "institution": "HCMC University of Technology", "year": "2019"}],
                experience=[{"company": "Nhat Tin Software", "title": "Frontend Engineer", "start": "2022", "end": "Present", "responsibilities": "Building web apps."}],
                resume_file_name="Minh_Tran_CV.pdf",
                resume_size=248000,
                preferences={"roles": ["Frontend Engineer", "Fullstack Engineer"], "locations": ["Ho Chi Minh City", "Remote"], "workMode": "Hybrid", "salary": "25M - 35M VND"},
            )
            db.add(profile)
            db.commit()

        # 7. Seed Applications
        job1 = db.query(Job).filter(Job.id == "JOB-2001").first()
        job2 = db.query(Job).filter(Job.id == "JOB-2002").first()

        if job1 and seeker and db.query(Application).filter(Application.seeker_id == seeker.id).count() == 0:
            print("Seeding Applications...")
            app1 = Application(
                id="APP-1001",
                job_id=job1.id,
                seeker_id=seeker.id,
                stage=ApplicationStage.APPLIED,
                match_score=85,
                resume_file_name="Minh_Tran_CV.pdf",
                cover_letter="I am very excited about this role and look forward to contributing.",
            )
            db.add(app1)
            db.flush()
            t1 = ApplicationTimeline(application_id=app1.id, stage=ApplicationStage.APPLIED)
            db.add(t1)

            if job2:
                app2 = Application(
                    id="APP-1002",
                    job_id=job2.id,
                    seeker_id=seeker.id,
                    stage=ApplicationStage.INTERVIEW_SCHEDULED,
                    match_score=92,
                    resume_file_name="Minh_Tran_CV.pdf",
                )
                db.add(app2)
                db.flush()
                t2 = ApplicationTimeline(application_id=app2.id, stage=ApplicationStage.INTERVIEW_SCHEDULED)
                db.add(t2)

                interview = Interview(
                    id="INT-1001",
                    application_id=app2.id,
                    round_name="First round – Hiring Manager",
                    scheduled_at=datetime.utcnow() + timedelta(days=2, hours=3),
                    duration_min=45,
                    mode=InterviewMode.VIDEO,
                    location_or_link="https://meet.lamviec360.vn/abc-designer-r1",
                    instructions="Please prepare a 5-minute walkthrough of your portfolio.",
                    interviewers=[{"name": "Trang Bui", "role": "Engineering Manager"}],
                    status=InterviewStatus.INVITED,
                )
                db.add(interview)

                note = ApplicationNote(
                    application_id=app2.id,
                    author="Lan Tran",
                    text="Strong portfolio, good communication in the screening call.",
                )
                db.add(note)

            db.commit()

        # 8. Seed Moderation Item
        if db.query(ModerationItem).count() == 0:
            print("Seeding Moderation Item...")
            mod = ModerationItem(
                id="MOD-0001",
                type=ModerationType.JOB_POSTING,
                target_id="JOB-2001",
                target_name="Senior Backend Engineer — ABC Technologies",
                company_id=company.id,
                reason="Flagged for review by automated keyword policy check.",
                flagged_by="System — keyword filter",
                status=ModerationStatus.OPEN,
                target_data={"title": "Senior Backend Engineer", "location": "Ho Chi Minh City"},
            )
            db.add(mod)
            db.commit()

        print("Database seeding completed successfully!")
    finally:
        db.close()


if __name__ == "__main__":
    seed_database()
