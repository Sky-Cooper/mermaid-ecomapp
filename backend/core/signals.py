# core/signals.py
from django.dispatch import receiver
from allauth.account.signals import user_signed_up
from .models import UserRole
from django.db.models.signals import post_save
from django.conf import settings
from .models import User, ShoppingCart
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from decimal import Decimal
from .models import User, Order, OrderStatus, LoyaltyProfile, LoyaltyHistory


@receiver(post_save, sender=User)
def create_user_loyalty_profile(sender, instance, created, **kwargs):
    if created:
        LoyaltyProfile.objects.create(user=instance)


@receiver(pre_save, sender=Order)
def award_points_logic(sender, instance, **kwargs):
    if not instance.pk:
        return

    try:
        old_order = Order.objects.get(pk=instance.pk)
    except Order.DoesNotExist:
        return

    # Check if status changed TO 'DELIVERED'
    if (
        old_order.status != OrderStatus.DELIVERED
        and instance.status == OrderStatus.DELIVERED
    ):

        # LOGIC: 10 DH Spent = 1 Point
        # We exclude shipping fee from point calculation
        net_spent = instance.total_amount - instance.shipping_fee

        if net_spent > 0:
            points_earned = int(net_spent // 10)

            if points_earned > 0:
                profile, _ = LoyaltyProfile.objects.get_or_create(user=instance.user)

                # Bonus Multiplier for Tiers (Optional Idea)
                if profile.tier == "GOLD":
                    points_earned = int(points_earned * 1.5)  # 1.5x points for Gold

                profile.points += points_earned
                profile.total_lifetime_points += points_earned
                profile.calculate_tier()  # Check if they leveled up
                profile.save()

                LoyaltyHistory.objects.create(
                    profile=profile,
                    type="EARN",
                    points=points_earned,
                    description=f"Reward for Order {instance.order_id}",
                )


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
