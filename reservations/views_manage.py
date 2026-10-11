from django.core.paginator import Paginator
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.contrib import messages
from django.db import transaction
from django.core.exceptions import ValidationError

from accounts.permission import role_required
from shop.models import ProductLocation
from .models import Reservation
from .services import expire_overdue_reservations
from .forms import StatusForm

# ทำเพื่อให้แสดงผลได้ก่อน แต่แก้ไขได้ ทำลวกๆมาก่อนเฉยๆ

@role_required("admin", "staff")
def reservation_list(request):
    # อัปเดตสถานะและคืนสต็อกเมื่อมีผู้เปิดหน้ารายการจอง trigger
    expire_overdue_reservations()

    user = request.user
    qs = Reservation.objects.select_related("product", "location").order_by("-reserved_at")

    if user.role != "admin":
        qs = qs.filter(location=user.location)

    status = request.GET.get("status", "").strip()
    if status in {choice[0] for choice in Reservation.Status.choices}:
        qs = qs.filter(status=status)

    paginator = Paginator(qs, 15)
    page_obj = paginator.get_page(request.GET.get("page"))

    return render(request, "manage/reservations.html", {
        "page_obj": page_obj,
        "status": status,
        "user": user,
        "selected_location": user.location,
        "now": timezone.now(),
        "reservation_status_choices": Reservation.Status.choices,
    })

@role_required("admin", "staff")
def reservation_manage(request, reservation_code):
    user = request.user
    reservation = Reservation.objects.filter(
        reservation_code=reservation_code
    ).select_related("product", "location").first()

    if reservation is None:
        return render(request, "manage/reservations_manage.html", {
            "reservation": None,
            "error": "ไม่พบรายการจองจากรหัสที่ระบุ",
        })

    if user.role == "staff" and user.location != reservation.location:
        return render(request, "manage/reservations_manage.html", {
            "reservation": reservation,
            "error": "ไม่มีสิทธิ์จัดการรายการจองนี้ (คุณไม่ได้ประจำจุดจำหน่ายนี้)",
        })

    if request.method == "POST":
        old_status = reservation.status
        form = StatusForm(request.POST, instance=reservation)
        if form.is_valid():
            try:
                with transaction.atomic():
                    new_status = form.cleaned_data["status"]

                    if old_status != new_status:
                        now = timezone.now()
                        if new_status == Reservation.Status.PICKED_UP:
                            reservation.picked_up_at = now
                        elif new_status == Reservation.Status.CANCELLED:
                            reservation.cancelled_at = now

                        # คืนสต็อกหากยกเลิก หรือหมดอายุจากสถานะรอรับสินค้า
                        if old_status == Reservation.Status.PENDING and new_status in (
                            Reservation.Status.CANCELLED,
                            Reservation.Status.EXPIRED,
                        ):
                            pl = ProductLocation.objects.select_for_update().filter(
                                product=reservation.product, location=reservation.location
                            ).first()
                            if pl:
                                pl.stock += reservation.quantity
                                pl.save(update_fields=["stock"])

                        # หากเปลี่ยนจากยกเลิก/หมดอายุกลับมารอรับสินค้าหรือรับแล้ว ให้ตัดสต็อกคืน
                        elif old_status in (
                            Reservation.Status.CANCELLED,
                            Reservation.Status.EXPIRED,
                        ) and new_status in (
                            Reservation.Status.PENDING,
                            Reservation.Status.PICKED_UP,
                        ):
                            pl = ProductLocation.objects.select_for_update().filter(
                                product=reservation.product, location=reservation.location
                            ).first()
                            if pl:
                                if pl.stock < reservation.quantity:
                                    raise ValidationError(
                                        f"สต็อกสินค้าไม่เพียงพอสำหรับคืนสถานะ (คงเหลือ ณ จุดจำหน่าย {pl.stock} ชิ้น)"
                                    )
                                pl.stock -= reservation.quantity
                                pl.save(update_fields=["stock"])

                        reservation.status = new_status
                        reservation.save()

                messages.success(request, f"อัปเดตสถานะการจอง {reservation.reservation_code} เรียบร้อยแล้ว")
                return redirect("reservation_manage", reservation_code=reservation.reservation_code)
            except ValidationError as e:
                form.add_error(None, e)
            except Exception as e:
                form.add_error(None, f"เกิดข้อผิดพลาดในการบันทึก: {e}")
    else:
        form = StatusForm(instance=reservation)

    return render(request, "manage/reservations_manage.html", {
        "reservation": reservation,
        "form": form,
        "error": None,
    })
