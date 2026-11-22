from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.http import Http404, HttpResponseRedirect
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.views.generic import CreateView, DetailView, ListView, UpdateView, View

from apps.accounts.services import seller_profile_request
from apps.shops.constants import GUINEAN_CITIES
from apps.shops.forms import ShopForm
from apps.shops.models import Shop
from apps.shops.selectors import shop_get_by_slug, shops_active_list, shops_for_user
from apps.shops.services import shop_create, shop_submit_for_review, shop_update


class ShopListView(ListView):
    """
    Public directory of active, verified shops.
    Supports filtering by Guinean city/commune.
    """

    model = Shop
    template_name = "shops/shop_list.html"
    context_object_name = "shops"
    paginate_by = 12

    def get_queryset(self):
        city = self.request.GET.get("city", "").strip()
        return shops_active_list(city=city)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["cities"] = GUINEAN_CITIES
        context["selected_city"] = self.request.GET.get("city", "")
        return context


class ShopDetailView(DetailView):
    """
    Public view of a shop.
    Non-active shops can only be viewed by the owner or staff.
    """

    model = Shop
    template_name = "shops/shop_detail.html"
    context_object_name = "shop"
    slug_field = "slug"
    slug_url_kwarg = "slug"

    def get_object(self, queryset=None):
        slug = self.kwargs.get("slug")
        shop = shop_get_by_slug(slug=slug)
        if not shop:
            raise Http404("Cette boutique n'existe pas.")

        # Permission check: public can only view ACTIVE shops
        if not shop.is_active:
            user = self.request.user
            if not user.is_authenticated or (shop.owner.user != user and not user.is_staff):
                raise Http404("Cette boutique est en attente de validation ou non disponible.")

        return shop


class SellerDashboardView(LoginRequiredMixin, ListView):
    """
    Dashboard for sellers to manage their shops.
    """

    template_name = "shops/dashboard.html"
    context_object_name = "shops"

    def get_queryset(self):
        return shops_for_user(user=self.request.user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        seller_profile = getattr(self.request.user, "seller_profile", None)
        context["seller_profile"] = seller_profile
        return context


class ShopCreateView(LoginRequiredMixin, CreateView):
    """
    View allowing an authenticated user to register a new shop.
    Automatically initializes SellerProfile if needed.
    Administrators are strictly moderators and cannot create shops.
    """

    model = Shop
    form_class = ShopForm
    template_name = "shops/shop_form.html"

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated and (request.user.is_staff or request.user.is_superuser):
            messages.warning(
                request,
                "Votre compte est un compte administrateur / modérateur. Les modérateurs ne peuvent pas créer de boutique vendeuse.",
            )
            return redirect("shops:seller_dashboard")
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        # Automatically ensure seller profile exists
        seller_profile = seller_profile_request(user=self.request.user)
        shop = shop_create(
            owner=seller_profile,
            name=form.cleaned_data["name"],
            city=form.cleaned_data["city"],
            whatsapp_number=form.cleaned_data["whatsapp_number"],
            address=form.cleaned_data.get("address", ""),
            description=form.cleaned_data.get("description", ""),
            logo=self.request.FILES.get("logo"),
        )
        messages.success(
            self.request,
            f"Votre boutique '{shop.name}' a été créée en brouillon. Vous pouvez maintenant la soumettre pour validation.",
        )
        return redirect(reverse("shops:seller_dashboard"))


class ShopUpdateView(LoginRequiredMixin, UpdateView):
    """
    Allows a seller to update shop information.
    """

    model = Shop
    form_class = ShopForm
    template_name = "shops/shop_form.html"
    slug_field = "slug"
    slug_url_kwarg = "slug"

    def get_object(self, queryset=None):
        shop = get_object_or_404(Shop, slug=self.kwargs.get("slug"))
        if shop.owner.user != self.request.user and not self.request.user.is_staff:
            raise PermissionDenied("Vous n'êtes pas autorisé à modifier cette boutique.")
        return shop

    def form_valid(self, form):
        shop = self.get_object()
        shop_update(
            shop=shop,
            user=self.request.user,
            name=form.cleaned_data["name"],
            city=form.cleaned_data["city"],
            address=form.cleaned_data.get("address", ""),
            description=form.cleaned_data.get("description", ""),
            whatsapp_number=form.cleaned_data["whatsapp_number"],
            logo=self.request.FILES.get("logo") or shop.logo,
        )
        messages.success(self.request, "Informations de la boutique mises à jour.")
        return redirect(reverse("shops:seller_dashboard"))


class ShopSubmitReviewView(LoginRequiredMixin, View):
    """
    Submits a draft shop for admin approval.
    """

    def post(self, request, slug):
        shop = get_object_or_404(Shop, slug=slug)
        try:
            shop_submit_for_review(shop=shop, user=request.user)
            messages.success(
                request,
                f"La boutique '{shop.name}' a été soumise avec succès. L'administrateur va vérifier votre compte.",
            )
        except Exception as e:
            messages.error(request, str(e))
        return HttpResponseRedirect(reverse("shops:seller_dashboard"))
