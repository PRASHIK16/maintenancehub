"""
Management command: seed_college

Seeds the database with a realistic IT engineering college scenario.
Replaces existing demo data (except superusers).

Usage:
    python manage.py seed_college
    python manage.py seed_college --keep-tickets   (keep existing tickets)
"""
import random
from django.core.management.base import BaseCommand
from django.utils.text import slugify
from django.db import transaction
from apps.organizations.models import Organization, Location, Team, TeamMembership
from apps.accounts.models import User
from apps.tickets.models import Ticket, Category
from apps.assets.models import Asset


COLLEGE_NAME = "Ramanujan Institute of Technology"
COLLEGE_SLUG = "ramanujan-it"

CATEGORIES = [
    ("Electrical", "#f59e0b"),
    ("Plumbing", "#3b82f6"),
    ("Internet / IT", "#8b5cf6"),
    ("Civil / Structural", "#6b7280"),
    ("HVAC & Ventilation", "#06b6d4"),
    ("Furniture & Fixtures", "#84cc16"),
    ("Cleaning & Sanitation", "#10b981"),
    ("Lab Equipment", "#f97316"),
    ("Security & Access", "#ef4444"),
    ("Lift / Elevator", "#a78bfa"),
]

TEAMS = [
    ("Electrical Team", "#f59e0b", "Handles all electrical repairs, wiring, and power issues across campus."),
    ("Plumbing Team", "#3b82f6", "Water supply, drainage, leaks, and sanitation infrastructure."),
    ("IT & Networks", "#8b5cf6", "Internet, networking, servers, lab equipment and AV systems."),
    ("Civil Works", "#6b7280", "Structural repairs, painting, roofing, and civil infrastructure."),
    ("Housekeeping", "#10b981", "Campus-wide cleaning, sanitation, and waste management."),
]

# (email, full_name, role, phone)
USERS = [
    ("admin@rit.edu", "Dr. Ramesh Kumar", "admin", "9800000001"),
    ("facilities@rit.edu", "Anita Sharma", "manager", "9800000002"),
    ("hod.it@rit.edu", "Prof. Suresh Nair", "manager", "9800000003"),
    ("elec.lead@rit.edu", "Vikram Patil", "staff", "9800000010"),
    ("plumb.lead@rit.edu", "Raju Yadav", "staff", "9800000011"),
    ("it.lead@rit.edu", "Priya Menon", "staff", "9800000012"),
    ("civil.lead@rit.edu", "Mohammed Khan", "staff", "9800000013"),
    ("hk.lead@rit.edu", "Savita Bai", "staff", "9800000014"),
    ("student1@rit.edu", "Arjun Reddy", "user", "9800000020"),
    ("student2@rit.edu", "Neha Gupta", "user", "9800000021"),
    ("student3@rit.edu", "Rohan Das", "user", "9800000022"),
    ("faculty1@rit.edu", "Dr. Kavitha Iyer", "user", "9800000030"),
    ("faculty2@rit.edu", "Prof. Arun Mehta", "user", "9800000031"),
]

# Location hierarchy: (name, type, parent_name)
LOCATIONS = [
    # Academic Block
    ("Academic Block A", "building", None),
    ("Ground Floor", "floor", "Academic Block A"),
    ("Seminar Hall 1", "room", "Ground Floor"),
    ("Faculty Room A01", "room", "Ground Floor"),
    ("First Floor", "floor", "Academic Block A"),
    ("CS Lab 1 (Hardware Lab)", "room", "First Floor"),
    ("CS Lab 2 (Software Lab)", "room", "First Floor"),
    ("Classroom A101", "room", "First Floor"),
    ("Classroom A102", "room", "First Floor"),
    ("Second Floor", "floor", "Academic Block A"),
    ("CS Lab 3 (Networks Lab)", "room", "Second Floor"),
    ("HOD Cabin (IT)", "room", "Second Floor"),
    ("Staff Room A", "room", "Second Floor"),

    # Academic Block B
    ("Academic Block B", "building", None),
    ("Ground Floor B", "floor", "Academic Block B"),
    ("Principal Office", "room", "Ground Floor B"),
    ("Admin Office", "room", "Ground Floor B"),
    ("First Floor B", "floor", "Academic Block B"),
    ("ECE Lab 1", "room", "First Floor B"),
    ("ECE Lab 2", "room", "First Floor B"),
    ("Second Floor B", "floor", "Academic Block B"),
    ("MBA Classroom B201", "room", "Second Floor B"),
    ("MBA Classroom B202", "room", "Second Floor B"),

    # Library
    ("Central Library", "building", None),
    ("Reading Hall", "area", "Central Library"),
    ("Digital Resource Centre", "room", "Central Library"),
    ("Periodical Section", "area", "Central Library"),

    # Hostel
    ("Men's Hostel Block 1", "block", None),
    ("Ground Floor H1", "floor", "Men's Hostel Block 1"),
    ("Common Room H1", "room", "Ground Floor H1"),
    ("Warden Office H1", "room", "Ground Floor H1"),
    ("First Floor H1", "floor", "Men's Hostel Block 1"),
    ("Room 101", "room", "First Floor H1"),
    ("Room 102", "room", "First Floor H1"),
    ("Room 103", "room", "First Floor H1"),

    ("Women's Hostel Block 1", "block", None),
    ("Ground Floor WH1", "floor", "Women's Hostel Block 1"),
    ("Common Room WH1", "room", "Ground Floor WH1"),
    ("First Floor WH1", "floor", "Women's Hostel Block 1"),
    ("Room W101", "room", "First Floor WH1"),
    ("Room W102", "room", "First Floor WH1"),

    # Common areas
    ("Campus Common Areas", "building", None),
    ("Main Entrance & Lobby", "area", "Campus Common Areas"),
    ("Canteen", "room", "Campus Common Areas"),
    ("Sports Ground", "outdoor", "Campus Common Areas"),
    ("Parking Area", "outdoor", "Campus Common Areas"),
    ("Generator Room", "room", "Campus Common Areas"),
]

TICKET_TEMPLATES = [
    # (title, description, category_name, priority, location_partial)
    ("Fan not working in CS Lab 1", "The ceiling fan in CS Lab 1 has stopped working. Students are uncomfortable during practical sessions.", "Electrical", "high", "CS Lab 1"),
    ("Projector display flickering in Classroom A101", "The projector in A101 keeps flickering during lectures. It needs urgent repair before exams.", "Electrical", "high", "Classroom A101"),
    ("Water leakage from pipe in Men's Hostel", "Water is dripping from a cracked pipe near Room 102. The floor is wet and slippery.", "Plumbing", "critical", "Room 102"),
    ("Internet not working in CS Lab 2", "All computers in CS Lab 2 show no network connectivity since this morning. Practical exam tomorrow.", "Internet / IT", "critical", "CS Lab 2"),
    ("Broken window pane in Library Reading Hall", "One of the glass window panes is cracked in the reading hall. Rain is getting in.", "Civil / Structural", "medium", "Reading Hall"),
    ("AC not cooling in HOD Cabin", "The air conditioner in HOD IT cabin is running but not cooling. Temperature is too high.", "HVAC & Ventilation", "high", "HOD Cabin (IT)"),
    ("Washroom tap leaking in Academic Block A", "The tap in the 1st floor washroom of Block A is continuously dripping water.", "Plumbing", "medium", "First Floor"),
    ("Laptop docking station faulty in Staff Room", "Two docking stations in Staff Room A are not working. Faculty cannot connect to monitors.", "Internet / IT", "medium", "Staff Room A"),
    ("Benches broken in Seminar Hall 1", "3 benches in Seminar Hall 1 have loose legs. Safety concern for students.", "Furniture & Fixtures", "medium", "Seminar Hall 1"),
    ("Street lights not working near parking", "The two street lights near the parking area are off since 3 days. Safety concern at night.", "Electrical", "high", "Parking Area"),
    ("Canteen kitchen exhaust fan stopped", "The exhaust fan in the canteen kitchen is not working. Smoke is filling the kitchen area.", "HVAC & Ventilation", "high", "Canteen"),
    ("Whiteboard markers exhausted in Classroom A102", "All whiteboard markers in A102 are dry. Faculty unable to write on board.", "Furniture & Fixtures", "low", "Classroom A102"),
    ("Drain blocked in Women's Hostel bathroom", "Drain in the WH1 first floor bathroom is completely blocked. Water is accumulating.", "Plumbing", "high", "First Floor WH1"),
    ("Network switch needs replacement in CS Lab 3", "The network switch in CS Lab 3 is failing intermittently causing packet loss.", "Internet / IT", "high", "CS Lab 3 (Networks Lab)"),
    ("Lift not working in Academic Block B", "The lift in Block B is stuck at 2nd floor. Faculty with mobility issues affected.", "Lift / Elevator", "critical", "Second Floor B"),
    ("Ant infestation in Digital Resource Centre", "Large number of ants have appeared near the computers in DRC. Needs pest control.", "Cleaning & Sanitation", "medium", "Digital Resource Centre"),
    ("Power socket sparking in ECE Lab 1", "One of the 3-pin sockets in ECE Lab 1 is sparking when plugged in. Very dangerous.", "Electrical", "critical", "ECE Lab 1"),
    ("Oscilloscope not working in ECE Lab 2", "The Tektronix oscilloscope is showing error and not booting. Lab practicals affected.", "Lab Equipment", "high", "ECE Lab 2"),
    ("Generator room door lock broken", "The lock on the generator room door is broken. Safety and security concern.", "Security & Access", "high", "Generator Room"),
    ("Hostel common room TV remote missing", "The TV remote in Men's Hostel common room is missing. Students cannot operate the TV.", "Furniture & Fixtures", "low", "Common Room H1"),
]

STATUSES_FOR_SEED = [
    "open", "open", "assigned", "in_progress", "in_progress",
    "resolved", "closed", "on_hold",
]


class Command(BaseCommand):
    help = "Seed database with college (IT engineering) demo data"

    def add_arguments(self, parser):
        parser.add_argument("--keep-tickets", action="store_true", help="Do not delete existing tickets")

    @transaction.atomic
    def handle(self, *args, **options):
        self.stdout.write(self.style.MIGRATE_HEADING("🎓 Seeding college demo data for Ramanujan Institute of Technology..."))

        # ── Organization ──────────────────────────────────────────────
        org, _ = Organization.objects.update_or_create(
            slug=COLLEGE_SLUG,
            defaults={
                "name": COLLEGE_NAME,
                "org_type": "college",
                "description": "A leading private engineering college offering B.Tech, M.Tech and MBA programmes.",
                "phone": "+91 80 2345 6789",
                "email": "admin@rit.edu",
                "address": "123 Knowledge Park, Electronic City",
                "city": "Bengaluru",
                "state": "Karnataka",
                "country": "India",
                "is_active": True,
                "enable_asset_management": True,
                "enable_preventive_maintenance": True,
                "enable_sla": True,
                "enable_ai_classification": False,
            },
        )
        # Deactivate any other orgs to avoid confusion
        Organization.objects.exclude(pk=org.pk).update(is_active=False)
        self.stdout.write(f"  ✓ Organization: {org.name}")

        # ── Wipe old non-superuser data ───────────────────────────────
        if not options["keep_tickets"]:
            Ticket.objects.filter(organization=org).delete()
        Location.objects.filter(organization=org).delete()
        Team.objects.filter(organization=org).delete()
        Category.objects.filter(organization=org).delete()
        Asset.objects.filter(organization=org).delete()
        User.objects.filter(organization=org).exclude(is_superuser=True).delete()

        # ── Categories ────────────────────────────────────────────────
        cat_map = {}
        for name, color in CATEGORIES:
            cat = Category.objects.create(organization=org, name=name, color=color)
            cat_map[name] = cat
        self.stdout.write(f"  ✓ {len(cat_map)} categories created")

        # ── Users ─────────────────────────────────────────────────────
        user_map = {}
        for email, full_name, role, phone in USERS:
            u = User.objects.create_user(
                email=email,
                full_name=full_name,
                password="demo1234",
                role=role,
                phone=phone,
                organization=org,
                is_email_verified=True,
                is_active=True,
            )
            user_map[email] = u
        self.stdout.write(f"  ✓ {len(user_map)} users created  (password: demo1234)")

        # ── Locations ─────────────────────────────────────────────────
        loc_map = {}
        for name, loc_type, parent_name in LOCATIONS:
            parent = loc_map.get(parent_name) if parent_name else None
            try:
                loc = Location.objects.create(
                    organization=org,
                    name=name,
                    location_type=loc_type,
                    parent=parent,
                    is_active=True,
                )
                loc_map[name] = loc
            except Exception as e:
                self.stdout.write(self.style.WARNING(f"  ! Location '{name}': {e}"))
        self.stdout.write(f"  ✓ {len(loc_map)} locations created")

        # ── Teams ─────────────────────────────────────────────────────
        staff_users = list(User.objects.filter(organization=org, role="staff"))
        team_assignments = {
            "Electrical Team": "elec.lead@rit.edu",
            "Plumbing Team": "plumb.lead@rit.edu",
            "IT & Networks": "it.lead@rit.edu",
            "Civil Works": "civil.lead@rit.edu",
            "Housekeeping": "hk.lead@rit.edu",
        }
        team_map = {}
        for team_name, desc_text, color in [(n, d, c) for n, c, d in TEAMS]:
            team = Team.objects.create(
                organization=org,
                name=team_name,
                description=color,  # swapped — fix below
                color=desc_text,
            )
            team_map[team_name] = team

        # Redo with correct fields
        Team.objects.filter(organization=org).delete()
        for team_name, color, description in TEAMS:
            team = Team.objects.create(
                organization=org, name=team_name, color=color, description=description,
            )
            team_map[team_name] = team
            lead_email = team_assignments.get(team_name)
            if lead_email and lead_email in user_map:
                TeamMembership.objects.create(team=team, user=user_map[lead_email], is_lead=True)

        self.stdout.write(f"  ✓ {len(team_map)} teams created")

        # ── Tickets ───────────────────────────────────────────────────
        if not options["keep_tickets"]:
            reporters = [u for e, u in user_map.items() if "student" in e or "faculty" in e]
            staff_list = [u for e, u in user_map.items() if u.role == "staff"]
            manager = user_map.get("facilities@rit.edu")

            created = 0
            for i, (title, desc, cat_name, priority, loc_partial) in enumerate(TICKET_TEMPLATES):
                # Find matching location
                loc = next((v for k, v in loc_map.items() if loc_partial in k), None)
                category = cat_map.get(cat_name)
                reporter = reporters[i % len(reporters)]
                status = STATUSES_FOR_SEED[i % len(STATUSES_FOR_SEED)]
                assignee = staff_list[i % len(staff_list)] if status not in ("open",) else None

                ticket = Ticket.objects.create(
                    organization=org,
                    title=title,
                    description=desc,
                    category=category,
                    priority=priority,
                    status=status,
                    location=loc,
                    created_by=reporter,
                    assigned_to=assignee,
                )
                created += 1

            self.stdout.write(f"  ✓ {created} tickets created")

        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS("✅ College seed complete!"))
        self.stdout.write("")
        self.stdout.write("  Login credentials (all use password: demo1234)")
        self.stdout.write("  ─────────────────────────────────────────────────")
        self.stdout.write("  Admin:    admin@rit.edu")
        self.stdout.write("  Manager:  facilities@rit.edu")
        self.stdout.write("  Staff:    elec.lead@rit.edu / it.lead@rit.edu")
        self.stdout.write("  Student:  student1@rit.edu")
        self.stdout.write("  Faculty:  faculty1@rit.edu")
        self.stdout.write("")
        self.stdout.write("  Run: python manage.py runserver")
        self.stdout.write("  URL: http://localhost:8000/")
