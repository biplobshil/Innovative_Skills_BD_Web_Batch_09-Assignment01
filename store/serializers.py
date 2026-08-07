from rest_framework import serializers

from .models import Category, Order, OrderItem, Product


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ["id", "name", "slug"]


class ProductSerializer(serializers.ModelSerializer):
    category_name = serializers.ReadOnlyField(source="category.name")

    class Meta:
        model = Product
        fields = [
            "id", "name", "slug", "description", "brand", "price",
            "stock", "image", "category", "category_name",
            "is_active", "created_at",
        ]


class ProductSearchResultSerializer(serializers.ModelSerializer):
    """Lightweight serializer used for the real-time search endpoint —
    keeps payloads small so results feel instant as the user types."""

    category_name = serializers.ReadOnlyField(source="category.name")

    class Meta:
        model = Product
        fields = ["id", "name", "slug", "brand", "price", "image", "category_name"]


class OrderItemSerializer(serializers.ModelSerializer):
    product_name = serializers.ReadOnlyField(source="product.name")

    class Meta:
        model = OrderItem
        fields = ["id", "product", "product_name", "quantity", "price", "subtotal"]
        read_only_fields = ["price"]


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True)
    total = serializers.ReadOnlyField()

    class Meta:
        model = Order
        fields = ["id", "user", "status", "created_at", "items", "total"]
        read_only_fields = ["user"]

    def create(self, validated_data):
        items_data = validated_data.pop("items")
        order = Order.objects.create(**validated_data)
        for item in items_data:
            product = item["product"]
            OrderItem.objects.create(
                order=order,
                product=product,
                quantity=item["quantity"],
                price=product.price,
            )
        return order
