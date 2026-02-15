from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from django.contrib.auth import get_user_model
from .models import (
    User,
    UserRole,
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
    LoyaltyHistory,
    LoyaltyProfile,
)

# ==========================================
# 1. USER & AUTH SERIALIZERS
# ==========================================


class CustomerRegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)
    password_confirm = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = (
            "first_name",
            "last_name",
            "email",
            "password",
            "password_confirm",
            "phone_number",
            "profile_image",
        )

    def validate(self, attrs):
        if attrs["password"] != attrs["password_confirm"]:
            raise serializers.ValidationError(
                {"password": "Password fields didn't match."}
            )
        if User.objects.filter(email=attrs["email"]).exists():
            raise serializers.ValidationError({"email": "Email already registered."})
        return attrs

    def create(self, validated_data):
        validated_data.pop("password_confirm")
        user = User.objects.create_user(
            email=validated_data["email"],
            password=validated_data["password"],
            first_name=validated_data["first_name"],
            last_name=validated_data["last_name"],
            phone_number=validated_data.get("phone_number"),
            role=UserRole.CUSTOMER,
            is_active=True,
            profile_image=validated_data.get("profile_image"),
        )
        return user


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token["role"] = user.role
        token["full_name"] = user.get_full_name()
        return token

    def validate(self, attrs):
        data = super().validate(attrs)
        data.update(
            {
                "user_id": self.user.id,
                "email": self.user.email,
                "full_name": self.user.get_full_name(),
                "role": self.user.role,
                "profile_image": (
                    self.user.profile_image.url if self.user.profile_image else None
                ),
            }
        )
        return data


class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            "id",
            "first_name",
            "last_name",
            "email",
            "phone_number",
            "profile_image",
            "preferred_language",
            "date_of_birth",
        ]
        read_only_fields = ["email", "role"]


class ShippingAddressSerializer(serializers.ModelSerializer):
    class Meta:
        model = ShippingAddress
        fields = "__all__"
        read_only_fields = ["user"]

    def create(self, validated_data):
        validated_data["user"] = self.context["request"].user
        return super().create(validated_data)


class StoreProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = StoreProfile
        fields = "__all__"


# ==========================================
# 2. PRODUCT CATALOG SERIALIZERS
# ==========================================


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ["id", "title", "slug", "image", "description"]


class SubCategorySerializer(serializers.ModelSerializer):
    category_title = serializers.ReadOnlyField(source="category.title")
    category_slug = serializers.ReadOnlyField(source="category.slug")

    class Meta:
        model = SubCategory
        fields = [
            "id",
            "category",
            "category_title",
            "category_slug",
            "title",
            "slug",
            "image",
        ]


class ProductImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductImage
        fields = ["id", "image", "alt_text"]


# --- ATTRIBUTE SERIALIZERS (NEW) ---
# Needed so the frontend can display filters (e.g. "Size: S, M, L")


class AttributeValueSerializer(serializers.ModelSerializer):
    class Meta:
        model = AttributeValue
        fields = ["id", "value"]


class AttributeSerializer(serializers.ModelSerializer):
    values = AttributeValueSerializer(many=True, read_only=True)

    class Meta:
        model = Attribute
        fields = ["id", "name", "values"]


# --- VARIANT SERIALIZER ---


class ProductVariantSerializer(serializers.ModelSerializer):
    # Flatten the Size object so frontend sees "XL" easily, not just ID 5
    size_value = serializers.ReadOnlyField(source="size.value")

    class Meta:
        model = ProductVariant
        fields = ["id", "size", "size_value", "color", "quantity", "sku_modifier"]


class ProductListSerializer(serializers.ModelSerializer):
    category_title = serializers.ReadOnlyField(source="sub_category.category.title")
    sub_category_title = serializers.ReadOnlyField(source="sub_category.title")

    image = serializers.ImageField(read_only=True)

    images = ProductImageSerializer(many=True, read_only=True)

    class Meta:
        model = Product
        fields = [
            "id",
            "title",
            "slug",
            "price",
            "old_price",
            "discount_percentage",
            "image",
            "images",
            "in_stock",
            "is_featured",
            "category_title",
            "sub_category_title",
        ]


class ProductDetailSerializer(serializers.ModelSerializer):

    images = ProductImageSerializer(many=True, read_only=True)
    variants = ProductVariantSerializer(many=True, read_only=True)
    tags = serializers.SerializerMethodField()
    sub_category_details = SubCategorySerializer(source="sub_category", read_only=True)

    class Meta:
        model = Product
        fields = [
            "id",
            "title",
            "slug",
            "sku",
            "short_description",
            "description",
            "price",
            "old_price",
            "discount_percentage",
            "specifications",  # <--- JSON Field included here
            "in_stock",
            "tags",
            "images",
            "variants",
            "sub_category",
            "sub_category_details",
        ]

    def get_tags(self, obj):
        return [tag.name for tag in obj.tags.all()]


# ==========================================
# 3. REVIEWS & WISHLIST
# ==========================================


class ProductReviewSerializer(serializers.ModelSerializer):
    user_full_name = serializers.ReadOnlyField(source="user.get_full_name")
    user_profile_image = serializers.SerializerMethodField()

    class Meta:
        model = ProductReview
        fields = [
            "id",
            "user",
            "user_full_name",
            "user_profile_image",
            "product",
            "rating",
            "review_text",
            "created_at",
        ]
        read_only_fields = ["user"]

    def get_user_profile_image(self, obj):
        if obj.user.profile_image:
            return obj.user.profile_image.url
        return None

    def create(self, validated_data):
        validated_data["user"] = self.context["request"].user
        return super().create(validated_data)


class WishlistSerializer(serializers.ModelSerializer):
    products = ProductListSerializer(many=True, read_only=True)

    class Meta:
        model = Wishlist
        fields = ["id", "products", "created_at"]


# ==========================================
# 4. CART SYSTEM SERIALIZERS
# ==========================================


class CartItemSerializer(serializers.ModelSerializer):
    product_details = ProductListSerializer(source="product", read_only=True)
    total_price = serializers.DecimalField(
        max_digits=10, decimal_places=2, source="get_total_item_price", read_only=True
    )

    class Meta:
        model = CartItem
        fields = [
            "id",
            "product",
            "product_details",
            "size",  # Stores String "XL"
            "color",  # Stores String "Red"
            "quantity",
            "total_price",
        ]

    def validate(self, data):
        """
        Validate stock availability.
        This is tricky because Cart stores 'strings' but Variants stores 'IDs'.
        """
        product = data.get("product")
        quantity = data.get("quantity")
        size = data.get("size")  # e.g. "XL"
        color = data.get("color")  # e.g. "Red"

        # 1. Basic Product Check
        if product and not product.in_stock:
            raise serializers.ValidationError(
                f"'{product.title}' is currently out of stock."
            )

        # 2. Detailed Variant Check
        # If the user selected a Size or Color, we must check if that specific variant exists and has stock.
        if size or color:
            variants = ProductVariant.objects.filter(product=product)

            if size:
                # We filter by the related AttributeValue's value
                variants = variants.filter(size__value=size)

            if color:
                variants = variants.filter(color=color)

            try:
                variant = variants.get()
            except ProductVariant.DoesNotExist:
                raise serializers.ValidationError(
                    f"This combination ({size}/{color}) is not available."
                )
            except ProductVariant.MultipleObjectsReturned:
                raise serializers.ValidationError(
                    f"Multiple variants found for ({size}/{color}). Please contact support."
                )

            if not variant:
                raise serializers.ValidationError(
                    f"This combination ({size}/{color}) is not available."
                )

            if variant.quantity < quantity:
                raise serializers.ValidationError(
                    f"Only {variant.quantity} items left for this option."
                )

        return data


class ShoppingCartSerializer(serializers.ModelSerializer):
    cart_items = CartItemSerializer(many=True, read_only=True)
    total_cart_price = serializers.DecimalField(
        max_digits=10, decimal_places=2, source="get_total_price", read_only=True
    )

    class Meta:
        model = ShoppingCart
        fields = ["id", "cart_items", "total_cart_price", "updated_at"]


# ==========================================
# 5. ORDER & CHECKOUT SERIALIZERS
# ==========================================


class CouponSerializer(serializers.ModelSerializer):
    class Meta:
        model = Coupon
        fields = ["code", "discount_percentage"]


class OrderItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderItem
        fields = [
            "id",
            "product_name",
            "product_price",
            "size",
            "color",
            "quantity",
            "get_subtotal",
        ]


class OrderReadSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)
    coupon_code = serializers.ReadOnlyField(source="coupon.code")

    class Meta:
        model = Order
        fields = [
            "id",
            "order_id",
            "status",
            "payment_method",
            "is_paid",
            "total_amount",
            "shipping_fee",
            "shipping_address",
            "shipping_city",
            "tracking_number",
            "created_at",
            "items",
            "coupon_code",
        ]


class OrderCreateSerializer(serializers.ModelSerializer):
    coupon_code = serializers.CharField(write_only=True, required=False)

    class Meta:
        model = Order
        fields = [
            "id",
            "shipping_address",
            "shipping_city",
            "shipping_phone",
            "note",
            "payment_method",
            "coupon_code",
        ]

    def create(self, validated_data):
        # Remove non-model field so Order.objects.create() doesn't explode
        validated_data.pop("coupon_code", None)
        return super().create(validated_data)


# ==========================================
# 6. NOTIFICATION SERIALIZER
# ==========================================


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = ["id", "title", "message", "is_read", "created_at"]


class LoyaltyHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = LoyaltyHistory
        fields = ["type", "points", "description", "created_at"]


class LoyaltyProfileSerializer(serializers.ModelSerializer):
    history = LoyaltyHistorySerializer(many=True, read_only=True)

    class Meta:
        model = LoyaltyProfile
        fields = ["points", "total_lifetime_points", "tier", "history"]


class ConvertPointsSerializer(serializers.Serializer):
    points_to_burn = serializers.IntegerField(min_value=100)


class CouponSerializer(serializers.ModelSerializer):
    is_valid = serializers.SerializerMethodField()

    class Meta:
        model = Coupon
        fields = [
            "code",
            "discount_percentage",
            "fixed_discount_amount",
            "valid_from",
            "valid_to",
            "active",
            "is_used",
            "used_at",
            "is_valid",
        ]

    def get_is_valid(self, obj):
        return obj.is_valid()
