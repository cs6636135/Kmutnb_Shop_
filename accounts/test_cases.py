"""Authentication, authorization, and staff account tests."""

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from shop.models import Location


class AuthenticationAuthorizationTests(TestCase):
    """Verify login/logout and role-based access control."""

    def setUp(self):
        self.admin = get_user_model().objects.create_user(
            username="admin", password="Strong-pass-123", role="admin"
        )
        self.staff = get_user_model().objects.create_user(
            username="staff", password="Strong-pass-123", role="staff"
        )

    def test_login_with_valid_credentials_redirects_to_dashboard(self):
        """TC-FR-15-01: admin credentials open the management dashboard."""
        response = self.client.post(reverse("login"), {"username": "admin", "password": "Strong-pass-123"})
        self.assertRedirects(response, reverse("dashboard"))
        self.assertTrue(response.wsgi_request.user.is_authenticated)

    def test_login_with_invalid_credentials_shows_error(self):
        """TC-NFR-01-02: invalid admin credentials do not create a session."""
        response = self.client.post(reverse("login"), {"username": "admin", "password": "wrong"})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Username หรือ Password ไม่ถูกต้อง")
        self.assertFalse(response.wsgi_request.user.is_authenticated)

    def test_logout_clears_authenticated_session(self):
        """TC-FR-15-02: admin can end the authenticated session."""
        self.client.force_login(self.admin)
        response = self.client.get(reverse("logout"))
        self.assertRedirects(response, reverse("login"))
        self.assertFalse(response.wsgi_request.user.is_authenticated)

    def test_anonymous_user_is_redirected_from_protected_page(self):
        """TC-FR-24-01: anonymous users cannot access management functions."""
        response = self.client.get(reverse("staffs"))
        self.assertRedirects(response, reverse("login"))

    def test_staff_cannot_access_admin_only_page(self):
        """TC-FR-24-02: staff users cannot access admin-only account management."""
        self.client.force_login(self.staff)
        response = self.client.get(reverse("staffs"))
        self.assertRedirects(response, reverse("dashboard"))

    def test_staff_can_access_shared_dashboard(self):
        """TC-NFR-12-01: authenticated staff role can access its dashboard."""
        self.client.force_login(self.staff)
        response = self.client.get(reverse("dashboard"))
        self.assertEqual(response.status_code, 200)

    def test_staff_can_login_with_valid_credentials(self):
        """TC-FR-27-01: staff can log in and reach the management dashboard."""
        response = self.client.post(reverse("login"), {
            "username": "staff", "password": "Strong-pass-123",
        })
        self.assertRedirects(response, reverse("dashboard"))
        self.assertTrue(response.wsgi_request.user.is_authenticated)
        self.assertEqual(response.wsgi_request.user.role, "staff")

    def test_admin_can_create_staff_with_location(self):
        """TC-FR-26-01: admin creates a staff account assigned to a location."""
        location = Location.objects.create(name="จุด staff", building="อาคาร 1")
        self.client.force_login(self.admin)
        response = self.client.post(reverse("staffs"), {
            "save": "", "username": "newstaff", "password": "Strong-pass-123",
            "first_name": "Test", "last_name": "Staff", "phone": "0812345678",
            "location": location.pk, "role": "staff",
        })
        self.assertRedirects(response, reverse("staffs"))
        created = get_user_model().objects.get(username="newstaff")
        self.assertEqual(created.role, "staff")
        self.assertEqual(created.location, location)

    def test_admin_can_update_and_delete_staff(self):
        """TC-FR-25-01: admin can update and delete a staff account."""
        location = Location.objects.create(name="จุด staff CRUD", building="อาคาร 2")
        staff = get_user_model().objects.create_user(
            username="editable-staff", password="Strong-pass-123", role="staff",
            first_name="เดิม", last_name="Staff", phone="0811111111", location=location,
        )
        self.client.force_login(self.admin)
        response = self.client.post(reverse("staffs"), {
            "save": staff.pk, "username": "editable-staff", "password": "",
            "first_name": "แก้ไขแล้ว", "last_name": "Staff", "phone": "0822222222",
            "location": location.pk, "role": "staff",
        })
        self.assertRedirects(response, reverse("staffs"))
        staff.refresh_from_db()
        self.assertEqual(staff.first_name, "แก้ไขแล้ว")
        self.assertEqual(staff.phone, "0822222222")

        response = self.client.post(reverse("staffs"), {"delete": staff.pk})
        self.assertRedirects(response, reverse("staffs"))
        self.assertFalse(get_user_model().objects.filter(pk=staff.pk).exists())

    def test_admin_staff_search_matches_user_and_location_fields(self):
        """TC-FR-25-02: admin can find staff records in the staff management page."""
        location = Location.objects.create(name="จุดจำหน่ายอาคารสาม", building="อาคาร 3")
        staff = get_user_model().objects.create_user(
            username="search-target", password="Strong-pass-123", role="staff",
            first_name="สมชาย", last_name="ทดสอบ", phone="0899999999", location=location,
        )
        self.client.force_login(self.admin)
        for query in ("search-target", "สมชาย", "0899999999", "อาคารสาม"):
            with self.subTest(query=query):
                response = self.client.get(reverse("staffs"), {"q": query})
                self.assertEqual(response.status_code, 200)
                self.assertIn(staff, response.context["page_obj"].object_list)
