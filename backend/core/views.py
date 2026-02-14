from django.shortcuts import get_object_or_404
from django.db import transaction
from django.conf import settings
from django.utils import timezone
from rest_framework.views import APIView
from rest_framework.generics import (
    ListAPIView,
    RetrieveAPIView,
    RetrieveUpdateAPIView,
    CreateAPIView,
    ListCreateAPIView,
)
from rest_framework.viewsets import ModelViewSet, ReadOnlyModelViewSet
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework import status, filters, serializers
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from django_filters.rest_framework import DjangoFilterBackend

# Google Auth
from allauth.socialaccount.providers.google.views import GoogleOAuth2Adapter
from allauth.socialaccount.providers.oauth2.client import OAuth2Client
from dj_rest_auth.registration.views import SocialLoginView
from rest_framework_simplejwt.tokens import RefreshToken
from django.db.models import Avg, Prefetch, Sum, Count

# Local Imports
from .models import (
    User,
    StoreProfile,
    ShippingAddress,
    Category,
    SubCategory,
    Product,
    ProductReview,
    Wishlist,
    ShoppingCart,
    CartItem,
    Order,
    OrderItem,
    Coupon,
    Notification,
    OrderStatus,
    Attribute,
    ProductVariant,  # <--- Added
)
from .serializers import (
    CustomerRegistrationSerializer,
    CustomTokenObtainPairSerializer,
    UserProfileSerializer,
    ShippingAddressSerializer,
    StoreProfileSerializer,
    CategorySerializer,
    ProductListSerializer,
    ProductDetailSerializer,
    ProductReviewSerializer,
    WishlistSerializer,
    ShoppingCartSerializer,
    CartItemSerializer,
    OrderReadSerializer,
    OrderCreateSerializer,
    NotificationSerializer,
    AttributeSerializer,
    SubCategorySerializer,
)
from .filters import ProductFilter, OrderFilter
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.pagination import PageNumberPagination
from .pagination import StandardResultsSetPagination


class CustomerRegistrationView(APIView):
    permission_classes = [AllowAny]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        serializer = CustomerRegistrationSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            return Response(
                {"message": "Account created successfully", "user_id": user.id},
                status=status.HTTP_201_CREATED,
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer

    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)
        if response.status_code == 200:
            refresh = response.data.get("refresh")
            access = response.data.get("access")

            # Secure Cookies
            response.set_cookie(
                key="refresh_token",
                value=refresh,
                httponly=True,
                secure=not settings.DEBUG,
                samesite="Lax",
            )
            response.set_cookie(
                key="access_token",
                value=access,
                httponly=True,
                secure=not settings.DEBUG,
                samesite="Lax",
            )
        return response


class CookieTokenRefreshView(TokenRefreshView):
    def post(self, request, *args, **kwargs):
        refresh_token = request.data.get("refresh") or request.COOKIES.get(
            "refresh_token"
        )

        if not refresh_token:
            return Response(
                {"detail": "Refresh token not provided"},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        try:
            refresh = RefreshToken(refresh_token)
            access_token = str(refresh.access_token)

            # Get user from token
            user_id = refresh["user_id"]
            user = User.objects.get(id=user_id)

        except Exception:
            return Response(
                {"detail": "Token is invalid or expired"},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        response = Response(
            {
                "access": access_token,
                "user_id": user.id,
                "email": user.email,
                "full_name": user.get_full_name(),
                "role": user.role,
                "profile_image": (
                    user.profile_image.url if user.profile_image else None
                ),
            },
            status=status.HTTP_200_OK,
        )

        response.set_cookie(
            key="access_token",
            value=access_token,
            httponly=True,
            secure=not settings.DEBUG,
            samesite="Lax",
        )

        return response


class LogoutView(APIView):
    def post(self, request):
        response = Response({"message": "Logged out successfully"}, status=200)
        response.delete_cookie("refresh_token")
        response.delete_cookie("access_token")
        return response


class GoogleLogin(SocialLoginView):
    adapter_class = GoogleOAuth2Adapter
    callback_url = "http://localhost:3000"
    client_class = OAuth2Client


# ==========================================
# 2. USER & PROFILE VIEWS
# ==========================================


class UserProfileView(RetrieveUpdateAPIView):
    """
    Get or Update the logged-in user's profile.
    """

    serializer_class = UserProfileSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return self.request.user


class ShippingAddressViewSet(ModelViewSet):

    serializer_class = ShippingAddressSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return ShippingAddress.objects.filter(user=self.request.user)


class StoreProfileView(RetrieveAPIView):
    """
    Public endpoint to get store branding/settings.
    """

    queryset = StoreProfile.objects.all()
    serializer_class = StoreProfileSerializer
    permission_classes = [AllowAny]

    def get_object(self):
        return StoreProfile.objects.first()


# ==========================================
# 3. PRODUCT CATALOG VIEWS
# ==========================================


class CategoryListView(ListAPIView):
    queryset = Category.objects.filter(is_active=True)
    serializer_class = CategorySerializer
    permission_classes = [AllowAny]


class SubCategoryListView(ListAPIView):

    serializer_class = SubCategorySerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        qs = (
            SubCategory.objects.filter(is_active=True, category__is_active=True)
            .select_related("category")
            .order_by("category__title", "title")
        )

        category_slug = self.request.query_params.get("category")
        if category_slug:
            qs = qs.filter(category__slug__iexact=category_slug)

        return qs


# --- NEW: ATTRIBUTE VIEW ---
class AttributeListView(ListAPIView):
    """
    Returns available attributes (Sizes, Colors, etc.) so frontend can build filters.
    """

    queryset = Attribute.objects.all().prefetch_related("values")
    serializer_class = AttributeSerializer
    permission_classes = [AllowAny]


class ProductListView(ListAPIView):
    serializer_class = ProductListSerializer
    permission_classes = [AllowAny]

    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]
    filterset_class = ProductFilter
    search_fields = ["title", "short_description", "description", "sku", "tags__name"]

    ordering_fields = [
        "price",
        "created_at",
        "discount_percentage",
        "avg_rating",  # annotated
    ]
    ordering = ["-created_at"]  # default

    def get_queryset(self):
        return (
            Product.objects.filter(is_active=True)
            .select_related("sub_category", "sub_category__category")
            .prefetch_related("variants", "images", "tags")
            .annotate(avg_rating=Avg("reviews__rating"))
        )


class ProductDetailView(RetrieveAPIView):
    queryset = Product.objects.filter(is_active=True)
    serializer_class = ProductDetailSerializer
    permission_classes = [AllowAny]
    lookup_field = "slug"


class ProductReviewCreateView(CreateAPIView):
    serializer_class = ProductReviewSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        user = self.request.user
        product_id = self.request.data.get("product")

        # 1. Check if User already reviewed this product
        if ProductReview.objects.filter(user=user, product_id=product_id).exists():
            raise serializers.ValidationError("You have already reviewed this product.")

        # 2. Check if User has purchased and received the product
        has_purchased = Order.objects.filter(
            user=user,
            status=OrderStatus.DELIVERED,
            items__product_id=product_id,
        ).exists()

        if not has_purchased:
            raise serializers.ValidationError(
                "You can only review products you have purchased and received."
            )

        serializer.save(user=user)


class TopProductsView(ListAPIView):
    """
    /products/top/?category=...&sub_category=...
    Defaults to page_size=10.
    """

    serializer_class = ProductListSerializer
    permission_classes = [AllowAny]
    pagination_class = StandardResultsSetPagination

    def get_queryset(self):
        qs = (
            Product.objects.filter(is_active=True)
            .select_related("sub_category", "sub_category__category")
            .annotate(total_sold=Sum("orderitem__quantity"))
            .order_by("-total_sold", "-created_at")
        )

        category = self.request.query_params.get("category")
        sub_category = self.request.query_params.get("sub_category")

        if category:
            qs = qs.filter(sub_category__category__slug__iexact=category)
        if sub_category:
            qs = qs.filter(sub_category__slug__iexact=sub_category)

        return qs

    def list(self, request, *args, **kwargs):
        # Default to 10 for this endpoint
        if "page_size" not in request.query_params:
            request.query_params._mutable = True
            request.query_params["page_size"] = "10"
            request.query_params._mutable = False
        return super().list(request, *args, **kwargs)


class BestRatedProductsView(ListAPIView):
    """
    /products/best-rated/?category=...&sub_category=...
    Orders by avg_rating, tie-break by review_count.
    """

    serializer_class = ProductListSerializer
    permission_classes = [AllowAny]
    pagination_class = StandardResultsSetPagination

    def get_queryset(self):
        qs = (
            Product.objects.filter(is_active=True)
            .select_related("sub_category", "sub_category__category")
            .annotate(avg_rating=Avg("reviews__rating"), review_count=Count("reviews"))
            .order_by("-avg_rating", "-review_count", "-created_at")
        )

        category = self.request.query_params.get("category")
        sub_category = self.request.query_params.get("sub_category")

        if category:
            qs = qs.filter(sub_category__category__slug__iexact=category)
        if sub_category:
            qs = qs.filter(sub_category__slug__iexact=sub_category)

        return qs


class NewArrivalsView(ListAPIView):
    """
    /products/new/
    """

    serializer_class = ProductListSerializer
    permission_classes = [AllowAny]
    pagination_class = StandardResultsSetPagination

    def get_queryset(self):
        qs = Product.objects.filter(is_active=True).order_by("-created_at")
        category = self.request.query_params.get("category")
        sub_category = self.request.query_params.get("sub_category")
        if category:
            qs = qs.filter(sub_category__category__slug__iexact=category)
        if sub_category:
            qs = qs.filter(sub_category__slug__iexact=sub_category)
        return qs


# ==========================================
# 4. WISHLIST VIEWS
# ==========================================


class WishlistView(RetrieveAPIView):
    serializer_class = WishlistSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        wishlist, created = Wishlist.objects.get_or_create(user=self.request.user)
        return wishlist


class ToggleWishlistItemView(APIView):
    """
    POST { "product_id": 1 }
    Adds to wishlist if not present, removes if present.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        product_id = request.data.get("product_id")
        if not product_id:
            return Response({"error": "Product ID required"}, status=400)

        product = get_object_or_404(Product, id=product_id)
        wishlist, _ = Wishlist.objects.get_or_create(user=request.user)

        if wishlist.products.filter(id=product.id).exists():
            wishlist.products.remove(product)
            return Response({"message": "Removed from wishlist", "active": False})
        else:
            wishlist.products.add(product)
            return Response({"message": "Added to wishlist", "active": True})


# ==========================================
# 5. CART SYSTEM VIEWS
# ==========================================


class CartRetrieveView(RetrieveAPIView):
    """
    Get the user's current shopping cart.
    """

    serializer_class = ShoppingCartSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        cart, created = ShoppingCart.objects.get_or_create(user=self.request.user)
        return cart


class CartItemViewSet(ModelViewSet):
    """
    Add/Update/Delete items in the cart.
    """

    serializer_class = CartItemSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return CartItem.objects.filter(cart__user=self.request.user)

    def create(self, request, *args, **kwargs):
        """
        Custom Create: Check if item exists in cart -> Update Quantity.
        Otherwise -> Create new Item.
        """
        cart, _ = ShoppingCart.objects.get_or_create(user=request.user)
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        product = serializer.validated_data["product"]
        size = serializer.validated_data.get("size")
        color = serializer.validated_data.get("color")
        quantity = serializer.validated_data["quantity"]

        # Check for existing item with same attributes (size/color strings)
        existing_item = CartItem.objects.filter(
            cart=cart, product=product, size=size, color=color
        ).first()

        if existing_item:
            new_qty = existing_item.quantity + quantity

            variant_qs = ProductVariant.objects.filter(product=product)
            if size:
                variant_qs = variant_qs.filter(size__value=size)
            if color:
                variant_qs = variant_qs.filter(color=color)

            variant = variant_qs.first()
            if (size or color) and variant and variant.quantity < new_qty:
                raise ValidationError(
                    f"Only {variant.quantity} left for this option. You already have {existing_item.quantity} in cart."
                )

            existing_item.quantity = new_qty
            existing_item.save()
            return Response(
                self.get_serializer(existing_item).data, status=status.HTTP_200_OK
            )
        else:
            self.perform_create(serializer)
            return Response(serializer.data, status=status.HTTP_201_CREATED)

    def perform_create(self, serializer):
        cart, _ = ShoppingCart.objects.get_or_create(user=self.request.user)
        serializer.save(cart=cart)


# ==========================================
# 6. ORDER & CHECKOUT VIEWS
# ==========================================


class OrderViewSet(ModelViewSet):
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_class = OrderFilter
    ordering_fields = ["created_at"]

    def get_serializer_class(self):
        if self.action == "create":
            return OrderCreateSerializer
        return OrderReadSerializer

    def get_queryset(self):
        return Order.objects.filter(user=self.request.user)

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        # 1. Get Cart
        cart = ShoppingCart.objects.filter(user=request.user).first()
        if not cart or not cart.cart_items.exists():
            return Response(
                {"error": "Cart is empty"}, status=status.HTTP_400_BAD_REQUEST
            )

        # 2. Serialize Order Data (Address, etc)
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # 3. Create Order Instance
        order = serializer.save(user=request.user)

        # 4. Handle Coupon (Optional)
        coupon_code = request.data.get("coupon_code")
        if coupon_code:
            coupon = Coupon.objects.filter(
                code=coupon_code,
                active=True,
                valid_from__lte=timezone.now(),
                valid_to__gte=timezone.now(),
            ).first()
            if coupon:
                order.coupon = coupon
                order.save()

        # 5. Move Items & Calculate Total
        total_amount = Decimal("0.00")
        order_items = []

        for item in cart.cart_items.select_related("product"):
            # 1) Find & LOCK the matching variant
            variant_qs = ProductVariant.objects.select_for_update().filter(
                product=item.product
            )

            if item.size:
                variant_qs = variant_qs.filter(size__value=item.size)

            if item.color:
                variant_qs = variant_qs.filter(color=item.color)

            variant = variant_qs.first()

            # If product uses variants, ensure the variant exists
            if item.size or item.color:
                if not variant:
                    raise ValidationError(
                        f"Variant not found for {item.product.title} ({item.size}/{item.color})."
                    )

                if variant.quantity < item.quantity:
                    raise ValidationError(
                        f"Only {variant.quantity} left for {item.product.title} ({item.size}/{item.color})."
                    )

                # 2) Decrement inventory
                variant.quantity -= item.quantity
                variant.save()

            # 3) Create order items as usual
            total_amount += item.get_total_item_price()
            order_items.append(
                OrderItem(
                    order=order,
                    product=item.product,
                    product_name=item.product.title,
                    product_price=item.product.price,
                    size=item.size,
                    color=item.color,
                    quantity=item.quantity,
                )
            )

        OrderItem.objects.bulk_create(order_items)

        # Apply Discount
        if order.coupon:
            discount = (
                total_amount * Decimal(order.coupon.discount_percentage)
            ) / Decimal("100")
            total_amount = total_amount - discount

        order.total_amount = total_amount
        order.save()

        # 6. Clear Cart
        cart.cart_items.all().delete()

        read_serializer = OrderReadSerializer(order)
        return Response(read_serializer.data, status=status.HTTP_201_CREATED)


# ==========================================
# 7. NOTIFICATION VIEWS
# ==========================================


class NotificationListView(ListAPIView):
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Notification.objects.filter(user=self.request.user)


class MarkNotificationReadView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        notification = get_object_or_404(Notification, id=pk, user=request.user)
        notification.is_read = True
        notification.save()
        return Response({"status": "Marked as read"})
