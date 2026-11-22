import io

import pytest
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from PIL import Image

from apps.accounts.services import seller_profile_request, user_create
from apps.catalog.image_processing import process_product_image
from apps.catalog.models import Product
from apps.catalog.selectors import (
    category_list_tree,
    products_published_list,
)
from apps.catalog.services import (
    category_create,
    product_create,
    product_hide,
    product_image_add,
    product_image_delete,
    product_publish,
)
from apps.shops.services import shop_activate, shop_create


def create_dummy_image_file(name="test.jpg", format="JPEG", size=(800, 600), color=(255, 0, 0)):
    """Helper creating an in-memory valid image file."""
    file_obj = io.BytesIO()
    image = Image.new("RGB", size, color=color)
    image.save(file_obj, format=format)
    file_obj.seek(0)
    return SimpleUploadedFile(name, file_obj.read(), content_type=f"image/{format.lower()}")


@pytest.fixture
def seller_user(db):
    return user_create(
        email="vendeur@mode.gn",
        password="Password123!",
        full_name="Kadiatou Camara",
        phone_number="620 11 22 33",
    )


@pytest.fixture
def other_seller(db):
    return user_create(
        email="autre@mode.gn",
        password="Password123!",
        full_name="Sekou Traore",
        phone_number="622 99 88 77",
    )


@pytest.fixture
def admin_user(db):
    from apps.accounts.models import User
    return User.objects.create_superuser(
        email="admin@marketplace.gn",
        password="AdminPassword123!",
        full_name="Admin Principal",
    )


@pytest.fixture
def shop(seller_user, admin_user):
    profile = seller_profile_request(user=seller_user)
    shop = shop_create(
        owner=profile,
        name="Kadiatou Confection",
        city="Conakry - Dixinn",
        whatsapp_number="620 11 22 33",
    )
    shop_activate(shop=shop, admin_user=admin_user)
    return shop


@pytest.fixture
def category_mode(db):
    mode = category_create(name="Mode & Vêtements", slug="mode")
    category_create(name="Robes & Bazin", parent=mode, slug="robes-bazin")
    return mode


@pytest.mark.django_db
class TestCategoryTree:
    def test_category_hierarchy(self, category_mode):
        tree = list(category_list_tree())
        assert len(tree) >= 1
        parent = tree[0]
        assert parent.name == "Mode & Vêtements"
        children = list(parent.children.all())
        assert len(children) == 1
        assert children[0].name == "Robes & Bazin"


@pytest.mark.django_db
class TestProductBasicsAndValidation:
    def test_product_create_and_slug(self, shop, seller_user, category_mode):
        subcat = category_mode.children.first()
        prod = product_create(
            shop=shop,
            user=seller_user,
            category=subcat,
            title="Robe Bazin Riche Riche Brodé",
            description="Superbe bazin getzner brodé fait main à Conakry.",
            price_gnf=450000,
            condition=Product.Condition.NEW,
            brand="Bazin VIP",
            stock=5,
        )
        assert prod.title == "Robe Bazin Riche Riche Brodé"
        assert prod.price_gnf == 450000
        assert prod.slug == "robe-bazin-riche-riche-brode"
        assert prod.status == Product.Status.DRAFT
        assert prod.is_published is False
        assert "450" in prod.whatsapp_order_url

    def test_product_price_must_be_strictly_positive(self, shop, seller_user, category_mode):
        with pytest.raises(ValidationError, match="strictement supérieur à 0 GNF"):
            product_create(
                shop=shop,
                user=seller_user,
                category=category_mode,
                title="Article Gratuit Faux",
                description="Test",
                price_gnf=0,
            )

    def test_product_ownership_check(self, shop, other_seller, category_mode):
        with pytest.raises(PermissionDenied):
            product_create(
                shop=shop,
                user=other_seller,
                category=category_mode,
                title="Article frauduleux",
                description="Test",
                price_gnf=100000,
            )


@pytest.mark.django_db
class TestImageOptimizationPipeline:
    def test_process_valid_image_to_webp(self):
        uploaded = create_dummy_image_file(name="photo.jpg", size=(2000, 1500))
        processed = process_product_image(uploaded, max_dimension=1200)

        assert processed.name.endswith(".webp")
        # Verify content with Pillow
        out_img = Image.open(processed)
        assert out_img.format == "WEBP"
        # Verify dimension was constrained to max_dimension
        assert max(out_img.size) <= 1200

    def test_reject_corrupt_or_non_image_file(self):
        fake_file = SimpleUploadedFile("script.jpg", b"<?php echo 'malicious'; ?>", content_type="image/jpeg")
        with pytest.raises(ValidationError, match="pas une image valide"):
            process_product_image(fake_file)

    def test_max_8_images_per_product_limit(self, shop, seller_user, category_mode):
        prod = product_create(
            shop=shop,
            user=seller_user,
            category=category_mode,
            title="Téléphone Test",
            description="Test",
            price_gnf=1000000,
        )

        for i in range(8):
            img_file = create_dummy_image_file(name=f"img_{i}.jpg")
            product_image_add(product=prod, user=seller_user, image_file=img_file)

        assert prod.images.count() == 8

        # 9th image must be rejected
        ninth_file = create_dummy_image_file(name="img_9.jpg")
        with pytest.raises(ValidationError, match="plus de 8 photos"):
            product_image_add(product=prod, user=seller_user, image_file=ninth_file)

    def test_first_image_becomes_cover(self, shop, seller_user, category_mode):
        prod = product_create(
            shop=shop,
            user=seller_user,
            category=category_mode,
            title="Article Cover Test",
            description="Test",
            price_gnf=50000,
        )
        img1 = product_image_add(product=prod, user=seller_user, image_file=create_dummy_image_file("img1.jpg"))
        assert img1.is_cover is True
        assert prod.cover_image == img1

        # Delete cover reassigns to remaining
        img2 = product_image_add(product=prod, user=seller_user, image_file=create_dummy_image_file("img2.jpg"))
        product_image_delete(image=img1, user=seller_user)
        img2.refresh_from_db()
        assert img2.is_cover is True


@pytest.mark.django_db
class TestProductPublishAndSearch:
    def test_cannot_publish_without_images(self, shop, seller_user, category_mode):
        prod = product_create(
            shop=shop,
            user=seller_user,
            category=category_mode,
            title="Sans photo",
            description="Test",
            price_gnf=100000,
        )
        with pytest.raises(ValidationError, match="au moins une photo"):
            product_publish(product=prod, user=seller_user)

    def test_publish_and_search_vector(self, shop, seller_user, category_mode):
        prod = product_create(
            shop=shop,
            user=seller_user,
            category=category_mode,
            title="Samsung Galaxy S22 Ultra 256GB",
            description="Téléphone haut de gamme écran AMOLED.",
            price_gnf=6500000,
            brand="Samsung",
        )
        product_image_add(product=prod, user=seller_user, image_file=create_dummy_image_file("samsung.jpg"))
        published_prod = product_publish(product=prod, user=seller_user)
        assert published_prod.is_published is True

        # Test search query
        results = list(products_published_list(query="Galaxy"))
        assert prod in results

        # Test price filter
        assert prod in list(products_published_list(min_price=6000000, max_price=7000000))
        assert prod not in list(products_published_list(max_price=5000000))

        # Test hide
        product_hide(product=prod, user=seller_user)
        assert prod not in list(products_published_list(query="Galaxy"))


@pytest.mark.django_db
class TestCatalogViews:
    def test_public_product_list(self, client, shop, seller_user, category_mode):
        prod = product_create(
            shop=shop,
            user=seller_user,
            category=category_mode,
            title="Robe Africaine Wax",
            description="Coton 100% garanti.",
            price_gnf=250000,
        )
        product_image_add(product=prod, user=seller_user, image_file=create_dummy_image_file())
        product_publish(product=prod, user=seller_user)

        response = client.get(reverse("catalog:list"))
        assert response.status_code == 200
        assert b"Robe Africaine Wax" in response.content

    def test_public_cannot_view_draft_product(self, client, shop, seller_user, category_mode):
        prod = product_create(
            shop=shop,
            user=seller_user,
            category=category_mode,
            title="Article Secret",
            description="Pas encore prêt.",
            price_gnf=100000,
        )
        url = reverse("catalog:detail", kwargs={"slug": prod.slug})
        response = client.get(url)
        assert response.status_code == 404

    def test_owner_can_view_draft_product(self, client, shop, seller_user, category_mode):
        prod = product_create(
            shop=shop,
            user=seller_user,
            category=category_mode,
            title="Article En Préparation",
            description="Visible par le vendeur.",
            price_gnf=100000,
        )
        client.force_login(seller_user)
        url = reverse("catalog:detail", kwargs={"slug": prod.slug})
        response = client.get(url)
        assert response.status_code == 200
        assert b"Article En" in response.content
