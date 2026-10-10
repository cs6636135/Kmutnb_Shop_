from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse


class StaffPageTest(TestCase):
    def test_admin_can_open_staff_page(self):
        admin = get_user_model().objects.create_user(
            username="staff-page-admin",
            password="test-password",
            role="admin",
        )
        self.client.force_login(admin)

        response = self.client.get(reverse("staffs"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "ยังไม่มีเครื่องมือจัดการบัญชี")

    def test_staff_cannot_open_staff_page(self):
        staff = get_user_model().objects.create_user(
            username="staff-page-user",
            password="test-password",
            role="staff",
        )
        self.client.force_login(staff)

        response = self.client.get(reverse("staffs"))

        self.assertRedirects(response, reverse("dashboard"))

    def test_anonymous_user_is_redirected_to_login(self):
        response = self.client.get(reverse("staffs"))

        self.assertRedirects(response, reverse("login"))
