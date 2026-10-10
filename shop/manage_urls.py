from django.urls import path

from . import views_manage

urlpatterns = [
    path("", views_manage.dashboard, name="dashboard"),
    path("products/", views_manage.products, name="products"),
    path("locations/", views_manage.locations, name="locations"),
    path("categories/", views_manage.categories, name="categories"),
]