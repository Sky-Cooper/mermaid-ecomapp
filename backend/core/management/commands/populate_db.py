import random
import requests  # <--- Make sure to pip install requests
from io import BytesIO
from PIL import Image
from django.core.management.base import BaseCommand
from django.core.files.base import ContentFile
from django.db import transaction
from django.utils.text import slugify
from core.models import (
    Category,
    SubCategory,
    Product,
    ProductVariant,
    Attribute,
    AttributeValue,
    ColorChoices,
)


class Command(BaseCommand):
    help = "Populates the database with test data for Mermaid E-com"

    def generate_image(self, name, category_type="general"):
        """
        Tries to get a real image from Picsum.
        Falls back to a solid color placeholder if internet fails.
        """
        try:
            # 1. Try to get a real random image (600x600 pixels)
            # random=1 ensures we don't get the same cached image every time
            response = requests.get(
                f"https://picsum.photos/600/600?random={random.randint(1, 1000)}",
                timeout=5,
            )

            if response.status_code == 200:
                return ContentFile(response.content, name=f"{slugify(name)}.jpg")

        except (requests.ConnectionError, requests.Timeout):
            self.stdout.write(
                self.style.WARNING(
                    f"⚠ Internet issue. Using fallback image for: {name}"
                )
            )

        # 2. Fallback: Generate a solid color placeholder
        return self.generate_placeholder_image(name)

    def generate_placeholder_image(self, name):
        """Generates a solid color image with random pastel colors."""
        color = (
            random.randint(150, 255),  # R (Pastel range)
            random.randint(150, 255),  # G
            random.randint(150, 255),  # B
        )
        image = Image.new("RGB", (600, 600), color)
        img_io = BytesIO()
        image.save(img_io, format="JPEG", quality=85)
        return ContentFile(img_io.getvalue(), name=f"{name}_placeholder.jpg")

    @transaction.atomic
    def handle(self, *args, **kwargs):
        self.stdout.write("Deleting old data...")
        # Order matters to respect ForeignKeys
        ProductVariant.objects.all().delete()
        Product.objects.all().delete()
        SubCategory.objects.all().delete()
        Category.objects.all().delete()
        AttributeValue.objects.all().delete()
        Attribute.objects.all().delete()

        self.stdout.write("Creating Attributes...")

        # 1. Create Attributes
        attr_size = Attribute.objects.create(code="SIZE", name="Clothing Size")
        attr_shoe = Attribute.objects.create(code="SHOE_SIZE", name="Shoe Size")

        # 2. Create Values
        sizes = ["XS", "S", "M", "L", "XL"]
        shoe_sizes = ["36", "37", "38", "39", "40"]

        size_objs = {
            s: AttributeValue.objects.create(attribute=attr_size, value=s)
            for s in sizes
        }
        shoe_objs = {
            s: AttributeValue.objects.create(attribute=attr_shoe, value=s)
            for s in shoe_sizes
        }

        self.stdout.write("Creating Categories...")

        # 3. Create Categories & SubCategories
        cats_data = [
            {
                "title": "Clothing",
                "subs": ["Dresses", "Tops", "Swimwear"],
            },
            {
                "title": "Shoes",
                "subs": ["Heels", "Sandals", "Sneakers"],
            },
            {
                "title": "Accessories",
                "subs": ["Jewelry", "Bags"],
            },
        ]

        for cat_data in cats_data:
            self.stdout.write(f"  - Category: {cat_data['title']}")
            cat_img = self.generate_image(cat_data["title"])

            category = Category.objects.create(
                title=cat_data["title"],
                slug=slugify(cat_data["title"]),
                description=f"Best collection of {cat_data['title']}",
                image=cat_img,
            )

            for sub_title in cat_data["subs"]:
                sub_img = self.generate_image(sub_title)
                sub_cat = SubCategory.objects.create(
                    category=category,
                    title=sub_title,
                    slug=slugify(sub_title),
                    image=sub_img,
                )

                # 4. Create Products for this SubCategory
                self.create_products_for_subcategory(
                    sub_cat, cat_data["title"], size_objs, shoe_objs
                )

        self.stdout.write(
            self.style.SUCCESS("Successfully populated database with REAL test data!")
        )

    def create_products_for_subcategory(self, sub_cat, cat_type, size_objs, shoe_objs):
        """Helper to generate 3 products per subcategory"""
        adjectives = ["Elegant", "Summer", "Cozy", "Luxury", "Mermaid", "Ocean"]

        for i in range(3):
            title = f"{random.choice(adjectives)} {sub_cat.title} {i+1}"
            price = random.randint(20, 200) + 0.99

            # Get a real image for the product
            prod_img = self.generate_image(title)

            product = Product.objects.create(
                title=title,
                slug=slugify(title),
                sku=f"SKU-{sub_cat.slug[:3].upper()}-{random.randint(1000, 9999)}",
                sub_category=sub_cat,
                short_description="This is a fantastic product for the summer season.",
                description="Lorem ipsum dolor sit amet, consectetur adipiscing elit. High quality material.",
                price=price,
                in_stock=True,
                is_featured=random.choice([True, False]),
                image=prod_img,
                specifications={"Material": "Polyester", "Care": "Hand wash only"},
            )

            # 5. Create Variants
            colors = [c[0] for c in ColorChoices.choices if c[0] != "NONE"]
            selected_colors = random.sample(colors, 2)

            if cat_type == "Clothing":
                for size_key in ["S", "M", "L"]:
                    for col in selected_colors:
                        ProductVariant.objects.create(
                            product=product,
                            size=size_objs.get(size_key),
                            color=col,
                            quantity=random.randint(0, 20),
                            sku_modifier=f"-{size_key}-{col}",
                        )
            elif cat_type == "Shoes":
                for size_key in ["38", "39"]:
                    for col in selected_colors:
                        ProductVariant.objects.create(
                            product=product,
                            size=shoe_objs.get(size_key),
                            color=col,
                            quantity=random.randint(0, 15),
                            sku_modifier=f"-{size_key}-{col}",
                        )
            else:
                for col in selected_colors:
                    ProductVariant.objects.create(
                        product=product,
                        size=None,
                        color=col,
                        quantity=random.randint(5, 50),
                        sku_modifier=f"-{col}",
                    )
