import random

from django.core.management.base import BaseCommand

from store.models import Category, Product

CATEGORIES = ["Electronics", "Clothing", "Home & Kitchen", "Books", "Sports"]

# Prices are in Bangladeshi Taka (৳), reflecting realistic BD retail pricing.
PRODUCTS = [
    ("Wireless Bluetooth Headphones", "Electronics", "Walton", 1850.00),
    ("Noise Cancelling Earbuds", "Electronics", "Walton", 2450.00),
    ("4K Ultra HD Smart TV 55\"", "Electronics", "Vision", 52990.00),
    ("Mechanical Gaming Keyboard", "Electronics", "A4Tech", 2890.00),
    ("Wireless Mouse", "Electronics", "A4Tech", 690.00),
    ("Portable Power Bank 20000mAh", "Electronics", "Symphony", 1490.00),
    ("Men's Running Shoes", "Sports", "Bata", 2290.00),
    ("Women's Yoga Leggings", "Clothing", "Aarong", 890.00),
    ("Men's Cotton Panjabi", "Clothing", "Aarong", 1650.00),
    ("Women's Cotton Saree", "Clothing", "Aarong", 2450.00),
    ("Stainless Steel Water Bottle", "Sports", "RFL", 450.00),
    ("Yoga Mat Non-Slip", "Sports", "RFL", 990.00),
    ("Non-Stick Frying Pan Set", "Home & Kitchen", "Miyako", 1590.00),
    ("Electric Kettle 1.7L", "Home & Kitchen", "Miyako", 1290.00),
    ("Memory Foam Pillow", "Home & Kitchen", "Vision", 990.00),
    ("Robot Vacuum Cleaner", "Home & Kitchen", "Walton", 12990.00),
    ("Bangla Sahitya Songroho", "Books", "Bangla Academy", 450.00),
    ("Mystery at Midnight (Novel)", "Books", "Ananya Prokashani", 320.00),
    ("Recipe Book: 100 Bangladeshi Meals", "Books", "Sheba Prokashoni", 380.00),
    ("Kids' Adventure Storybook", "Books", "Sheba Prokashoni", 250.00),
    ("Smartwatch Series 5", "Electronics", "Walton", 3990.00),
    ("Fitness Tracker Band", "Electronics", "Symphony", 1290.00),
    ("Men's Leather Wallet", "Clothing", "Apex", 890.00),
    ("Women's Running Sneakers", "Sports", "Bata", 2190.00),
    ("Bluetooth Portable Speaker", "Electronics", "Walton", 1990.00),
    ("Men's Formal Shirt", "Clothing", "Yellow", 1450.00),
    ("Rice Cooker 1.8L", "Home & Kitchen", "Miyako", 2190.00),
    ("Table Fan 16 inch", "Home & Kitchen", "Vision", 2490.00),
    ("Men's Sandals", "Clothing", "Apex", 990.00),
    ("Cricket Bat (Kashmir Willow)", "Sports", "SS", 1890.00),
]


class Command(BaseCommand):
    help = "Seed the database with Bangladesh-localized sample categories and products (prices in Tk)."

    def handle(self, *args, **options):
        cat_objs = {}
        for name in CATEGORIES:
            cat, _ = Category.objects.get_or_create(name=name)
            cat_objs[name] = cat

        created = 0
        for name, cat_name, brand, price in PRODUCTS:
            _, was_created = Product.objects.get_or_create(
                name=name,
                defaults={
                    "category": cat_objs[cat_name],
                    "brand": brand,
                    "price": price,
                    "stock": random.randint(0, 50),
                    "description": f"{name} by {brand}. High quality {cat_name.lower()} product.",
                },
            )
            if was_created:
                created += 1

        self.stdout.write(self.style.SUCCESS(
            f"Seeded {created} new products across {len(CATEGORIES)} categories (prices in Tk)."
        ))