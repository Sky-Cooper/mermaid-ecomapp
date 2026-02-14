# core/signals.py
from django.dispatch import receiver
from allauth.account.signals import user_signed_up
from .models import UserRole
from django.db.models.signals import post_save
from django.conf import settings
from .models import User, ShoppingCart


@receiver(user_signed_up)
def populate_google_user_role(request, user, **kwargs):
    """
    When a user signs up via Social Auth (Google),
    ensure their role is set to CUSTOMER.
    """
    if not user.role:
        user.role = UserRole.CUSTOMER
        user.save()


@receiver(post_save, sender=User)
def create_user_cart(sender, instance, created, **kwargs):
    if created:
        ShoppingCart.objects.create(user=instance)
