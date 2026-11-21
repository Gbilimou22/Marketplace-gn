import pytest
from django.core.exceptions import ValidationError

from apps.accounts.models import SellerProfile, User
from apps.accounts.selectors import (
    seller_profile_get_for_user,
    seller_profiles_pending_list,
    seller_profiles_verified_list,
    user_get_by_email,
)
from apps.accounts.services import (
    seller_profile_request,
    seller_profile_suspend,
    seller_profile_verify,
    user_create,
)
from apps.core.utils import normalize_guinean_phone_number


@pytest.mark.django_db
class TestUserModel:
    def test_create_user_successful(self):
        user = user_create(
            email="DIALLO@example.com",
            password="SecurePassword123!",
            full_name="Mamadou Diallo",
            phone_number="620 12 34 56",
        )
        assert user.email == "diallo@example.com"
        assert user.full_name == "Mamadou Diallo"
        assert user.phone_number == "+224620123456"
        assert user.is_active is True
        assert user.is_staff is False
        assert user.is_superuser is False
        assert user.check_password("SecurePassword123!")
        assert user.is_seller is False

    def test_create_user_without_email_fails(self):
        with pytest.raises(ValueError, match="L'adresse email est obligatoire"):
            User.objects.create_user(email="", password="somepassword", full_name="Test")

    def test_create_superuser(self):
        admin = User.objects.create_superuser(
            email="admin@marketplace.gn",
            password="AdminPassword123!",
            full_name="Admin Principal",
        )
        assert admin.is_staff is True
        assert admin.is_superuser is True
        assert admin.email == "admin@marketplace.gn"

    def test_user_get_by_email_case_insensitive(self):
        user_create(
            email="bah@example.com",
            password="Password123!",
            full_name="Fatoumata Bah",
        )
        found = user_get_by_email(email="BAH@example.com")
        assert found is not None
        assert found.email == "bah@example.com"


class TestPhoneNormalization:
    @pytest.mark.parametrize(
        "raw_input, expected",
        [
            ("620123456", "+224620123456"),
            ("+224620123456", "+224620123456"),
            ("00224620123456", "+224620123456"),
            ("224620123456", "+224620123456"),
            ("620 12 34 56", "+224620123456"),
            ("620-12-34-56", "+224620123456"),
            ("664.11.22.33", "+224664112233"),
        ],
    )
    def test_valid_guinean_numbers(self, raw_input, expected):
        assert normalize_guinean_phone_number(raw_input) == expected

    @pytest.mark.parametrize(
        "invalid_input",
        [
            "123456789",       # does not start with 6
            "62012345",        # too short (8 digits)
            "6201234567",      # too long (10 digits)
            "+33612345678",    # French number
            "abcdefghi",       # letters
        ],
    )
    def test_invalid_guinean_numbers_raise_validation_error(self, invalid_input):
        with pytest.raises(ValidationError):
            normalize_guinean_phone_number(invalid_input)


@pytest.mark.django_db
class TestSellerProfileLifecycle:
    @pytest.fixture
    def buyer(self):
        return user_create(
            email="buyer@example.com",
            password="Password123!",
            full_name="Acheteur Test",
        )

    @pytest.fixture
    def admin_user(self):
        return User.objects.create_superuser(
            email="admin@marketplace.gn",
            password="AdminPassword123!",
            full_name="Admin Modérateur",
        )

    def test_seller_profile_request_starts_pending(self, buyer):
        profile = seller_profile_request(user=buyer)
        assert profile.status == SellerProfile.Status.PENDING
        assert profile.is_pending is True
        assert profile.is_verified is False
        assert buyer.is_seller is False
        assert seller_profile_get_for_user(user=buyer) == profile

    def test_seller_profile_verify_by_admin(self, buyer, admin_user):
        profile = seller_profile_request(user=buyer)
        verified_profile = seller_profile_verify(
            profile=profile,
            verified_by=admin_user,
            notes="Vérifié par appel WhatsApp vidéo. Boutique physique à Madina confirmée.",
        )
        assert verified_profile.status == SellerProfile.Status.VERIFIED
        assert verified_profile.is_verified is True
        assert verified_profile.verified_by == admin_user
        assert verified_profile.verified_at is not None
        assert "Madina" in verified_profile.internal_notes
        assert buyer.is_seller is True

    def test_seller_profile_verify_rejected_if_not_staff(self, buyer):
        profile = seller_profile_request(user=buyer)
        non_staff = user_create(
            email="other@example.com",
            password="Password123!",
            full_name="Autre Utilisateur",
        )
        with pytest.raises(ValidationError, match="Seul un administrateur"):
            seller_profile_verify(profile=profile, verified_by=non_staff)

    def test_seller_profile_suspend_flow(self, buyer, admin_user):
        profile = seller_profile_request(user=buyer)
        seller_profile_verify(profile=profile, verified_by=admin_user)

        suspended = seller_profile_suspend(
            profile=profile,
            suspended_by=admin_user,
            reason="Plaintes multiples pour articles non conformes.",
        )
        assert suspended.status == SellerProfile.Status.SUSPENDED
        assert suspended.is_suspended is True
        assert buyer.is_seller is False
        assert "Plaintes multiples" in suspended.internal_notes

    def test_seller_selectors(self, buyer, admin_user):
        profile = seller_profile_request(user=buyer)
        pending_list = list(seller_profiles_pending_list())
        assert profile in pending_list

        seller_profile_verify(profile=profile, verified_by=admin_user)
        assert profile not in list(seller_profiles_pending_list())
        assert profile in list(seller_profiles_verified_list())
