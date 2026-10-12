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
        """TC-AUTH-001: valid credentials authenticate and open the dashboard."""
        response = self.client.post(reverse("login"), {"username": "admin", "password": "Strong-pass-123"})
        self.assertRedirects(response, reverse("dashboard"))
        self.assertTrue(response.wsgi_request.user.is_authenticated)

    def test_login_with_invalid_credentials_shows_error(self):
        """TC-AUTH-002: invalid credentials do not create a session."""
        response = self.client.post(reverse("login"), {"username": "admin", "password": "wrong"})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Username หรือ Password ไม่ถูกต้อง")
        self.assertFalse(response.wsgi_request.user.is_authenticated)

    def test_logout_clears_authenticated_session(self):
        """TC-AUTH-003: logout clears the current authenticated user."""
        self.client.force_login(self.admin)
        response = self.client.get(reverse("logout"))
        self.assertRedirects(response, reverse("login"))
        self.assertFalse(response.wsgi_request.user.is_authenticated)

    def test_anonymous_user_is_redirected_from_protected_page(self):
        """TC-AUTHZ-001: anonymous users cannot access staff management."""
        response = self.client.get(reverse("staffs"))
        self.assertRedirects(response, reverse("login"))

    def test_staff_cannot_access_admin_only_page(self):
        """TC-AUTHZ-002: staff users are denied admin-only account management."""
        self.client.force_login(self.staff)
        response = self.client.get(reverse("staffs"))
        self.assertRedirects(response, reverse("dashboard"))

    def test_staff_can_access_shared_dashboard(self):
        """TC-AUTHZ-003: an authenticated staff user can access shared pages."""
        self.client.force_login(self.staff)
        response = self.client.get(reverse("dashboard"))
        self.assertEqual(response.status_code, 200)

    def test_admin_can_create_staff_with_location(self):
        """TC-CREATE-003: admin creates a staff account assigned to a location."""
        location = Location.objects.create(name="จุด staff", building="อาคาร 1")
        self.client.force_login(self.admin)
        response = self.client.post(reverse("staffs"), {
            "save": "", "username": "newstaff", "password": "Strong-pass-123",
            "first_name": "Test", "last_name": "Staff", "phone": "0812345678",
            "location": location.pk, "role": "staff",
        })
        self.assertRedirects(response, reverse("staffs"))
        self.assertTrue(get_user_model().objects.filter(username="newstaff", role="staff").exists())

    def test_admin_staff_search_matches_user_and_location_fields(self):
        """TC-FILTER-005: staff search matches username, person fields, and location."""
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
