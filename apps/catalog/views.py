from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied, ValidationError
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect
from django.views.generic import CreateView, DetailView, FormView, ListView, UpdateView, View

from apps.catalog.forms import ProductForm, ProductImageUploadForm
from apps.catalog.models import Category, Product, ProductImage
from apps.catalog.selectors import (
    category_list_tree,
    product_get_by_slug,
    products_published_list,
)
from apps.catalog.services import (
    product_create,
    product_hide,
    product_image_add,
    product_image_delete,
    product_publish,
    product_update,
)
from apps.shops.constants import GUINEAN_CITIES
from apps.shops.models import Shop


class ProductListView(ListView):
    """
    Public catalog browsing view with search and filters.
    """

    model = Product
    template_name = "catalog/product_list.html"
    context_object_name = "products"
    paginate_by = 16

    def get_queryset(self):
        category_slug = self.request.GET.get("category", "").strip()
        selected_category = None
        if category_slug:
            selected_category = Category.objects.filter(slug=category_slug).first()

        city = self.request.GET.get("city", "").strip()
        condition = self.request.GET.get("condition", "").strip()
        query = self.request.GET.get("q", "").strip()
        ordering = self.request.GET.get("sort", "-created_at").strip()

        # Parse prices
        min_price = None
        max_price = None
        try:
            if self.request.GET.get("min_price"):
                min_price = int(self.request.GET.get("min_price"))
            if self.request.GET.get("max_price"):
                max_price = int(self.request.GET.get("max_price"))
        except ValueError:
            pass

        return products_published_list(
            category=selected_category,
            city=city,
            condition=condition,
            min_price=min_price,
            max_price=max_price,
            query=query,
            ordering=ordering,
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["categories"] = category_list_tree()
        context["cities"] = GUINEAN_CITIES
        context["selected_category"] = self.request.GET.get("category", "")
        context["selected_city"] = self.request.GET.get("city", "")
        context["selected_condition"] = self.request.GET.get("condition", "")
        context["query"] = self.request.GET.get("q", "")
        context["min_price"] = self.request.GET.get("min_price", "")
        context["max_price"] = self.request.GET.get("max_price", "")
        context["sort"] = self.request.GET.get("sort", "-created_at")
        return context


class ProductDetailView(DetailView):
    """
    Public product detail view.
    Only published products of active shops are visible to the public.
    """

    model = Product
    template_name = "catalog/product_detail.html"
    context_object_name = "product"
    slug_field = "slug"
    slug_url_kwarg = "slug"

    def get_object(self, queryset=None):
        slug = self.kwargs.get("slug")
        product = product_get_by_slug(slug=slug)
        if not product:
            raise Http404("Cet article n'existe pas ou n'est plus en vente.")

        user = self.request.user
        is_owner_or_staff = user.is_authenticated and (product.shop.owner.user == user or user.is_staff)

        if not product.is_published and not is_owner_or_staff:
            raise Http404("Cet article n'est pas encore disponible.")

        return product


class SellerProductCreateView(LoginRequiredMixin, CreateView):
    """Seller view to add a new product to their shop."""

    model = Product
    form_class = ProductForm
    template_name = "catalog/product_form.html"

    def dispatch(self, request, *args, **kwargs):
        self.shop = get_object_or_404(Shop, slug=self.kwargs.get("shop_slug"))
        if self.shop.owner.user != request.user and not request.user.is_staff:
            raise PermissionDenied("Vous n'êtes pas le propriétaire de cette boutique.")
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        product = product_create(
            shop=self.shop,
            user=self.request.user,
            category=form.cleaned_data["category"],
            title=form.cleaned_data["title"],
            description=form.cleaned_data["description"],
            price_gnf=form.cleaned_data["price_gnf"],
            condition=form.cleaned_data["condition"],
            brand=form.cleaned_data.get("brand", ""),
            stock=form.cleaned_data.get("stock", 1),
        )
        messages.success(
            self.request,
            f"Article '{product.title}' créé. Ajoutez maintenant au moins une photo pour pouvoir le publier.",
        )
        return redirect("catalog:seller_product_images", slug=product.slug)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["shop"] = self.shop
        return context


class SellerProductUpdateView(LoginRequiredMixin, UpdateView):
    """Seller view to edit an existing product."""

    model = Product
    form_class = ProductForm
    template_name = "catalog/product_form.html"
    slug_field = "slug"
    slug_url_kwarg = "slug"

    def get_object(self, queryset=None):
        product = get_object_or_404(Product, slug=self.kwargs.get("slug"))
        if product.shop.owner.user != self.request.user and not self.request.user.is_staff:
            raise PermissionDenied("Vous n'êtes pas autorisé à modifier cet article.")
        return product

    def form_valid(self, form):
        product = self.get_object()
        product_update(
            product=product,
            user=self.request.user,
            category=form.cleaned_data["category"],
            title=form.cleaned_data["title"],
            description=form.cleaned_data["description"],
            price_gnf=form.cleaned_data["price_gnf"],
            condition=form.cleaned_data["condition"],
            brand=form.cleaned_data.get("brand", ""),
            stock=form.cleaned_data.get("stock", 1),
        )
        messages.success(self.request, "Article mis à jour avec succès.")
        return redirect("catalog:detail", slug=product.slug)


class SellerProductImageManageView(LoginRequiredMixin, FormView):
    """View allowing a seller to upload and manage the 8 photos of an article."""

    form_class = ProductImageUploadForm
    template_name = "catalog/product_images.html"

    def dispatch(self, request, *args, **kwargs):
        self.product = get_object_or_404(Product, slug=self.kwargs.get("slug"))
        if self.product.shop.owner.user != request.user and not request.user.is_staff:
            raise PermissionDenied("Vous n'êtes pas autorisé à gérer les photos de cet article.")
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["product"] = self.product
        context["images"] = self.product.images.all()
        return context

    def form_valid(self, form):
        image_file = form.cleaned_data["image"]
        is_cover = form.cleaned_data.get("is_cover", False)
        try:
            product_image_add(
                product=self.product,
                user=self.request.user,
                image_file=image_file,
                is_cover=is_cover,
            )
            messages.success(self.request, "Photo ajoutée et optimisée en WebP avec succès.")
        except ValidationError as e:
            messages.error(self.request, str(e.message if hasattr(e, "message") else e))

        return redirect("catalog:seller_product_images", slug=self.product.slug)


class SellerProductImageDeleteView(LoginRequiredMixin, View):
    """Deletes a photo with ownership verification."""

    def post(self, request, image_id):
        image = get_object_or_404(ProductImage, id=image_id)
        product = image.product
        try:
            product_image_delete(image=image, user=request.user)
            messages.success(request, "Photo supprimée.")
        except PermissionDenied as e:
            messages.error(request, str(e))
        return redirect("catalog:seller_product_images", slug=product.slug)


class SellerProductPublishToggleView(LoginRequiredMixin, View):
    """Publishes or hides a product."""

    def post(self, request, slug):
        product = get_object_or_404(Product, slug=slug)
        action = request.POST.get("action")

        try:
            if action == "publish":
                product_publish(product=product, user=request.user)
                messages.success(request, f"L'article '{product.title}' est maintenant publié et en vente !")
            elif action == "hide":
                product_hide(product=product, user=request.user)
                messages.success(request, f"L'article '{product.title}' a été masqué du catalogue.")
        except (PermissionDenied, ValidationError) as e:
            messages.error(request, str(e.message if hasattr(e, "message") else e))

        return redirect("shops:detail", slug=product.shop.slug)
