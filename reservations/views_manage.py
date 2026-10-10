from django.core.paginator import Paginator
from django.shortcuts import render
from django.utils import timezone

from accounts.permission import role_required
from .models import Reservation

# ทำเพื่อให้แสดงผลได้ก่อน แต่แก้ไขได้ ทำลวกๆมาก่อนเฉยๆ

@role_required("admin", "staff")
def reservation_list(request):
    user = request.user
    qs = Reservation.objects.select_related("product", "location").order_by("-reserved_at")

    if user.role != "admin":
        qs = qs.filter(location=user.location)

    status = request.GET.get("status", "").strip()
    if status in {choice[0] for choice in Reservation.Status.choices}:
        qs = qs.filter(status=status)

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
