"""
Management command: seed_demo
Creates a demo organization with realistic data:
  - 1 org (Green Valley Apartments)
  - 1 admin, 3 managers, 8 staff, 40 residents
  - 150+ tickets across all statuses and priorities
  - SLA rules, categories, locations
  - Comments, activities, notifications

Usage:
  python manage.py seed_demo
  python manage.py seed_demo --flush   # clear existing demo data first
"""
import random
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone
from django.contrib.auth import get_user_model

User = get_user_model()


CATEGORIES = [
    ("Plumbing", "🔧", ["Leaking tap", "Blocked drain", "Burst pipe", "No hot water", "Toilet not flushing"]),
    ("Electrical", "⚡", ["Power outage", "Faulty socket", "Lights flickering", "Tripped breaker", "Fan not working"]),
    ("HVAC", "❄️", ["AC not cooling", "Heater not working", "Strange noise from AC", "AC remote missing", "Duct cleaning"]),
    ("Structural", "🏗️", ["Crack in wall", "Ceiling leak", "Broken window", "Door not closing", "Flooring damaged"]),
    ("Cleaning", "🧹", ["Common area dirty", "Garbage not collected", "Pest infestation", "Graffiti removal"]),
    ("Security", "🔒", ["CCTV not working", "Main gate issue", "Intercom broken", "Lost key", "Lock replacement"]),
    ("Lift / Elevator", "🛗", ["Lift not working", "Lift door issue", "Emergency phone broken"]),
    ("Internet / IT", "🌐", ["No internet", "Router down", "Cable damaged"]),
]

BUILDINGS = [
    ("Block A", [("Floor 1", ["A-101", "A-102", "A-103"]),
                 ("Floor 2", ["A-201", "A-202", "A-203"]),
                 ("Floor 3", ["A-301", "A-302", "A-303"])]),
    ("Block B", [("Floor 1", ["B-101", "B-102", "B-103"]),
                 ("Floor 2", ["B-201", "B-202", "B-203"])]),
    ("Block C", [("Floor 1", ["C-101", "C-102"]),
                 ("Floor 2", ["C-201", "C-202"])]),
    ("Common Areas", [("Ground", ["Lobby", "Parking", "Gym", "Swimming Pool", "Garden"])]),
]

STAFF_NAMES = [
    ("Ramesh Kumar", "ramesh.kumar"),
    ("Suresh Patel", "suresh.patel"),
    ("Anil Singh", "anil.singh"),
    ("Priya Nair", "priya.nair"),
    ("Dinesh Yadav", "dinesh.yadav"),
    ("Kavitha Reddy", "kavitha.reddy"),
    ("Mohan Das", "mohan.das"),
    ("Sita Devi", "sita.devi"),
]

MANAGER_NAMES = [
    ("Vikram Sharma", "vikram.sharma"),
    ("Anjali Mehta", "anjali.mehta"),
    ("Rajiv Gupta", "rajiv.gupta"),
]

RESIDENT_NAMES = [
    ("Arjun Verma", "arjun.verma"),
    ("Meena Iyer", "meena.iyer"),
    ("Sanjay Joshi", "sanjay.joshi"),
    ("Pooja Desai", "pooja.desai"),
    ("Kiran Rao", "kiran.rao"),
    ("Anita Pillai", "anita.pillai"),
    ("Deepak Mishra", "deepak.mishra"),
    ("Sunita Tiwari", "sunita.tiwari"),
    ("Mahesh Pandey", "mahesh.pandey"),
    ("Lata Bhatt", "lata.bhatt"),
    ("Rahul Saxena", "rahul.saxena"),
    ("Geeta Menon", "geeta.menon"),
    ("Sunil Bose", "sunil.bose"),
    ("Rekha Nanda", "rekha.nanda"),
    ("Vivek Chopra", "vivek.chopra"),
    ("Nisha Goyal", "nisha.goyal"),
    ("Amit Tripathi", "amit.tripathi"),
    ("Smita Kulkarni", "smita.kulkarni"),
    ("Rakesh Choudhury", "rakesh.choudhury"),
    ("Divya Naik", "divya.naik"),
    ("Vikas Srivastava", "vikas.srivastava"),
    ("Padma Krishnan", "padma.krishnan"),
    ("Arun Malhotra", "arun.malhotra"),
    ("Savita Rao", "savita.rao"),
    ("Naresh Aggarwal", "naresh.aggarwal"),
    ("Asha Dubey", "asha.dubey"),
    ("Suresh Tyagi", "suresh.tyagi"),
    ("Usha Banerjee", "usha.banerjee"),
    ("Ashok Ghosh", "ashok.ghosh"),
    ("Ritu Kapoor", "ritu.kapoor"),
    ("Manohar Lal", "manohar.lal"),
    ("Swati Dixit", "swati.dixit"),
    ("Girish Wagh", "girish.wagh"),
    ("Chetna Shah", "chetna.shah"),
    ("Bharat Solanki", "bharat.solanki"),
    ("Alka Sondhi", "alka.sondhi"),
    ("Karthik Rajan", "karthik.rajan"),
    ("Preethi Sundaram", "preethi.sundaram"),
    ("Harish Deshpande", "harish.deshpande"),
    ("Jyoti Agarwal", "jyoti.agarwal"),
]

PRIORITIES = ["low", "medium", "high", "critical"]
PRIORITY_WEIGHTS = [20, 40, 28, 12]

TICKET_STATUS_DISTRIBUTION = [
    ("submitted", 15),
    ("triaged", 8),
    ("assigned", 18),
    ("in_progress", 22),
    ("on_hold", 5),
    ("resolved", 10),
    ("verification_pending", 8),
    ("closed", 12),
    ("cancelled", 2),
]

DEMO_PASSWORD = "Demo@1234"


class Command(BaseCommand):
    help = "Seed the database with demo data for MaintenanceHub"

    def add_arguments(self, parser):
        parser.add_argument("--flush", action="store_true", help="Remove existing demo org first")

    def handle(self, *args, **options):
        from apps.organizations.models import Organization, Location, Team, TeamMembership
        from apps.accounts.models import UserRole
        from apps.tickets.models import (
            Category, SLARule, Ticket, TicketStatus, Priority,
            TicketActivity, ActivityType, TicketComment, TicketStatusHistory,
        )
        from apps.notifications.models import Notification, NotificationType

        self.stdout.write(self.style.HTTP_INFO("🌱 Starting demo seed..."))

        if options["flush"]:
            org = Organization.objects.filter(slug="green-valley-apartments").first()
            if org:
                self.stdout.write("  Removing existing demo org...")
                org.delete()

        # ── Organization ──
        org, created = Organization.objects.get_or_create(
            slug="green-valley-apartments",
            defaults={
                "name": "Green Valley Apartments",
                "org_type": "apartment",
                "address": "123 Green Valley Road, Whitefield",
                "city": "Bengaluru",
                "state": "Karnataka",
                "country": "India",
                "email": "admin@greenvalley.in",
                "phone": "+91 80 1234 5678",
                "enable_asset_management": True,
                "enable_sla": True,
            }
        )
        if created:
            self.stdout.write(f"  ✓ Created org: {org.name}")
        else:
            self.stdout.write(f"  → Using existing org: {org.name}")

        # ── SLA Rules ──
        sla_rules = [
            ("critical", 2, 4),
            ("high", 4, 8),
            ("medium", 12, 24),
            ("low", 24, 72),
        ]
        for priority, response, resolution in sla_rules:
            SLARule.objects.get_or_create(
                organization=org,
                priority=priority,
                defaults={"response_time_hours": response, "resolution_time_hours": resolution},
            )
        self.stdout.write("  ✓ SLA rules configured")

        # ── Locations ──
        all_locations = []
        for building_name, floors in BUILDINGS:
            building, _ = Location.objects.get_or_create(
                organization=org,
                name=building_name,
                parent=None,
                defaults={"location_type": "building"},
            )
            for floor_name, rooms in floors:
                floor, _ = Location.objects.get_or_create(
                    organization=org,
                    name=floor_name,
                    parent=building,
                    defaults={"location_type": "floor"},
                )
                for room_name in rooms:
                    room, _ = Location.objects.get_or_create(
                        organization=org,
                        name=room_name,
                        parent=floor,
                        defaults={"location_type": "room"},
                    )
                    all_locations.append(room)
        self.stdout.write(f"  ✓ Created {len(all_locations)} locations")

        # ── Categories ──
        all_categories = []
        for cat_name, icon, _ in CATEGORIES:
            cat, _ = Category.objects.get_or_create(
                organization=org,
                name=cat_name,
                parent=None,
                defaults={"icon": icon},
            )
            all_categories.append(cat)
        self.stdout.write(f"  ✓ Created {len(all_categories)} categories")

        # ── Teams ──
        team_plumbing, _ = Team.objects.get_or_create(
            organization=org, name="Plumbing & Electrical",
            defaults={"color": "#6366f1"},
        )
        team_hvac, _ = Team.objects.get_or_create(
            organization=org, name="HVAC & Structural",
            defaults={"color": "#f59e0b"},
        )
        team_security, _ = Team.objects.get_or_create(
            organization=org, name="Security & IT",
            defaults={"color": "#22c55e"},
        )

        # ── Admin user ──
        admin_user, created = User.objects.get_or_create(
            email="admin@greenvalley.in",
            defaults={
                "full_name": "Admin User",
                "organization": org,
                "role": UserRole.ORG_ADMIN,
                "is_staff": True,
                "is_active": True,
                "is_email_verified": True,
            }
        )
        if created:
            admin_user.set_password(DEMO_PASSWORD)
            admin_user.save()
        self.stdout.write(f"  ✓ Admin: admin@greenvalley.in / {DEMO_PASSWORD}")

        # ── Managers ──
        managers = []
        for i, (full_name, username) in enumerate(MANAGER_NAMES):
            email = f"{username}@greenvalley.in"
            user, created = User.objects.get_or_create(
                email=email,
                defaults={
                    "full_name": full_name,
                    "organization": org,
                    "role": UserRole.MANAGER,
                    "is_active": True,
                    "is_email_verified": True,
                }
            )
            if created:
                user.set_password(DEMO_PASSWORD)
                user.save()
            managers.append(user)
        self.stdout.write(f"  ✓ {len(managers)} managers")

        # ── Staff ──
        staff_members = []
        for i, (full_name, username) in enumerate(STAFF_NAMES):
            email = f"{username}@greenvalley.in"
            user, created = User.objects.get_or_create(
                email=email,
                defaults={
                    "full_name": full_name,
                    "organization": org,
                    "role": UserRole.STAFF,
                    "is_active": True,
                    "is_email_verified": True,
                }
            )
            if created:
                user.set_password(DEMO_PASSWORD)
                user.save()
            staff_members.append(user)

            # Assign to teams
            team = [team_plumbing, team_hvac, team_security][i % 3]
            TeamMembership.objects.get_or_create(
                team=team, user=user,
                defaults={"is_lead": i % 3 == 0},
            )
        self.stdout.write(f"  ✓ {len(staff_members)} staff members")

        # ── Residents ──
        residents = []
        for i, (full_name, username) in enumerate(RESIDENT_NAMES):
            email = f"{username}@gmail.com"
            location = all_locations[i % len(all_locations)]
            user, created = User.objects.get_or_create(
                email=email,
                defaults={
                    "full_name": full_name,
                    "organization": org,
                    "role": UserRole.USER,
                    "is_active": True,
                    "is_email_verified": True,
                    "unit_number": location.name,
                    "phone": f"+91 98{random.randint(10000000, 99999999)}",
                }
            )
            if created:
                user.set_password(DEMO_PASSWORD)
                user.save()
            residents.append(user)
        self.stdout.write(f"  ✓ {len(residents)} residents")

        # ── Tickets ──
        now = timezone.now()
        tickets_created = 0

        for status, count in TICKET_STATUS_DISTRIBUTION:
            for i in range(count):
                cat_idx = random.randint(0, len(CATEGORIES) - 1)
                cat_name, _, issue_titles = CATEGORIES[cat_idx]
                category = all_categories[cat_idx]
                location = random.choice(all_locations)
                resident = random.choice(residents)
                priority = random.choices(PRIORITIES, weights=PRIORITY_WEIGHTS)[0]
                title = random.choice(issue_titles)

                created_days_ago = random.randint(1, 60)
                created_at = now - timedelta(days=created_days_ago, hours=random.randint(0, 23))

                ticket = Ticket(
                    organization=org,
                    created_by=resident,
                    title=title,
                    description=f"{title} in {location.name}. "
                                f"This has been affecting residents since "
                                f"{created_days_ago} day{'s' if created_days_ago > 1 else ''} ago. "
                                f"Please resolve at the earliest.",
                    category=category,
                    location=location,
                    priority=priority,
                    status=status,
                    contact_phone=resident.phone or "+91 9876543210",
                    preferred_visit_time=random.choice([
                        "Weekday mornings 9-11am",
                        "Anytime except weekends",
                        "Evening 5-7pm",
                        "Weekend mornings",
                        "",
                    ]),
                    created_at=created_at,
                    updated_at=created_at,
                )

                # Apply SLA
                sla_hours = {"critical": 4, "high": 8, "medium": 24, "low": 72}[priority]
                ticket.sla_response_due = created_at + timedelta(hours=sla_hours // 4)
                ticket.sla_resolution_due = created_at + timedelta(hours=sla_hours)

                # Assign staff for non-submitted tickets
                if status not in ("submitted", "cancelled"):
                    ticket.assigned_to = random.choice(staff_members)
                    ticket.assigned_team = random.choice([team_plumbing, team_hvac, team_security])
                    ticket.assigned_at = created_at + timedelta(hours=random.randint(1, 4))

                # Work started
                if status in ("in_progress", "on_hold", "resolved", "verification_pending", "closed"):
                    ticket.work_started_at = ticket.assigned_at + timedelta(hours=random.randint(1, 8))

                # Resolved
                if status in ("resolved", "verification_pending", "closed"):
                    ticket.resolved_at = ticket.work_started_at + timedelta(hours=random.randint(2, sla_hours))
                    ticket.sla_resolution_met = ticket.resolved_at <= ticket.sla_resolution_due
                    ticket.resolution_notes = random.choice([
                        "Issue has been resolved. The part was replaced and tested.",
                        "Repaired and tested successfully. Please verify.",
                        "Fixed the issue. Regular maintenance scheduled.",
                        "Resolved after inspection. No further action needed.",
                    ])

                # Closed
                if status == "closed":
                    ticket.closed_at = ticket.resolved_at + timedelta(hours=random.randint(2, 48))
                    ticket.rating = random.choices([1, 2, 3, 4, 5], weights=[2, 3, 10, 35, 50])[0]

                ticket.save()
                tickets_created += 1

                # Create activity
                TicketActivity.objects.create(
                    ticket=ticket,
                    actor=resident,
                    activity_type=ActivityType.TICKET_CREATED,
                    description="Ticket created",
                    timestamp=created_at,
                )

                if ticket.assigned_to:
                    assigner = random.choice(managers)
                    TicketActivity.objects.create(
                        ticket=ticket,
                        actor=assigner,
                        activity_type=ActivityType.ASSIGNED,
                        description=f"Assigned to {ticket.assigned_to.display_name}",
                        timestamp=ticket.assigned_at,
                    )

                # Add a comment for some tickets
                if random.random() < 0.6 and ticket.assigned_to:
                    comment_time = (ticket.assigned_at or created_at) + timedelta(hours=random.randint(1, 6))
                    TicketComment.objects.create(
                        ticket=ticket,
                        author=ticket.assigned_to,
                        body=random.choice([
                            "I've inspected the issue and will begin work shortly.",
                            "Parts have been ordered. Will fix tomorrow.",
                            "Work in progress. Should be resolved by end of day.",
                            "Issue identified. Awaiting spare parts.",
                            "Fixed the primary issue. Monitoring for any recurrence.",
                        ]),
                        created_at=comment_time,
                        updated_at=comment_time,
                    )

        self.stdout.write(f"  ✓ {tickets_created} tickets created across all statuses")

        # ── Print summary ──
        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS("=" * 60))
        self.stdout.write(self.style.SUCCESS("✅ Demo seed complete!"))
        self.stdout.write(self.style.SUCCESS("=" * 60))
        self.stdout.write("")
        self.stdout.write("  🏢 Organization: Green Valley Apartments")
        self.stdout.write("")
        self.stdout.write("  Demo Accounts (password: Demo@1234):")
        self.stdout.write(f"    Admin:   admin@greenvalley.in")
        self.stdout.write(f"    Manager: vikram.sharma@greenvalley.in")
        self.stdout.write(f"    Staff:   ramesh.kumar@greenvalley.in")
        self.stdout.write(f"    User:    arjun.verma@gmail.com")
        self.stdout.write("")
        self.stdout.write(f"  Tickets: {tickets_created}")
        self.stdout.write(f"  Users: {1 + len(managers) + len(staff_members) + len(residents)}")
        self.stdout.write("")
        self.stdout.write("  Start the server: python manage.py runserver")
        self.stdout.write("")
