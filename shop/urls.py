from django.urls import path

from shop import views_public

urlpatterns = [
    path("", views_public.home, name="home"),
    path("products/<int:product_id>/", views_public.product_detail, name="product_detail"),
    path("products/", views_public.product_list, name="public_products"),
]