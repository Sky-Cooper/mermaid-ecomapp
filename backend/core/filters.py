import django_filters
from .models import Product, Order


class ProductFilter(django_filters.FilterSet):
    min_price = django_filters.NumberFilter(field_name="price", lookup_expr="gte")
    max_price = django_filters.NumberFilter(field_name="price", lookup_expr="lte")

    # Filter by Category Slug (e.g. ?category=clothing)
    category = django_filters.CharFilter(field_name="sub_category__category__slug")

    # Filter by SubCategory Slug (e.g. ?subcategory=dresses)
    sub_category = django_filters.CharFilter(field_name="sub_category__slug")

    # Boolean filters
    in_stock = django_filters.BooleanFilter(field_name="in_stock")
    is_featured = django_filters.BooleanFilter(field_name="is_featured")

    class Meta:
        model = Product
        fields = [
            "min_price",
            "max_price",
            "category",
            "sub_category",
            "in_stock",
            "is_featured",
        ]


class OrderFilter(django_filters.FilterSet):
    status = django_filters.CharFilter(field_name="status")
    created_at = django_filters.DateFromToRangeFilter()

    class Meta:
        model = Order
        fields = ["status", "created_at"]
