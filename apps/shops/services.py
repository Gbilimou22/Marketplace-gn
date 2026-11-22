from django.core.exceptions import PermissionDenied, ValidationError
from django.utils.text import slugify

from apps.accounts.models import SellerProfile, User
from apps.accounts.services import seller_profile_verify
from apps.core.utils import normalize_guinean_phone_number
from apps.shops.models import Shop


def shop_create(
    *,
    owner: SellerProfile,
    name: str,
    city: str,
    whatsapp_number: str,
    address: str = "",
    description: str = "",
    logo=None,
) -> Shop:
    """
    Creates a new shop in DRAFT status for a seller.
    """
    if not name.strip():
        raise ValidationError("Le nom de la boutique est obligatoire.")

    normalized_whatsapp = normalize_guinean_phone_number(whatsapp_number)

    shop = Shop(
        owner=owner,
        name=name.strip(),
        city=city.strip(),
        address=address.strip(),
        description=description.strip(),
        whatsapp_number=normalized_whatsapp,
        logo=logo,
        status=Shop.Status.DRAFT,
    )
    shop.save()
    return shop


def shop_update(
    *,
    shop: Shop,
    user: User,
    **fields,
) -> Shop:
    """
    Updates shop information with strict ownership check.
    """
    if shop.owner.user != user and not user.is_staff:
        raise PermissionDenied("Vous n'êtes pas autorisé à modifier cette boutique.")

    allowed_fields = {"name", "city", "address", "description", "whatsapp_number", "logo"}
    updated_fields = []

    for field, value in fields.items():
        if field not in allowed_fields:
            continue
        if field == "whatsapp_number" and value:
            value = normalize_guinean_phone_number(value)
        if field == "name" and value and value.strip() != shop.name:
            shop.name = value.strip()
            # Regenerate slug if name changed
            base_slug = slugify(shop.name) or "boutique"
            unique_slug = base_slug
            counter = 1
            while Shop.objects.filter(slug=unique_slug).exclude(pk=shop.pk).exists():
                unique_slug = f"{base_slug}-{counter}"
                counter += 1
            shop.slug = unique_slug
            updated_fields.extend(["name", "slug"])
            continue

        setattr(shop, field, value)
        updated_fields.append(field)

    if updated_fields:
        updated_fields.append("updated_at")
        shop.save(update_fields=list(set(updated_fields)))

    return shop


def shop_submit_for_review(
    *,
    shop: Shop,
    user: User,
) -> Shop:
    """
    Submits a draft shop for administrative review.
    """
    if shop.owner.user != user and not user.is_staff:
        raise PermissionDenied("Vous n'êtes pas le propriétaire de cette boutique.")

    if shop.status not in [Shop.Status.DRAFT, Shop.Status.SUSPENDED]:
        raise ValidationError("Seule une boutique en brouillon ou suspendue peut être soumise à validation.")

    if not shop.name or not shop.city or not shop.whatsapp_number:
        raise ValidationError("Le nom, la ville et le numéro WhatsApp sont obligatoires pour soumettre la boutique.")

    shop.status = Shop.Status.PENDING_REVIEW
    shop.save(update_fields=["status", "updated_at"])
    return shop


def shop_activate(
    *,
    shop: Shop,
    admin_user: User,
    notes: str = "",
) -> Shop:
    """
    Approves and activates a shop for public display (Admin action).
    Also marks the seller profile as verified if it is still pending.
    """
    if not admin_user.is_staff:
        raise PermissionDenied("Seul un administrateur peut activer une boutique.")

    shop.status = Shop.Status.ACTIVE
    shop.save(update_fields=["status", "updated_at"])

    # Ensure seller profile is also verified
    if shop.owner.status == SellerProfile.Status.PENDING:
        seller_profile_verify(
            profile=shop.owner,
            verified_by=admin_user,
            notes=notes or f"Vérification automatique lors de l'activation de la boutique {shop.name}.",
        )

    return shop


def shop_suspend(
    *,
    shop: Shop,
    admin_user: User,
    reason: str,
) -> Shop:
    """
    Suspends a shop (Admin action).
    """
    if not admin_user.is_staff:
        raise PermissionDenied("Seul un administrateur peut suspendre une boutique.")

    if not reason.strip():
        raise ValidationError("Le motif de suspension de la boutique est obligatoire.")

    shop.status = Shop.Status.SUSPENDED
    shop.save(update_fields=["status", "updated_at"])
    return shop
