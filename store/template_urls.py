from django.urls import path

from . import views

app_name = "store"

urlpatterns = [
    path("", views.product_list_view, name="product-list"),
    path("search/", views.product_search_fragment, name="product-search-fragment"),

    # Categories (read-only — managed via Django admin)
    path("categories/", views.category_list_view, name="category-list"),

    # Cart
    path("cart/", views.cart_view, name="cart-detail"),
    path("cart/add/<int:product_id>/", views.cart_add_view, name="cart-add"),
    path("cart/update/<int:product_id>/", views.cart_update_view, name="cart-update"),
    path("cart/remove/<int:product_id>/", views.cart_remove_view, name="cart-remove"),

    # Checkout (requires login — see @login_required in views.py)
    path("checkout/", views.checkout_view, name="checkout"),
    path("checkout/bkash/callback/", views.bkash_callback_view, name="bkash-callback"),
    path("checkout/<int:order_id>/success/", views.checkout_success_view, name="checkout-success"),

    path("<slug:slug>/", views.product_detail_view, name="product-detail"),
]
