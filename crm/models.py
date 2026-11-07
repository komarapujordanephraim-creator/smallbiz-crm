from decimal import Decimal

from django.conf import settings
from django.db import models
from django.urls import reverse


class OwnedQuerySet(models.QuerySet):
    def for_user(self, user):
        """Every record belongs to one user; nobody sees another user's data."""
        return self.filter(owner=user)


class Company(models.Model):
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="companies")
    name = models.CharField(max_length=200)
    website = models.URLField(blank=True)
    industry = models.CharField(max_length=100, blank=True)
    created = models.DateTimeField(auto_now_add=True)

    objects = OwnedQuerySet.as_manager()

    class Meta:
        ordering = ["name"]
        verbose_name_plural = "companies"

    def __str__(self):
        return self.name


class Contact(models.Model):
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="contacts")
    company = models.ForeignKey(Company, null=True, blank=True, on_delete=models.SET_NULL, related_name="contacts")
    name = models.CharField(max_length=200)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=40, blank=True)
    job_title = models.CharField(max_length=100, blank=True)
    created = models.DateTimeField(auto_now_add=True)

    objects = OwnedQuerySet.as_manager()

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse("contact_detail", args=[self.pk])


class Deal(models.Model):
    class Stage(models.TextChoices):
        LEAD = "lead", "Lead"
        QUALIFIED = "qualified", "Qualified"
        PROPOSAL = "proposal", "Proposal"
        WON = "won", "Won"
        LOST = "lost", "Lost"

    OPEN_STAGES = (Stage.LEAD, Stage.QUALIFIED, Stage.PROPOSAL)

    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="deals")
    contact = models.ForeignKey(Contact, on_delete=models.CASCADE, related_name="deals")
    title = models.CharField(max_length=200)
    value = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0"))
    stage = models.CharField(max_length=20, choices=Stage.choices, default=Stage.LEAD)
    expected_close = models.DateField(null=True, blank=True)
    created = models.DateTimeField(auto_now_add=True)
    closed_at = models.DateTimeField(null=True, blank=True)

    objects = OwnedQuerySet.as_manager()

    class Meta:
        ordering = ["-created"]

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse("deal_detail", args=[self.pk])


class Activity(models.Model):
    class Kind(models.TextChoices):
        NOTE = "note", "Note"
        CALL = "call", "Call"
        EMAIL = "email", "Email"
        MEETING = "meeting", "Meeting"

    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="activities")
    contact = models.ForeignKey(Contact, on_delete=models.CASCADE, related_name="activities")
    deal = models.ForeignKey(Deal, null=True, blank=True, on_delete=models.SET_NULL, related_name="activities")
    kind = models.CharField(max_length=20, choices=Kind.choices, default=Kind.NOTE)
    text = models.TextField()
    created = models.DateTimeField(auto_now_add=True)

    objects = OwnedQuerySet.as_manager()

    class Meta:
        ordering = ["-created"]
        verbose_name_plural = "activities"

    def __str__(self):
        return f"{self.get_kind_display()} for {self.contact}"
