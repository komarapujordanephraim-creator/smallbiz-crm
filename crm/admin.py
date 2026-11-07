from django.contrib import admin

from .models import Activity, Company, Contact, Deal

admin.site.register([Company, Contact, Deal, Activity])
