from django.urls import path

from . import views_manage

urlpatterns = [
    #หลัง
    path("", views_manage.dashboard, name="dashboard"),
    path("products/", views_manage.products, name="products"),  
]