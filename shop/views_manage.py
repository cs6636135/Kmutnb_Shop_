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
from reservations.services import expire_overdue_reservations


from django.contrib import messages
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.db import IntegrityError, transaction
from django.db.models import ProtectedError
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

SAVE_ERROR = "บันทึกไม่สำเร็จ ข้อมูลอาจซ้ำหรือไม่ครบ"

#Product
@role_required("admin")
def products(request):
    search_query = request.GET.get("q", "").strip()
    category_query = request.GET.get("category", "").strip()
    categories = Category.objects.order_by("name")

    qs = Product.objects.select_related("category").order_by("-created_at")
    for term in search_query.split():
        qs = qs.filter(name__icontains=term)

    if category_query.isdigit():
        qs = qs.filter(category_id=int(category_query))

    page_obj = Paginator(qs, 10).get_page(request.GET.get("page"))

    return render(request, "manage/products.html", {
        "page_obj": page_obj,
        "search_query": search_query,
        "categories": categories,
        "category_query": category_query,
    })

@role_required("admin")
def product_form(request, pk=None):
    product = get_object_or_404(Product, pk=pk) if pk else None
    form = ProductModelForm(request.POST or None, request.FILES or None, instance=product)

    if request.method == "POST" and form.is_valid():
        try:
            with transaction.atomic():
                form.save()
        except ValidationError as e:
            form.add_error(None, e)
        except IntegrityError:
            form.add_error(None, SAVE_ERROR)
        else:
            messages.success(request, "บันทึกสินค้าเรียบร้อยแล้ว")
            return redirect("products")

    return render(request, "manage/product_form.html", {"form": form, "product": product})

@role_required("admin")
@require_POST
def product_delete(request, pk):
    product = get_object_or_404(Product, pk=pk)
    try:
        product.delete()
        messages.success(request, "ลบสินค้าเรียบร้อยแล้ว")
    except ProtectedError:
        messages.error(request, "ลบไม่ได้ เพราะสินค้านี้ยังถูกใช้งานอยู่")
    return redirect("products")


#Location 
@role_required("admin")
def locations(request):
    search_query = request.GET.get("q", "").strip()

    qs = Location.objects.order_by("-id")
    for term in search_query.split():
        qs = qs.filter(name__icontains=term)

    page_obj = Paginator(qs, 10).get_page(request.GET.get("page"))

    return render(request, "manage/locations.html", {
        "page_obj": page_obj,
        "search_query": search_query,
    })

@role_required("admin")
def location_form(request, pk=None):
    location = get_object_or_404(Location, pk=pk) if pk else None
    form = LocationModelForm(request.POST or None, request.FILES or None, instance=location)

    if request.method == "POST" and form.is_valid():
        try:
            with transaction.atomic():
                form.save()
        except ValidationError as e:
            form.add_error(None, e)
        except IntegrityError:
            form.add_error(None, SAVE_ERROR)
        else:
            messages.success(request, "บันทึกจุดจำหน่ายเรียบร้อยแล้ว")
            return redirect("locations")

    return render(request, "manage/location_form.html", {"form": form, "location": location})

@role_required("admin")
@require_POST
def location_delete(request, pk):
    location = get_object_or_404(Location, pk=pk)
    try:
        location.delete()
        messages.success(request, "ลบจุดจำหน่ายเรียบร้อยแล้ว")
    except ProtectedError:
        messages.error(request, "ลบไม่ได้ เพราะจุดจำหน่ายนี้ยังถูกใช้งานอยู่")
    return redirect("locations")


#Category
@role_required("admin")
def categories(request):
    search_query = request.GET.get("q", "").strip()

    qs = Category.objects.order_by("name")
    for term in search_query.split():
        qs = qs.filter(name__icontains=term)

    page_obj = Paginator(qs, 10).get_page(request.GET.get("page"))

    return render(request, "manage/categories.html", {
        "page_obj": page_obj,
        "search_query": search_query,
    })

@role_required("admin")
def category_form(request, pk=None):
    category = get_object_or_404(Category, pk=pk) if pk else None
    form = CategoryModelForm(request.POST or None, instance=category)

    if request.method == "POST" and form.is_valid():
        try:
            with transaction.atomic():
                form.save()
        except ValidationError as e:
            form.add_error(None, e)
        except IntegrityError:
            form.add_error(None, SAVE_ERROR)
        else:
            messages.success(request, "บันทึกหมวดหมู่สินค้าเรียบร้อยแล้ว")
            return redirect("categories")

    return render(request, "manage/category_form.html", {"form": form, "category": category})

@role_required("admin")
@require_POST
def category_delete(request, pk):
    category = get_object_or_404(Category, pk=pk)
    try:
        category.delete()
        messages.success(request, "ลบหมวดหมู่สินค้าเรียบร้อยแล้ว")
    except ProtectedError:
        messages.error(request, "ไม่สามารถลบหมวดหมู่ได้ เนื่องจากยังมีข้อมูลที่เกี่ยวข้องอยู่")
    return redirect("categories")


#dashboard
@role_required("admin", "staff")
def dashboard(request):
    # อ่านข้อมูลผู้ใช้เพื่อเลือกสิทธิ์และสาขาที่จะแสดง
    user = request.user
    is_admin = user.role == "admin"
    if is_admin:
        # อัปเดตการจองหมดอายุก่อนสรุปสต็อกแยกตาม location ให้ admin
        expire_overdue_reservations()

    user_location = user.location

    # Admin เห็นข้อมูลทุกสาขา ส่วน staff เห็นเฉพาะสาขาที่ตนเองประจำอยู่
    stocks = ProductLocation.objects.all()
    reservations = Reservation.objects.all()
    if not is_admin:
        stocks = stocks.filter(location=user_location)
        reservations = reservations.filter(location=user_location)

    # รวมสต็อกคงเหลือทั้งหมดในขอบเขตสาขาที่ผู้ใช้มีสิทธิ์เห็น
    total_units_stock = stocks.aggregate(total=Sum("stock"))["total"] or 0

    # นับรายการจองตามสถานะ
    active_reservations = reservations.filter(
        status=Reservation.Status.PENDING
    ).count()
    expired_reservations = reservations.filter(
        status=Reservation.Status.EXPIRED
    ).count()

    # นับรายการที่รับสินค้าแล้วในวันนี้ตามเวลาท้องถิ่น
    today = timezone.localdate()
    picked_up_today = reservations.filter(
        status=Reservation.Status.PICKED_UP,
        picked_up_at__date=today,
    ).count()

    # ดึงรายการจองล่าสุดไม่เกิน 8 รายการ
    recent_reservations = reservations.order_by("-reserved_at")[:8]

    # ดึงสินค้าที่เหลือไม่เกิน 5 ชิ้น เรียงจากเหลือน้อยไปมาก ไม่เกิน 6 รายการ
    low_stocks = stocks.filter(stock__lte=5).order_by("stock")[:6]

    # สรุปสต็อกและการจองแยกตามสาขาสำหรับ admin
    locations_summary = []
    if is_admin:
        stock_by_location = {
            row["location_id"]: row["total"] or 0
            for row in ProductLocation.objects.values("location_id").annotate(
                total=Sum("stock")
            )
        }
        reservations_by_location = {
            row["location_id"]: row["total"]
            for row in Reservation.objects.filter(
                status=Reservation.Status.PENDING
            ).values("location_id").annotate(total=Count("pk"))
        }
        locations_summary = [
            {
                "location": {"name": location.name},
                "total_stock": stock_by_location.get(location.pk, 0),
                "active_reservations": reservations_by_location.get(location.pk, 0),
            }
            for location in Location.objects.all()
        ]

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
