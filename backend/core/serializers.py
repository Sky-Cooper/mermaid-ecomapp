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
# 1. AUTH & USER SERIALIZERS
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
    """
    Used for users to view/update their own profile.
    """

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
        # Auto-assign the user from the request context
        validated_data["user"] = self.context["request"].user
        return super().create(validated_data)


class StoreProfileSerializer(serializers.ModelSerializer):
    """
    Read-only for customers, Writable for Admin.
    """

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
    # To display the parent category name instead of just ID
    category_title = serializers.ReadOnlyField(source="category.title")

    class Meta:
        model = SubCategory
        fields = ["id", "category", "category_title", "title", "slug", "image"]


class ProductImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductImage
        fields = ["id", "image", "alt_text"]


class ProductVariantSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductVariant
        fields = ["id", "size", "color", "quantity"]


class ProductListSerializer(serializers.ModelSerializer):
    """
    Lightweight serializer for listing pages (Grid View).
    Excludes heavy descriptions and full relationship data.
    """

    category_title = serializers.ReadOnlyField(source="sub_category.category.title")
    sub_category_title = serializers.ReadOnlyField(source="sub_category.title")

    # Show the first image as the main thumbnail if available
    image = serializers.ImageField(read_only=True)

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
            "in_stock",
            "is_featured",
            "category_title",
            "sub_category_title",
        ]


class ProductDetailSerializer(serializers.ModelSerializer):
    """
    Heavy serializer for the single product page.
    Includes images, variants, and tags.
    """

    images = ProductImageSerializer(many=True, read_only=True)
    variants = ProductVariantSerializer(many=True, read_only=True)

    # Return tags as a list of strings
    tags = serializers.SerializerMethodField()

    # Flatten Category Info
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
    # Nested products so we see what's inside
    products = ProductListSerializer(many=True, read_only=True)

    class Meta:
        model = Wishlist
        fields = ["id", "products", "created_at"]


# ==========================================
# 4. CART SYSTEM SERIALIZERS
# ==========================================


class CartItemSerializer(serializers.ModelSerializer):
    """
    Serializer for individual items in the cart.
    We need Read (Nested Product) and Write (Product ID) logic.
    """

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
            "size",
            "color",
            "quantity",
            "total_price",
        ]

    def validate(self, data):
        """
        Check stock before adding to cart.
        """
        product = data.get("product")
        quantity = data.get("quantity")

        # Basic check: Is product in stock?
        if product and not product.in_stock:
            raise serializers.ValidationError(f"{product.title} is out of stock.")

        # Advanced check: Check Variant stock (if specific size/color chosen)
        # Note: You can expand this based on your exact requirements
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
    """
    Used when viewing order history.
    """

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
            "shipping_address",
            "shipping_city",
            "tracking_number",
            "created_at",
            "items",
            "coupon_code",
        ]


class OrderCreateSerializer(serializers.ModelSerializer):
    """
    Used when placing an order.
    The view will handle moving items from Cart to OrderItems.
    """

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


# ==========================================
# 6. NOTIFICATION SERIALIZER
# ==========================================


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = ["id", "title", "message", "is_read", "created_at"]
