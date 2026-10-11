from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.core.paginator import Paginator
from django.db.models import Q
from django.contrib import messages
from django.db import transaction, IntegrityError
from django.core.exceptions import ValidationError

from .permission import role_required
from .models import User
from .forms import UserModelForm

#login หลังร้าน
def user_login(request):
    if request.method == "POST":
        username = request.POST["username"]
        password = request.POST["password"]

        user = authenticate(
            request,
            username=username,
            password=password
        )

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

#เขียน crud staff ตรงนี้ได้เลย
@role_required("admin")
def staffs(request):
    if request.method == "POST":

        if "add" in request.POST:
            return render(request, "manage/staff_form.html", {
                "form": UserModelForm(),
            })

        elif "edit" in request.POST:
            staff_member = get_object_or_404(User, pk=request.POST["edit"])
            return render(request, "manage/staff_form.html", {
                "form": UserModelForm(instance=staff_member),
                "staff": staff_member,
            })

        elif "save" in request.POST:
            pk = request.POST.get("save")
            staff_member = get_object_or_404(User, pk=pk) if pk else None
            form = UserModelForm(request.POST, request.FILES or None, instance=staff_member)

            if form.is_valid():
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

            return render(request, "manage/staff_form.html", {
                "form": form,
                "staff": staff_member,
            })

        elif "delete" in request.POST:
            staff_member = get_object_or_404(User, pk=request.POST["delete"])
            if staff_member.pk == request.user.pk:
                messages.error(request, "ไม่สามารถลบบัญชีของตัวเองที่กำลังเข้าสู่ระบบอยู่ได้")
            else:
                try:
                    staff_member.delete()
                    messages.success(request, "ลบเจ้าหน้าที่เรียบร้อยแล้ว")
                except Exception:
                    messages.error(request, "ไม่สามารถลบบัญชีนี้ได้เนื่องจากมีข้อมูลที่เกี่ยวข้องอยู่ในระบบ")
            return redirect("staffs")
    search_query = request.GET.get("q", "").strip()

    qs = User.objects.filter(role=User.Role.STAFF).select_related("location").order_by("username")
    if search_query:
        for term in search_query.split():
            qs = qs.filter(
                Q(username__icontains=term)
                | Q(first_name__icontains=term)
                | Q(last_name__icontains=term)
                | Q(phone__icontains=term)
                | Q(location__name__icontains=term)
            )

    paginator = Paginator(qs, 10)
    page_obj = paginator.get_page(request.GET.get("page"))

    return render(request, "manage/staffs.html", {
        "page_obj": page_obj,
        "search_query": search_query,
    })