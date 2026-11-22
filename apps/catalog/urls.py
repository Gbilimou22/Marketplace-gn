from django.urls import path

from apps.catalog import views

app_name = "catalog"

urlpatterns = [
    path("", views.ProductListView.as_view(), name="list"),
    path("<slug:slug>/", views.ProductDetailView.as_view(), name="detail"),
    path("boutiques/<slug:shop_slug>/nouveau/", views.SellerProductCreateView.as_view(), name="create"),
    path("<slug:slug>/modifier/", views.SellerProductUpdateView.as_view(), name="update"),
    path("<slug:slug>/photos/", views.SellerProductImageManageView.as_view(), name="seller_product_images"),
    path("photos/<uuid:image_id>/supprimer/", views.SellerProductImageDeleteView.as_view(), name="image_delete"),
    path("<slug:slug>/statut/", views.SellerProductPublishToggleView.as_view(), name="publish_toggle"),
]
