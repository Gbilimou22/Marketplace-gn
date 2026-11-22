import urllib.parse

from django.db import models
from django.utils.text import slugify

from apps.accounts.models import SellerProfile
from apps.core.models import TimeStampedModel, UUIDModel
from apps.shops.constants import GUINEAN_CITIES


class Shop(UUIDModel, TimeStampedModel):
    """
    Shop entity representing a seller's storefront on the marketplace.
    Must be reviewed and activated manually by an administrator before public listing.
    """

    class Status(models.TextChoices):
        DRAFT = "draft", "Brouillon"
        PENDING_REVIEW = "pending_review", "En attente de validation"
        ACTIVE = "active", "Active (en ligne)"
        SUSPENDED = "suspended", "Suspendue"

    owner = models.ForeignKey(
        SellerProfile,
        on_delete=models.CASCADE,
        related_name="shops",
        verbose_name="Propriétaire (vendeur)",
    )
    name = models.CharField(
        max_length=150,
        verbose_name="Nom de la boutique",
        help_text="Nom commercial visible par les acheteurs.",
    )
    slug = models.SlugField(
        max_length=160,
        unique=True,
        verbose_name="Identifiant URL (slug)",
        help_text="Identifiant unique pour l'adresse web de la boutique.",
    )
    description = models.TextField(
        blank=True,
        verbose_name="Description de la boutique",
        help_text="Présentation de vos articles, spécialités et horaires.",
    )
    city = models.CharField(
        max_length=100,
        choices=GUINEAN_CITIES,
        default="Conakry - Matoto",
        verbose_name="Ville / Commune",
    )
    address = models.CharField(
        max_length=255,
        blank=True,
        verbose_name="Adresse ou repère physique",
        help_text="Ex: Marché Madina, Carrefour Constantin, etc.",
    )
    whatsapp_number = models.CharField(
        max_length=20,
        verbose_name="Numéro WhatsApp de contact",
        help_text="Format guinéen (+224...).",
    )
    logo = models.ImageField(
        upload_to="shops/logos/",
        blank=True,
        null=True,
        verbose_name="Logo ou photo de la boutique",
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT,
        db_index=True,
        verbose_name="Statut de la boutique",
    )

    class Meta:
        verbose_name = "Boutique"
        verbose_name_plural = "Boutiques"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status", "city"]),
            models.Index(fields=["owner", "status"]),
        ]

    def __str__(self) -> str:
        return f"{self.name} ({self.get_status_display()})"

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.name) or "boutique"
            unique_slug = base_slug
            counter = 1
            while Shop.objects.filter(slug=unique_slug).exclude(pk=self.pk).exists():
                unique_slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = unique_slug
        super().save(*args, **kwargs)

    @property
    def is_active(self) -> bool:
        return self.status == self.Status.ACTIVE

    @property
    def is_pending_review(self) -> bool:
        return self.status == self.Status.PENDING_REVIEW

    @property
    def is_draft(self) -> bool:
        return self.status == self.Status.DRAFT

    @property
    def is_suspended(self) -> bool:
        return self.status == self.Status.SUSPENDED

    @property
    def whatsapp_url(self) -> str:
        """
        Generates direct pre-filled WhatsApp link (wa.me) for zero-cost merchant contact.
        """
        if not self.whatsapp_number:
            return ""
        clean_number = self.whatsapp_number.replace("+", "").replace(" ", "").replace("-", "")
        message = f"Bonjour {self.name}, je vous contacte depuis la place de marché."
        encoded_message = urllib.parse.quote(message)
        return f"https://wa.me/{clean_number}?text={encoded_message}"
