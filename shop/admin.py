from django.contrib import admin
# Register your models here.
from .models import Location, Product,ProductLocation,Category
admin.site.register(Location)   
admin.site.register(Product)
admin.site.register(ProductLocation)
admin.site.register(Category)
