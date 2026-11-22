from django.contrib import admin

from apps.catalog.models import Category, Product, ProductImage


class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1
    fields = ("image", "position", "is_cover", "created_at")
    readonly_fields = ("created_at",)


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "parent", "slug", "icon", "order")
    list_filter = ("parent",)
    search_fields = ("name", "slug")
    prepopulated_fields = {"slug": ("name",)}
    ordering = ("order", "name")


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("title", "shop", "category", "price_gnf", "condition", "stock", "status", "created_at")
    list_filter = ("status", "condition", "category", "shop__city", "created_at")
    search_fields = ("title", "brand", "description", "shop__name")
    prepopulated_fields = {"slug": ("title",)}
    raw_id_fields = ("shop",)
    readonly_fields = ("created_at", "updated_at")
    inlines = [ProductImageInline]


@admin.register(ProductImage)
class ProductImageAdmin(admin.ModelAdmin):
    list_display = ("product", "position", "is_cover", "created_at")
    list_filter = ("is_cover", "created_at")
    raw_id_fields = ("product",)
