from django.urls import path
from . import views

urlpatterns = [
    path("manage/login/", views.user_login, name="login"),
    path("manage/logout/", views.user_logout, name="logout"),

    path("manage/staffs/", views.staffs, name="staffs"),
    path("manage/staffs/create/", views.staff_form, name="staff_create"),
    path("manage/staffs/<int:pk>/edit/", views.staff_form, name="staff_edit"),
    path("manage/staffs/<int:pk>/delete/", views.staff_delete, name="staff_delete"),
]