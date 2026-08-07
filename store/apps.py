from django.apps import AppConfig


class StoreConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "store"

    def ready(self):
        # Registers the order_paid signal receiver (sends the confirmation email).
        from . import receivers  # noqa: F401