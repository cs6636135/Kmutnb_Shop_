import secrets
from datetime import timedelta

from django.db import transaction
from django.db.models import Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from shop.models import Product, ProductLocation
from .models import Reservation


def reservation_create(request, product_id):
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
		).select_related("location").order_by("location__name")
	)
	error = None
	customer_id = request.POST.get("customer_id", "").strip()
	quantity_value = request.POST.get("quantity", "1")
	selected_location_id = request.POST.get("location", "")
	can_reserve = product.reservable and product.stock > 0 and bool(available_locations)

	if request.method == "POST":
		if not product.reservable:
			error = "สินค้านี้ไม่เปิดให้จอง"
		elif product.stock <= 0:
			error = "สินค้าหมด ไม่พร้อมจอง"
		elif not customer_id:
			error = "กรุณากรอกรหัสนักศึกษา"
		elif len(customer_id) > 20: #6604062636127 - 13?
			error = "รหัสนักศึกษาต้องมีความยาวไม่เกิน 20 ตัวอักษร"
		elif not quantity_value.isdigit() or int(quantity_value) < 1:
			error = "กรุณาระบุจำนวนสินค้าอย่างน้อย 1 ชิ้น"
		elif not selected_location_id.isdigit():
			error = "กรุณาเลือกจุดรับสินค้า"
		else:
			quantity = int(quantity_value)
			reservation = None
			try:
				with transaction.atomic():
					product_location = ProductLocation.objects.select_for_update().select_related(
						"location"
					).get(pk=int(selected_location_id), product=product)
					if product_location.stock < quantity:
						error = (
							f"สินค้า ณ จุดรับนี้มีเพียง {product_location.stock} ชิ้น "
							"กรุณาปรับจำนวนแล้วลองอีกครั้ง"
						)
					else:
						product_location.stock -= quantity
						product_location.save(update_fields=["stock"])

						reservation_code = secrets.token_hex(12).upper()
						while Reservation.objects.filter(
							reservation_code=reservation_code
						).exists():
							reservation_code = secrets.token_hex(12).upper()

						reservation = Reservation.objects.create(
							reservation_code=reservation_code,
							customer_id=customer_id,
							product=product,
							location=product_location.location,
							quantity=quantity,
							expires_at=timezone.now() + timedelta(hours=4),
						)
			except ProductLocation.DoesNotExist:
				error = "ไม่พบจุดรับสินค้าที่เลือก กรุณาเลือกใหม่"

			if reservation is not None:
				return redirect(
					"reservation_confirmation",
					reservation_code=reservation.reservation_code,
				)

		available_locations = list(
			ProductLocation.objects.filter(
				product=product,
				stock__gt=0,
			).select_related("location").order_by("location__name")
		)
		can_reserve = product.reservable and any(
			item.stock > 0 for item in available_locations
		)

	return render(request, "reservations/create.html", {
		"product": product,
		"available_locations": available_locations,
		"can_reserve": can_reserve,
		"error": error,
		"customer_id": customer_id,
		"quantity_value": quantity_value,
		"selected_location_id": selected_location_id,
	})


def reservation_confirmation(request, reservation_code):
	reservation = get_object_or_404(
		Reservation.objects.select_related("product", "location"),
		reservation_code=reservation_code,
	)
	return render(request, "reservations/confirmation.html", {
		"reservation": reservation,
	})


def reservation_status(request):
	reservation = None
	error = None

	if request.method == "POST":
		reservation_code = request.POST.get("reservation_code", "").strip()
		if reservation_code:
			reservation = Reservation.objects.filter(
				reservation_code=reservation_code
			).select_related("product", "location").first()
			if reservation is None:
				error = "ไม่พบรายการจองจากรหัสที่ระบุ"
		else:
			error = "กรุณากรอกรหัสการจอง"

	return render(request, "reservations/status.html", {
		"reservation": reservation,
		"error": error,
	})