from datetime import timedelta
from statistics import median
from time import perf_counter
from unittest.mock import patch

from django.db import connection
from django.test import TestCase, tag
from django.test.utils import CaptureQueriesContext
from django.utils import timezone
from django.urls import reverse

from shop.models import Category, Location, Product, ProductLocation
from .models import Reservation
from .services import expire_overdue_reservations


class ExpireOverdueReservationsTest(TestCase):
    def setUp(self):
        self.category = Category.objects.create(name="Test category")
        self.location = Location.objects.create(
            name="Test location",
            building="Test building",
        )
        self.product = Product.objects.create(
            name="Test product",
            price="10.00",
            category=self.category,
        )
        self.product_location = ProductLocation.objects.create(
            product=self.product,
            location=self.location,
            stock=5,
        )

    def create_reservation(self, *, code, quantity=2, status=Reservation.Status.PENDING,
                           expires_at=None, product=None):
        return Reservation.objects.create(
            reservation_code=code,
            customer_id="1234567890123",
            product=product or self.product,
            location=self.location,
            quantity=quantity,
            status=status,
            expires_at=expires_at or timezone.now() - timedelta(minutes=1),
        )

    def test_expires_overdue_reservation_and_restores_stock(self):
        reservation = self.create_reservation(code="OVERDUE")

        expired_count = expire_overdue_reservations()

        reservation.refresh_from_db()
        self.product_location.refresh_from_db()
        self.assertEqual(expired_count, 1)
        self.assertEqual(reservation.status, Reservation.Status.EXPIRED)
        self.assertEqual(self.product_location.stock, 7)

    def test_does_not_change_unexpired_or_non_pending_reservations(self):
        unexpired = self.create_reservation(
            code="UNEXPIRED",
            expires_at=timezone.now() + timedelta(minutes=30),
        )
        cancelled = self.create_reservation(
            code="CANCELLED",
            status=Reservation.Status.CANCELLED,
        )

        expired_count = expire_overdue_reservations()

        unexpired.refresh_from_db()
        cancelled.refresh_from_db()
        self.product_location.refresh_from_db()
        self.assertEqual(expired_count, 0)
        self.assertEqual(unexpired.status, Reservation.Status.PENDING)
        self.assertEqual(cancelled.status, Reservation.Status.CANCELLED)
        self.assertEqual(self.product_location.stock, 5)

    def test_product_id_only_expires_reservations_for_that_product(self):
        other_product = Product.objects.create(
            name="Other test product",
            price="10.00",
            category=self.category,
        )
        other_product_location = ProductLocation.objects.create(
            product=other_product,
            location=self.location,
            stock=5,
        )
        self.create_reservation(code="FIRST")
        other_reservation = self.create_reservation(
            code="SECOND",
            product=other_product,
        )

        expired_count = expire_overdue_reservations(product_id=self.product.pk)

        other_reservation.refresh_from_db()
        self.product_location.refresh_from_db()
        other_product_location.refresh_from_db()
        self.assertEqual(expired_count, 1)
        self.assertEqual(other_reservation.status, Reservation.Status.PENDING)
        self.assertEqual(self.product_location.stock, 7)
        self.assertEqual(other_product_location.stock, 5)

    def test_repeated_call_does_not_restore_stock_twice(self):
        self.create_reservation(code="ONLY-ONCE")

        first_count = expire_overdue_reservations()
        second_count = expire_overdue_reservations()

        self.product_location.refresh_from_db()
        self.assertEqual(first_count, 1)
        self.assertEqual(second_count, 0)
        self.assertEqual(self.product_location.stock, 7)


@tag("performance")
class ReservationExpiryPerformanceTest(TestCase):
    def setUp(self):
        category = Category.objects.create(name="Performance category")
        location = Location.objects.create(
            name="Performance location",
            building="Performance building",
        )
        product = Product.objects.create(
            name="Performance product",
            price="10.00",
            category=category,
        )
        ProductLocation.objects.create(
            product=product,
            location=location,
            stock=5,
        )
        Reservation.objects.create(
            reservation_code="PERFORMANCE",
            customer_id="1234567890123",
            product=product,
            location=location,
            quantity=1,
            expires_at=timezone.now() + timedelta(hours=1),
        )

    def test_status_page_performance_with_and_without_expiry_trigger(self):
        url = reverse("reservation_status")
        request_data = {"reservation_code": "PERFORMANCE"}
        requests_per_batch = 10
        batch_count = 6
        timings = {"with trigger": [], "without trigger": []}
        query_counts = {"with trigger": [], "without trigger": []}

        def run_batch(use_trigger):
            label = "with trigger" if use_trigger else "without trigger"
            trigger_patch = (
                patch("reservations.views_public.expire_overdue_reservations")
                if not use_trigger
                else None
            )
            if trigger_patch:
                trigger_patch.start()

            try:
                with CaptureQueriesContext(connection) as queries:
                    started_at = perf_counter()
                    for _ in range(requests_per_batch):
                        response = self.client.post(url, request_data)
                        self.assertEqual(response.status_code, 200)
                    elapsed = perf_counter() - started_at
            finally:
                if trigger_patch:
                    trigger_patch.stop()

            timings[label].append(elapsed / requests_per_batch)
            query_counts[label].append(len(queries) / requests_per_batch)

        for batch in range(batch_count):
            if batch % 2 == 0:
                run_batch(use_trigger=True)
                run_batch(use_trigger=False)
            else:
                run_batch(use_trigger=False)
                run_batch(use_trigger=True)

        with_trigger = median(timings["with trigger"])
        without_trigger = median(timings["without trigger"])
        overhead_ms = (with_trigger - without_trigger) * 1000
        overhead_percent = (
            (with_trigger / without_trigger - 1) * 100
            if without_trigger
            else 0
        )

        print(
            "\nReservation status page performance "
            f"({requests_per_batch * batch_count} requests per case):\n"
            f"  With expiry trigger:    {with_trigger * 1000:.3f} ms/request, "
            f"{median(query_counts['with trigger']):.1f} DB queries/request\n"
            f"  Without expiry trigger: {without_trigger * 1000:.3f} ms/request, "
            f"{median(query_counts['without trigger']):.1f} DB queries/request\n"
            f"  Trigger overhead:       {overhead_ms:+.3f} ms/request "
            f"({overhead_percent:+.1f}%)"
        )
