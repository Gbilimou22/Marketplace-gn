from django.conf import settings
from django.contrib.auth.base_user import BaseUserManager
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.db import models
from django.utils import timezone

from apps.core.models import TimeStampedModel, UUIDModel


class UserManager(BaseUserManager):
    """
    Custom user manager where email is the unique identifier
    for authentication instead of usernames.
    """

    def create_user(self, email: str, password: str | None = None, **extra_fields):
        if not email:
            raise ValueError("L'adresse email est obligatoire.")

        email = self.normalize_email(email).lower()
        user = self.model(email=email, **extra_fields)
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()

        user.save(using=self._db)
        return user

    def create_superuser(self, email: str, password: str | None = None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Le superutilisateur doit avoir is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Le superutilisateur doit avoir is_superuser=True.")

        return self.create_user(email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin, UUIDModel, TimeStampedModel):
    """
    Custom User model for Marketplace Guinée.
    Primary key is a public, unguessable UUID.
    Email is the unique authentication login.
    """

    email = models.EmailField(
        unique=True,
        max_length=255,
        verbose_name="Adresse email",
        help_text="Identifiant de connexion unique.",
    )
    full_name = models.CharField(
        max_length=255,
        verbose_name="Nom complet",
        help_text="Prénom et nom de famille.",
    )
    phone_number = models.CharField(
        max_length=20,
        blank=True,
        verbose_name="Numéro de téléphone",
        help_text="Numéro au format guinéen (+224...).",
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name="Actif",
        help_text="Désactivez ce compte au lieu de le supprimer.",
    )
    is_staff = models.BooleanField(
        default=False,
        verbose_name="Accès administration",
        help_text="Indique si l'utilisateur peut se connecter au site d'administration.",
    )
    date_joined = models.DateTimeField(
        default=timezone.now,
        verbose_name="Date d'inscription",
    )

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["full_name"]

    class Meta:
        verbose_name = "Utilisateur"
        verbose_name_plural = "Utilisateurs"
        ordering = ["-date_joined"]

    def __str__(self) -> str:
        return f"{self.full_name} ({self.email})"

    @property
    def is_seller(self) -> bool:
        """Helper to quickly check if user is a verified seller."""
        return hasattr(self, "seller_profile") and self.seller_profile.is_verified


class SellerProfile(UUIDModel, TimeStampedModel):
    """
    Seller profile linked 1-to-1 with a User.
    Enforces strict manual review by administrator before publication.
    NO identity documents are stored (phone/video verification only).
    """

    class Status(models.TextChoices):
        PENDING = "pending", "En attente de vérification"
        VERIFIED = "verified", "Vérifié"
        SUSPENDED = "suspended", "Suspendu"

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="seller_profile",
        verbose_name="Compte utilisateur",
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True,
        verbose_name="Statut du vendeur",
    )
    verified_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Date de vérification",
    )
    verified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
        verbose_name="Vérifié par",
    )
    internal_notes = models.TextField(
        blank=True,
        verbose_name="Notes internes administrateur",
        help_text="Consigne d'appel ou vérification vidéo. Aucune pièce d'identité n'est stockée.",
    )

    class Meta:
        verbose_name = "Profil vendeur"
        verbose_name_plural = "Profils vendeurs"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"Vendeur {self.user.full_name} [{self.get_status_display()}]"

    @property
    def is_verified(self) -> bool:
        return self.status == self.Status.VERIFIED

    @property
    def is_pending(self) -> bool:
        return self.status == self.Status.PENDING

    @property
    def is_suspended(self) -> bool:
        return self.status == self.Status.SUSPENDED
