import pytest
from django.core.exceptions import PermissionDenied, ValidationError
from django.urls import reverse

from apps.accounts.models import SellerProfile, User
from apps.accounts.services import seller_profile_request, user_create
from apps.shops.models import Shop
from apps.shops.selectors import (
    shop_get_by_id,
    shop_get_by_slug,
    shops_active_list,
    shops_for_user,
    shops_pending_review_list,
)
from apps.shops.services import (
    shop_activate,
    shop_create,
    shop_submit_for_review,
    shop_suspend,
    shop_update,
)


@pytest.fixture
def seller_user(db):
    return user_create(
        email="amadou@boutique.gn",
        password="Password123!",
        full_name="Amadou Barry",
        phone_number="621 11 22 33",
    )


@pytest.fixture
def other_seller(db):
    return user_create(
        email="moussa@boutique.gn",
        password="Password123!",
        full_name="Moussa Camara",
        phone_number="622 33 44 55",
    )


@pytest.fixture
def admin_user(db):
    return User.objects.create_superuser(
        email="admin@marketplace.gn",
        password="AdminPassword123!",
        full_name="Admin Principal",
    )


@pytest.fixture
def seller_profile(seller_user):
    return seller_profile_request(user=seller_user)


@pytest.fixture
def shop(seller_profile):
    return shop_create(
        owner=seller_profile,
        name="Barry Électronique Conakry",
        city="Conakry - Matoto",
        whatsapp_number="621 11 22 33",
        address="Marché Matoto, Kiosque 12",
        description="Vente de téléphones et accessoires neufs et reconditionnés.",
    )


@pytest.mark.django_db
class TestShopCreationAndBasics:
    def test_shop_create_defaults_and_normalization(self, shop):
        assert shop.name == "Barry Électronique Conakry"
        assert shop.slug == "barry-electronique-conakry"
        assert shop.whatsapp_number == "+224621112233"
        assert shop.status == Shop.Status.DRAFT
        assert shop.is_draft is True
        assert shop.is_active is False
        assert "https://wa.me/224621112233" in shop.whatsapp_url

    def test_slug_collision_resolution(self, seller_profile):
        shop1 = shop_create(
            owner=seller_profile,
            name="Mode Féminine",
            city="Conakry - Kaloum",
            whatsapp_number="620 00 00 01",
        )
        shop2 = shop_create(
            owner=seller_profile,
            name="Mode Féminine",
            city="Kindia",
            whatsapp_number="620 00 00 02",
        )
        assert shop1.slug == "mode-feminine"
        assert shop2.slug == "mode-feminine-1"

    def test_admin_cannot_request_seller_profile_nor_create_shop(self, admin_user):
        with pytest.raises(PermissionDenied, match="Les comptes administrateurs"):
            seller_profile_request(user=admin_user)

    def test_admin_create_view_redirects_away(self, client, admin_user):
        client.force_login(admin_user)
        response = client.get(reverse("shops:create"))
        assert response.status_code == 302
        assert response.url == reverse("shops:seller_dashboard")


@pytest.mark.django_db
class TestShopLifecycleAndPermissions:
    def test_shop_update_by_owner_succeeds(self, shop, seller_user):
        updated = shop_update(
            shop=shop,
            user=seller_user,
            description="Nouvelle description mise à jour.",
            address="Nouveau repère",
        )
        assert updated.description == "Nouvelle description mise à jour."
        assert updated.address == "Nouveau repère"

    def test_shop_update_by_other_user_denied(self, shop, other_seller):
        with pytest.raises(PermissionDenied):
            shop_update(
                shop=shop,
                user=other_seller,
                description="Tentative malveillante",
            )

    def test_submit_for_review_flow(self, shop, seller_user):
        submitted = shop_submit_for_review(shop=shop, user=seller_user)
        assert submitted.status == Shop.Status.PENDING_REVIEW
        assert submitted.is_pending_review is True
        assert submitted in list(shops_pending_review_list())

    def test_shop_activation_by_admin(self, shop, seller_user, admin_user):
        shop_submit_for_review(shop=shop, user=seller_user)
        activated = shop_activate(shop=shop, admin_user=admin_user, notes="Boutique vérifiée physiquement.")

        assert activated.status == Shop.Status.ACTIVE
        assert activated.is_active is True
        # Verify that seller profile was automatically verified
        assert shop.owner.status == SellerProfile.Status.VERIFIED
        assert seller_user.is_seller is True

    def test_shop_activation_denied_for_non_admin(self, shop, seller_user, other_seller):
        shop_submit_for_review(shop=shop, user=seller_user)
        with pytest.raises(PermissionDenied):
            shop_activate(shop=shop, admin_user=other_seller)

    def test_shop_suspend_flow(self, shop, admin_user, seller_user):
        shop_submit_for_review(shop=shop, user=seller_user)
        shop_activate(shop=shop, admin_user=admin_user)

        suspended = shop_suspend(shop=shop, admin_user=admin_user, reason="Signalements vérifiés pour contrefaçon.")
        assert suspended.status == Shop.Status.SUSPENDED
        assert suspended.is_suspended is True

    def test_shop_suspend_without_reason_fails(self, shop, admin_user):
        with pytest.raises(ValidationError, match="motif de suspension"):
            shop_suspend(shop=shop, admin_user=admin_user, reason="")


@pytest.mark.django_db
class TestShopSelectors:
    def test_shops_active_list_filtering(self, seller_profile, admin_user):
        shop1 = shop_create(owner=seller_profile, name="Boutique Conakry", city="Conakry - Matam", whatsapp_number="620111111")
        shop_create(owner=seller_profile, name="Boutique Kindia", city="Kindia", whatsapp_number="620222222")

        # Before activation, neither appears in active list
        assert list(shops_active_list()) == []

        # Activate shop 1
        shop_activate(shop=shop1, admin_user=admin_user)
        assert list(shops_active_list()) == [shop1]

        # Filter by city
        assert list(shops_active_list(city="Kindia")) == []
        assert list(shops_active_list(city="Conakry - Matam")) == [shop1]

    def test_shops_for_user(self, seller_user, seller_profile, shop):
        user_shops = list(shops_for_user(user=seller_user))
        assert shop in user_shops

    def test_shop_get_by_slug_and_id(self, shop):
        assert shop_get_by_slug(slug=shop.slug) == shop
        assert shop_get_by_id(id=shop.id) == shop


@pytest.mark.django_db
class TestShopViewsAndPermissions:
    def test_public_cannot_view_draft_shop(self, client, shop):
        url = reverse("shops:detail", kwargs={"slug": shop.slug})
        response = client.get(url)
        assert response.status_code == 404

    def test_owner_can_view_draft_shop(self, client, shop, seller_user):
        client.force_login(seller_user)
        url = reverse("shops:detail", kwargs={"slug": shop.slug})
        response = client.get(url)
        assert response.status_code == 200
        assert shop.name.encode() in response.content

    def test_public_can_view_active_shop(self, client, shop, admin_user):
        shop_activate(shop=shop, admin_user=admin_user)
        url = reverse("shops:detail", kwargs={"slug": shop.slug})
        response = client.get(url)
        assert response.status_code == 200
        assert shop.name.encode() in response.content
        assert b"https://wa.me/224621112233" in response.content
