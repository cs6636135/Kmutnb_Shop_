from django.core.paginator import Paginator
from django.shortcuts import render, redirect
from django.utils import timezone
from django.contrib import messages
from django.db import transaction
from django.core.exceptions import ValidationError

from accounts.permission import role_required
from shop.models import ProductLocation
from .models import Reservation
from .services import expire_overdue_reservations
from .forms import StatusForm


@role_required("admin", "staff")
def reservation_list(request):
    # อัปเดตสถานะและคืน Stock เมื่อเปิดหน้ารายการจอง
    expire_overdue_reservations()

    user = request.user

    qs = Reservation.objects.select_related(
        "product", "location"
    ).order_by("-reserved_at")

    # Staff ดูได้เฉพาะสาขาที่รับผิดชอบ
    if user.role != "admin":
        qs = qs.filter(location=user.location)

    # กรองตามสถานะ
    status = request.GET.get("status", "").strip()

    if status in {choice[0] for choice in Reservation.Status.choices}:
        qs = qs.filter(status=status)

    # Pagination
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

    reservation = (
        Reservation.objects.filter(
            reservation_code=reservation_code
        )
        .select_related("product", "location")
        .first()
    )

    if reservation is None:
        messages.error(request, "ไม่พบรายการจองจากรหัสที่ระบุ")
        return redirect("reservation_list")

    # Staff จัดการได้เฉพาะรายการจองของสาขาตนเอง
    if user.role == "staff" and user.location != reservation.location:
        messages.error(
            request,
            "ไม่มีสิทธิ์จัดการรายการจองนี้ "
            "(คุณไม่ได้ประจำจุดจำหน่ายนี้)"
        )
        return redirect("reservation_list")

    if request.method == "POST":
        old_status = reservation.status
        form = StatusForm(request.POST, instance=reservation)

        if form.is_valid():
            try:
                with transaction.atomic():
                    # ดึงสถานะใหม่จากฟอร์ม
                    new_status = form.cleaned_data["status"]

                    if old_status != new_status:
                        now = timezone.now()

                        if new_status == Reservation.Status.PICKED_UP:
                            reservation.picked_up_at = now

                        elif new_status == Reservation.Status.CANCELLED:
                            reservation.cancelled_at = now

                        # คืน Stock เมื่อเปลี่ยนจากรอรับสินค้า
                        # เป็นยกเลิกหรือหมดอายุ
                        if (
                            old_status == Reservation.Status.PENDING
                            and new_status in (
                                Reservation.Status.CANCELLED,
                                Reservation.Status.EXPIRED,
                            )
                        ):
                            pl = ProductLocation.objects.select_for_update().filter(
                                product=reservation.product,
                                location=reservation.location,
                            ).first()

                            if pl:
                                pl.stock += reservation.quantity
                                pl.save(update_fields=["stock"])

                        # ตัด Stock เมื่อเปลี่ยนจากยกเลิกหรือหมดอายุ
                        # กลับเป็นรอรับสินค้าหรือรับสินค้าแล้ว
                        elif (
                            old_status in (
                                Reservation.Status.CANCELLED,
                                Reservation.Status.EXPIRED,
                            )
                            and new_status in (
                                Reservation.Status.PENDING,
                                Reservation.Status.PICKED_UP,
                            )
                        ):
                            pl = ProductLocation.objects.select_for_update().filter(
                                product=reservation.product,
                                location=reservation.location,
                            ).first()

                            if pl:
                                if pl.stock < reservation.quantity:
                                    raise ValidationError(
                                        "สต็อกสินค้าไม่เพียงพอ "
                                        f"(คงเหลือ {pl.stock} ชิ้น)"
                                    )

                                pl.stock -= reservation.quantity
                                pl.save(update_fields=["stock"])

                        # บันทึกสถานะการจอง
                        reservation.status = new_status
                        reservation.save()

                # บันทึกสำเร็จแล้ว กลับไปหน้ารายการจอง
                messages.success(
                    request,
                    f"อัปเดตสถานะการจอง "
                    f"{reservation.reservation_code} เรียบร้อยแล้ว"
                )

                return redirect("reservation_list")

            except ValidationError as e:
                form.add_error(None, e)

            except Exception:
                form.add_error(
                    None,
                    "เกิดข้อผิดพลาดในการบันทึก กรุณาลองใหม่อีกครั้ง"
                )

    else:
        form = StatusForm(instance=reservation)

    return render(request, "manage/reservations_manage.html", {
        "reservation": reservation,
        "form": form,
        "error": None,
    })
