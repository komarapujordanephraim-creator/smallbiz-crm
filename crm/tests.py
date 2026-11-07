from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .models import Activity, Company, Contact, Deal

User = get_user_model()


class Base(TestCase):
    def setUp(self):
        self.alice = User.objects.create_user("alice", password="pw-alice-123")
        self.bob = User.objects.create_user("bob", password="pw-bob-123")
        self.client.login(username="alice", password="pw-alice-123")
        self.a_company = Company.objects.create(owner=self.alice, name="Alice Co")
        self.a_contact = Contact.objects.create(owner=self.alice, company=self.a_company, name="Ann Lee", email="ann@example.com")
        self.b_contact = Contact.objects.create(owner=self.bob, name="Bob's Secret Contact", email="secret@example.com")
        self.b_deal = Deal.objects.create(owner=self.bob, contact=self.b_contact, title="Bob deal", value=999)


class AccessTests(Base):
    def test_login_required(self):
        self.client.logout()
        for name in ("dashboard", "contact_list", "company_list", "deal_board", "contact_export"):
            r = self.client.get(reverse(name))
            self.assertEqual(r.status_code, 302, name)
            self.assertIn("/login/", r["Location"])

    def test_user_cannot_see_other_users_contact(self):
        self.assertEqual(self.client.get(reverse("contact_detail", args=[self.b_contact.pk])).status_code, 404)
        self.assertNotContains(self.client.get(reverse("contact_list")), "Bob's Secret Contact")

    def test_user_cannot_edit_or_delete_other_users_records(self):
        self.assertEqual(self.client.get(reverse("contact_edit", args=[self.b_contact.pk])).status_code, 404)
        self.assertEqual(self.client.post(reverse("contact_delete", args=[self.b_contact.pk])).status_code, 404)
        self.assertEqual(self.client.post(reverse("deal_delete", args=[self.b_deal.pk])).status_code, 404)
        self.assertTrue(Contact.objects.filter(pk=self.b_contact.pk).exists())

    def test_cannot_move_other_users_deal(self):
        r = self.client.post(reverse("deal_stage", args=[self.b_deal.pk]), {"stage": "won"})
        self.assertEqual(r.status_code, 404)
        self.b_deal.refresh_from_db()
        self.assertEqual(self.b_deal.stage, "lead")

    def test_cannot_attach_deal_to_other_users_contact(self):
        r = self.client.post(reverse("deal_create"), {"title": "Sneaky", "contact": self.b_contact.pk, "value": "10", "stage": "lead"})
        self.assertEqual(r.status_code, 200)  # form re-rendered with an error
        self.assertFalse(Deal.objects.filter(title="Sneaky").exists())

    def test_cannot_log_activity_on_other_users_contact(self):
        r = self.client.post(reverse("add_activity", args=[self.b_contact.pk]), {"kind": "note", "text": "x"})
        self.assertEqual(r.status_code, 404)
        self.assertEqual(Activity.objects.count(), 0)


class DealTests(Base):
    def test_create_assigns_owner_and_stage_won_sets_closed_at(self):
        r = self.client.post(reverse("deal_create"), {"title": "Big", "contact": self.a_contact.pk, "value": "5000", "stage": "won"})
        self.assertEqual(r.status_code, 302)
        d = Deal.objects.get(title="Big")
        self.assertEqual(d.owner, self.alice)
        self.assertIsNotNone(d.closed_at)

    def test_reopening_clears_closed_at(self):
        d = Deal.objects.create(owner=self.alice, contact=self.a_contact, title="D", value=1, stage="won", closed_at=timezone.now())
        self.client.post(reverse("deal_stage", args=[d.pk]), {"stage": "proposal"})
        d.refresh_from_db()
        self.assertEqual(d.stage, "proposal")
        self.assertIsNone(d.closed_at)

    def test_invalid_stage_is_ignored(self):
        d = Deal.objects.create(owner=self.alice, contact=self.a_contact, title="D", value=1)
        self.client.post(reverse("deal_stage", args=[d.pk]), {"stage": "hacked"})
        d.refresh_from_db()
        self.assertEqual(d.stage, "lead")

    def test_negative_value_rejected(self):
        r = self.client.post(reverse("deal_create"), {"title": "Neg", "contact": self.a_contact.pk, "value": "-5", "stage": "lead"})
        self.assertEqual(r.status_code, 200)
        self.assertFalse(Deal.objects.filter(title="Neg").exists())

    def test_stage_change_requires_post(self):
        d = Deal.objects.create(owner=self.alice, contact=self.a_contact, title="D", value=1)
        self.assertEqual(self.client.get(reverse("deal_stage", args=[d.pk])).status_code, 405)


class DashboardTests(Base):
    def test_numbers(self):
        mk = lambda t, v, s, closed=None: Deal.objects.create(owner=self.alice, contact=self.a_contact, title=t, value=v, stage=s, closed_at=closed)
        mk("o1", 100, "lead")
        mk("o2", 250, "proposal")
        mk("w1", 400, "won", timezone.now())
        mk("l1", 50, "lost", timezone.now())
        mk("w-old", 999, "won", timezone.now() - timedelta(days=90))
        ctx = self.client.get(reverse("dashboard")).context
        self.assertEqual(ctx["open_value"], Decimal("350"))
        self.assertEqual(ctx["win_rate"], 67)  # 2 won, 1 lost
        self.assertEqual(ctx["won_this_month"], Decimal("400"))  # the 90-day-old win is not counted
        self.assertEqual(ctx["contacts"], 1)

    def test_other_users_deals_not_counted(self):
        ctx = self.client.get(reverse("dashboard")).context
        self.assertEqual(ctx["open_value"], Decimal("0"))
        self.assertIsNone(ctx["win_rate"])


class ContactTests(Base):
    def test_search(self):
        Contact.objects.create(owner=self.alice, name="Zed Zimmer", email="zed@example.com")
        r = self.client.get(reverse("contact_list"), {"q": "zimmer"})
        self.assertContains(r, "Zed Zimmer")
        self.assertNotContains(r, "Ann Lee")

    def test_activity_added(self):
        d = Deal.objects.create(owner=self.alice, contact=self.a_contact, title="D", value=1)
        self.client.post(reverse("add_activity", args=[self.a_contact.pk]), {"kind": "call", "text": "Talked", "deal": d.pk})
        a = Activity.objects.get()
        self.assertEqual((a.owner, a.contact, a.deal), (self.alice, self.a_contact, d))

    def test_csv_export_only_own_and_formula_safe(self):
        Contact.objects.create(owner=self.alice, name="=HYPERLINK(\"http://evil\")", email="e@example.com")
        r = self.client.get(reverse("contact_export"))
        body = r.content.decode()
        self.assertEqual(r["Content-Type"], "text/csv")
        self.assertIn("Ann Lee", body)
        self.assertNotIn("Secret", body)
        self.assertIn("'=HYPERLINK", body)

    def test_deleting_contact_deletes_its_deals(self):
        Deal.objects.create(owner=self.alice, contact=self.a_contact, title="D", value=1)
        self.client.post(reverse("contact_delete", args=[self.a_contact.pk]))
        self.assertEqual(Deal.objects.filter(owner=self.alice).count(), 0)
