from django.urls import path

from apps.shops import views

app_name = "shops"

urlpatterns = [
    path("", views.ShopListView.as_view(), name="list"),
    path("mon-compte/boutiques/", views.SellerDashboardView.as_view(), name="seller_dashboard"),
    path("mon-compte/boutiques/nouvelle/", views.ShopCreateView.as_view(), name="create"),
    path("mon-compte/boutiques/<slug:slug>/modifier/", views.ShopUpdateView.as_view(), name="update"),
    path("mon-compte/boutiques/<slug:slug>/soumettre/", views.ShopSubmitReviewView.as_view(), name="submit_review"),
    path("<slug:slug>/", views.ShopDetailView.as_view(), name="detail"),
]
