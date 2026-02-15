from django.utils.text import slugify
from decimal import Decimal


def calculate_shipping_fee(city: str) -> Decimal:
    if (city or "").upper() == "CASABLANCA":
        return Decimal("10.00")
    return Decimal("25.00")


def unique_slugify(instance, base, slug_field="slug"):
    slug = slugify(base)
    Model = instance.__class__
    i = 1
    unique = slug
    while Model.objects.filter(**{slug_field: unique}).exclude(pk=instance.pk).exists():
        i += 1
        unique = f"{slug}-{i}"
    return unique
