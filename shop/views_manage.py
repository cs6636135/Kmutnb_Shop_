
from django.shortcuts import render
from django.db.models import Sum

from accounts.permission import manage_required, admin_required
from shop.models import Product, ProductLocation, Location
from django.shortcuts import render
from accounts.permission import manage_required, admin_required


# ฝั่งจัดการร้านค้า: ดูแลข้อมูลหลังร้าน ยกเว้นการจอง
@manage_required
def dashboard(request):
    # ข้อมูลสินค้า
    total_products = Product.objects.count()

    reservable_products = Product.objects.filter(
        reservable=True
    ).count()

    unavailable_products = Product.objects.filter(
        reservable=False
    ).count()

    # ข้อมูลสต็อกสินค้า
    stock_summary = ProductLocation.objects.aggregate(
        total_stock=Sum("stock")
    )

    total_stock = stock_summary["total_stock"] or 0

    # จำนวนจุดรับสินค้า
    total_locations = Location.objects.count()

    # รายการสินค้าเพิ่มล่าสุด 5 รายการ
    recent_products = Product.objects.select_related(
        "category"
    ).order_by("-created_at")[:5]

    # ข้อมูลบัญชีและ Session เดิม
    context = {
        "user": request.user,
        "session_info": request.session.items(),

        "total_products": total_products,
        "reservable_products": reservable_products,
        "unavailable_products": unavailable_products,
        "total_stock": total_stock,
        "total_locations": total_locations,
        "recent_products": recent_products,
    }

    return render(request, "manage/dashboard.html", context)


@admin_required
def products(request):
    return render(request, "manage/products.html", {
        "user": request.user,
        "session_info": request.session.items()
    })

@manage_required
def reservations(request):
    return render(request, "manage/reservations.html", {
        "user": request.user,
        "session_info": request.session.items()
    })
