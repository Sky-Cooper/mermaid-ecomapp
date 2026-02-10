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
)
from .filters import ProductFilter, OrderFilter


# ==========================================
# 1. AUTHENTICATION VIEWS
# ==========================================


class CustomerRegistrationView(APIView):
    permission_classes = [AllowAny]

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
                httponly=False,
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
            return Response({"detail": "Refresh token not provided"}, status=401)

        data = {"refresh": refresh_token}
        serializer = self.get_serializer(data=data)

        try:
            serializer.is_valid(raise_exception=True)
        except Exception:
            return Response({"detail": "Token is invalid or expired"}, status=401)

        access_token = serializer.validated_data["access"]
        response = Response({"access": access_token}, status=200)
        response.set_cookie(
            key="access_token",
            value=access_token,
            httponly=False,
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
    """
    CRUD for User Addresses.
    Automatically scopes queries to the logged-in user.
    """

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
        # Always return the first store profile
        return StoreProfile.objects.first()


# ==========================================
# 3. PRODUCT CATALOG VIEWS
# ==========================================


class CategoryListView(ListAPIView):
    queryset = Category.objects.filter(is_active=True)
    serializer_class = CategorySerializer
    permission_classes = [AllowAny]


class ProductListView(ListAPIView):
    """
    List products with Filtering, Searching, and Sorting.
    """

    queryset = Product.objects.filter(is_active=True)
    serializer_class = ProductListSerializer
    permission_classes = [AllowAny]

    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]
    filterset_class = ProductFilter
    search_fields = ["title", "description", "sku"]
    ordering_fields = ["price", "created_at"]


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

        # 2. Check if User has actually purchased (and received) the product
        # We look for an Order that is DELIVERED and contains this product
        has_purchased = Order.objects.filter(
            user=user,
            status=OrderStatus.DELIVERED,  # Only allow review if delivered
            items__product_id=product_id,
        ).exists()

        if not has_purchased:
            raise serializers.ValidationError(
                "You can only review products you have purchased and received."
            )

        serializer.save(user=user)


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

        # Check for existing item with same attributes
        existing_item = CartItem.objects.filter(
            cart=cart, product=product, size=size, color=color
        ).first()

        if existing_item:
            existing_item.quantity += quantity
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
        """
        Custom Checkout Logic:
        1. Get Cart
        2. Validate Cart is not empty
        3. Create Order
        4. Move CartItems -> OrderItems
        5. Clear Cart
        """
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
        total_amount = 0
        order_items = []

        for item in cart.cart_items.all():
            if item.product.in_stock:
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
            discount = (total_amount * order.coupon.discount_percentage) / 100
            total_amount -= discount

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
