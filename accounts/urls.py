from django.urls import path
from . import views

urlpatterns = [
    path("manage/login/", views.user_login, name="login"),
    path("manage/logout/", views.user_logout, name="logout"),
]