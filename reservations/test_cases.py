"""Reservation CRUD-like workflow, validation, stock, and error tests."""

from datetime import timedelta

from django.contrib.auth import get_user_model
from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from django.utils import timezone

from shop.models import Category, Location, Product, ProductLocation
from .models import Reservation
from .services import expire_overdue_reservations


class ReservationWorkflowTests(TestCase):
    """Verify public reservation creation and management state transitions."""

    def setUp(self):
        category = Category.objects.create(name="จองได้")
        self.location = Location.objects.create(name="จุดรับ", building="อาคาร 1")
        self.product = Product.objects.create(name="สินค้าให้จอง", price=100, category=category)
        self.stock = ProductLocation.objects.create(product=self.product, location=self.location, stock=5)
        self.admin = get_user_model().objects.create_user(
            username="reservation-admin", password="Strong-pass-123", role="admin"
        )

    def post_reservation(self, **overrides):
        """Submit a valid student reservation, allowing focused overrides."""
        data = {
            "customer_type": "student", "customer_id": "1234567890123",
            "quantity": "2", "location": self.stock.pk,
        }
        data.update(overrides)
        return self.client.post(reverse("reservation_create", args=[self.product.pk]), data)

    def test_create_reservation_decreases_stock_and_redirects(self):
        """TC-CREATE-004: valid reservation creates a pending record and decrements stock."""
        response = self.post_reservation()
        self.assertEqual(response.status_code, 302)
        reservation = Reservation.objects.get()
        self.assertEqual(reservation.status, Reservation.Status.PENDING)
        self.stock.refresh_from_db()
        self.assertEqual(self.stock.stock, 3)

    def test_create_reservation_expires_old_reservation_before_using_stock(self):
        """TC-TRIGGER-001: reservation create triggers expiry and restores stock first."""
        old_reservation = Reservation.objects.create(
            reservation_code="TRIGGER-CREATE-001",
            customer_id="1234567890123",
            product=self.product,
            location=self.location,
            quantity=2,
            expires_at=timezone.now() - timedelta(minutes=1),
        )
        self.stock.stock = 3
        self.stock.save(update_fields=["stock"])

        response = self.post_reservation(quantity="1")

        self.assertEqual(response.status_code, 302)
        old_reservation.refresh_from_db()
        self.stock.refresh_from_db()
        self.assertEqual(old_reservation.status, Reservation.Status.EXPIRED)
        self.assertEqual(self.stock.stock, 4)

    def test_status_page_triggers_expiry_and_restores_stock(self):
        """TC-TRIGGER-002: status lookup triggers expiry before displaying the reservation."""
        reservation = Reservation.objects.create(
            reservation_code="TRIGGER-STATUS-001",
            customer_id="1234567890123",
            product=self.product,
            location=self.location,
            quantity=2,
            expires_at=timezone.now() - timedelta(minutes=1),
        )
        self.stock.stock = 3
        self.stock.save(update_fields=["stock"])

        response = self.client.post(
            reverse("reservation_status"),
            {"reservation_code": reservation.reservation_code},
        )

        self.assertEqual(response.status_code, 200)
        reservation.refresh_from_db()
        self.stock.refresh_from_db()
        self.assertEqual(reservation.status, Reservation.Status.EXPIRED)
        self.assertEqual(self.stock.stock, 5)

    def test_reservation_list_triggers_expiry_and_restores_stock(self):
        """TC-TRIGGER-003: opening the reservation list runs expiry processing."""
        reservation = Reservation.objects.create(
            reservation_code="TRIGGER-LIST-001",
            customer_id="1234567890123",
            product=self.product,
            location=self.location,
            quantity=2,
            expires_at=timezone.now() - timedelta(minutes=1),
        )
        self.stock.stock = 3
        self.stock.save(update_fields=["stock"])
        self.client.force_login(self.admin)

        response = self.client.get(reverse("reservation_list"))

        self.assertEqual(response.status_code, 200)
        reservation.refresh_from_db()
        self.stock.refresh_from_db()
        self.assertEqual(reservation.status, Reservation.Status.EXPIRED)
        self.assertEqual(self.stock.stock, 5)

    def test_reservation_list_stays_within_query_budget(self):
        """TC-PERF-001: reservation list stays within the measured query budget."""
        for index in range(5):
            Reservation.objects.create(
                reservation_code=f"PERF-{index:03d}",
                customer_id="1234567890123",
                product=self.product,
                location=self.location,
                quantity=1,
                expires_at=timezone.now() + timedelta(hours=1),
            )
        self.client.force_login(self.admin)

        with CaptureQueriesContext(connection) as queries:
            response = self.client.get(reverse("reservation_list"))

        self.assertEqual(response.status_code, 200)
        self.assertLessEqual(
            len(queries),
            10,
            f"reservation list used {len(queries)} queries; expected <= 10",
        )

    def test_reservation_expiry_is_set_to_four_hours(self):
        """TC-BUSINESS-001: a successful reservation expires exactly four hours later."""
        before = timezone.now()
        response = self.post_reservation(quantity="1")
        after = timezone.now()
        self.assertEqual(response.status_code, 302)
        reservation = Reservation.objects.get()
        self.assertGreaterEqual(reservation.expires_at, before + timedelta(hours=4))
        self.assertLessEqual(reservation.expires_at, after + timedelta(hours=4))

    def test_quantity_above_five_is_rejected(self):
        """TC-VALIDATE-006: one reservation cannot request more than five items."""
        self.stock.stock = 10
        self.stock.save(update_fields=["stock"])
        response = self.post_reservation(quantity="6")
        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            "สามารถจองสินค้าได้ตั้งแต่ 1 ถึง 5 ชิ้นต่อรายการเท่านั้น",
        )
        self.assertFalse(Reservation.objects.exists())

    def test_quantity_cannot_exceed_available_stock(self):
        """TC-BUSINESS-002: reservation quantity cannot exceed stock at the selected location."""
        self.stock.stock = 2
        self.stock.save(update_fields=["stock"])
        response = self.post_reservation(quantity="3")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "มีเพียง 2 ชิ้น")
        self.assertFalse(Reservation.objects.exists())

    def test_non_reservable_product_cannot_be_reserved(self):
        """TC-BUSINESS-003: products marked as non-reservable reject reservation requests."""
        self.product.reservable = False
        self.product.save(update_fields=["reservable"])
        response = self.post_reservation()
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "สินค้านี้ไม่เปิดให้จอง")
        self.assertFalse(Reservation.objects.exists())

    def test_out_of_stock_product_cannot_be_reserved(self):
        """TC-BUSINESS-004: an out-of-stock product cannot create a reservation."""
        self.stock.stock = 0
        self.stock.save(update_fields=["stock"])
        response = self.post_reservation()
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "สินค้าหมด ไม่พร้อมจอง")
        self.assertFalse(Reservation.objects.exists())

    def test_invalid_customer_id_does_not_create_reservation(self):
        """TC-VALIDATE-004: student ID must contain exactly 13 digits."""
        response = self.post_reservation(customer_id="123")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "รหัสนักศึกษาเป็นตัวเลข 13 หลัก")
        self.assertFalse(Reservation.objects.exists())

    def test_invalid_quantity_does_not_create_reservation(self):
        """TC-VALIDATE-005: zero, negative, and non-numeric quantities are rejected."""
        for quantity in ("0", "-1", "abc"):
            with self.subTest(quantity=quantity):
                response = self.post_reservation(quantity=quantity)
                self.assertEqual(response.status_code, 200)
        self.assertFalse(Reservation.objects.exists())

    def test_unknown_location_returns_error_without_stock_change(self):
        """TC-ERROR-002: a location belonging to another product cannot be used."""
        response = self.post_reservation(location="999999")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "ไม่พบจุดรับสินค้าที่เลือก")
        self.stock.refresh_from_db()
        self.assertEqual(self.stock.stock, 5)

    def test_status_page_reads_existing_reservation_and_handles_unknown_code(self):
        """TC-READ-002: status lookup shows an existing record or a clear error."""
        reservation = Reservation.objects.create(
            reservation_code="READ-001", customer_id="1234567890123",
            product=self.product, location=self.location, quantity=1,
            expires_at=timezone.now() + timedelta(hours=1),
        )
        response = self.client.post(reverse("reservation_status"), {"reservation_code": reservation.reservation_code})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["reservation"].pk, reservation.pk)
        missing = self.client.post(reverse("reservation_status"), {"reservation_code": "missing"})
        self.assertContains(missing, "ไม่พบรายการจองจากรหัสที่ระบุ")

    def test_admin_reservation_list_filters_by_status(self):
        """TC-FILTER-006: admin reservation list returns only the requested status."""
        Reservation.objects.create(
            reservation_code="PENDING-FILTER", customer_id="1234567890123",
            product=self.product, location=self.location, quantity=1,
            status=Reservation.Status.PENDING,
            expires_at=timezone.now() + timedelta(hours=1),
        )
        Reservation.objects.create(
            reservation_code="CANCEL-FILTER", customer_id="1234567890123",
            product=self.product, location=self.location, quantity=1,
            status=Reservation.Status.CANCELLED,
            expires_at=timezone.now() + timedelta(hours=1),
        )
        self.client.force_login(self.admin)
        response = self.client.get(reverse("reservation_list"), {"status": "cancelled"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            [item.reservation_code for item in response.context["page_obj"]],
            ["CANCEL-FILTER"],
        )

    def test_cancel_reservation_restores_stock(self):
        """TC-UPDATE-002: cancelling a pending reservation restores reserved stock."""
        reservation = Reservation.objects.create(
            reservation_code="CANCEL-001", customer_id="1234567890123",
            product=self.product, location=self.location, quantity=2,
            expires_at=timezone.now() + timedelta(hours=1),
        )
        self.stock.stock = 3
        self.stock.save()
        self.client.force_login(self.admin)
        response = self.client.post(reverse("reservation_manage", args=[reservation.reservation_code]), {"status": "cancelled"})
        self.assertRedirects(response, reverse("reservation_manage", args=[reservation.reservation_code]))
        reservation.refresh_from_db()
        self.stock.refresh_from_db()
        self.assertEqual(reservation.status, Reservation.Status.CANCELLED)
        self.assertEqual(self.stock.stock, 5)

    def test_expired_reservation_is_marked_and_stock_is_restored_once(self):
        """TC-ERROR-003: expiry processing restores stock exactly once."""
        reservation = Reservation.objects.create(
            reservation_code="EXPIRE-001", customer_id="1234567890123",
            product=self.product, location=self.location, quantity=2,
            expires_at=timezone.now() - timedelta(minutes=1),
        )
        self.stock.stock = 3
        self.stock.save()
        self.assertEqual(expire_overdue_reservations(), 1)
        self.assertEqual(expire_overdue_reservations(), 0)
        reservation.refresh_from_db()
        self.stock.refresh_from_db()
        self.assertEqual(reservation.status, Reservation.Status.EXPIRED)
        self.assertEqual(self.stock.stock, 5)
