from decimal import Decimal

from .models import Product

CART_SESSION_KEY = "cart"


class Cart:
    """
    A shopping cart stored in the session, so it works for anonymous
    shoppers without requiring an account. Structure in session:
        {"<product_id>": {"quantity": 2, "price": "59.99"}, ...}
    """

    def __init__(self, request):
        self.session = request.session
        cart = self.session.get(CART_SESSION_KEY)
        if cart is None:
            cart = self.session[CART_SESSION_KEY] = {}
        self.cart = cart

    def add(self, product, quantity=1):
        product_id = str(product.id)
        if product_id in self.cart:
            self.cart[product_id]["quantity"] += quantity
        else:
            self.cart[product_id] = {"quantity": quantity, "price": str(product.price)}
        self._save()

    def update(self, product, quantity):
        product_id = str(product.id)
        if product_id not in self.cart:
            return
        if quantity <= 0:
            self.remove(product)
        else:
            self.cart[product_id]["quantity"] = quantity
            self._save()

    def remove(self, product):
        product_id = str(product.id)
        if product_id in self.cart:
            del self.cart[product_id]
            self._save()

    def clear(self):
        self.session[CART_SESSION_KEY] = {}
        self._save()

    def _save(self):
        self.session.modified = True

    def __iter__(self):
        """Yield dicts with product, quantity, price, subtotal for template rendering."""
        product_ids = self.cart.keys()
        products = {str(p.id): p for p in Product.objects.filter(id__in=product_ids)}

        for product_id, item in self.cart.items():
            product = products.get(product_id)
            if not product:
                continue  # product was deleted since being added to cart
            price = Decimal(item["price"])
            quantity = item["quantity"]
            yield {
                "product": product,
                "quantity": quantity,
                "price": price,
                "subtotal": price * quantity,
            }

    def __len__(self):
        """Total number of items (sum of quantities) — used for the nav badge."""
        return sum(item["quantity"] for item in self.cart.values())

    def get_total(self):
        return sum(Decimal(item["price"]) * item["quantity"] for item in self.cart.values())
