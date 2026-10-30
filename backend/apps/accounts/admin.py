from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User
@admin.register(User)
class CustomUserAdmin(UserAdmin):
    fieldsets=UserAdmin.fieldsets + (("SynfoTalent", {"fields":("employee_code","role","phone","date_joined_company")}),)
    add_fieldsets=UserAdmin.add_fieldsets + (("SynfoTalent", {"fields":("employee_code","role","phone")}),)
