import re

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from accounts.permission import role_required
from .models import Product,Location,Category
from .form import ProductModelForm,LocationModelForm,CategoryModelForm
from django.db.models import ProtectedError
from django.db import transaction, IntegrityError
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator

@role_required("admin", "staff")
def dashboard(request):
    return render(request, "manage/dashboard.html", {
        "user": request.user,
        "session_info": request.session.items(),
    })


@role_required("admin")
def products(request):
    if request.method == "POST":

        if "add" in request.POST:                       # เปิดฟอร์มว่าง
            return render(request, "manage/product_form.html", {
                "form": ProductModelForm(),
            })

        elif "edit" in request.POST:                    # เปิดฟอร์มพร้อมค่าเดิม
            product = get_object_or_404(Product, pk=request.POST["edit"])
            return render(request, "manage/product_form.html", {
                "form": ProductModelForm(instance=product),
                "product": product,
            })

        elif "save" in request.POST:
            pk = request.POST.get("save")
            product = get_object_or_404(Product, pk=pk) if pk else None
            form = ProductModelForm(request.POST,request.FILES or None, instance=product)

            if form.is_valid():
                try:
                    with transaction.atomic():
                        form.save()
                except ValidationError as e:
                    # error จาก model (เช่น full_clean ใน save()) ใช้ข้อความจริง
                    form.add_error(None, e)
                except IntegrityError as e:
                    # error จากฐานข้อมูล แสดงข้อความจริงจาก DB
                    print("IntegrityError:", e)
                    form.add_error(None, "บันทึกไม่สำเร็จ ข้อมูลอาจซ้ำหรือไม่ครบ")
                else:
                    messages.success(request, "บันทึกสินค้าเรียบร้อยแล้ว")
                    return redirect("products")      # redirect เฉพาะสำเร็จ
            print("FORM ERRORS:", form.errors)
                # มาถึงตรงนี้ = มี error ทุกชนิดรวมอยู่ใน form.errors แล้ว
            return render(request, "manage/product_form.html", {
                    "form": form,
                    "product": product,
            })

        elif "delete" in request.POST:                  # ลบ
            product = get_object_or_404(Product, pk=request.POST["delete"])
            try:
                product.delete()
                messages.success(request, "ลบสินค้าเรียบร้อยแล้ว")
            except ProtectedError:
                messages.error(request, "ลบไม่ได้ เพราะสินค้านี้ยังถูกใช้งานอยู่")
            return redirect("products")

    search_query = request.GET.get("q", "").strip()          # search

    qs = Product.objects.select_related("category").order_by("-created_at")
    for term in search_query.split():
        qs = qs.filter(name__icontains=term)

    paginator = Paginator(qs, 10)                            # หน้าละ 10 อัน
    page_obj = paginator.get_page(request.GET.get("page"))   # เลขหน้าจากลิงก์ ?page=2

    return render(request, "manage/products.html", {
        "page_obj": page_obj,
        "search_query": search_query,
    })

@role_required("admin")
def locations(request):
    if request.method == "POST":

        if "add" in request.POST:
            return render(request, "manage/location_form.html", {
                "form": LocationModelForm(),
            })

        elif "edit" in request.POST:
            location = get_object_or_404(Location, pk=request.POST["edit"])
            return render(request, "manage/location_form.html", {
                "form": LocationModelForm(instance=location),
                "location": location,
            })

        elif "save" in request.POST:
            pk = request.POST.get("save")
            location = get_object_or_404(Location, pk=pk) if pk else None
            form = LocationModelForm(request.POST, request.FILES or None, instance=location)

            if form.is_valid():
                try:
                    with transaction.atomic():
                        form.save()
                except ValidationError as e:
                    form.add_error(None, e)
                except IntegrityError:
                    form.add_error(None, "บันทึกไม่สำเร็จ ข้อมูลอาจซ้ำหรือไม่ครบ")
                else:
                    messages.success(request, "บันทึกสถานที่เรียบร้อยแล้ว")
                    return redirect("locations")

            return render(request, "manage/location_form.html", {
                "form": form,
                "location": location,
            })

        elif "delete" in request.POST:
            location = get_object_or_404(Location, pk=request.POST["delete"])
            location.delete()
            messages.success(request, "ลบสถานที่เรียบร้อยแล้ว")
            return redirect("locations")

    search_query = request.GET.get("q", "").strip()

    qs = Location.objects.all()
    for term in search_query.split():
        qs = qs.filter(name__icontains=term)

    paginator = Paginator(qs, 10)
    page_obj = paginator.get_page(request.GET.get("page"))

    return render(request, "manage/locations.html", {
        "page_obj": page_obj,
        "search_query": search_query,
    })