from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from apps.accounts.models import SellerProfile, User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ("email", "full_name", "phone_number", "is_seller", "is_staff", "is_active", "date_joined")
    list_filter = ("is_staff", "is_superuser", "is_active")
    search_fields = ("email", "full_name", "phone_number")
    ordering = ("-date_joined",)

    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Informations personnelles", {"fields": ("full_name", "phone_number")}),
        ("Permissions", {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")}),
        ("Dates", {"fields": ("date_joined",)}),
    )
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("email", "full_name", "phone_number", "password1", "password2"),
            },
        ),
    )

    def is_seller(self, obj: User) -> bool:
        return obj.is_seller

    is_seller.boolean = True
    is_seller.short_description = "Vendeur vérifié"


@admin.register(SellerProfile)
class SellerProfileAdmin(admin.ModelAdmin):
    list_display = ("user_full_name", "user_email", "status", "verified_at", "verified_by", "created_at")
    list_filter = ("status", "created_at", "verified_at")
    search_fields = ("user__email", "user__full_name", "user__phone_number", "internal_notes")
    raw_id_fields = ("user", "verified_by")
    readonly_fields = ("created_at", "updated_at")

    def user_full_name(self, obj: SellerProfile) -> str:
        return obj.user.full_name

    user_full_name.short_description = "Nom complet"

    def user_email(self, obj: SellerProfile) -> str:
        return obj.user.email

    user_email.short_description = "Adresse email"
