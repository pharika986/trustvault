from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import Group
from .models import User


@admin.register(User)
class VaultUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (("Role", {"fields": ("role",)}),)
    add_fieldsets = UserAdmin.add_fieldsets + (("Role", {"fields": ("role",)}),)


admin.site.site_header = "TrustVault Admin"
admin.site.site_title = "TrustVault Admin"
admin.site.index_title = "User management"

# Groups are not used in TrustVault. Guarded so a repeat cannot crash startup.
if admin.site.is_registered(Group):
    admin.site.unregister(Group)
