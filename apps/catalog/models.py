import urllib.parse

from django.core.validators import MinValueValidator
from django.db import models
from django.utils.text import slugify

from apps.core.models import TimeStampedModel, UUIDModel
from apps.shops.models import Shop


class Category(UUIDModel, TimeStampedModel):
    """
    Product category supporting hierarchical parent-child relationships
    (e.g., Mode -> Vêtements Homme, Électronique -> Smartphones).
    """

    name = models.CharField(max_length=100, verbose_name="Nom de la catégorie")
    slug = models.SlugField(max_length=120, unique=True, verbose_name="Slug URL")
    parent = models.ForeignKey(
        "self",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="children",
        verbose_name="Catégorie parente",
    )
    icon = models.CharField(
        max_length=50,
        blank=True,
        default="",
        verbose_name="Icône ou emoji",
        help_text="Ex: 👕, 📱, 👟",
    )
    order = models.PositiveSmallIntegerField(default=0, verbose_name="Ordre d'affichage")

    class Meta:
        verbose_name = "Catégorie"
        verbose_name_plural = "Catégories"
        ordering = ["order", "name"]

    def __str__(self) -> str:
        if self.parent:
            return f"{self.parent.name} > {self.name}"
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class Product(UUIDModel, TimeStampedModel):
    """
    Product listing sold by a specific shop.
    Prices are strictly in GNF (integer amounts without decimals).
    """

    class Condition(models.TextChoices):
        NEW = "new", "Neuf"
        USED = "used", "Occasion"
        REFURBISHED = "refurbished", "Reconditionné"

    class Status(models.TextChoices):
        DRAFT = "draft", "Brouillon"
        PUBLISHED = "published", "Publié"
        HIDDEN = "hidden", "Masqué"

    shop = models.ForeignKey(
        Shop,
        on_delete=models.CASCADE,
        related_name="products",
        verbose_name="Boutique",
    )
    category = models.ForeignKey(
        Category,
        on_delete=models.PROTECT,
        related_name="products",
        verbose_name="Catégorie",
    )
    title = models.CharField(
        max_length=200,
        verbose_name="Titre de l'article",
    )
    slug = models.SlugField(
        max_length=220,
        unique=True,
        verbose_name="Slug URL",
    )
    description = models.TextField(
        verbose_name="Description détaillée",
    )
    price_gnf = models.PositiveBigIntegerField(
        validators=[MinValueValidator(1)],
        verbose_name="Prix en GNF (Franc Guinéen)",
        help_text="Montant entier strict sans centimes.",
    )
    condition = models.CharField(
        max_length=20,
        choices=Condition.choices,
        default=Condition.NEW,
        verbose_name="État de l'article",
    )
    brand = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Marque déclarée",
        help_text="Ex: Samsung, Apple, Zara, etc.",
    )
    stock = models.PositiveIntegerField(
        default=1,
        verbose_name="Quantité en stock",
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT,
        db_index=True,
        verbose_name="Statut de publication",
    )

    class Meta:
        verbose_name = "Article"
        verbose_name_plural = "Articles"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["shop", "status"]),
            models.Index(fields=["status", "-created_at"]),
            models.Index(fields=["category", "status"]),
        ]

    def __str__(self) -> str:
        return f"{self.title} - {self.price_gnf:,} GNF ({self.shop.name})"

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.title) or "article"
            unique_slug = base_slug
            counter = 1
            while Product.objects.filter(slug=unique_slug).exclude(pk=self.pk).exists():
                unique_slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = unique_slug
        super().save(*args, **kwargs)

    @property
    def is_published(self) -> bool:
        return self.status == self.Status.PUBLISHED

    @property
    def is_in_stock(self) -> bool:
        return self.stock > 0

    @property
    def cover_image(self):
        """Returns the cover image or first image if available."""
        cover = self.images.filter(is_cover=True).first()
        if not cover:
            cover = self.images.first()
        return cover

    @property
    def whatsapp_order_url(self) -> str:
        """
        Generates direct WhatsApp link for this product.
        Pre-fills product name, price in GNF and shop context.
        """
        if not self.shop.whatsapp_number:
            return ""
        clean_number = self.shop.whatsapp_number.replace("+", "").replace(" ", "").replace("-", "")
        message = (
            f"Bonjour {self.shop.name}, je suis intéressé par votre article '{self.title}' "
            f"au prix de {self.price_gnf:,} GNF vu sur la place de marché."
        )
        encoded_message = urllib.parse.quote(message)
        return f"https://wa.me/{clean_number}?text={encoded_message}"


class ProductImage(UUIDModel, TimeStampedModel):
    """
    Image associated with a Product.
    Maximum 8 images per product.
    Always validated, stripped of EXIF and compressed to WebP.
    """

    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="images",
        verbose_name="Article",
    )
    image = models.ImageField(
        upload_to="products/%Y/%m/",
        verbose_name="Fichier image (WebP)",
    )
    position = models.PositiveSmallIntegerField(
        default=0,
        verbose_name="Position d'affichage",
    )
    is_cover = models.BooleanField(
        default=False,
        verbose_name="Image de couverture",
    )

    class Meta:
        verbose_name = "Photo d'article"
        verbose_name_plural = "Photos d'articles"
        ordering = ["position", "created_at"]

    def __str__(self) -> str:
        return f"Photo de {self.product.title} (pos {self.position})"
