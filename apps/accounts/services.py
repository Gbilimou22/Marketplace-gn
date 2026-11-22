from django.core.exceptions import PermissionDenied, ValidationError
from django.utils import timezone

from apps.accounts.models import SellerProfile, User
from apps.core.utils import normalize_guinean_phone_number


def user_create(
    *,
    email: str,
    password: str,
    full_name: str,
    phone_number: str = "",
    is_staff: bool = False,
    is_superuser: bool = False,
) -> User:
    """
    Creates a new user with normalized email and Guinean phone number.
    """
    normalized_phone = ""
    if phone_number:
        normalized_phone = normalize_guinean_phone_number(phone_number)

    user = User.objects.create_user(
        email=email,
        password=password,
        full_name=full_name.strip(),
        phone_number=normalized_phone,
        is_staff=is_staff,
        is_superuser=is_superuser,
    )
    return user


def seller_profile_request(*, user: User) -> SellerProfile:
    """
    Registers a request to become a seller.
    Status starts in PENDING for manual admin validation.
    Administrators/staff cannot become sellers (strict role separation).
    """
    if user.is_staff or user.is_superuser:
        raise PermissionDenied("Les comptes administrateurs sont réservés à la modération et ne peuvent pas créer de profil vendeur.")

    if hasattr(user, "seller_profile"):
        profile = user.seller_profile
        if profile.status == SellerProfile.Status.SUSPENDED:
            raise ValidationError("Ce profil vendeur a été suspendu par l'administration.")
        return profile

    profile = SellerProfile.objects.create(
        user=user,
        status=SellerProfile.Status.PENDING,
    )
    return profile


def seller_profile_verify(
    *,
    profile: SellerProfile,
    verified_by: User,
    notes: str = "",
) -> SellerProfile:
    """
    Validates a seller profile manually (admin action after phone/video check).
    """
    if not verified_by.is_staff:
        raise ValidationError("Seul un administrateur peut valider un profil vendeur.")

    profile.status = SellerProfile.Status.VERIFIED
    profile.verified_at = timezone.now()
    profile.verified_by = verified_by
    if notes:
        existing = profile.internal_notes
        timestamp = timezone.now().strftime("%Y-%m-%d %H:%M")
        profile.internal_notes = (
            f"{existing}\n[{timestamp} - {verified_by.full_name}]: {notes}".strip()
        )
    profile.save(update_fields=["status", "verified_at", "verified_by", "internal_notes", "updated_at"])
    return profile


def seller_profile_suspend(
    *,
    profile: SellerProfile,
    suspended_by: User,
    reason: str,
) -> SellerProfile:
    """
    Suspends a seller profile.
    """
    if not suspended_by.is_staff:
        raise ValidationError("Seul un administrateur peut suspendre un profil vendeur.")
    if not reason.strip():
        raise ValidationError("Le motif de la suspension est obligatoire.")

    profile.status = SellerProfile.Status.SUSPENDED
    timestamp = timezone.now().strftime("%Y-%m-%d %H:%M")
    existing = profile.internal_notes
    profile.internal_notes = (
        f"{existing}\n[{timestamp} - SUSPENDU par {suspended_by.full_name}]: {reason}".strip()
    )
    profile.save(update_fields=["status", "internal_notes", "updated_at"])
    return profile
