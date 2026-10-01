from django.contrib import messages
from django.shortcuts import redirect


#permission หลังร้าน 
def manage_required(view_func):
    def wrapper(request, *args, **kwargs):

        # ยังไม่ได้ Login
        if not request.user.is_authenticated:
            messages.error(request, "กรุณาเข้าสู่ระบบ")
            return redirect("login")

        # Login แล้ว แต่ไม่ใช่ Admin/Staff
        if request.user.role not in ["admin", "staff"]:
            messages.error(request, "คุณไม่มีสิทธิ์เข้าสู่ระบบจัดการ")
            return redirect("home") #เผื่อในอนาคตมี customer login

        return view_func(request, *args, **kwargs)

    return wrapper


def admin_required(view_func):
    def wrapper(request, *args, **kwargs):

        # ยังไม่ได้ Login
        if not request.user.is_authenticated:
            messages.error(request, "กรุณาเข้าสู่ระบบ")
            return redirect("login")

        # Login แล้ว แต่ไม่ใช่ Admin
        if request.user.role != "admin":
            messages.error(request, "ต้องเป็น Admin เท่านั้น")
            return redirect("dashboard")

        return view_func(request, *args, **kwargs)

    return wrapper

#permission หน้าบ้าน ถ้าในอนาคตมีหน้าบ้านที่ต้อง login ก็สามารถเอาไปใช้ได้ (เผื่อนะ)