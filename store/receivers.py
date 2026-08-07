import logging

from django.core.mail import send_mail
from django.conf import settings
from django.dispatch import receiver

from .signals import order_paid

logger = logging.getLogger(__name__)


@receiver(order_paid)
def send_order_confirmation_email(sender, order, **kwargs):
    """
    Emails the shopper a plain-text order receipt once payment is confirmed.
    Connected via store/apps.py's ready() so it's registered on startup.
    """
    user = order.user
    if not user.email:
        logger.warning("Order #%s paid but user %s has no email on file — skipping receipt.",
                        order.id, user.username)
        return

    lines = [f"Hi {user.username},", "", "Your order has been confirmed. Thanks for shopping with us!", ""]
    lines.append(f"Order #{order.id}")
    if order.bkash_trx_id:
        lines.append(f"bKash transaction ID: {order.bkash_trx_id}")
    lines.append("")
    lines.append("Items:")
    for item in order.items.select_related("product"):
        lines.append(f"  - {item.product.name} x{item.quantity} = ৳{item.subtotal}")
    lines.append("")
    lines.append(f"Total: ৳{order.total}")
    lines.append("")
    lines.append("Thanks again!")

    send_mail(
        subject=f"Order #{order.id} confirmed",
        message="\n".join(lines),
        from_email=getattr(settings, "DEFAULT_FROM_EMAIL", None),
        recipient_list=[user.email],
        fail_silently=False,
    )
    logger.info("Order confirmation email sent to %s for order #%s", user.email, order.id)