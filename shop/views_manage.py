from django.shortcuts import render
from django.shortcuts import redirect
from accounts.permission import role_required

#ฝั่งคนจัดการร้านค้า ประมาณว่าเป็นหลังร้าน เกี่ยวกับทุกอย่างของหลังร้านยกเว้นการจองๆ
# Create your views here.
@role_required("admin", "staff")
def dashboard(request):
    print("DASHBOARD USER:", request.user)
    print("AUTHENTICATED:", request.user.is_authenticated)

    return render(request, "manage/dashboard.html", {
        "user": request.user,
        "session_info": request.session.items()
    })

@role_required("admin")
def products(request):
    return render(request, "manage/products.html", {
        "user": request.user,
        "session_info": request.session.items()
    })
