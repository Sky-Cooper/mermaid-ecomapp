from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.html import mark_safe
from django.utils.translation import gettext_lazy as _
from .models import (
    User,
    StoreProfile,
    ShippingAddress,
    Category,
    SubCategory,
    Product,
    ProductImage,
    ProductVariant,
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


# ==========================================
# 2. USER & AUTH ADMIN
# ==========================================


class ShippingAddressInline(admin.StackedInline):
    model = ShippingAddress
    extra = 0
    classes = ["collapse"]


@admin.register(User)
class UserAdmin(BaseUserAdmin, ImagePreviewMixin):
    ordering = ["email"]
    list_display = (
        "email",
        "get_full_name",
        "role",
        "is_active",
        "is_email_verified",
        "get_image_preview",
        "date_joined_display",
    )
    list_filter = ("role", "is_active", "is_email_verified", "preferred_language")
    search_fields = ("email", "first_name", "last_name", "phone_number")

    # Customizing the edit form layout
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        (
            _("Personal Info"),
            {
                "fields": (
                    "first_name",
                    "last_name",
                    "phone_number",
                    "date_of_birth",
                    "profile_image",
                )
            },
        ),
        (
            _("Permissions"),
            {
                "fields": (
                    "role",
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "is_email_verified",
                    "groups",
                    "user_permissions",
                )
            },
        ),
        (_("Preferences"), {"fields": ("preferred_language",)}),
        (_("Dates"), {"fields": ("created_at", "updated_at")}),
    )
    readonly_fields = ("created_at", "updated_at")
    inlines = [ShippingAddressInline]

    def date_joined_display(self, obj):
        return obj.created_at.strftime("%Y-%m-%d")

    date_joined_display.short_description = "Joined"


@admin.register(StoreProfile)
class StoreProfileAdmin(admin.ModelAdmin):
    list_display = ("store_name", "support_email", "updated_at")

    def has_add_permission(self, request):
        # Prevent creating multiple store profiles if one exists
        if StoreProfile.objects.exists():
            return False
        return True


@admin.register(ShippingAddress)
class ShippingAddressAdmin(admin.ModelAdmin):
    list_display = ("user", "address_type", "city", "phone_number", "is_default")
    list_filter = ("address_type", "city")
    search_fields = ("user__email", "address_line_1", "phone_number")
    autocomplete_fields = ["user"]


# ==========================================
# 3. PRODUCT CATALOG ADMIN
# ==========================================


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin, ImagePreviewMixin):
    list_display = ("title", "slug", "is_active", "get_image_preview")
    prepopulated_fields = {"slug": ("title",)}
    search_fields = ("title",)


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


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin, ImagePreviewMixin):
    list_display = (
        "title",
        "sku",
        "price",
        "discount_percentage",
        "in_stock",
        "is_active",
        "is_featured",
        "get_image_preview",
    )
    list_filter = (
        "is_active",
        "in_stock",
        "is_featured",
        "sub_category__category",
        "created_at",
    )
    search_fields = ("title", "sku", "description")
    prepopulated_fields = {"slug": ("title",)}
    inlines = [ProductImageInline, ProductVariantInline]
    actions = ["mark_active", "mark_inactive", "mark_featured"]
    list_editable = ["price", "in_stock", "is_active", "is_featured"]

    fieldsets = (
        (_("Basic Info"), {"fields": ("title", "slug", "sku", "sub_category", "tags")}),
        (_("Media"), {"fields": ("image",)}),
        (_("Pricing"), {"fields": ("price", "old_price", "discount_percentage")}),
        (_("Status"), {"fields": ("in_stock", "is_active", "is_featured")}),
        (_("Content"), {"fields": ("short_description", "description")}),
    )

    # Optimization to avoid N+1 queries on sub_category
    def get_queryset(self, request):
        return super().get_queryset(request).select_related("sub_category")

    @admin.action(description="Mark selected products as Active")
    def mark_active(self, request, queryset):
        queryset.update(is_active=True)

    @admin.action(description="Mark selected products as Inactive")
    def mark_inactive(self, request, queryset):
        queryset.update(is_active=False)

    @admin.action(description="Toggle Featured status")
    def mark_featured(self, request, queryset):
        # This toggles boolean. For bulk, setting to True is safer.
        queryset.update(is_featured=True)


# ==========================================
# 4. REVIEWS & WISHLIST ADMIN
# ==========================================


@admin.register(ProductReview)
class ProductReviewAdmin(admin.ModelAdmin):
    list_display = ("user", "product", "rating", "created_at")
    list_filter = ("rating", "created_at")
    search_fields = ("user__email", "product__title", "review_text")
    autocomplete_fields = ["user", "product"]


@admin.register(Wishlist)
class WishlistAdmin(admin.ModelAdmin):
    list_display = ("user", "count_products", "created_at")
    search_fields = ("user__email",)
    filter_horizontal = ("products",)  # Better UI for ManyToMany

    def count_products(self, obj):
        return obj.products.count()

    count_products.short_description = "Product Count"


# ==========================================
# 5. CART SYSTEM ADMIN
# ==========================================


class CartItemInline(admin.TabularInline):
    model = CartItem
    extra = 0
    readonly_fields = ("get_total_item_price",)


@admin.register(ShoppingCart)
class ShoppingCartAdmin(admin.ModelAdmin):
    list_display = ("user", "get_item_count", "updated_at")
    inlines = [CartItemInline]

    def get_item_count(self, obj):
        return obj.cart_items.count()

    get_item_count.short_description = "Items"


# ==========================================
# 6. ORDER SYSTEM ADMIN
# ==========================================


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    # Usually you don't want admins changing order history details,
    # but sometimes corrections are needed.
    # We make price read-only to ensure history integrity.
    readonly_fields = ("product_price", "get_subtotal")
    can_delete = False


@admin.register(Coupon)
class CouponAdmin(admin.ModelAdmin):
    list_display = (
        "code",
        "discount_percentage",
        "valid_from",
        "valid_to",
        "active",
        "is_valid_now",
    )
    list_filter = ("active", "valid_from", "valid_to")
    search_fields = ("code",)

    def is_valid_now(self, obj):
        return obj.is_valid()

    is_valid_now.boolean = True


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = (
        "order_id",
        "user",
        "total_amount",
        "status",
        "payment_method",
        "is_paid",
        "created_at",
    )
    list_filter = ("status", "payment_method", "is_paid", "created_at")
    search_fields = ("order_id", "user__email", "shipping_phone", "shipping_address")
    readonly_fields = ("order_id", "created_at", "updated_at")
    inlines = [OrderItemInline]
    actions = ["mark_processing", "mark_shipped", "mark_delivered", "mark_paid"]

    fieldsets = (
        (_("Order ID"), {"fields": ("order_id", "user", "created_at")}),
        (
            _("Shipping Info"),
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
            _("Financials"),
            {"fields": ("total_amount", "payment_method", "is_paid", "coupon")},
        ),
        (_("Status"), {"fields": ("status", "note")}),
    )

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("user")

    @admin.action(description="Set status to Processing")
    def mark_processing(self, request, queryset):
        queryset.update(status="PROCESSING")

    @admin.action(description="Set status to Shipped")
    def mark_shipped(self, request, queryset):
        queryset.update(status="SHIPPED")

    @admin.action(description="Set status to Delivered")
    def mark_delivered(self, request, queryset):
        queryset.update(status="DELIVERED")

    @admin.action(description="Mark as Paid")
    def mark_paid(self, request, queryset):
        queryset.update(is_paid=True)


# ==========================================
# 7. NOTIFICATIONS ADMIN
# ==========================================


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ("user", "title", "is_read", "created_at")
    list_filter = ("is_read", "created_at")
    search_fields = ("user__email", "title", "message")
