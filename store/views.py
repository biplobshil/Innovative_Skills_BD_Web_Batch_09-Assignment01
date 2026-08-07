from django.contrib import messages
from django.contrib.auth import login as auth_login
from django.contrib.auth.decorators import login_required
from django.db.models import Case, Count, IntegerField, Q, When
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response

from .cart import Cart
from .filters import ProductFilter
from .forms import SignupForm
from .models import Category, Order, OrderItem, Product
from .payments import bkash
from .signals import order_paid
from .serializers import (
    CategorySerializer,
    OrderSerializer,
    ProductSearchResultSerializer,
    ProductSerializer,
)


class CategoryViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    lookup_field = "slug"


class ProductViewSet(viewsets.ModelViewSet):
    """
    Standard CRUD for products, plus:
      GET /api/products/search/?q=<term>  -> instant/typeahead search
    """

    queryset = Product.objects.filter(is_active=True).select_related("category")
    serializer_class = ProductSerializer
    filterset_class = ProductFilter
    search_param = "q"

    def get_permissions(self):
        if self.action in ["create", "update", "partial_update", "destroy"]:
            return [permissions.IsAdminUser()]
        return [permissions.AllowAny()]

    @action(detail=False, methods=["get"], url_path="search")
    def search(self, request):
        """
        Real-time / typeahead search endpoint.

        Designed to be called on every keystroke from the frontend (debounced
        client-side ~250-300ms). Ranks results so matches at the start of the
        product name surface first, then substring matches in name/brand,
        then matches in description.

        NOTE: on SQLite this uses indexed `icontains` lookups, which is fine
        for demo/small catalogs. For production-scale full-text search on
        PostgreSQL, swap this for `SearchVector` / `SearchRank`
        (django.contrib.postgres.search) or an external engine like
        Elasticsearch/Meilisearch/Algolia — the endpoint contract below
        (same query params, same response shape) would stay identical.
        """
        query = request.query_params.get(self.search_param, "").strip()
        limit = int(request.query_params.get("limit", 10))

        if not query:
            return Response({"count": 0, "results": []})

        qs = self.filter_queryset(self.get_queryset())

        qs = qs.filter(
            Q(name__icontains=query)
            | Q(brand__icontains=query)
            | Q(description__icontains=query)
            | Q(category__name__icontains=query)
        )

        qs = qs.annotate(
            relevance=Case(
                When(name__istartswith=query, then=0),
                When(name__icontains=query, then=1),
                When(brand__icontains=query, then=2),
                When(category__name__icontains=query, then=3),
                default=4,
                output_field=IntegerField(),
            )
        ).order_by("relevance", "name")[:limit]

        serializer = ProductSearchResultSerializer(qs, many=True, context={"request": request})
        return Response({"count": len(serializer.data), "results": serializer.data})

    @action(detail=False, methods=["get"], url_path="suggestions")
    def suggestions(self, request):
        """Lightweight autocomplete: just distinct matching product names."""
        query = request.query_params.get(self.search_param, "").strip()
        if not query:
            return Response([])
        names = (
            Product.objects.filter(is_active=True, name__icontains=query)
            .order_by("name")
            .values_list("name", flat=True)
            .distinct()[:8]
        )
        return Response(list(names))


class OrderViewSet(viewsets.ModelViewSet):
    serializer_class = OrderSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Order.objects.filter(user=self.request.user).prefetch_related("items")

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(user=request.user)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


# ---------------------------------------------------------------------------
# Django-template views (server-rendered data viewing)
#
# These render HTML directly instead of JSON. The product list page loads
# with results already rendered server-side (works with JS off), and the
# search box then re-fetches just the results fragment on each keystroke —
# same relevance ranking as the DRF /api/products/search/ endpoint, but the
# response is a rendered HTML partial rather than JSON.
# ---------------------------------------------------------------------------

def _filtered_products(request):
    """Shared query logic for the product list page and its live-search fragment."""
    query = request.GET.get("q", "").strip()
    category_slug = request.GET.get("category", "").strip()
    min_price = request.GET.get("min_price", "").strip()
    max_price = request.GET.get("max_price", "").strip()

    products = Product.objects.filter(is_active=True).select_related("category")

    if category_slug:
        products = products.filter(category__slug=category_slug)
    if min_price:
        products = products.filter(price__gte=min_price)
    if max_price:
        products = products.filter(price__lte=max_price)

    if query:
        products = products.filter(
            Q(name__icontains=query)
            | Q(brand__icontains=query)
            | Q(description__icontains=query)
            | Q(category__name__icontains=query)
        ).annotate(
            relevance=Case(
                When(name__istartswith=query, then=0),
                When(name__icontains=query, then=1),
                When(brand__icontains=query, then=2),
                When(category__name__icontains=query, then=3),
                default=4,
                output_field=IntegerField(),
            )
        ).order_by("relevance", "name")
    else:
        products = products.order_by("-created_at")

    return products[:60], query


def product_list_view(request):
    """Full page: sidebar filters + initial server-rendered product grid."""
    products, query = _filtered_products(request)
    context = {
        "products": products,
        "query": query,
        "categories": Category.objects.all(),
        "selected_category": request.GET.get("category", ""),
        "min_price": request.GET.get("min_price", ""),
        "max_price": request.GET.get("max_price", ""),
    }
    return render(request, "store/product_list.html", context)


def product_search_fragment(request):
    """
    Called on every keystroke (debounced client-side) by product_list.html.
    Returns just the rendered grid HTML — no JSON, no client-side templating.
    """
    products, query = _filtered_products(request)
    return render(request, "store/partials/product_grid.html", {
        "products": products,
        "query": query,
    })


def product_detail_view(request, slug):
    product = get_object_or_404(
        Product.objects.select_related("category"), slug=slug, is_active=True
    )
    related = (
        Product.objects.filter(category=product.category, is_active=True)
        .exclude(pk=product.pk)[:4]
    )
    return render(request, "store/product_detail.html", {
        "product": product,
        "related": related,
    })


# ---------------------------------------------------------------------------
# Category viewing (read-only — creating/editing/deleting is done via
# Django admin at /admin/store/category/, not exposed to end users here)
# ---------------------------------------------------------------------------

def category_list_view(request):
    categories = Category.objects.annotate(product_count=Count("products")).order_by("name")
    return render(request, "store/category_list.html", {"categories": categories})


# ---------------------------------------------------------------------------
# Cart (session-based — works without login)
# ---------------------------------------------------------------------------

def cart_view(request):
    return render(request, "store/cart.html", {"cart": Cart(request)})


def cart_add_view(request, product_id):
    if request.method != "POST":
        return redirect("store:cart-detail")

    product = get_object_or_404(Product, id=product_id, is_active=True)
    try:
        quantity = int(request.POST.get("quantity", 1))
    except ValueError:
        quantity = 1
    quantity = max(1, min(quantity, product.stock)) if product.stock else 0

    if quantity == 0:
        messages.error(request, f'"{product.name}" is out of stock.')
    else:
        Cart(request).add(product, quantity)
        messages.success(request, f'Added "{product.name}" to your cart.')

    next_url = request.POST.get("next") or request.META.get("HTTP_REFERER") or reverse("store:cart-detail")
    return redirect(next_url)


def cart_update_view(request, product_id):
    if request.method != "POST":
        return redirect("store:cart-detail")

    product = get_object_or_404(Product, id=product_id)
    try:
        quantity = int(request.POST.get("quantity", 1))
    except ValueError:
        quantity = 1
    Cart(request).update(product, quantity)
    return redirect("store:cart-detail")


def cart_remove_view(request, product_id):
    if request.method != "POST":
        return redirect("store:cart-detail")

    product = get_object_or_404(Product, id=product_id)
    Cart(request).remove(product)
    messages.success(request, f'Removed "{product.name}" from your cart.')
    return redirect("store:cart-detail")


# ---------------------------------------------------------------------------
# Auth (signup only — login/logout use Django's built-in views, wired up
# in ecommerce/urls.py with our own templates)
# ---------------------------------------------------------------------------

def signup_view(request):
    if request.user.is_authenticated:
        return redirect("store:product-list")

    if request.method == "POST":
        form = SignupForm(request.POST)
        if form.is_valid():
            user = form.save()
            auth_login(request, user)
            messages.success(request, f"Welcome, {user.username}!")
            next_url = request.POST.get("next") or reverse("store:product-list")
            return redirect(next_url)
    else:
        form = SignupForm()

    return render(request, "registration/signup.html", {
        "form": form,
        "next": request.GET.get("next", ""),
    })


# ---------------------------------------------------------------------------
# Checkout — requires login. Anonymous users get redirected to /accounts/login/
# with ?next=/products/checkout/ and land back here automatically after
# signing in, courtesy of Django's login_required + LoginView.
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Checkout — requires login. Anonymous users get redirected to /accounts/login/
# with ?next=/products/checkout/ and land back here automatically after
# signing in, courtesy of Django's login_required + LoginView.
#
# Payment is via bKash Tokenized Checkout:
#   checkout_view       -> creates a pending Order, calls bKash Create Payment,
#                          redirects the browser to bKash's hosted payment page
#   bkash_callback_view -> bKash redirects back here after the shopper pays
#                          (or cancels/fails); we call Execute Payment to
#                          confirm, then mark the order paid/failed
# ---------------------------------------------------------------------------

@login_required
def checkout_view(request):
    cart = Cart(request)
    if len(cart) == 0:
        messages.error(request, "Your cart is empty.")
        return redirect("store:cart-detail")

    if request.method == "POST":
        payer_reference = request.POST.get("payer_reference", "").strip()
        if not payer_reference:
            messages.error(request, "Enter the mobile number linked to your bKash account.")
            return render(request, "store/checkout.html", {"cart": cart})

        # Re-check stock at the moment of purchase — it may have changed
        # since the item was added to the cart. Stock is only decremented
        # once payment is confirmed in bkash_callback_view, not here.
        for item in cart:
            if item["quantity"] > item["product"].stock:
                messages.error(
                    request,
                    f'Only {item["product"].stock} of "{item["product"].name}" left in stock.'
                )
                return redirect("store:cart-detail")

        order = Order.objects.create(user=request.user, status="pending")
        for item in cart:
            OrderItem.objects.create(
                order=order,
                product=item["product"],
                quantity=item["quantity"],
                price=item["price"],
            )

        callback_url = request.build_absolute_uri(reverse("store:bkash-callback"))
        try:
            id_token = bkash.grant_token()
            payment = bkash.create_payment(
                id_token,
                amount=cart.get_total(),
                callback_url=callback_url,
                merchant_invoice_number=f"ORD{order.id}",
                payer_reference=payer_reference,
            )
        except bkash.BkashError as exc:
            order.status = "payment_failed"
            order.save(update_fields=["status"])
            messages.error(request, f"Could not start bKash payment: {exc}")
            return render(request, "store/checkout.html", {"cart": cart})

        order.bkash_payment_id = payment["paymentID"]
        order.save(update_fields=["bkash_payment_id"])

        # Stash identifiers in the session so the callback can verify the
        # order it's completing actually belongs to this shopper's checkout.
        request.session["bkash_order_id"] = order.id
        request.session["bkash_payment_id"] = payment["paymentID"]

        return redirect(payment["bkashURL"])

    return render(request, "store/checkout.html", {"cart": cart})


@login_required
def bkash_callback_view(request):
    payment_id = request.GET.get("paymentID")
    status = request.GET.get("status")  # bKash sends: success | failure | cancel

    expected_order_id = request.session.get("bkash_order_id")
    expected_payment_id = request.session.get("bkash_payment_id")

    if not payment_id or payment_id != expected_payment_id or not expected_order_id:
        messages.error(request, "This payment session is invalid or has expired.")
        return redirect("store:cart-detail")

    order = get_object_or_404(Order, id=expected_order_id, user=request.user)

    if status != "success":
        order.status = "payment_failed"
        order.save(update_fields=["status"])
        messages.error(request, "Payment was not completed. Your cart items are still saved.")
        return redirect("store:cart-detail")

    try:
        id_token = bkash.grant_token()
        result = bkash.execute_payment(id_token, payment_id)
    except bkash.BkashError as exc:
        order.status = "payment_failed"
        order.save(update_fields=["status"])
        messages.error(request, f"Could not confirm bKash payment: {exc}")
        return redirect("store:cart-detail")

    if result.get("transactionStatus") != "Completed":
        order.status = "payment_failed"
        order.save(update_fields=["status"])
        messages.error(
            request,
            result.get("statusMessage") or "bKash could not complete this payment.",
        )
        return redirect("store:cart-detail")

    # Payment confirmed — commit the order: decrement stock, clear cart.
    order.status = "paid"
    order.bkash_trx_id = result.get("trxID", "")
    order.save(update_fields=["status", "bkash_trx_id"])

    for item in order.items.select_related("product"):
        item.product.stock = max(0, item.product.stock - item.quantity)
        item.product.save(update_fields=["stock"])

    Cart(request).clear()
    request.session.pop("bkash_order_id", None)
    request.session.pop("bkash_payment_id", None)

    # Notify any listeners (currently: email receipt) that this order is paid.
    order_paid.send(sender=Order, order=order)

    messages.success(request, "Payment successful — your order is confirmed.")
    return redirect("store:checkout-success", order_id=order.id)


@login_required
def checkout_success_view(request, order_id):
    order = get_object_or_404(
        Order.objects.prefetch_related("items__product"), id=order_id, user=request.user
    )
    return render(request, "store/checkout_success.html", {"order": order})