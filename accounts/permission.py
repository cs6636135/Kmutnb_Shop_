from django.contrib import messages
from django.shortcuts import redirect
from functools import wraps
#permission หลังร้าน 
#ไว้เชคสิทธิ์ 
def role_required(*roles):
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):

            # ยังไม่ได้ Login
            if not request.user.is_authenticated:
                messages.error(request, "กรุณาเข้าสู่ระบบ")
                return redirect("login")

            # Role ไม่มีสิทธิ์
            if request.user.role not in roles:
                messages.error(request, "คุณไม่มีสิทธิ์เข้าถึง")
                return redirect("home")

            return view_func(request, *args, **kwargs)

        return wrapper

    return decorator
#permission หน้าบ้าน ถ้าในอนาคตมีหน้าบ้านที่ต้อง login ก็สามารถเอาไปใช้ได้ (เผื่อนะ)