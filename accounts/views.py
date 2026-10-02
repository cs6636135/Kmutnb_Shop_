from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout

#login หลังร้าน
def user_login(request):
    if request.method == "POST":
        username = request.POST["username"]
        password = request.POST["password"]

        user = authenticate(
            request,
            username=username,
            password=password
        )

        if user is not None:

            login(request, user)
            return redirect("dashboard")


        return render(request, "manage/login.html", {
            "error": "Username หรือ Password ไม่ถูกต้อง"
        })
    return render(request, "manage/login.html")

def user_logout(request):
    logout(request)
    return redirect("login")