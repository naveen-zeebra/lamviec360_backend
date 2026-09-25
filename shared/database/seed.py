import sys
import json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

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
)
from shared.utils.password import hash_password
from shared.utils.logger import get_logger

logger = get_logger("seeder")

MODULES = ["DASHBOARD", "USERS", "ROLES", "COMPANIES", "JOBSEEKERS", "JOBS", "APPLICATIONS", "AUDIT_LOGS"]

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

        # 3. Seed Platform Admin Roles & Permissions for Super Admin Platform
        admin_roles_data = [
            ("Super Admin", "super_admin", "Complete platform root superuser access with all privileges"),
            ("Operations Admin", "operations_admin", "Tenant moderation, job management, and operational workflows"),
            ("Compliance Officer", "compliance_officer", "Platform compliance, legal review, and data governance"),
            ("Billing Manager", "billing_manager", "Commercial plan management, billing tiers, and revenue oversight"),
            ("Read-Only Auditor", "read_only_auditor", "Read-only access across all platform modules"),
        ]
        admin_modules = [
            "DASHBOARD", "ANALYTICS", "TENANTS", "USERS", "COMMERCIAL",
            "GOVERNANCE", "CONFIGURATION", "ADMIN_MANAGEMENT", "ACCOUNT"
        ]

        admin_role_map = {}
        for name, code, desc in admin_roles_data:
            arole = db.query(AdminRole).filter_by(code=code).first()
            if not arole:
                arole = AdminRole(name=name, code=code, description=desc, is_system=True)
                db.add(arole)
                db.flush()
            admin_role_map[code] = arole

            # Populate permissions
            existing_admin_mods = {p.module_key for p in arole.permissions}
            for amod in admin_modules:
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

        # 4. Seed Dedicated Platform Administrators into admin_users Table
        super_admins_to_seed = [
            ("superadmin@lamviec360.vn", "password123", "Nguyen", "Van An", "+84 901 234 567", "super_admin"),
            ("admin@jobportal.com", "Admin@123", "Super", "Administrator", "+84 900 000 000", "super_admin"),
            ("operations@lamviec360.vn", "password123", "Tran", "Thi Mai", "+84 912 345 678", "operations_admin"),
            ("compliance@lamviec360.vn", "password123", "Le", "Hoang Nam", "+84 933 456 789", "compliance_officer"),
            ("billing@lamviec360.vn", "password123", "Pham", "Minh Duc", "+84 944 567 890", "billing_manager"),
        ]

        for email, pwd, fname, lname, phone, rcode in super_admins_to_seed:
            existing_adm = db.query(AdminUser).filter_by(email=email).first()
            if not existing_adm:
                role_obj = admin_role_map.get(rcode)
                new_adm = AdminUser(
                    email=email,
                    password_hash=hash_password(pwd),
                    first_name=fname,
                    last_name=lname,
                    phone=phone,
                    role_id=role_obj.id if role_obj else None,
                    role_name=role_obj.name if role_obj else "Super Admin",
                    is_active=True,
                )
                db.add(new_adm)
                db.flush()
                logger.info(f"Created dedicated admin user: {email}")

        # =====================================================================
        # 5. SEED TENANT 1: TechCorp Global (company@techcorp.com / Company@123)
        # =====================================================================
        techcorp_email = "company@techcorp.com"
        techcorp_user = db.query(User).filter_by(email=techcorp_email).first()
        if not techcorp_user:
            techcorp_user = User(
                email=techcorp_email,
                hashed_password=hash_password("Company@123"),
                full_name="David Nguyen",
                user_type="company",
                phone="+84 28 3910 1122",
                is_superuser=False,
                is_verified=True,
                is_active=True,
                roles=[role_map["company"]],
            )
            db.add(techcorp_user)
            db.flush()
            logger.info("Created Tenant 1 User: company@techcorp.com")

        techcorp_settings = json.dumps({
            "notifications": {
                "newApplications": True,
                "interviewReminders": True,
                "teamActivity": True,
                "billing": True,
                "marketing": False,
            },
            "security": {"twoFactor": True},
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

        techcorp_profile = db.query(CompanyProfile).filter_by(user_id=techcorp_user.id).first()
        if not techcorp_profile:
            techcorp_profile = CompanyProfile(
                user_id=techcorp_user.id,
                company_name="TechCorp Global",
                legal_name="TechCorp Innovations Vietnam Ltd",
                tax_code="0315891234",
                contact_person="David Nguyen (VP of Engineering)",
                contact_email="careers@techcorp.com",
                contact_phone="+84 28 3910 1122",
                founded_year=2016,
                industry="Software & IT",
                company_size="201–500 employees",
                about="TechCorp Global is a premier software engineering firm delivering enterprise cloud platforms, AI integrations, and digital products for Fortune 500 customers across APAC and North America.",
                website="https://techcorp.example.com",
                linkedin_url="https://linkedin.com/company/techcorp-global",
                facebook_url="https://facebook.com/techcorpglobal",
                address="Level 15, Saigon Centre Tower 2, 67 Le Loi Boulevard, District 1",
                city="Ho Chi Minh City",
                country="Vietnam",
                benefits="13th month bonus + annual performance bonus (up to 3 months), Premium Bao Viet healthcare for employee & family, 18 annual leave days, Hybrid work model (2 days remote/week), High-end MacBook Pro M3 Max provided",
                verification_status="verified",
                is_featured=True,
                subscription_tier="Professional",
                settings=techcorp_settings,
            )
            db.add(techcorp_profile)
            db.flush()
            logger.info("Created Tenant 1 Profile: TechCorp Global")
        else:
            # Update missing extended fields if already exists
            techcorp_profile.tax_code = techcorp_profile.tax_code or "0315891234"
            techcorp_profile.contact_person = techcorp_profile.contact_person or "David Nguyen (VP of Engineering)"
            techcorp_profile.contact_email = techcorp_profile.contact_email or "careers@techcorp.com"
            techcorp_profile.contact_phone = techcorp_profile.contact_phone or "+84 28 3910 1122"
            techcorp_profile.founded_year = techcorp_profile.founded_year or 2016
            techcorp_profile.linkedin_url = techcorp_profile.linkedin_url or "https://linkedin.com/company/techcorp-global"
            techcorp_profile.facebook_url = techcorp_profile.facebook_url or "https://facebook.com/techcorpglobal"
            techcorp_profile.address = techcorp_profile.address or "Level 15, Saigon Centre Tower 2, 67 Le Loi Boulevard, District 1"
            techcorp_profile.benefits = techcorp_profile.benefits or "13th month bonus + annual performance bonus, Premium healthcare, Hybrid work model, MacBook Pro M3 Max"
            techcorp_profile.subscription_tier = "Professional"
            if not techcorp_profile.settings:
                techcorp_profile.settings = techcorp_settings
            db.flush()

        # =====================================================================
        # 6. SEED TENANT 2: ABC Technologies (lan.tran@abctech.vn / password123)
        # =====================================================================
        abctech_email = "lan.tran@abctech.vn"
        abctech_user = db.query(User).filter_by(email=abctech_email).first()
        if not abctech_user:
            abctech_user = User(
                email=abctech_email,
                hashed_password=hash_password("password123"),
                full_name="Lan Tran",
                user_type="company",
                phone="+84 24 3788 5678",
                is_superuser=False,
                is_verified=True,
                is_active=True,
                roles=[role_map["company"]],
            )
            db.add(abctech_user)
            db.flush()
            logger.info("Created Tenant 2 User: lan.tran@abctech.vn")

        abctech_settings = json.dumps({
            "notifications": {
                "newApplications": True,
                "interviewReminders": True,
                "teamActivity": True,
                "billing": True,
                "marketing": False,
            },
            "security": {"twoFactor": True},
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

        abctech_profile = db.query(CompanyProfile).filter_by(user_id=abctech_user.id).first()
        if not abctech_profile:
            abctech_profile = CompanyProfile(
                user_id=abctech_user.id,
                company_name="ABC Technologies",
                legal_name="Cong Ty Co Phan Cong Nghe ABC Viet Nam",
                tax_code="0108923456",
                contact_person="Lan Tran (Head of Talent Acquisition)",
                contact_email="recruitment@abctech.vn",
                contact_phone="+84 24 3788 5678",
                founded_year=2019,
                industry="Technology",
                company_size="51–200 employees",
                about="ABC Technologies is one of Vietnam's fastest-growing technology pioneers, building next-generation SaaS workforce platforms, modern fintech solutions, and AI-driven automation systems.",
                website="https://abctech.vn",
                linkedin_url="https://linkedin.com/company/abc-tech-vn",
                facebook_url="https://facebook.com/abctechvietnam",
                address="Floor 8, Keangnam Landmark 72, Pham Hung Road, Nam Tu Liem District",
                city="Hanoi",
                country="Vietnam",
                benefits="14 months guaranteed salary package, Full comprehensive health insurance, Flexible working hours (core hours 9:30 - 16:30), Annual company luxury retreat in Da Nang, Continuous learning budget $1000/year",
                verification_status="verified",
                is_featured=True,
                subscription_tier="Enterprise",
                settings=abctech_settings,
            )
            db.add(abctech_profile)
            db.flush()
            logger.info("Created Tenant 2 Profile: ABC Technologies")
        else:
            # Update missing extended fields if already exists
            abctech_profile.tax_code = abctech_profile.tax_code or "0108923456"
            abctech_profile.contact_person = abctech_profile.contact_person or "Lan Tran (Head of Talent Acquisition)"
            abctech_profile.contact_email = abctech_profile.contact_email or "recruitment@abctech.vn"
            abctech_profile.contact_phone = abctech_profile.contact_phone or "+84 24 3788 5678"
            abctech_profile.founded_year = abctech_profile.founded_year or 2019
            abctech_profile.linkedin_url = abctech_profile.linkedin_url or "https://linkedin.com/company/abc-tech-vn"
            abctech_profile.facebook_url = abctech_profile.facebook_url or "https://facebook.com/abctechvietnam"
            abctech_profile.address = abctech_profile.address or "Floor 8, Keangnam Landmark 72, Pham Hung Road, Nam Tu Liem District"
            abctech_profile.city = abctech_profile.city or "Hanoi"
            abctech_profile.benefits = abctech_profile.benefits or "14 months guaranteed salary package, Comprehensive health insurance, Flexible hours, $1000/year learning budget"
            abctech_profile.subscription_tier = "Enterprise"
            if not abctech_profile.settings:
                abctech_profile.settings = abctech_settings
            db.flush()

        # =====================================================================
        # 7. SEED DEMO JOB SEEKERS
        # =====================================================================
        seekers_seed_data = [
            (
                "seeker@example.com",
                "Seeker@123",
                "Nguyen Van A",
                "+84 908 111 222",
                "Senior Full Stack Engineer (Python & React)",
                "Experienced engineer with 6+ years of building resilient backend microservices, distributed caching, and modern React SPAs.",
                "Python, FastAPI, React, TypeScript, PostgreSQL, Docker, Redis",
                6.0,
                3200.0,
                "Ho Chi Minh City",
            ),
            (
                "hoa.le@candidate.vn",
                "Password123!",
                "Le Thi Hoa",
                "+84 919 333 444",
                "Senior QA Automation Specialist (Playwright / CI-CD)",
                "Quality engineer specializing in end-to-end automation, regression testing, and CI/CD test pipelines for modern web & mobile apps.",
                "Playwright, Cypress, Selenium, Python, JavaScript, Jest, GitHub Actions",
                4.5,
                2200.0,
                "Hanoi",
            ),
            (
                "minh.tran@design.vn",
                "Password123!",
                "Tran Minh Duc",
                "+84 938 555 666",
                "Principal Product Designer & Design System Lead",
                "Human-centered UI/UX designer with 7 years crafting design systems, user journey maps, and high-conversion SaaS web applications.",
                "Figma, Design Systems, Wireframing, User Research, Prototyping, CSS3",
                7.0,
                2800.0,
                "Ho Chi Minh City",
            ),
        ]

        seeker_profiles = []
        for email, pwd, fname, phone, headline, bio, skills, exp, sal, city in seekers_seed_data:
            s_user = db.query(User).filter_by(email=email).first()
            if not s_user:
                s_user = User(
                    email=email,
                    hashed_password=hash_password(pwd),
                    full_name=fname,
                    user_type="jobseeker",
                    phone=phone,
                    is_superuser=False,
                    is_verified=True,
                    is_active=True,
                    roles=[role_map["jobseeker"]],
                )
                db.add(s_user)
                db.flush()

            s_prof = db.query(JobSeekerProfile).filter_by(user_id=s_user.id).first()
            if not s_prof:
                s_prof = JobSeekerProfile(
                    user_id=s_user.id,
                    headline=headline,
                    bio=bio,
                    skills=skills,
                    experience_years=exp,
                    expected_salary=sal,
                    city=city,
                    country="Vietnam",
                    github_url="https://github.com",
                    linkedin_url="https://linkedin.com",
                )
                db.add(s_prof)
                db.flush()
            seeker_profiles.append(s_prof)

        # =====================================================================
        # 8. SEED TENANT 1 JOBS (TechCorp Global)
        # =====================================================================
        techcorp_jobs_count = db.query(JobPosting).filter_by(company_id=techcorp_profile.id, is_deleted=False).count()
        techcorp_job_list = []
        if techcorp_jobs_count == 0:
            job_t1 = JobPosting(
                company_id=techcorp_profile.id,
                title="Senior Python / FastAPI Backend Engineer",
                description="We are looking for an experienced Backend Engineer to design and scale the microservices behind our enterprise hiring platform. You will lead system design, mentor team members, and drive architecture decisions.",
                requirements="5+ years of production experience in Python, FastAPI or Django, PostgreSQL, Redis, Docker, and REST API design.",
                benefits="Competitive salary ($2500 - $3500), 13th month bonus, premium Bao Viet healthcare, high-end MacBook Pro.",
                job_type="Full-time",
                workplace_type="Hybrid",
                experience_level="Senior",
                city="Ho Chi Minh City",
                country="Vietnam",
                salary_min=35000000.0,
                salary_max=55000000.0,
                salary_currency="VND",
                required_skills="Python, FastAPI, PostgreSQL, Docker, Redis",
                status="published",
                moderation_status="approved",
            )
            job_t2 = JobPosting(
                company_id=techcorp_profile.id,
                title="Lead Frontend Engineer (React & TypeScript)",
                description="Join our frontend platform team to craft ultra-responsive user interfaces and reusable design system component libraries using React 19, TypeScript, and modern styling.",
                requirements="Deep expertise in React, TypeScript, state management, web performance optimization, and clean architecture.",
                benefits="Attractive salary ($2200 - $3200), flexible hours, stock options, luxury annual team retreat.",
                job_type="Full-time",
                workplace_type="Hybrid",
                experience_level="Lead",
                city="Ho Chi Minh City",
                country="Vietnam",
                salary_min=30000000.0,
                salary_max=50000000.0,
                salary_currency="VND",
                required_skills="React, TypeScript, Next.js, TailwindCSS, State Management",
                status="published",
                moderation_status="approved",
            )
            job_t3 = JobPosting(
                company_id=techcorp_profile.id,
                title="Senior Cloud DevOps & Platform Engineer (AWS / K8s)",
                description="Own our cloud infrastructure automation, CI/CD deployment pipelines, and observability stack across multi-region Kubernetes clusters on AWS.",
                requirements="Strong expertise in AWS, Kubernetes (EKS), Terraform, Docker, CI/CD automation, and Prometheus/Grafana monitoring.",
                benefits="Excellent compensation ($2600 - $3800), comprehensive medical package, annual tech conference budget.",
                job_type="Full-time",
                workplace_type="Remote",
                experience_level="Senior",
                city="Ho Chi Minh City",
                country="Vietnam",
                salary_min=40000000.0,
                salary_max=65000000.0,
                salary_currency="VND",
                required_skills="AWS, Kubernetes, Docker, Terraform, CI/CD",
                status="published",
                moderation_status="approved",
            )
            db.add_all([job_t1, job_t2, job_t3])
            db.flush()
            techcorp_job_list = [job_t1, job_t2, job_t3]
            logger.info("Created 3 demo jobs for Tenant 1 (TechCorp Global)")
        else:
            techcorp_job_list = db.query(JobPosting).filter_by(company_id=techcorp_profile.id, is_deleted=False).all()

        # =====================================================================
        # 9. SEED TENANT 2 JOBS (ABC Technologies)
        # =====================================================================
        abctech_jobs_count = db.query(JobPosting).filter_by(company_id=abctech_profile.id, is_deleted=False).count()
        abctech_job_list = []
        if abctech_jobs_count == 0:
            job_a1 = JobPosting(
                company_id=abctech_profile.id,
                title="Full Stack Product Engineer (Next.js & Python)",
                description="ABC Technologies is looking for a versatile Full Stack Product Engineer to develop customer-facing SaaS modules from initial concept to high-scale production.",
                requirements="3+ years building full-stack applications with React/Next.js, Python or Node.js, relational databases, and modern APIs.",
                benefits="14 months guaranteed salary, comprehensive healthcare, flexible core working hours, $1000/year learning budget.",
                job_type="Full-time",
                workplace_type="Hybrid",
                experience_level="Mid-Senior",
                city="Hanoi",
                country="Vietnam",
                salary_min=28000000.0,
                salary_max=45000000.0,
                salary_currency="VND",
                required_skills="Next.js, React, Python, PostgreSQL, REST APIs",
                status="published",
                moderation_status="approved",
            )
            job_a2 = JobPosting(
                company_id=abctech_profile.id,
                title="Senior QA Automation Engineer (Playwright & CI/CD)",
                description="Lead automated end-to-end quality assurance across our suite of web applications. Design scalable test frameworks and integrate automated regression suites into CI pipelines.",
                requirements="Solid experience with Playwright or Cypress, TypeScript, API test automation, and GitHub Actions integration.",
                benefits="Attractive package (up to 38M VND), premium medical plan, annual luxury team trip, MacBook Pro.",
                job_type="Full-time",
                workplace_type="Hybrid",
                experience_level="Senior",
                city="Hanoi",
                country="Vietnam",
                salary_min=25000000.0,
                salary_max=38000000.0,
                salary_currency="VND",
                required_skills="Playwright, TypeScript, Cypress, CI/CD, Automated Testing",
                status="published",
                moderation_status="approved",
            )
            job_a3 = JobPosting(
                company_id=abctech_profile.id,
                title="Principal Product Designer / UI-UX Lead",
                description="Lead the design vision and component design systems for our recruitment platforms. Turn complex employer and job seeker workflows into elegant, intuitive interfaces.",
                requirements="5+ years in product design, expert in Figma, design tokens, interactive prototyping, and cross-functional collaboration.",
                benefits="Market-leading salary ($2000 - $3000), stock options, flexible hybrid working, wellness allowance.",
                job_type="Full-time",
                workplace_type="Hybrid",
                experience_level="Lead",
                city="Hanoi",
                country="Vietnam",
                salary_min=32000000.0,
                salary_max=48000000.0,
                salary_currency="VND",
                required_skills="Figma, UI/UX Design, Design Systems, Prototyping, User Research",
                status="published",
                moderation_status="approved",
            )
            db.add_all([job_a1, job_a2, job_a3])
            db.flush()
            abctech_job_list = [job_a1, job_a2, job_a3]
            logger.info("Created 3 demo jobs for Tenant 2 (ABC Technologies)")
        else:
            abctech_job_list = db.query(JobPosting).filter_by(company_id=abctech_profile.id, is_deleted=False).all()

        # =====================================================================
        # 10. SEED ATS APPLICANTS & APPLICATIONS (Strictly Isolated per Tenant)
        # =====================================================================
        # Tenant 1 Applications
        if techcorp_job_list and len(seeker_profiles) >= 3:
            j1 = techcorp_job_list[0]
            j2 = techcorp_job_list[1] if len(techcorp_job_list) > 1 else j1
            
            existing_t1_apps = db.query(JobApplication).filter_by(job_id=j1.id).count()
            if existing_t1_apps == 0:
                app_t1 = JobApplication(
                    job_id=j1.id,
                    jobseeker_id=seeker_profiles[0].id,
                    status="interviewing",
                    rating=5,
                    cover_letter="I am passionate about building resilient FastAPI microservices and would love to bring my backend architecture expertise to TechCorp Global.",
                    recruiter_notes="Strong performance in round 1 technical interview. Recommended for system design round.",
                )
                app_t2 = JobApplication(
                    job_id=j2.id,
                    jobseeker_id=seeker_profiles[1].id,
                    status="applied",
                    rating=4,
                    cover_letter="My testing and frontend automation background allows me to ensure rock-solid user experiences across modern React platforms.",
                    recruiter_notes="Good portfolio and testing mindset.",
                )
                app_t3 = JobApplication(
                    job_id=j1.id,
                    jobseeker_id=seeker_profiles[2].id,
                    status="shortlisted",
                    rating=4,
                    cover_letter="Interested in the technical leadership opportunities at TechCorp Global.",
                    recruiter_notes="Profile shortlisted by engineering manager.",
                )
                db.add_all([app_t1, app_t2, app_t3])
                db.flush()
                logger.info("Created 3 demo applicants for Tenant 1 (TechCorp Global)")

        # Tenant 2 Applications
        if abctech_job_list and len(seeker_profiles) >= 3:
            ja1 = abctech_job_list[0]
            ja2 = abctech_job_list[1] if len(abctech_job_list) > 1 else ja1
            ja3 = abctech_job_list[2] if len(abctech_job_list) > 2 else ja1

            existing_t2_apps = db.query(JobApplication).filter_by(job_id=ja1.id).count()
            if existing_t2_apps == 0:
                app_a1 = JobApplication(
                    job_id=ja1.id,
                    jobseeker_id=seeker_profiles[0].id,
                    status="applied",
                    rating=4,
                    cover_letter="Excited about ABC Technologies' growth in Vietnam. I have built multiple Next.js + Python web products.",
                    recruiter_notes="Candidate has solid Next.js experience. Resume reviewed by Lan Tran.",
                )
                app_a2 = JobApplication(
                    job_id=ja2.id,
                    jobseeker_id=seeker_profiles[1].id,
                    status="interviewing",
                    rating=5,
                    cover_letter="I have 5 years building automated test suites with Playwright and GitHub Actions. ABC Tech's product suite aligns perfectly with my background.",
                    recruiter_notes="Excellent round 1 coding challenge. Scheduled for cultural interview.",
                )
                app_a3 = JobApplication(
                    job_id=ja3.id,
                    jobseeker_id=seeker_profiles[2].id,
                    status="shortlisted",
                    rating=5,
                    cover_letter="I love building scalable design systems and would be thrilled to lead UI/UX design at ABC Technologies.",
                    recruiter_notes="Exceptional Figma portfolio and design tokens knowledge.",
                )
                db.add_all([app_a1, app_a2, app_a3])
                db.flush()
                logger.info("Created 3 demo applicants for Tenant 2 (ABC Technologies)")

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
