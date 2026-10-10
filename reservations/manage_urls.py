from django.urls import path

from . import views_manage


urlpatterns = [
    path("reservations/", views_manage.reservation_list, name="reservation_list"),
]
