from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout


def user_login(request):
    if request.method == "POST":
        username = request.POST["username"]
        password = request.POST["password"]

        user = authenticate(
            request,
            username=username,
            password=password
        )
        #print("USER:", user)

        if user is not None:
            #print("LOGIN OK")
            login(request, user)
            #print("REDIRECT DASHBOARD")
            return redirect("dashboard")

        #print("LOGIN FAIL")

        return render(request, "manage/login.html", {
            "error": "Username หรือ Password ไม่ถูกต้อง"
        })
    return render(request, "manage/login.html")

def user_logout(request):
    logout(request)
    return redirect("login")