from django.urls import path
from . import views_manage as views
from shop import views_public

urlpatterns = [
    path("", views_public.home, name="home"),
    path("products/<int:product_id>/", views_public.product_detail, name="product_detail"),
    path("products/", views_public.product_list, name="public_products"),
    path("", views.dashboard, name="manage_dashboard"),
    path("dashboard/", views.dashboard, name="dashboard"),
    path("reservations/", views.reservations, name="reservations"),
]


    