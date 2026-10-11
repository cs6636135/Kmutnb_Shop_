from django.contrib.auth import get_user_model
from django.contrib.auth import SESSION_KEY
from django.test import TestCase
from django.urls import reverse


class AuthenticationTest(TestCase):
    def setUp(self):
        self.admin = get_user_model().objects.create_user(
            username="auth-admin",
            password="test-password",
            role="admin",
        )
        self.staff = get_user_model().objects.create_user(
            username="auth-staff",
            password="test-password",
            role="staff",
        )

    def test_login_page_is_available(self):
        response = self.client.get(reverse("login"))

        self.assertEqual(response.status_code, 200)

    def test_admin_can_log_in(self):
        response = self.client.post(reverse("login"), {
            "username": self.admin.username,
            "password": "test-password",
        })

        self.assertRedirects(response, reverse("dashboard"))
        self.assertEqual(
            str(self.client.session[SESSION_KEY]),
            str(self.admin.pk),
        )

    def test_staff_can_log_in(self):
        response = self.client.post(reverse("login"), {
            "username": self.staff.username,
            "password": "test-password",
        })

        self.assertRedirects(response, reverse("dashboard"))
        self.assertEqual(
            str(self.client.session[SESSION_KEY]),
            str(self.staff.pk),
        )

    def test_invalid_credentials_do_not_log_in(self):
        response = self.client.post(reverse("login"), {
            "username": self.admin.username,
            "password": "wrong-password",
        })

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Username หรือ Password ไม่ถูกต้อง")
        self.assertNotIn(SESSION_KEY, self.client.session)

    def test_logout_clears_authenticated_session(self):
        self.client.force_login(self.admin)

        response = self.client.post(reverse("logout"))

        self.assertRedirects(response, reverse("login"))
        self.assertNotIn(SESSION_KEY, self.client.session)


class RolePermissionTest(TestCase):
    def setUp(self):
        self.admin = get_user_model().objects.create_user(
            username="permission-admin",
            password="test-password",
            role="admin",
        )
        self.staff = get_user_model().objects.create_user(
            username="permission-staff",
            password="test-password",
            role="staff",
        )
        self.other_role = get_user_model().objects.create_user(
            username="permission-other",
            password="test-password",
            role="customer",
        )

    def test_only_admin_can_open_staff_management(self):
        self.client.force_login(self.admin)
        admin_response = self.client.get(reverse("staffs"))
        self.assertEqual(admin_response.status_code, 200)

        self.client.force_login(self.staff)
        staff_response = self.client.get(reverse("staffs"))
        self.assertRedirects(staff_response, reverse("dashboard"))

        self.client.force_login(self.other_role)
        other_role_response = self.client.get(reverse("staffs"))
        self.assertRedirects(
            other_role_response,
            reverse("dashboard"),
            fetch_redirect_response=False,
        )

    def test_admin_and_staff_can_open_shared_management_pages(self):
        shared_pages = (
            reverse("dashboard"),
            reverse("reservation_list"),
        )
        for user in (self.admin, self.staff):
            self.client.force_login(user)
            for url in shared_pages:
                with self.subTest(role=user.role, url=url):
                    response = self.client.get(url)
                    self.assertEqual(response.status_code, 200)

    def test_anonymous_user_is_redirected_to_login_for_protected_page(self):
        response = self.client.get(reverse("staffs"))

        self.assertRedirects(response, reverse("login"))
        self.assertIn("กรุณาเข้าสู่ระบบ", [
            str(message) for message in response.wsgi_request._messages
        ])
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
