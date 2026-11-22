import uuid

from django.contrib.postgres.search import SearchQuery, SearchRank, SearchVector
from django.db.models import Q, QuerySet

from apps.accounts.models import User
from apps.catalog.models import Category, Product
from apps.shops.models import Shop


def category_list_tree() -> QuerySet[Category]:
    """Returns top-level categories with prefetched subcategories."""
    return (
        Category.objects.filter(parent__isnull=True)
        .prefetch_related("children")
        .order_by("order", "name")
    )


def category_get_by_slug(*, slug: str) -> Category | None:
    """Retrieves a category by slug."""
    if not slug:
        return None
    return Category.objects.filter(slug=slug).first()


def product_get_by_slug(*, slug: str) -> Product | None:
    """Retrieves a product by slug with shop and images prefetched."""
    if not slug:
        return None
    return (
        Product.objects.filter(slug=slug)
        .select_related("shop__owner__user", "category")
        .prefetch_related("images")
        .first()
    )


def product_get_by_id(*, id: uuid.UUID | str) -> Product | None:
    """Retrieves a product by UUID."""
    if not id:
        return None
    return (
        Product.objects.filter(id=id)
        .select_related("shop__owner__user", "category")
        .prefetch_related("images")
        .first()
    )


def products_published_list(
    *,
    category: Category | None = None,
    city: str = "",
    condition: str = "",
    min_price: int | None = None,
    max_price: int | None = None,
    query: str = "",
    ordering: str = "-created_at",
) -> QuerySet[Product]:
    """
    Search and filter engine for published products in active shops.
    Supports PostgreSQL full-text search and faceted filtering.
    """
    qs = (
        Product.objects.filter(
            status=Product.Status.PUBLISHED,
            shop__status=Shop.Status.ACTIVE,
        )
        .select_related("shop", "category")
        .prefetch_related("images")
    )

    # Filter by category (including all descendant subcategories)
    if category:
        category_ids = [category.id] + list(category.children.values_list("id", flat=True))
        qs = qs.filter(category_id__in=category_ids)

    # Filter by shop city
    if city:
        qs = qs.filter(shop__city=city)

    # Filter by item condition (new, used, refurbished)
    if condition:
        qs = qs.filter(condition=condition)

    # Price range filters (in GNF)
    if min_price is not None and min_price > 0:
        qs = qs.filter(price_gnf__gte=min_price)
    if max_price is not None and max_price > 0:
        qs = qs.filter(price_gnf__lte=max_price)

    # PostgreSQL full-text search with ranking
    if query and query.strip():
        search_query = SearchQuery(query.strip())
        vector = (
            SearchVector("title", weight="A")
            + SearchVector("brand", weight="B")
            + SearchVector("description", weight="C")
        )
        qs = (
            qs.annotate(search=vector, rank=SearchRank(vector, search_query))
            .filter(Q(search=search_query) | Q(title__icontains=query.strip()))
            .order_by("-rank", "-created_at")
        )
        return qs

    # Ordering
    allowed_orderings = {
        "-created_at": "-created_at",
        "price_asc": "price_gnf",
        "price_desc": "-price_gnf",
    }
    order_by_field = allowed_orderings.get(ordering, "-created_at")
    return qs.order_by(order_by_field)


def products_for_shop(
    *,
    shop: Shop,
    user: User | None = None,
) -> QuerySet[Product]:
    """
    Returns products for a given shop.
    Owners and staff can see drafts and hidden products; the public only sees published ones.
    """
    qs = shop.products.select_related("category").prefetch_related("images")

    is_owner_or_staff = user and user.is_authenticated and (shop.owner.user == user or user.is_staff)
    if not is_owner_or_staff:
        qs = qs.filter(status=Product.Status.PUBLISHED)

    return qs.order_by("-created_at")
