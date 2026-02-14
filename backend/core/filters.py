import django_filters
from django.db.models import Avg, Q
from .models import Product, Order


class ProductFilter(django_filters.FilterSet):
    # Price range
    min_price = django_filters.NumberFilter(field_name="price", lookup_expr="gte")
    max_price = django_filters.NumberFilter(field_name="price", lookup_expr="lte")

    # Category/Subcategory
    category = django_filters.CharFilter(
        field_name="sub_category__category__slug", lookup_expr="iexact"
    )
    sub_category = django_filters.CharFilter(
        field_name="sub_category__slug", lookup_expr="iexact"
    )

    # Variant filters
    size = django_filters.CharFilter(
        field_name="variants__size__value", lookup_expr="iexact"
    )
    color = django_filters.CharFilter(
        field_name="variants__color", lookup_expr="iexact"
    )

    # Boolean flags
    in_stock = django_filters.BooleanFilter(field_name="in_stock")
    is_featured = django_filters.BooleanFilter(field_name="is_featured")

    # Discount filters
    min_discount = django_filters.NumberFilter(
        field_name="discount_percentage", lookup_expr="gte"
    )
    has_discount = django_filters.BooleanFilter(method="filter_has_discount")

    # Date range (created_at_after, created_at_before)
    created_at = django_filters.DateFromToRangeFilter(field_name="created_at")

    # Tags (comma separated): ?tags=heels,makeup
    tags = django_filters.CharFilter(method="filter_tags")

    # Rating filters (requires annotation)
    min_rating = django_filters.NumberFilter(method="filter_min_rating")
    max_rating = django_filters.NumberFilter(method="filter_max_rating")

    class Meta:
        model = Product
        fields = [
            "min_price",
            "max_price",
            "category",
            "sub_category",
            "size",
            "color",
            "in_stock",
            "is_featured",
            "min_discount",
            "has_discount",
            "created_at",
            "tags",
            "min_rating",
            "max_rating",
        ]

    def filter_has_discount(self, queryset, name, value):
        if value is True:
            return queryset.filter(discount_percentage__gt=0)
        if value is False:
            return queryset.filter(discount_percentage=0)
        return queryset

    def filter_tags(self, queryset, name, value):
        tags = [t.strip() for t in value.split(",") if t.strip()]
        if not tags:
            return queryset
        # django-taggit: tags__name
        return queryset.filter(tags__name__in=tags).distinct()

    def _with_avg_rating(self, queryset):
        # annotate avg rating for rating filters & ordering
        return queryset.annotate(avg_rating=Avg("reviews__rating"))

    def filter_min_rating(self, queryset, name, value):
        qs = self._with_avg_rating(queryset)
        return qs.filter(avg_rating__gte=value)

    def filter_max_rating(self, queryset, name, value):
        qs = self._with_avg_rating(queryset)
        return qs.filter(avg_rating__lte=value)

    @property
    def qs(self):
        # avoid duplicates from variants/tags joins
        return super().qs.distinct()


class OrderFilter(django_filters.FilterSet):
    status = django_filters.CharFilter(field_name="status", lookup_expr="iexact")
    payment_method = django_filters.CharFilter(
        field_name="payment_method", lookup_expr="iexact"
    )
    is_paid = django_filters.BooleanFilter(field_name="is_paid")

    # ?created_at_after=YYYY-MM-DD&created_at_before=YYYY-MM-DD
    created_at = django_filters.DateFromToRangeFilter(field_name="created_at")

    class Meta:
        model = Order
        fields = ["status", "payment_method", "is_paid", "created_at"]
