from django.db.models import QuerySet

from apps.accounts.models import SellerProfile, User


def user_get_by_email(*, email: str) -> User | None:
    """
    Finds a user by normalized email.
    """
    if not email:
        return None
    return User.objects.filter(email__iexact=email.strip()).first()


def seller_profile_get_for_user(*, user: User) -> SellerProfile | None:
    """
    Retrieves the seller profile for a specific user if it exists.
    """
    return SellerProfile.objects.filter(user=user).select_related("user").first()


def seller_profiles_pending_list() -> QuerySet[SellerProfile]:
    """
    Returns the list of seller profiles awaiting admin verification.
    """
    return (
        SellerProfile.objects.filter(status=SellerProfile.Status.PENDING)
        .select_related("user")
        .order_by("created_at")
    )


def seller_profiles_verified_list() -> QuerySet[SellerProfile]:
    """
    Returns the list of active verified sellers.
    """
    return (
        SellerProfile.objects.filter(status=SellerProfile.Status.VERIFIED)
        .select_related("user")
        .order_by("-verified_at")
    )
