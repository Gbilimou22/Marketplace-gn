import uuid

from django.db.models import QuerySet

from apps.accounts.models import User
from apps.shops.models import Shop


def shop_get_by_slug(*, slug: str) -> Shop | None:
    """
    Retrieves a shop by its unique slug.
    """
    if not slug:
        return None
    return Shop.objects.filter(slug=slug).select_related("owner__user").first()


def shop_get_by_id(*, id: uuid.UUID | str) -> Shop | None:
    """
    Retrieves a shop by its UUID primary key.
    """
    if not id:
        return None
    return Shop.objects.filter(id=id).select_related("owner__user").first()


def shops_active_list(*, city: str = "") -> QuerySet[Shop]:
    """
    Returns active shops for the public directory, optionally filtered by city.
    """
    qs = Shop.objects.filter(status=Shop.Status.ACTIVE).select_related("owner__user")
    if city:
        qs = qs.filter(city=city)
    return qs.order_by("name")


def shops_for_user(*, user: User) -> QuerySet[Shop]:
    """
    Returns all shops owned by the given user.
    """
    if not hasattr(user, "seller_profile"):
        return Shop.objects.none()
    return Shop.objects.filter(owner=user.seller_profile).order_by("-created_at")


def shops_pending_review_list() -> QuerySet[Shop]:
    """
    Returns shops waiting for admin approval.
    """
    return (
        Shop.objects.filter(status=Shop.Status.PENDING_REVIEW)
        .select_related("owner__user")
        .order_by("created_at")
    )
