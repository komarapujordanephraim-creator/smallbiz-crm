import csv
from decimal import Decimal

from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q, Sum
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.utils import timezone
from django.views import View
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from django.views.generic import CreateView, DeleteView, DetailView, ListView, TemplateView, UpdateView
from django.urls import reverse_lazy

from .forms import ActivityForm, CompanyForm, ContactForm, DealForm, UserScopedForm
from .models import Activity, Company, Contact, Deal


class OwnedMixin(LoginRequiredMixin):
    """Scopes every queryset to the logged-in user and passes the user to forms."""

    def get_queryset(self):
        return super().get_queryset().for_user(self.request.user)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        if issubclass(self.get_form_class(), UserScopedForm):  # delete views use a plain Form
            kwargs["user"] = self.request.user
        return kwargs


class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = "crm/dashboard.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        user = self.request.user
        deals = Deal.objects.for_user(user)
        now = timezone.now()
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        zero = Decimal("0")
        stages = []
        for value, label in Deal.Stage.choices:
            agg = deals.filter(stage=value).aggregate(total=Sum("value"))
            stages.append({"key": value, "label": label, "count": deals.filter(stage=value).count(), "total": agg["total"] or zero})
        won = deals.filter(stage=Deal.Stage.WON).count()
        lost = deals.filter(stage=Deal.Stage.LOST).count()
        ctx.update(
            contacts=Contact.objects.for_user(user).count(),
            companies=Company.objects.for_user(user).count(),
            open_value=deals.filter(stage__in=Deal.OPEN_STAGES).aggregate(t=Sum("value"))["t"] or zero,
            won_this_month=deals.filter(stage=Deal.Stage.WON, closed_at__gte=month_start).aggregate(t=Sum("value"))["t"] or zero,
            win_rate=round(100 * won / (won + lost)) if (won + lost) else None,
            stages=stages,
            recent=Activity.objects.for_user(user).select_related("contact")[:8],
        )
        return ctx


class ContactList(OwnedMixin, ListView):
    model = Contact
    paginate_by = 25

    def get_queryset(self):
        qs = super().get_queryset().select_related("company")
        q = self.request.GET.get("q", "").strip()
        if q:
            qs = qs.filter(Q(name__icontains=q) | Q(email__icontains=q) | Q(company__name__icontains=q))
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["q"] = self.request.GET.get("q", "")
        return ctx


class ContactDetail(OwnedMixin, DetailView):
    model = Contact

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["form"] = ActivityForm(user=self.request.user, contact=self.object)
        ctx["deals"] = self.object.deals.all()
        ctx["activities"] = self.object.activities.select_related("deal")
        return ctx


class ContactCreate(OwnedMixin, CreateView):
    model = Contact
    form_class = ContactForm


class ContactUpdate(OwnedMixin, UpdateView):
    model = Contact
    form_class = ContactForm


class ContactDelete(OwnedMixin, DeleteView):
    model = Contact
    success_url = reverse_lazy("contact_list")


class CompanyList(OwnedMixin, ListView):
    model = Company


class CompanyCreate(OwnedMixin, CreateView):
    model = Company
    form_class = CompanyForm
    success_url = reverse_lazy("company_list")


class DealBoard(LoginRequiredMixin, TemplateView):
    template_name = "crm/deal_board.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        deals = Deal.objects.for_user(self.request.user).select_related("contact")
        ctx["columns"] = [{"key": v, "label": l, "deals": [d for d in deals if d.stage == v]} for v, l in Deal.Stage.choices]
        ctx["stages"] = Deal.Stage.choices
        return ctx


class DealDetail(OwnedMixin, DetailView):
    model = Deal

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["stages"] = Deal.Stage.choices
        ctx["activities"] = self.object.activities.all()
        return ctx


class DealCreate(OwnedMixin, CreateView):
    model = Deal
    form_class = DealForm

    def get_initial(self):
        initial = super().get_initial()
        contact = self.request.GET.get("contact")
        if contact and Contact.objects.for_user(self.request.user).filter(pk=contact).exists():
            initial["contact"] = contact
        return initial

    def form_valid(self, form):
        response = super().form_valid(form)
        _apply_stage(self.object, self.object.stage)
        return response


class DealUpdate(OwnedMixin, UpdateView):
    model = Deal
    form_class = DealForm

    def form_valid(self, form):
        response = super().form_valid(form)
        _apply_stage(self.object, self.object.stage)
        return response


class DealDelete(OwnedMixin, DeleteView):
    model = Deal
    success_url = reverse_lazy("deal_board")


def _apply_stage(deal, stage):
    """Set the stage and keep closed_at consistent (set when won/lost, cleared when reopened)."""
    deal.stage = stage
    if stage in (Deal.Stage.WON, Deal.Stage.LOST):
        if deal.closed_at is None:
            deal.closed_at = timezone.now()
    else:
        deal.closed_at = None
    deal.save(update_fields=["stage", "closed_at"])


@login_required
@require_POST
def deal_set_stage(request, pk):
    deal = get_object_or_404(Deal.objects.for_user(request.user), pk=pk)
    stage = request.POST.get("stage")
    if stage in Deal.Stage.values:
        _apply_stage(deal, stage)
    if request.POST.get("next") == "board":
        return redirect("deal_board")
    return redirect(deal)


@login_required
@require_POST
def add_activity(request, pk):
    contact = get_object_or_404(Contact.objects.for_user(request.user), pk=pk)
    form = ActivityForm(request.POST, user=request.user, contact=contact)
    if form.is_valid():
        form.save()
    return redirect(contact)


def _csv_safe(value):
    """Stop spreadsheet formula injection: cells starting with = + - @ are prefixed with an apostrophe."""
    value = "" if value is None else str(value)
    return "'" + value if value[:1] in ("=", "+", "-", "@", "\t", "\r") else value


class ContactExport(LoginRequiredMixin, View):
    def get(self, request):
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = 'attachment; filename="contacts.csv"'
        writer = csv.writer(response)
        writer.writerow(["Name", "Company", "Job title", "Email", "Phone"])
        for c in Contact.objects.for_user(request.user).select_related("company"):
            writer.writerow([_csv_safe(x) for x in (c.name, c.company.name if c.company else "", c.job_title, c.email, c.phone)])
        return response
