from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.core.paginator import Paginator
from django.db.models import Q
from django.contrib import messages
from django.db import transaction, IntegrityError
from django.core.exceptions import ValidationError
from django.views.decorators.http import require_POST
from .permission import role_required
from .models import User
from .forms import UserModelForm

#login หลังร้าน
def user_login(request):
    if request.method == "POST":
        username = request.POST["username"]
        password = request.POST["password"]

        user = authenticate(request,username=username, password=password)

        if user is not None:
            login(request, user)
            return redirect("dashboard")

        return render(request, "manage/login.html", {
            "error": "Username หรือ Password ไม่ถูกต้อง"
        })
    return render(request, "manage/login.html")

def user_logout(request):
    logout(request)
    return redirect("login")


@role_required("admin")
def staffs(request):
    search_query = request.GET.get("q", "").strip()

    qs = User.objects.select_related("location").order_by("username")
    for term in search_query.split():
        qs = qs.filter(
            Q(username__icontains=term)
            | Q(first_name__icontains=term)
            | Q(last_name__icontains=term)
            | Q(phone__icontains=term)
            | Q(location__name__icontains=term)
        )

    page_obj = Paginator(qs, 10).get_page(request.GET.get("page"))

    return render(request, "manage/staffs.html", {
        "page_obj": page_obj,
        "search_query": search_query,
    })

@role_required("admin")
def staff_form(request, pk=None):
    # ไม่มี pk = เพิ่มใหม่, มี pk = แก้ไข 
    staff_member = get_object_or_404(User, pk=pk) if pk else None
    form = UserModelForm(request.POST or None, request.FILES or None, instance=staff_member)

    if request.method == "POST" and form.is_valid():
        try:
            with transaction.atomic():
                form.save()
        except ValidationError as e:
            form.add_error(None, e)
        except IntegrityError:
            form.add_error(None, "บันทึกไม่สำเร็จ ข้อมูลอาจซ้ำหรือไม่ครบ")
        else:
            messages.success(request, "บันทึกเจ้าหน้าที่เรียบร้อยแล้ว")
            return redirect("staffs")

    return render(request, "manage/staff_form.html", {"form": form, "staff": staff_member})

@role_required("admin")
@require_POST
def staff_delete(request, pk):
    staff_member = get_object_or_404(User, pk=pk)

    # ห้ามลบบัญชีตัวเอง
    if staff_member.pk == request.user.pk:
        messages.error(request, "ไม่สามารถลบบัญชีของตัวเองที่กำลังเข้าสู่ระบบอยู่ได้")
    else:
        try:
            staff_member.delete()
            messages.success(request, "ลบเจ้าหน้าที่เรียบร้อยแล้ว")
        except Exception:
            messages.error(request, "ไม่สามารถลบบัญชีนี้ได้เนื่องจากมีข้อมูลที่เกี่ยวข้องอยู่ในระบบ")
    return redirect("staffs")