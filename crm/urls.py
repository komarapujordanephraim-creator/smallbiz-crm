from django.urls import path

from . import views

urlpatterns = [
    path("", views.DashboardView.as_view(), name="dashboard"),
    path("contacts/", views.ContactList.as_view(), name="contact_list"),
    path("contacts/new/", views.ContactCreate.as_view(), name="contact_create"),
    path("contacts/export.csv", views.ContactExport.as_view(), name="contact_export"),
    path("contacts/<int:pk>/", views.ContactDetail.as_view(), name="contact_detail"),
    path("contacts/<int:pk>/edit/", views.ContactUpdate.as_view(), name="contact_edit"),
    path("contacts/<int:pk>/delete/", views.ContactDelete.as_view(), name="contact_delete"),
    path("contacts/<int:pk>/activity/", views.add_activity, name="add_activity"),
    path("companies/", views.CompanyList.as_view(), name="company_list"),
    path("companies/new/", views.CompanyCreate.as_view(), name="company_create"),
    path("deals/", views.DealBoard.as_view(), name="deal_board"),
    path("deals/new/", views.DealCreate.as_view(), name="deal_create"),
    path("deals/<int:pk>/", views.DealDetail.as_view(), name="deal_detail"),
    path("deals/<int:pk>/edit/", views.DealUpdate.as_view(), name="deal_edit"),
    path("deals/<int:pk>/delete/", views.DealDelete.as_view(), name="deal_delete"),
    path("deals/<int:pk>/stage/", views.deal_set_stage, name="deal_stage"),
]
