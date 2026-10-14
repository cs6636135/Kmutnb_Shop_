import re
import secrets
from datetime import timedelta

from django.db import transaction
from django.db.models import Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from shop.models import Product, ProductLocation
from .models import Reservation
from .services import expire_overdue_reservations
from django.db.models import Q 

def reservation_create(request, product_id):
    # คืนสต็อกจากรายการจองที่หมดอายุก่อนตรวจสอบสต็อก
    expire_overdue_reservations(product_id=product_id)

    product = get_object_or_404(
        Product.objects.annotate(
            stock=Sum("productlocation__stock", default=0)
        ),
        pk=product_id,
    )

    available_locations = list(
        ProductLocation.objects.filter(
            product=product,
            stock__gt=0,
        )
        .select_related("location")
        .order_by("location__name")
    )

    error = None

    customer_type = request.POST.get(
        "customer_type", "student"
    ).strip()

    student_id = request.POST.get(
        "customer_id", ""
    ).strip()

    customer_phone = request.POST.get(
        "customer_phone", ""
    ).strip()

    customer_id = (
        student_id
        if customer_type == "student"
        else customer_phone
    )

    quantity_value = request.POST.get(
        "quantity", "1"
    ).strip()

    selected_location_id = request.POST.get(
        "location", ""
    ).strip()

    can_reserve = (
        product.reservable
        and product.stock > 0
        and bool(available_locations)
    )

    if request.method == "POST":

        # ตรวจสอบว่าสินค้าเปิดให้จองหรือไม่
        if not product.reservable:
            error = "สินค้านี้ไม่เปิดให้จอง"

        # ตรวจสอบสต็อกรวม
        elif product.stock <= 0:
            error = "สินค้าหมด ไม่พร้อมจอง"

        # ตรวจสอบประเภทผู้จอง
        elif customer_type not in {"student", "external"}:
            error = "กรุณาเลือกประเภทผู้จอง"

        # ตรวจสอบรหัสนักศึกษา 13 หลัก
        elif (
            customer_type == "student"
            and not re.fullmatch(r"[0-9]{13}", student_id)
        ):
            error = "กรุณากรอกรหัสนักศึกษาเป็นตัวเลข 13 หลัก"

        # ตรวจสอบเบอร์โทรศัพท์ 10 หลัก
        elif (
            customer_type == "external"
            and not re.fullmatch(r"[0-9]{10}", customer_phone)
        ):
            error = "กรุณากรอกเบอร์โทรศัพท์เป็นตัวเลข 10 หลัก"

        # จำนวนที่จองต้องเป็นจำนวนเต็มตั้งแต่ 1 ถึง 5 ชิ้น
        elif (
            not quantity_value.isascii()
            or not quantity_value.isdigit()
            or not 1 <= int(quantity_value) <= 5
        ):
            error = (
                "สามารถจองสินค้าได้ตั้งแต่ 1 ถึง 5 ชิ้นต่อรายการเท่านั้น"
            )

        # ตรวจสอบจุดรับสินค้า
        elif (
            not selected_location_id.isascii()
            or not selected_location_id.isdigit()
        ):
            error = "กรุณาเลือกจุดรับสินค้า"

        else:
            quantity = int(quantity_value)
            reservation = None

            try:
                with transaction.atomic():
                    # ล็อกแถวสต็อกเพื่อป้องกันการจองพร้อมกัน
                    product_location = (
                        ProductLocation.objects
                        .select_for_update()
                        .select_related("location")
                        .get(
                            pk=int(selected_location_id),
                            product=product,
                        )
                    )

                    # ตรวจสอบสต็อก ณ จุดรับที่เลือก
                    if product_location.stock <= 0:
                        error = "สินค้าหมด ณ จุดรับที่เลือก"

                    elif quantity > product_location.stock:
                        error = (
                            f"สินค้า ณ จุดรับนี้มีเพียง "
                            f"{product_location.stock} ชิ้น "
                            "กรุณาปรับจำนวนแล้วลองอีกครั้ง"
                        )

                    else:
                        # ตัดสต็อกเมื่อจองสำเร็จ
                        product_location.stock -= quantity
                        product_location.save(
                            update_fields=["stock"]
                        )

                        # สร้างรหัสจองที่ไม่ซ้ำกัน
                        reservation_code = secrets.token_hex(12).upper()

                        while Reservation.objects.filter(
                            reservation_code=reservation_code
                        ).exists():
                            reservation_code = (
                                secrets.token_hex(12).upper()
                            )

                        # สร้างรายการจองและกำหนดเวลาหมดอายุ 4 ชั่วโมง
                        reservation = Reservation.objects.create(
                            reservation_code=reservation_code,
                            customer_id=customer_id,
                            product=product,
                            location=product_location.location,
                            quantity=quantity,
                            expires_at=(
                                timezone.now() + timedelta(hours=4)
                            ),
                        )

            except ProductLocation.DoesNotExist:
                error = (
                    "ไม่พบจุดรับสินค้าที่เลือก กรุณาเลือกใหม่"
                )

            # หากจองสำเร็จ ไปยังหน้ายืนยันการจอง
            if reservation is not None:
                return redirect(
                    "reservation_confirmation",
                    reservation_code=reservation.reservation_code,
                )

        # โหลดสต็อกและจุดรับสินค้าใหม่หลังตรวจสอบ
        available_locations = list(
            ProductLocation.objects.filter(
                product=product,
                stock__gt=0,
            )
            .select_related("location")
            .order_by("location__name")
        )

        can_reserve = (
            product.reservable
            and any(
                item.stock > 0
                for item in available_locations
            )
        )

    return render(
        request,
        "reservations/create.html",
        {
            "product": product,
            "available_locations": available_locations,
            "can_reserve": can_reserve,
            "error": error,
            "customer_type": customer_type,
            "customer_id": customer_id,
            "student_id": student_id,
            "customer_phone": customer_phone,
            "quantity_value": quantity_value,
            "selected_location_id": selected_location_id,
        },
    )


def reservation_confirmation(request, reservation_code):
	reservation = get_object_or_404(
		Reservation.objects.select_related("product", "location"),
		reservation_code=reservation_code,
	)

	reservation.refresh_from_db()
	return render(request, "reservations/confirmation.html", {
		"reservation": reservation,
	})



def reservation_status(request):
    reservations = None
    error = None

    if request.method == "POST":
        customer_id = request.POST.get("reservation_code", "").strip()

        if not customer_id:
            error = "กรุณากรอกรหัสลูกค้าของคุณ"
        else:
            query = Q(reservation_code=customer_id) | Q(customer_id=customer_id)

            reservations = Reservation.objects.filter(query).select_related(
                "product", "location"
            ).order_by("-reserved_at")

            if not reservations.exists():
                error = "ไม่พบรายการจองจากรหัสลูกค้าที่ระบุ"
                reservations = None
            else:
                # อัปเดตสถานะรายการจองที่หมดอายุ
                for reservation in reservations:
                    expire_overdue_reservations(
                      product_id=reservation.product_id
                    )

                # โหลดข้อมูลใหม่หลังอัปเดตสถานะ
                reservations = Reservation.objects.filter(query).select_related(
                    "product", "location"
                ).order_by("-reserved_at")


    return render(request, "reservations/status.html", {
        "reservations": reservations,
        "error": error,
    })
