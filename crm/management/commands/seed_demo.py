"""Creates a demo user and clearly fictional sample data. Safe to run twice."""
import random
from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.utils import timezone

from crm.models import Activity, Company, Contact, Deal

COMPANIES = [
    ("Northwind Demo Traders", "Retail"), ("Blue Harbor Example Logistics", "Logistics"),
    ("Sample Cedar Clinic", "Healthcare"), ("Acme Fictional Studio", "Design"), ("Example Greenfield Farms", "Agriculture"),
]
PEOPLE = [
    ("Asha Verma", "Owner"), ("Daniel Brooks", "Operations Manager"), ("Priya Nair", "Founder"), ("Liam Carter", "Head of Sales"),
    ("Meera Rao", "Director"), ("Tom Wilson", "IT Lead"), ("Sara Khan", "Marketing Manager"), ("Ravi Kumar", "CEO"),
]
DEALS = [
    ("Website redesign", 2400), ("Inventory app", 5200), ("CRM setup", 3100), ("Monthly automation retainer", 900),
    ("Order tracking portal", 6800), ("Data dashboard", 1800), ("Security review", 1200), ("Mobile booking app", 7500),
]
NOTES = ["Intro call, interested in a fixed-scope quote.", "Sent proposal by email.", "Asked for a demo next week.", "Waiting on budget approval.", "Follow-up meeting booked."]


class Command(BaseCommand):
    help = "Create demo data (username: demo, password: demo12345). Do not use in production."

    def handle(self, *args, **opts):
        random.seed(7)
        User = get_user_model()
        user, created = User.objects.get_or_create(username="demo")
        if created:
            user.set_password("demo12345")
            user.save()
        if Contact.objects.for_user(user).exists():
            self.stdout.write("Demo data already present.")
            return
        companies = [Company.objects.create(owner=user, name=n, industry=i, website=f"https://example.com/{n.split()[0].lower()}") for n, i in COMPANIES]
        contacts = []
        for idx, (name, title) in enumerate(PEOPLE):
            first = name.split()[0].lower()
            contacts.append(Contact.objects.create(owner=user, company=companies[idx % len(companies)], name=name, job_title=title, email=f"{first}@example.com", phone=f"+1 555 01{idx:02d}"))
        stages = ["lead", "qualified", "proposal", "won", "lost", "qualified", "lead", "proposal"]
        for idx, (title, value) in enumerate(DEALS):
            d = Deal.objects.create(owner=user, contact=contacts[idx], title=title, value=Decimal(value), stage=stages[idx], expected_close=timezone.now().date() + timedelta(days=14 + idx * 6))
            if d.stage in ("won", "lost"):
                d.closed_at = timezone.now() - timedelta(days=2)
                d.save(update_fields=["closed_at"])
            Activity.objects.create(owner=user, contact=contacts[idx], deal=d, kind=random.choice(["call", "email", "meeting", "note"]), text=random.choice(NOTES))
        self.stdout.write(self.style.SUCCESS("Demo data created. Log in as demo / demo12345."))
