#ฝั่งลูกค้า ประมาณว่าเป็นหน้าร้าน
from django.shortcuts import render, redirect
def home(request):
    return render(request, "shop/home.html")