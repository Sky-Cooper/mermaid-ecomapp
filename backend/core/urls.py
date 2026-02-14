from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    # Auth
    CustomerRegistrationView,
    CustomTokenObtainPairView,
    CookieTokenRefreshView,
    LogoutView,
    GoogleLogin,
    # User & Profile
    UserProfileView,
    StoreProfileView,
    ShippingAddressViewSet,
    # Products
    CategoryListView,
    AttributeListView,  # <--- Added
    ProductListView,
    ProductDetailView,
    ProductReviewCreateView,
    TopProductsView,  # <--- Added
    BestRatedProductsView,  # <--- Added
    NewArrivalsView,  # <--- Added
    # Wishlist
    WishlistView,
    ToggleWishlistItemView,
    # Cart
    CartRetrieveView,
    CartItemViewSet,
    # Orders
    OrderViewSet,
    # Notifications
    NotificationListView,
    MarkNotificationReadView,
)

# 1. Setup Router for ViewSets
# ViewSets handle multiple actions (GET list, GET detail, POST, PUT, DELETE) automatically
router = DefaultRouter()
router.register(r"addresses", ShippingAddressViewSet, basename="address")
router.register(r"cart/items", CartItemViewSet, basename="cart-items")
router.register(r"orders", OrderViewSet, basename="orders")

urlpatterns = [
    # ==============================
    # 1. Authentication
    # ==============================
    path("auth/register/", CustomerRegistrationView.as_view(), name="register"),
    path("auth/login/", CustomTokenObtainPairView.as_view(), name="login"),
    path("auth/refresh/", CookieTokenRefreshView.as_view(), name="refresh"),
    path("auth/logout/", LogoutView.as_view(), name="logout"),
    path("auth/google/", GoogleLogin.as_view(), name="google_login"),
    # ==============================
    # 2. User & Store Profile
    # ==============================
    path("profile/", UserProfileView.as_view(), name="user-profile"),
    path("store/info/", StoreProfileView.as_view(), name="store-info"),
    # ==============================
    # 3. Product Catalog
    # ==============================
    # Metadata & Filters
    path("products/categories/", CategoryListView.as_view(), name="category-list"),
    path(
        "products/attributes/", AttributeListView.as_view(), name="attribute-list"
    ),  # Used for frontend filters
    # Specialized Lists (MUST come before <slug:slug>)
    path("products/trending/", TopProductsView.as_view(), name="product-trending"),
    path(
        "products/best-rated/",
        BestRatedProductsView.as_view(),
        name="product-best-rated",
    ),
    path("products/new/", NewArrivalsView.as_view(), name="product-new"),
    # General List & Reviews
    path("products/", ProductListView.as_view(), name="product-list"),
    path("products/review/", ProductReviewCreateView.as_view(), name="product-review"),
    # Product Detail (Catches everything else, so keep it last in this section)
    path("products/<slug:slug>/", ProductDetailView.as_view(), name="product-detail"),
    # ==============================
    # 4. Wishlist
    # ==============================
    path("wishlist/", WishlistView.as_view(), name="wishlist"),
    path("wishlist/toggle/", ToggleWishlistItemView.as_view(), name="wishlist-toggle"),
    # ==============================
    # 5. Cart System
    # ==============================
    path("cart/", CartRetrieveView.as_view(), name="cart-detail"),
    # Note: 'cart/items/' is handled by the Router above
    # ==============================
    # 6. Notifications
    # ==============================
    path("notifications/", NotificationListView.as_view(), name="notifications"),
    path(
        "notifications/<int:pk>/read/",
        MarkNotificationReadView.as_view(),
        name="notification-read",
    ),
    # ==============================
    # 7. Router URLs (Addresses, Orders, CartItems)
    # ==============================
    path("", include(router.urls)),
]
