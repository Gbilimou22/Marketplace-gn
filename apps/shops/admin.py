from django.contrib import admin, messages
from django.utils.translation import ngettext

from apps.shops.models import Shop
from apps.shops.services import shop_activate, shop_suspend


@admin.register(Shop)
class ShopAdmin(admin.ModelAdmin):
    list_display = ("name", "owner_name", "city", "whatsapp_number", "status", "created_at")
    list_filter = ("status", "city", "created_at")
    search_fields = ("name", "owner__user__full_name", "owner__user__email", "whatsapp_number")
    prepopulated_fields = {"slug": ("name",)}
    raw_id_fields = ("owner",)
    readonly_fields = ("created_at", "updated_at")
    actions = ["activate_selected_shops", "suspend_selected_shops"]

    def owner_name(self, obj: Shop) -> str:
        return f"{obj.owner.user.full_name} ({obj.owner.user.email})"

    owner_name.short_description = "Propriétaire"

    @admin.action(description="Activer et publier les boutiques sélectionnées")
    def activate_selected_shops(self, request, queryset):
        count = 0
        for shop in queryset:
            shop_activate(shop=shop, admin_user=request.user)
            count += 1
        self.message_user(
            request,
            ngettext(
                "%d boutique a été activée avec succès.",
                "%d boutiques ont été activées avec succès.",
                count,
            )
            % count,
            messages.SUCCESS,
        )

    @admin.action(description="Suspendre les boutiques sélectionnées")
    def suspend_selected_shops(self, request, queryset):
        count = 0
        for shop in queryset:
            shop_suspend(shop=shop, admin_user=request.user, reason="Action administrative groupée.")
            count += 1
        self.message_user(
            request,
            ngettext(
                "%d boutique a été suspendue.",
                "%d boutiques ont été suspendues.",
                count,
            )
            % count,
            messages.WARNING,
        )
