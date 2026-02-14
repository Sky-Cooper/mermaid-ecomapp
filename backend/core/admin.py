from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.html import mark_safe
from django.utils.translation import gettext_lazy as _
import json

from .models import (
    User,
    StoreProfile,
    ShippingAddress,
    Category,
    SubCategory,
    Product,
    ProductImage,
    ProductVariant,
    Attribute,
    AttributeValue,
    ProductReview,
    Wishlist,
    ShoppingCart,
    CartItem,
    Coupon,
    Order,
    OrderItem,
    Notification,
)

# ==========================================
# 1. SHARED UTILS & MIXINS
# ==========================================


class ImagePreviewMixin:
    """Helper to display image thumbnails in admin list views."""

    def get_image_preview(self, obj):
        if hasattr(obj, "image") and obj.image:
            return mark_safe(
                f'<img src="{obj.image.url}" style="height: 50px; width: 50px; object-fit: cover; border-radius: 4px;" />'
            )
        if hasattr(obj, "profile_image") and obj.profile_image:
            return mark_safe(
                f'<img src="{obj.profile_image.url}" style="height: 50px; width: 50px; object-fit: cover; border-radius: 50%;" />'
            )
        return "-"

    get_image_preview.short_description = "Preview"


class JSONPrettyMixin:
    """Helper to display JSON fields as a pretty HTML table."""

    def get_specs_html(self, obj):
        if not obj.specifications:
            return "-"
        try:
            # Check if it's already a dict or needs parsing
            data = (
                obj.specifications
                if isinstance(obj.specifications, dict)
                else json.loads(obj.specifications)
            )
            html = '<table style="width:100%; border-collapse: collapse;">'
            for key, value in data.items():
                html += f'<tr><td style="border: 1px solid #ddd; padding: 4px; font-weight: bold;">{key}</td><td style="border: 1px solid #ddd; padding: 4px;">{value}</td></tr>'
            html += "</table>"
            return mark_safe(html)
        except Exception:
            return "Invalid JSON"

    get_specs_html.short_description = "Specifications"


# ==========================================
# 2. ATTRIBUTE ADMIN
# ==========================================


class AttributeValueInline(admin.TabularInline):
    model = AttributeValue
    extra = 1


@admin.register(Attribute)
class AttributeAdmin(admin.ModelAdmin):
    list_display = ("name", "count_values")
    inlines = [AttributeValueInline]

    def count_values(self, obj):
        return obj.values.count()

    count_values.short_description = "Options Count"


# --- FIX: Register AttributeValue so autocomplete works ---
@admin.register(AttributeValue)
class AttributeValueAdmin(admin.ModelAdmin):
    search_fields = ["value"]
    list_display = ["value", "attribute"]
    list_filter = ["attribute"]


# ==========================================
# 3. USER & AUTH ADMIN
# ==========================================


class ShippingAddressInline(admin.StackedInline):
    model = ShippingAddress
    extra = 0
    classes = ["collapse"]


@admin.register(User)
class UserAdmin(BaseUserAdmin, ImagePreviewMixin):
    ordering = ["email"]
    list_display = ("email", "get_full_name", "role", "is_active", "get_image_preview")
    list_filter = ("role", "is_active", "preferred_language")
    search_fields = ("email", "first_name", "last_name", "phone_number")

    fieldsets = (
        (None, {"fields": ("email", "password")}),
        (
            _("Personal Info"),
            {"fields": ("first_name", "last_name", "phone_number", "profile_image")},
        ),
        (
            _("Permissions"),
            {"fields": ("role", "is_active", "is_staff", "is_superuser", "groups")},
        ),
        (_("Important Dates"), {"fields": ("last_login", "date_joined")}),
    )
    inlines = [ShippingAddressInline]


@admin.register(StoreProfile)
class StoreProfileAdmin(admin.ModelAdmin):
    list_display = ("store_name", "support_email", "updated_at")

    def has_add_permission(self, request):
        return not StoreProfile.objects.exists()


@admin.register(ShippingAddress)
class ShippingAddressAdmin(admin.ModelAdmin):
    list_display = ("user", "address_type", "city", "is_default")
    list_filter = ("address_type", "city")
    autocomplete_fields = ["user"]


# ==========================================
# 4. PRODUCT CATALOG ADMIN
# ==========================================


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin, ImagePreviewMixin):
    list_display = ("title", "slug", "is_active", "get_image_preview")
    prepopulated_fields = {"slug": ("title",)}
    search_fields = ["title"]  # --- FIX: Added search_fields


@admin.register(SubCategory)
class SubCategoryAdmin(admin.ModelAdmin):
    list_display = ("title", "category", "is_active")
    list_filter = ("category",)
    prepopulated_fields = {"slug": ("title",)}
    autocomplete_fields = ["category"]


class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1


class ProductVariantInline(admin.TabularInline):
    model = ProductVariant
    extra = 1
    classes = ["collapse"]
    autocomplete_fields = [
        "size"
    ]  # Works now because AttributeValueAdmin is registered above


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin, ImagePreviewMixin, JSONPrettyMixin):
    list_display = (
        "title",
        "sku",
        "price",
        "in_stock",
        "is_active",
        "get_image_preview",
    )
    list_filter = ("is_active", "in_stock", "sub_category__category")
    search_fields = ("title", "sku")
    prepopulated_fields = {"slug": ("title",)}
    inlines = [ProductImageInline, ProductVariantInline]
    actions = ["mark_active", "mark_inactive"]

    readonly_fields = ("get_specs_html", "created_at", "updated_at")

    fieldsets = (
        (_("Basic Info"), {"fields": ("title", "slug", "sku", "sub_category", "tags")}),
        (_("Media"), {"fields": ("image",)}),
        (_("Pricing"), {"fields": ("price", "old_price", "discount_percentage")}),
        (
            _("Details"),
            {
                "fields": (
                    "short_description",
                    "description",
                    "specifications",
                    "get_specs_html",
                )
            },
        ),
        (_("Status"), {"fields": ("in_stock", "is_active", "is_featured")}),
    )

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("sub_category")

    @admin.action(description="Mark selected products as Active")
    def mark_active(self, request, queryset):
        queryset.update(is_active=True)

    @admin.action(description="Mark selected products as Inactive")
    def mark_inactive(self, request, queryset):
        queryset.update(is_active=False)


# ==========================================
# 5. ORDER SYSTEM ADMIN
# ==========================================


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = (
        "product_name",
        "product_price",
        "size",
        "color",
        "quantity",
        "get_subtotal",
    )
    can_delete = False


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = (
        "order_id",
        "user",
        "total_amount",
        "status",
        "payment_method",
        "created_at",
    )
    list_filter = ("status", "payment_method", "created_at")
    search_fields = ("order_id", "user__email", "shipping_phone")
    inlines = [OrderItemInline]

    readonly_fields = ("order_id", "user", "total_amount", "created_at", "updated_at")

    fieldsets = (
        (_("Order Info"), {"fields": ("order_id", "user", "created_at", "status")}),
        (
            _("Shipping"),
            {
                "fields": (
                    "shipping_address",
                    "shipping_city",
                    "shipping_phone",
                    "tracking_number",
                )
            },
        ),
        (
            _("Payment"),
            {"fields": ("total_amount", "payment_method", "is_paid", "coupon")},
        ),
    )


@admin.register(Coupon)
class CouponAdmin(admin.ModelAdmin):
    list_display = ("code", "discount_percentage", "active", "valid_to")


# ==========================================
# 6. OTHER ADMINS
# ==========================================


@admin.register(ProductReview)
class ProductReviewAdmin(admin.ModelAdmin):
    list_display = ("product", "user", "rating", "created_at")
    list_filter = ("rating",)


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ("user", "title", "is_read", "created_at")
    list_filter = ("is_read",)
