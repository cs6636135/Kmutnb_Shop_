from django.urls import path
from . import views_public

urlpatterns = [
	path("reservation-status/", views_public.reservation_status, name="reservation_status"),
	path("reservation/create/<int:product_id>/", views_public.reservation_create, name="reservation_create"),
	path("reservation/confirmation/<str:reservation_code>/", views_public.reservation_confirmation, name="reservation_confirmation"),
]