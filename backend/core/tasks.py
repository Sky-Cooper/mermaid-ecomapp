import os
from decimal import Decimal
from email.mime.image import MIMEImage

from celery import shared_task
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils import timezone


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_kwargs={"max_retries": 5},
)
def send_order_confirmation_email(self, order_db_id: int) -> str:
    # Import models inside the task to avoid celery boot import issues
    from core.models import Order

    order = (
        Order.objects.select_related("user", "coupon")
        .prefetch_related("items")
        .get(id=order_db_id)
    )

    user = order.user
    to_email = user.email
    if not to_email:
        return f"Skipped: user {user.id} has no email"

    items_ctx = []
    subtotal = Decimal("0.00")

    for it in order.items.all():
        line = (it.product_price or Decimal("0.00")) * (it.quantity or 0)
        subtotal += line
        items_ctx.append(
            {
                "product_name": it.product_name,
                "quantity": it.quantity,
                "size": it.size,
                "color": it.color,
                "subtotal": f"{line:.2f}",
            }
        )

    support_email = getattr(settings, "DEFAULT_FROM_EMAIL", None) or getattr(
        settings, "EMAIL_HOST_USER", ""
    )

    context = {
        "user_first_name": getattr(user, "first_name", "") or "Valued Client",
        "order_id": order.order_id,
        "order_date": timezone.localtime(order.created_at).strftime(
            "%B %d, %Y · %H:%M"
        ),
        "order_status": order.status,
        "items": items_ctx,
        "subtotal": f"{subtotal:.2f}",
        "shipping_fee": f"{(order.shipping_fee or Decimal('0.00')):.2f}",
        "total_amount": f"{(order.total_amount or Decimal('0.00')):.2f}",
        "coupon_code": getattr(order.coupon, "code", "") if order.coupon else "",
        "shipping_city": order.shipping_city,
        "support_email": support_email,
        "year": timezone.now().year,
    }

    subject = f"LUNEA — Order Confirmed · {order.order_id}"
    html_body = render_to_string("orders/neworder.html", context)

    text_body = (
        f"LUNEA — Order Confirmed\n"
        f"Order: {order.order_id}\n"
        f"Date: {context['order_date']}\n\n"
        f"Total: {context['total_amount']} MAD\n\n"
        f"With gratitude,\nLUNEA Concierge\nSupport: {support_email}\n"
    )

    from_email = (
        getattr(settings, "DEFAULT_FROM_EMAIL", None) or settings.EMAIL_HOST_USER
    )

    msg = EmailMultiAlternatives(
        subject=subject,
        body=text_body,
        from_email=from_email,
        to=[to_email],
    )
    msg.attach_alternative(html_body, "text/html")

    # Inline logo
    logo_path = os.path.join(
        settings.BASE_DIR.parent, "static", "assets", "LuneaLOGO.png"
    )
    if os.path.exists(logo_path):
        with open(logo_path, "rb") as f:
            img = MIMEImage(f.read())
            img.add_header("Content-ID", "<lunea_logo>")
            img.add_header("Content-Disposition", "inline", filename="LuneaLOGO.png")
            msg.mixed_subtype = "related"
            msg.attach(img)

    msg.send(fail_silently=False)
    return f"Sent confirmation to {to_email} for {order.order_id}"


@shared_task
def ping():
    return "pong"
