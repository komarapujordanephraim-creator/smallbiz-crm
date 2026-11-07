from django import forms

from .models import Activity, Company, Contact, Deal


class UserScopedForm(forms.ModelForm):
    """Limits every related-object dropdown to the current user's own records."""

    def __init__(self, *args, user, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user
        for name, field in self.fields.items():
            qs = getattr(field, "queryset", None)
            if qs is not None and hasattr(qs, "for_user"):
                field.queryset = qs.for_user(user)

    def save(self, commit=True):
        obj = super().save(commit=False)
        obj.owner = self.user
        if commit:
            obj.save()
        return obj


class CompanyForm(UserScopedForm):
    class Meta:
        model = Company
        fields = ["name", "website", "industry"]


class ContactForm(UserScopedForm):
    class Meta:
        model = Contact
        fields = ["name", "company", "email", "phone", "job_title"]


class DealForm(UserScopedForm):
    class Meta:
        model = Deal
        fields = ["title", "contact", "value", "stage", "expected_close"]
        widgets = {"expected_close": forms.DateInput(attrs={"type": "date"})}

    def clean_value(self):
        value = self.cleaned_data["value"]
        if value < 0:
            raise forms.ValidationError("Value cannot be negative.")
        return value


class ActivityForm(UserScopedForm):
    class Meta:
        model = Activity
        fields = ["kind", "deal", "text"]
        widgets = {"text": forms.Textarea(attrs={"rows": 3})}

    def __init__(self, *args, contact=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.contact = contact
        if contact is not None:
            self.fields["deal"].queryset = self.fields["deal"].queryset.filter(contact=contact)
        self.fields["deal"].required = False

    def save(self, commit=True):
        obj = super().save(commit=False)
        obj.contact = self.contact
        if commit:
            obj.save()
        return obj
