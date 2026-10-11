import re

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from accounts.permission import role_required
from .models import Product,Location,Category,ProductLocation
from reservations.models import Reservation
from .form import ProductModelForm,LocationModelForm,CategoryModelForm
from django.db.models import Count, ProtectedError, Sum
from django.db import transaction, IntegrityError
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.utils import timezone


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
            #instance คือ
            if form.is_valid():
                try:
                    with transaction.atomic(): #ถ้าล้มจะไปต่อได้
                        form.save() #ในรุปถ้าเรียกแบบไม่มีค่า commit = true
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
                messages.error(request, "ลบไม่ได้ เพราะสินค้านี้ยังถูกใช้งานอยู่") #เช่นเอาไปใช้จองอยู่
            return redirect("products")

    search_query = request.GET.get("q", "").strip()          # search
    category_query = request.GET.get("category", "").strip()
    categories = Category.objects.order_by("name")

    qs = Product.objects.select_related("category").order_by("-created_at")
    for term in search_query.split():
        qs = qs.filter(name__icontains=term)

    if category_query:
        try:
            category_id = int(category_query)
        except ValueError:
            category_query = ""
        else:
            if categories.filter(pk=category_id).exists():
                qs = qs.filter(category_id=category_id)
            else:
                category_query = ""

    paginator = Paginator(qs, 10)                            # หน้าละ 10 อัน
    page_obj = paginator.get_page(request.GET.get("page"))   # เลขหน้าจากลิงก์ ?page=2

    return render(request, "manage/products.html", {
        "page_obj": page_obj,
        "search_query": search_query,
        "categories": categories,
        "category_query": category_query,
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
                    messages.success(request, "บันทึกจุดจำหน่ายเรียบร้อยแล้ว")
                    return redirect("locations")

            return render(request, "manage/location_form.html", {
                "form": form,
                "location": location,
            })

        elif "delete" in request.POST:
            location = get_object_or_404(Location, pk=request.POST["delete"])
            location.delete()
            messages.success(request, "ลบจุดจำหน่ายเรียบร้อยแล้ว")
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

@role_required("admin")
def categories(request):
    if request.method == "POST":

        if "add" in request.POST:
            return render(request, "manage/category_form.html", {
                "form": CategoryModelForm(),
            })

        elif "edit" in request.POST:
            category = get_object_or_404(Category, pk=request.POST["edit"])
            return render(request, "manage/category_form.html", {
                "form": CategoryModelForm(instance=category),
                "category": category,
            })

        elif "save" in request.POST:
            pk = request.POST.get("save")
            category = get_object_or_404(Category, pk=pk) if pk else None
            form = CategoryModelForm(request.POST, instance=category)

            if form.is_valid():
                try:
                    with transaction.atomic():
                        form.save()
                except ValidationError as e:
                    form.add_error(None, e)
                except IntegrityError:
                    form.add_error(None, "บันทึกไม่สำเร็จ ข้อมูลอาจซ้ำหรือไม่ครบ")
                else:
                    messages.success(request, "บันทึกหมวดหมู่สินค้าเรียบร้อยแล้ว")
                    return redirect("categories")

            return render(request, "manage/category_form.html", {
                "form": form,
                "category": category,
            })

        elif "delete" in request.POST:
            category = get_object_or_404(Category, pk=request.POST["delete"])
            try:
                category.delete()
            except ProtectedError:
                messages.error(request, "ไม่สามารถลบหมวดหมู่ได้ เนื่องจากยังมีข้อมูลที่เกี่ยวข้องอยู่")
                return redirect("categories")
            messages.success(request, "ลบหมวดหมู่สินค้าเรียบร้อยแล้ว")
            return redirect("categories")

    search_query = request.GET.get("q", "").strip()

    qs = Category.objects.all().order_by("name")
    for term in search_query.split():
        qs = qs.filter(name__icontains=term)

    paginator = Paginator(qs, 10)
    page_obj = paginator.get_page(request.GET.get("page"))

    return render(request, "manage/categories.html", {
        "page_obj": page_obj,
        "search_query": search_query,
    })


# เปลี่ยนการจองที่หมดเวลาเป็น expired และคืนสต็อก
def expire_overdue_reservations():
    now = timezone.now()

    # atomic: คืนสต็อกกับเปลี่ยนสถานะ ต้องสำเร็จพร้อมกันหรือย้อนกลับพร้อมกัน
    with transaction.atomic():
        # select_for_update: ล็อกแถวไว้ กันสองคำขอคืนสต็อกซ้ำ
        overdue = Reservation.objects.select_for_update().filter(
            status=Reservation.Status.PENDING,
            expires_at__lte=now,
        )

        for r in overdue:
            # หาสต็อกของสินค้านี้ ณ จุดที่จอง (unique คู่ product+location จึงได้ 1 แถว)
            pl = ProductLocation.objects.get(product=r.product, location=r.location)
            pl.stock = pl.stock + r.quantity   # คืนสต็อก
            pl.save()

            r.status = Reservation.Status.EXPIRED
            r.save()

#ทำให้เร็ว
@role_required("admin", "staff")
def dashboard(request):
    user = request.user
    is_admin = user.role == "admin"
    user_location = user.location

    # อัปเดตรายการหมดเวลาก่อน เพื่อให้ตัวเลขตรงความจริง
    expire_overdue_reservations()

    # Admin: all() เห็นทุกสาขา / Staff: filter() เฉพาะสาขาตัวเอง
    if is_admin:
        stocks = ProductLocation.objects.all()
        reservations = Reservation.objects.all()
    else:
        stocks = ProductLocation.objects.filter(location=user_location)
        reservations = Reservation.objects.filter(location=user_location)

    # ---------- การ์ดสถิติ ----------
    total_units_stock = stocks.aggregate(total=Sum("stock"))["total"] or 0

    # chaining filters แล้ว count()
    active_reservations = reservations.filter(
        status=Reservation.Status.PENDING
    ).count()
    expired_reservations = reservations.filter(
        status=Reservation.Status.EXPIRED
    ).count()

    # วันนี้ตามเวลาท้องถิ่น (ไทย UTC+7)
    today = timezone.localdate()
    picked_up_today = reservations.filter(
        status=Reservation.Status.PICKED_UP,
        picked_up_at__date=today,
    ).count()

    # ---------- จองล่าสุด 8 แถว (เรียงใหม่ไปเก่า) ----------
    recent_reservations = reservations.order_by("-reserved_at")[:8]

    # ---------- สินค้าใกล้หมด (<= 5 ชิ้น) เรียงน้อยไปมาก 6 รายการ ----------
    low_stocks = stocks.filter(stock__lte=5).order_by("stock")[:6]

    # ---------- สรุปรายสาขา (เฉพาะ admin) ----------
    locations_summary = []
    if is_admin:
        stock_by_location = {
            row["location_id"]: row["total_stock"]
            for row in ProductLocation.objects.values("location_id").annotate(
                total_stock=Sum("stock")
            )
        }
        reservations_by_location = {
            row["location_id"]: row["total"]
            for row in Reservation.objects.filter(
                status=Reservation.Status.PENDING
            ).values("location_id").annotate(total=Count("pk"))
        }

        for loc in Location.objects.all():
            locations_summary.append({
                "location": loc,
                "total_stock": stock_by_location.get(loc.pk, 0),
                "active_reservations": reservations_by_location.get(loc.pk, 0),
            })

    context = {
        "is_admin": is_admin,
        "user_location": user_location,
        "total_units_stock": total_units_stock,
        "active_reservations": active_reservations,
        "picked_up_today": picked_up_today,
        "expired_reservations": expired_reservations,
        "recent_reservations": recent_reservations,
        "low_stocks": low_stocks,
        "locations_summary": locations_summary,
    }
    return render(request, "manage/dashboard.html", context)