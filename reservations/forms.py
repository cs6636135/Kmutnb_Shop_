from django import forms
from .models import Reservation

INPUT = "w-full min-w-0 rounded-lg border border-slate-300 px-4 py-3 text-base outline-none focus:border-[#F47745] focus:ring-2 focus:ring-[#F47745]/20"
SELECT = INPUT + " bg-white"

STATUS_CHOICES = [
    (Reservation.Status.PENDING, "รอรับสินค้า (Pending)"),
    (Reservation.Status.PICKED_UP, "รับสินค้าแล้ว (Picked up)"),
    (Reservation.Status.CANCELLED, "ยกเลิก (Cancelled)"),
    (Reservation.Status.EXPIRED, "หมดอายุ (Expired)"),
]

class StatusForm(forms.ModelForm):
    status = forms.ChoiceField(
        choices=STATUS_CHOICES,
        label="สถานะการจอง",
        widget=forms.Select(attrs={"class": SELECT}),
    )

    class Meta:
        model = Reservation
        fields = ["status"]