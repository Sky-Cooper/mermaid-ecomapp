from django.db import models
from django.contrib.auth.models import (
    AbstractBaseUser,
    BaseUserManager,
    PermissionsMixin,
)
from phonenumber_field.modelfields import PhoneNumberField
from django.utils import timezone
from django.utils.html import mark_safe
from django.utils.text import slugify
from django.core.validators import MinValueValidator, MaxValueValidator
from taggit.managers import TaggableManager
from django.contrib.auth.models import (
    Group,
    Permission,
)
from decimal import Decimal, ROUND_HALF_UP
from .helpers import unique_slugify


class LanguageChoices(models.TextChoices):
    ARABIC = "ar", "Arabic"
    FRENCH = "fr", "French"
    ENGLISH = "en", "English"


class ShippingCity(models.TextChoices):
    AGADIR = "AGADIR", "Agadir"
    AL_HOCEIMA = "AL_HOCEIMA", "Al Hoceïma"
    AZILAL = "AZILAL", "Azilal"
    BENI_MELLAL = "BENI_MELLAL", "Béni Mellal"
    BEN_SLIMANE = "BEN_SLIMANE", "Ben Slimane"
    BERKANE = "BERKANE", "Berkane"
    BERRECHID = "BERRECHID", "Berrechid"
    BOUSKOURA = "BOUSKOURA", "Bouskoura"
    CASABLANCA = "CASABLANCA", "Casablanca"
    CHEFCHAOUEN = "CHEFCHAOUEN", "Chefchaouen"
    DAKHLA = "DAKHLA", "Dakhla"
    DAR_BOUAZZA = "DAR_BOUAZZA", "Dar Bouazza"
    EL_JADIDA = "EL_JADIDA", "El Jadida"
    ERRACHIDIA = "ERRACHIDIA", "Errachidia"
    ESSAOUIRA = "ESSAOUIRA", "Essaouira"
    FES = "FES", "Fès"
    FNIDEQ = "FNIDEQ", "Fnideq"
    GUELMIM = "GUELMIM", "Guelmim"
    IFRANE = "IFRANE", "Ifrane"
    KENITRA = "KENITRA", "Kénitra"
    KHEMISSET = "KHEMISSET", "Khémisset"
    KHENIFRA = "KHENIFRA", "Khénifra"
    KHOURIBGA = "KHOURIBGA", "Khouribga"
    LAAYOUNE = "LAAYOUNE", "Laâyoune"
    LARACHE = "LARACHE", "Larache"
    MARRAKECH = "MARRAKECH", "Marrakech"
    MARTIL = "MARTIL", "Martil"
    MEKNES = "MEKNES", "Meknès"
    MOHAMMEDIA = "MOHAMMEDIA", "Mohammédia"
    NADOR = "NADOR", "Nador"
    OUARZAZATE = "OUARZAZATE", "Ouarzazate"
    OUJDA = "OUJDA", "Oujda"
    RABAT = "RABAT", "Rabat"
    SAFI = "SAFI", "Safi"
    SALE = "SALE", "Salé"
    SETTAT = "SETTAT", "Settat"
    SIDI_KACEM = "SIDI_KACEM", "Sidi Kacem"
    SKHIRAT = "SKHIRAT", "Skhirat"
    TANGER = "TANGER", "Tanger"
    TAROUDANT = "TAROUDANT", "Taroudant"
    TAZA = "TAZA", "Taza"
    TEMARA = "TEMARA", "Témara"
    TETOUAN = "TETOUAN", "Tétouan"
    TIZNIT = "TIZNIT", "Tiznit"
    OTHER = "OTHER", "Other"


class LoyaltyTier(models.TextChoices):
    BRONZE = "BRONZE", "Bronze Member"
    SILVER = "SILVER", "Silver Member"
    GOLD = "GOLD", "Gold Member"


class UserRole(models.TextChoices):
    SUPER_ADMIN = "SUPER_ADMIN", "Super Admin"
    ADMIN = "ADMIN", "Admin"
    CUSTOMER = "CUSTOMER", "Customer"
    SUPPORT = "SUPPORT", "Customer Support"


class OrderStatus(models.TextChoices):
    PENDING = "PENDING", "Pending"
    PROCESSING = "PROCESSING", "Processing"
    SHIPPED = "SHIPPED", "Shipped"
    DELIVERED = "DELIVERED", "Delivered"
    CANCELLED = "CANCELLED", "Cancelled"
    RETURNED = "RETURNED", "Returned"
    REFUNDED = "REFUNDED", "Refunded"


class PaymentMethod(models.TextChoices):
    CASH_ON_DELIVERY = "COD", "Cash on Delivery"
    CARD = "CARD", "Credit Card"
    PAYPAL = "PAYPAL", "PayPal"


class AddressType(models.TextChoices):
    HOME = "HOME", "Home"
    OFFICE = "OFFICE", "Office"


class ColorChoices(models.TextChoices):
    BLACK = "BLACK", "Black"
    WHITE = "WHITE", "White"
    RED = "RED", "Red"
    PINK = "PINK", "Pink"
    NUDE = "NUDE", "Nude"
    GOLD = "GOLD", "Gold"
    SILVER = "SILVER", "Silver"
    BLUE = "BLUE", "Blue"
    GREEN = "GREEN", "Green"
    PURPLE = "PURPLE", "Purple"
    MULTICOLOR = "MULTI", "Multicolor"
    NONE = "NONE", "None"


class RatingChoices(models.IntegerChoices):
    ONE = 1, "★☆☆☆☆"
    TWO = 2, "★★☆☆☆"
    THREE = 3, "★★★☆☆"
    FOUR = 4, "★★★★☆"
    FIVE = 5, "★★★★★"


# ==========================================
# 2. USER & AUTH MODELS
# ==========================================


class ApplicationUserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("Email is required")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("role", UserRole.SUPER_ADMIN)
        return self.create_user(email, password, **extra_fields)


class StoreProfile(models.Model):
    """
    Since this is a single-owner app, this model holds
    YOUR store's settings and metadata.
    """

    store_name = models.CharField(max_length=255, default="My Mermaid Store")
    description = models.TextField(blank=True, null=True)
    support_email = models.EmailField()
    support_phone = PhoneNumberField(region="MA")

    # Store Branding
    logo = models.ImageField(upload_to="store/branding/", blank=True, null=True)

    # Social Media Links
    instagram_link = models.URLField(blank=True, null=True)
    tiktok_link = models.URLField(blank=True, null=True)

    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.store_name


class User(AbstractBaseUser, PermissionsMixin):
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    phone_number = PhoneNumberField(region="MA", unique=True, null=True, blank=True)

    role = models.CharField(
        max_length=30, choices=UserRole.choices, default=UserRole.CUSTOMER
    )
    preferred_language = models.CharField(
        max_length=10, choices=LanguageChoices.choices, default=LanguageChoices.FRENCH
    )
    profile_image = models.ImageField(upload_to="profiles/", null=True, blank=True)

    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)

    is_email_verified = models.BooleanField(default=False)
    date_of_birth = models.DateField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # ------------- Fix for group & permission clashes -------------
    groups = models.ManyToManyField(
        Group,
        related_name="core_user_set",  # <--- avoid clash with auth.User
        blank=True,
        help_text="The groups this user belongs to.",
    )
    user_permissions = models.ManyToManyField(
        Permission,
        related_name="core_user_permissions_set",  # <--- avoid clash
        blank=True,
        help_text="Specific permissions for this user.",
    )
    # --------------------------------------------------------------

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["first_name", "last_name"]

    objects = ApplicationUserManager()

    def get_full_name(self):
        return f"{self.first_name} {self.last_name}"

    def __str__(self):
        return self.email


class LoyaltyProfile(models.Model):
    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name="loyalty_profile"
    )
    points = models.PositiveIntegerField(default=0)
    total_lifetime_points = models.PositiveIntegerField(
        default=0
    )  # Used to calculate Tier
    tier = models.CharField(
        max_length=20, choices=LoyaltyTier.choices, default=LoyaltyTier.BRONZE
    )
    updated_at = models.DateTimeField(auto_now=True)

    def calculate_tier(self):
        """Auto-upgrade tier based on lifetime points"""
        if self.total_lifetime_points >= 2000:  # 20,000 DH spent
            self.tier = LoyaltyTier.GOLD
        elif self.total_lifetime_points >= 500:  # 5,000 DH spent
            self.tier = LoyaltyTier.SILVER
        else:
            self.tier = LoyaltyTier.BRONZE
        self.save()

    def __str__(self):
        return f"{self.user.email} - {self.points} pts ({self.tier})"


class LoyaltyHistory(models.Model):
    TRANSACTION_TYPES = (
        ("EARN", "Earned"),
        ("SPEND", "Spent"),
        ("BONUS", "Bonus"),
    )
    profile = models.ForeignKey(
        LoyaltyProfile, on_delete=models.CASCADE, related_name="history"
    )
    type = models.CharField(max_length=10, choices=TRANSACTION_TYPES)
    points = models.IntegerField()  # Can be negative for refunds
    description = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)


class ShippingAddress(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="addresses")
    name = models.CharField(max_length=100, help_text="e.g. Home, Office")
    full_name = models.CharField(max_length=100, help_text="Receiver's name")
    address_line_1 = models.CharField(max_length=255)
    address_line_2 = models.CharField(max_length=255, blank=True, null=True)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100, blank=True, null=True)
    postal_code = models.CharField(max_length=20)
    phone_number = PhoneNumberField(region="MA")

    address_type = models.CharField(
        max_length=20, choices=AddressType.choices, default=AddressType.HOME
    )
    is_default = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = "Shipping Addresses"

    def save(self, *args, **kwargs):
        if self.is_default:
            ShippingAddress.objects.filter(user=self.user).exclude(id=self.id).update(
                is_default=False
            )
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name} - {self.city}"


# ==========================================
# 3. PRODUCT CATALOG MODELS
# ==========================================


class Category(models.Model):
    title = models.CharField(max_length=128)
    slug = models.SlugField(unique=True)
    image = models.ImageField(upload_to="categories/")
    description = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = "Categories"

    def __str__(self):
        return self.title


class SubCategory(models.Model):
    category = models.ForeignKey(
        Category, on_delete=models.CASCADE, related_name="sub_categories"
    )
    title = models.CharField(max_length=128)
    slug = models.SlugField(unique=True)
    image = models.ImageField(upload_to="subcategories/", blank=True, null=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name_plural = "Sub Categories"

    def __str__(self):
        return f"{self.category.title} > {self.title}"


class Product(models.Model):
    title = models.CharField(max_length=255)
    slug = models.SlugField(unique=True)
    sku = models.CharField(max_length=100, unique=True, help_text="Stock Keeping Unit")

    sub_category = models.ForeignKey(
        SubCategory, on_delete=models.SET_NULL, null=True, related_name="products"
    )

    # Description & SEO
    short_description = models.CharField(max_length=165)
    description = models.TextField()
    tags = TaggableManager(blank=True)

    # Media
    image = models.ImageField(
        upload_to="products/main/", help_text="Main Product Image"
    )

    # Pricing
    price = models.DecimalField(max_digits=10, decimal_places=2)
    old_price = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )
    discount_percentage = models.PositiveIntegerField(default=0)
    specifications = models.JSONField(default=dict, blank=True)

    # Status
    in_stock = models.BooleanField(default=True)
    is_active = models.BooleanField(default=True)
    is_featured = models.BooleanField(default=False)

    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def save(self, *args, **kwargs):
        # Auto-calculate discount
        if self.old_price and self.old_price > self.price:
            discount = (self.old_price - self.price) / self.old_price * Decimal("100")
            self.discount_percentage = int(
                discount.quantize(Decimal("1"), rounding=ROUND_HALF_UP)
            )
        else:
            self.discount_percentage = 0

        # Auto-slug if missing
        if not self.slug:
            self.slug = unique_slugify(self, self.title)

        super().save(*args, **kwargs)

    def __str__(self):
        return self.title


class ProductImage(models.Model):
    product = models.ForeignKey(
        Product, on_delete=models.CASCADE, related_name="images"
    )
    image = models.ImageField(upload_to="products/gallery/")
    alt_text = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self):
        return f"Img for {self.product.title}"


class Attribute(models.Model):
    """
    Defines the TYPE of variation.
    e.g., "Size", "Color", "Shoe Size", "Ring Size"
    """

    code = models.CharField(max_length=30, unique=True)
    name = models.CharField(max_length=50)  # e.g. "Clothing Size"

    def __str__(self):
        return self.name


class AttributeValue(models.Model):
    """
    Defines the specific options.
    """

    attribute = models.ForeignKey(
        Attribute, on_delete=models.CASCADE, related_name="values"
    )
    value = models.CharField(max_length=50)  # e.g. "XL", "Red", "38"

    def __str__(self):
        return f"{self.attribute.name}: {self.value}"


class ProductVariant(models.Model):
    product = models.ForeignKey(
        Product, on_delete=models.CASCADE, related_name="variants"
    )
    size = models.ForeignKey(
        AttributeValue,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="variant_sizes",
        limit_choices_to={
            "attribute__code__in": ["SIZE", "SHOE_SIZE"]
        },  # Optional filter
    )
    color = models.CharField(
        max_length=20, choices=ColorChoices.choices, default=ColorChoices.NONE
    )
    sku_modifier = models.CharField(max_length=50, blank=True, help_text="e.g. -RED-XL")
    quantity = models.PositiveIntegerField(default=0)

    class Meta:
        unique_together = ("product", "size", "color")

    def __str__(self):
        return f"{self.product.title} - {self.color} - {self.size}"


# ==========================================
# 4. REVIEWS & WISHLIST
# ==========================================


class ProductReview(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="reviews")
    product = models.ForeignKey(
        Product, on_delete=models.CASCADE, related_name="reviews"
    )
    rating = models.PositiveIntegerField(choices=RatingChoices.choices)
    review_text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("user", "product")  # User can review product only once

    def __str__(self):
        return f"{self.user.get_full_name()} - {self.product.title} ({self.rating})"


class Wishlist(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="wishlist")
    products = models.ManyToManyField(Product, related_name="wishlisted_by", blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Wishlist of {self.user.get_full_name()}"


# ==========================================
# 5. CART SYSTEM
# ==========================================


class ShoppingCart(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="cart")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def get_total_price(self):
        return sum(item.get_total_item_price() for item in self.cart_items.all())

    def __str__(self):
        return f"Cart: {self.user.email}"


class CartItem(models.Model):
    cart = models.ForeignKey(
        ShoppingCart, on_delete=models.CASCADE, related_name="cart_items"
    )
    product = models.ForeignKey(Product, on_delete=models.CASCADE)

    # Selected Attributes
    size = models.CharField(max_length=50, blank=True, null=True)
    color = models.CharField(
        max_length=20, choices=ColorChoices.choices, default=ColorChoices.NONE
    )

    quantity = models.PositiveIntegerField(default=1, validators=[MinValueValidator(1)])
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("cart", "product", "size", "color")

    def get_total_item_price(self):
        return self.quantity * self.product.price

    def __str__(self):
        return f"{self.quantity} x {self.product.title}"


# ==========================================
# 6. ORDER SYSTEM (Checkout)
# ==========================================


class Coupon(models.Model):
    code = models.CharField(max_length=50, unique=True)

    discount_percentage = models.PositiveIntegerField(
        validators=[MaxValueValidator(100)]
    )
    fixed_discount_amount = models.DecimalField(
        max_digits=10, decimal_places=2, default=Decimal("0.00")
    )

    valid_from = models.DateTimeField()
    valid_to = models.DateTimeField()
    active = models.BooleanField(default=True)

    # NEW
    owner = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="coupons", null=True, blank=True
    )
    is_used = models.BooleanField(default=False)
    used_at = models.DateTimeField(null=True, blank=True)

    def is_valid(self):
        now = timezone.now()
        return (
            self.active and self.valid_from <= now <= self.valid_to and not self.is_used
        )


class Order(models.Model):
    # Order Identification
    order_id = models.CharField(
        max_length=100, unique=True, editable=False
    )  # e.g. ORD-2025-001
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="orders")

    # Shipping Info (Snapshot at time of order)
    shipping_address = models.TextField()
    shipping_phone = models.CharField(max_length=50)

    # Status
    status = models.CharField(
        max_length=20, choices=OrderStatus.choices, default=OrderStatus.PENDING
    )
    payment_method = models.CharField(
        max_length=20,
        choices=PaymentMethod.choices,
        default=PaymentMethod.CASH_ON_DELIVERY,
    )
    is_paid = models.BooleanField(default=False)

    shipping_city = models.CharField(
        max_length=50,
        choices=ShippingCity.choices,
    )

    shipping_fee = models.DecimalField(
        max_digits=10, decimal_places=2, default=Decimal("0.00")
    )
    total_amount = models.DecimalField(
        max_digits=10, decimal_places=2, default=Decimal("0.00")
    )
    coupon = models.ForeignKey(Coupon, on_delete=models.SET_NULL, null=True, blank=True)

    # Tracking
    tracking_number = models.CharField(max_length=100, blank=True, null=True)
    note = models.TextField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if not self.order_id:
            # Simple ID generation strategy
            timestamp = timezone.now().strftime("%Y%m%d%H%M%S")
            self.order_id = f"ORD-{timestamp}-{self.user.id}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.order_id} - {self.user.get_full_name()}"


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True)

    # Snapshot of data in case product is deleted/changed later
    product_name = models.CharField(max_length=255)
    product_price = models.DecimalField(
        max_digits=10, decimal_places=2
    )  # Price AT MOMENT of purchase

    size = models.CharField(max_length=50, blank=True, null=True)
    color = models.CharField(max_length=20)
    quantity = models.PositiveIntegerField(default=1)

    def get_subtotal(self):
        return (self.product_price or Decimal("0.00")) * (self.quantity or 0)

    def __str__(self):
        return f"{self.quantity} x {self.product_name}"


# ==========================================
# 7. NOTIFICATIONS
# ==========================================


class Notification(models.Model):
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="notifications"
    )
    title = models.CharField(max_length=255)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user.email} - {self.title}"
