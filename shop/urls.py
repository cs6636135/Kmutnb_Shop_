from django.urls import path

from shop import views_public

urlpatterns = [
    #หน้า
    path("", views_public.home, name="home"),
]