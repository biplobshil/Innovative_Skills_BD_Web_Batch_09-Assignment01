import django.dispatch

# Fired once, right after an Order is confirmed paid (bKash execute succeeded).
# Sender: the Order model class. Keyword args: order (the paid Order instance).
order_paid = django.dispatch.Signal()