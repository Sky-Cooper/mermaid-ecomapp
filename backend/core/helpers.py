from django.utils.text import slugify


def unique_slugify(instance, base, slug_field="slug"):
    slug = slugify(base)
    Model = instance.__class__
    i = 1
    unique = slug
    while Model.objects.filter(**{slug_field: unique}).exclude(pk=instance.pk).exists():
        i += 1
        unique = f"{slug}-{i}"
    return unique
