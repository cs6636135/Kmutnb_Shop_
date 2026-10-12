from django.urls import path

from . import views_manage

urlpatterns = [
    path("", views_manage.dashboard, name="dashboard"),

    path("products/", views_manage.products, name="products"),
    path("products/create/", views_manage.product_form, name="product_create"),
    path("products/<int:pk>/edit/", views_manage.product_form, name="product_edit"),
    path("products/<int:pk>/delete/", views_manage.product_delete, name="product_delete"),

    path("locations/", views_manage.locations, name="locations"),
    path("locations/create/", views_manage.location_form, name="location_create"),
    path("locations/<int:pk>/edit/", views_manage.location_form, name="location_edit"),
    path("locations/<int:pk>/delete/", views_manage.location_delete, name="location_delete"),

    path("categories/", views_manage.categories, name="categories"),
    path("categories/create/", views_manage.category_form, name="category_create"),
    path("categories/<int:pk>/edit/", views_manage.category_form, name="category_edit"),
    path("categories/<int:pk>/delete/", views_manage.category_delete, name="category_delete"),
]