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
        """TC-FR-10-01: successful reservation creates a code and updates stock."""
        response = self.post_reservation()
        self.assertEqual(response.status_code, 302)
        reservation = Reservation.objects.get()
        self.assertEqual(reservation.status, Reservation.Status.PENDING)
        self.assertTrue(reservation.reservation_code)
        self.assertEqual(len(reservation.reservation_code), 24)
        self.assertEqual(response.url, reverse(
            "reservation_confirmation",
            args=[reservation.reservation_code],
        ))
        self.stock.refresh_from_db()
        self.assertEqual(self.stock.stock, 3)
        confirmation = self.client.get(response.url)
        self.assertEqual(confirmation.status_code, 200)
        self.assertContains(confirmation, "จองสินค้าสำเร็จ")
        self.assertContains(confirmation, reservation.reservation_code)

    def test_one_reservation_request_creates_one_record_and_one_stock_change(self):
        """TC-FR-38-01: one reservation request creates one record and one stock change."""
        response = self.post_reservation(quantity="1")
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Reservation.objects.count(), 1)
        self.stock.refresh_from_db()
        self.assertEqual(self.stock.stock, 4)

    def test_create_reservation_expires_old_reservation_before_using_stock(self):
        """TC-FR-14-02: a new reservation restores expired stock before reserving."""
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
        """TC-FR-14-03: status lookup expires old reservations and restores stock."""
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
        """TC-FR-14-04: opening reservation list expires old reservations."""
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
        """TC-ADD-PERF-01: reservation list stays within the query budget."""
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
        """TC-FR-39-01: reservation and expiration timestamps are recorded four hours apart."""
        before = timezone.now()
        response = self.post_reservation(quantity="1")
        after = timezone.now()
        self.assertEqual(response.status_code, 302)
        reservation = Reservation.objects.get()
        self.assertGreaterEqual(reservation.reserved_at, before)
        self.assertLessEqual(reservation.reserved_at, after)
        self.assertGreaterEqual(reservation.expires_at, before + timedelta(hours=4))
        self.assertLessEqual(reservation.expires_at, after + timedelta(hours=4))
        self.assertLessEqual(
            abs((reservation.expires_at - reservation.reserved_at) - timedelta(hours=4)),
            timedelta(seconds=1),
        )

    def test_quantity_above_five_is_rejected(self):
        """TC-FR-09-01: a reservation cannot request more than five items."""
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
        """TC-FR-41-02: failed reservation reports insufficient stock without saving."""
        self.stock.stock = 2
        self.stock.save(update_fields=["stock"])
        response = self.post_reservation(quantity="3")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "มีเพียง 2 ชิ้น")
        self.assertFalse(Reservation.objects.exists())
        self.stock.refresh_from_db()
        self.assertEqual(self.stock.stock, 2)

    def test_non_reservable_product_cannot_be_reserved(self):
        """TC-FR-07-02: products marked as non-reservable reject reservation requests."""
        self.product.reservable = False
        self.product.save(update_fields=["reservable"])
        response = self.post_reservation()
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "สินค้านี้ไม่เปิดให้จอง")
        self.assertFalse(Reservation.objects.exists())

    def test_out_of_stock_product_cannot_be_reserved(self):
        """TC-FR-35-01: an out-of-stock product cannot be reserved."""
        self.stock.stock = 0
        self.stock.save(update_fields=["stock"])
        response = self.post_reservation()
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "สินค้าหมด ไม่พร้อมจอง")
        self.assertFalse(Reservation.objects.exists())

    def test_invalid_customer_id_does_not_create_reservation(self):
        """TC-NFR-03-03: student ID and phone number formats are checked."""
        response = self.post_reservation(customer_id="123")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "รหัสนักศึกษาเป็นตัวเลข 13 หลัก")
        self.assertFalse(Reservation.objects.exists())
        phone_response = self.post_reservation(
            customer_type="external",
            customer_phone="123",
        )
        self.assertEqual(phone_response.status_code, 200)
        self.assertContains(phone_response, "เบอร์โทรศัพท์เป็นตัวเลข 10 หลัก")
        self.assertFalse(Reservation.objects.exists())

    def test_invalid_quantity_does_not_create_reservation(self):
        """TC-NFR-03-04: invalid reservation quantities are rejected."""
        for quantity in ("0", "-1", "abc"):
            with self.subTest(quantity=quantity):
                response = self.post_reservation(quantity=quantity)
                self.assertEqual(response.status_code, 200)
        self.assertFalse(Reservation.objects.exists())

    def test_unknown_location_returns_error_without_stock_change(self):
        """TC-NFR-03-05: an unknown pickup location is rejected without stock changes."""
        response = self.post_reservation(location="999999")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "ไม่พบจุดรับสินค้าที่เลือก")
        self.stock.refresh_from_db()
        self.assertEqual(self.stock.stock, 5)

    def test_status_page_reads_existing_reservation_and_handles_unknown_code(self):
        """TC-FR-12-01: status lookup shows a reservation or a clear not-found error."""
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
        """TC-FR-22-01: admin can filter the reservation list by status."""
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
        """TC-FR-23-01: admin can cancel a pending reservation under valid conditions."""
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
        self.assertIsNotNone(reservation.cancelled_at)

    def test_admin_can_view_reservations_from_all_locations(self):
        """TC-FR-22-02: admin sees reservations from every selling location."""
        other_location = Location.objects.create(name="จุดจำหน่ายอีกแห่ง", building="อาคาร 2")
        first = Reservation.objects.create(
            reservation_code="ADMIN-LOCATION-001",
            customer_id="1234567890123",
            product=self.product,
            location=self.location,
            quantity=1,
            expires_at=timezone.now() + timedelta(hours=1),
        )
        second = Reservation.objects.create(
            reservation_code="ADMIN-LOCATION-002",
            customer_id="1234567890123",
            product=self.product,
            location=other_location,
            quantity=1,
            expires_at=timezone.now() + timedelta(hours=1),
        )
        self.client.force_login(self.admin)

        response = self.client.get(reverse("reservation_list"))

        self.assertEqual(response.status_code, 200)
        self.assertCountEqual(list(response.context["page_obj"]), [first, second])

    def test_staff_can_view_only_reservations_at_assigned_location(self):
        """TC-FR-29-01: staff sees reservations only at the assigned location."""
        other_location = Location.objects.create(name="จุดอื่น", building="อาคาร 2")
        own = Reservation.objects.create(
            reservation_code="STAFF-OWN-001", customer_id="1234567890123",
            product=self.product, location=self.location, quantity=1,
            expires_at=timezone.now() + timedelta(hours=1),
        )
        Reservation.objects.create(
            reservation_code="STAFF-OTHER-001", customer_id="1234567890123",
            product=self.product, location=other_location, quantity=1,
            expires_at=timezone.now() + timedelta(hours=1),
        )
        staff = get_user_model().objects.create_user(
            username="reservation-staff", password="Strong-pass-123",
            role="staff", location=self.location,
        )
        self.client.force_login(staff)
        response = self.client.get(reverse("reservation_list"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(list(response.context["page_obj"]), [own])

    def test_staff_can_change_status_at_assigned_location(self):
        """TC-FR-30-01: staff can mark an assigned-location reservation as picked up."""
        self.stock.stock = 4
        self.stock.save(update_fields=["stock"])
        reservation = Reservation.objects.create(
            reservation_code="STAFF-PICKUP-001", customer_id="1234567890123",
            product=self.product, location=self.location, quantity=1,
            expires_at=timezone.now() + timedelta(hours=1),
        )
        staff = get_user_model().objects.create_user(
            username="reservation-staff-pickup", password="Strong-pass-123",
            role="staff", location=self.location,
        )
        self.client.force_login(staff)
        response = self.client.post(
            reverse("reservation_manage", args=[reservation.reservation_code]),
            {"status": Reservation.Status.PICKED_UP},
        )
        self.assertRedirects(
            response,
            reverse("reservation_manage", args=[reservation.reservation_code]),
        )
        reservation.refresh_from_db()
        self.stock.refresh_from_db()
        self.assertEqual(reservation.status, Reservation.Status.PICKED_UP)
        self.assertIsNotNone(reservation.picked_up_at)
        self.assertEqual(self.stock.stock, 4)

    def test_staff_cannot_view_or_change_reservation_at_other_location(self):
        """TC-FR-40-01: staff cannot view or change another location's reservation."""
        other_location = Location.objects.create(name="จุดต้องห้าม", building="อาคาร 3")
        reservation = Reservation.objects.create(
            reservation_code="STAFF-FORBIDDEN-001", customer_id="1234567890123",
            product=self.product, location=other_location, quantity=1,
            expires_at=timezone.now() + timedelta(hours=1),
        )
        staff = get_user_model().objects.create_user(
            username="reservation-staff-limited", password="Strong-pass-123",
            role="staff", location=self.location,
        )
        self.client.force_login(staff)
        list_response = self.client.get(reverse("reservation_list"))
        self.assertNotIn(reservation.reservation_code, list_response.content.decode())
        manage_response = self.client.get(
            reverse("reservation_manage", args=[reservation.reservation_code])
        )
        self.assertContains(manage_response, "ไม่มีสิทธิ์จัดการรายการจองนี้")
        self.client.post(
            reverse("reservation_manage", args=[reservation.reservation_code]),
            {"status": Reservation.Status.CANCELLED},
        )
        reservation.refresh_from_db()
        self.assertEqual(reservation.status, Reservation.Status.PENDING)

    def test_confirmation_shows_customer_identifier_as_entered(self):
        """TC-NFR-09-01: confirmation shows the identifier entered for the reservation."""
        customer_id = "1234567890123"
        response = self.post_reservation(customer_id=customer_id)
        self.assertEqual(response.status_code, 302)

        confirmation = self.client.get(response.url)

        self.assertEqual(confirmation.status_code, 200)
        self.assertContains(confirmation, customer_id)

    def test_expired_reservation_is_marked_and_stock_is_restored_once(self):
        """TC-FR-14-01: expired reservation status and stock are updated only once."""
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
