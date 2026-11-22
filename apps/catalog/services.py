from django.core.exceptions import PermissionDenied, ValidationError
from django.utils.text import slugify

from apps.accounts.models import User
from apps.catalog.image_processing import process_product_image
from apps.catalog.models import Category, Product, ProductImage
from apps.shops.models import Shop


def category_create(
    *,
    name: str,
    parent: Category | None = None,
    slug: str = "",
    icon: str = "",
    order: int = 0,
) -> Category:
    """Creates a new catalog category."""
    if not name.strip():
        raise ValidationError("Le nom de la catégorie est obligatoire.")

    category_slug = slug.strip() or slugify(name)
    category = Category.objects.create(
        name=name.strip(),
        slug=category_slug,
        parent=parent,
        icon=icon.strip(),
        order=order,
    )
    return category


def product_create(
    *,
    shop: Shop,
    user: User,
    category: Category,
    title: str,
    description: str,
    price_gnf: int,
    condition: str = Product.Condition.NEW,
    brand: str = "",
    stock: int = 1,
    status: str = Product.Status.DRAFT,
) -> Product:
    """
    Creates a new product for a shop.
    Enforces ownership check (shop.owner.user == user).
    """
    if shop.owner.user != user and not user.is_staff:
        raise PermissionDenied("Vous n'êtes pas autorisé à ajouter des articles pour cette boutique.")

    if not title.strip():
        raise ValidationError("Le titre de l'article est obligatoire.")
    if price_gnf <= 0:
        raise ValidationError("Le prix doit être strictement supérieur à 0 GNF.")
    if stock < 0:
        raise ValidationError("La quantité en stock ne peut pas être négative.")

    product = Product(
        shop=shop,
        category=category,
        title=title.strip(),
        description=description.strip(),
        price_gnf=price_gnf,
        condition=condition,
        brand=brand.strip(),
        stock=stock,
        status=status,
    )
    product.save()
    return product


def product_update(
    *,
    product: Product,
    user: User,
    **fields,
) -> Product:
    """
    Updates an existing product with ownership verification.
    """
    if product.shop.owner.user != user and not user.is_staff:
        raise PermissionDenied("Vous n'êtes pas autorisé à modifier cet article.")

    allowed_fields = {"category", "title", "description", "price_gnf", "condition", "brand", "stock", "status"}
    updated_fields = []

    for field, value in fields.items():
        if field not in allowed_fields:
            continue
        if field == "price_gnf" and value <= 0:
            raise ValidationError("Le prix doit être supérieur à 0 GNF.")
        if field == "stock" and value < 0:
            raise ValidationError("Le stock ne peut pas être négatif.")
        if field == "title" and value and value.strip() != product.title:
            product.title = value.strip()
            # Regenerate slug on title change
            base_slug = slugify(product.title) or "article"
            unique_slug = base_slug
            counter = 1
            while Product.objects.filter(slug=unique_slug).exclude(pk=product.pk).exists():
                unique_slug = f"{base_slug}-{counter}"
                counter += 1
            product.slug = unique_slug
            updated_fields.extend(["title", "slug"])
            continue

        setattr(product, field, value)
        updated_fields.append(field)

    if updated_fields:
        updated_fields.append("updated_at")
        product.save(update_fields=list(set(updated_fields)))

    return product


def product_publish(
    *,
    product: Product,
    user: User,
) -> Product:
    """
    Publishes a product to make it publicly visible.
    Requires at least 1 image and an active shop.
    """
    if product.shop.owner.user != user and not user.is_staff:
        raise PermissionDenied("Vous n'êtes pas autorisé à publier cet article.")

    if not product.shop.is_active:
        raise ValidationError("Vous ne pouvez pas publier d'articles tant que votre boutique n'est pas activée par l'administrateur.")

    if not product.images.exists():
        raise ValidationError("Vous devez ajouter au moins une photo avant de publier l'article.")

    if product.stock <= 0:
        raise ValidationError("Le stock doit être d'au moins 1 pour publier l'article.")

    product.status = Product.Status.PUBLISHED
    product.save(update_fields=["status", "updated_at"])
    return product


def product_hide(
    *,
    product: Product,
    user: User,
) -> Product:
    """Hides a product from the public catalog."""
    if product.shop.owner.user != user and not user.is_staff:
        raise PermissionDenied("Vous n'êtes pas autorisé à masquer cet article.")

    product.status = Product.Status.HIDDEN
    product.save(update_fields=["status", "updated_at"])
    return product


def product_image_add(
    *,
    product: Product,
    user: User,
    image_file,
    is_cover: bool = False,
) -> ProductImage:
    """
    Adds an optimized WebP image to a product.
    Enforces the strict limit of maximum 8 images per product.
    """
    if product.shop.owner.user != user and not user.is_staff:
        raise PermissionDenied("Vous n'êtes pas autorisé à modifier les photos de cet article.")

    current_count = product.images.count()
    if current_count >= 8:
        raise ValidationError("Un article ne peut pas avoir plus de 8 photos.")

    # Process image with Pillow (strips EXIF GPS, resizes, converts to WebP)
    optimized_content = process_product_image(image_file)

    # First image is cover by default
    make_cover = is_cover or (current_count == 0)

    if make_cover:
        product.images.filter(is_cover=True).update(is_cover=False)

    product_image = ProductImage.objects.create(
        product=product,
        image=optimized_content,
        position=current_count,
        is_cover=make_cover,
    )
    return product_image


def product_image_delete(
    *,
    image: ProductImage,
    user: User,
) -> None:
    """
    Deletes an image from a product with ownership validation.
    """
    if image.product.shop.owner.user != user and not user.is_staff:
        raise PermissionDenied("Vous n'êtes pas autorisé à supprimer cette photo.")

    product = image.product
    was_cover = image.is_cover

    # Delete disk file and record
    image.image.delete(save=False)
    image.delete()

    # If deleted image was cover, assign cover to first remaining image
    if was_cover:
        first_remaining = product.images.order_by("position", "created_at").first()
        if first_remaining:
            first_remaining.is_cover = True
            first_remaining.save(update_fields=["is_cover"])
