from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User


@admin.register(User)
class VaultUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (("Role", {"fields": ("role",)}),)
    add_fieldsets = UserAdmin.add_fieldsets + (("Role", {"fields": ("role",)}),)


from django.contrib.auth.models import Group

admin.site.site_header = "TrustVault Admin"
admin.site.site_title = "TrustVault Admin"
admin.site.index_title = "User management"
admin.site.unregister(Group)


from django.contrib.auth.models import Group

admin.site.site_header = "TrustVault Admin"
admin.site.site_title = "TrustVault Admin"
admin.site.index_title = "User management"
admin.site.unregister(Group)


from django.contrib.auth.models import Group

admin.site.site_header = "TrustVault Admin"
admin.site.site_title = "TrustVault Admin"
admin.site.index_title = "User management"
admin.site.unregister(Group)


from django.contrib.auth.models import Group

admin.site.site_header = "TrustVault Admin"
admin.site.site_title = "TrustVault Admin"
admin.site.index_title = "User management"
admin.site.unregister(Group)
