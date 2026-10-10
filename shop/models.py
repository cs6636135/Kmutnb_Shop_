from django.db import models
from django.core.validators import MinValueValidator
# Create your models here.

class Location(models.Model):
    name  = models.CharField(max_length=150)
    building = models.CharField(max_length=100)
    floor = models.CharField(max_length=30, blank=True)
    room = models.CharField(max_length=100, blank=True)
    description = models.TextField(blank=True)
    image_url = models.URLField(max_length=255, blank=True)

    class Meta:
        ordering = ["building", "floor", "room", "name"]

    def __str__(self):
        return f"{self.name} - {self.building} - {self.floor} - {self.room}"

class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True, null=True)

    parent = models.ForeignKey("self", on_delete=models.CASCADE,null=True,blank=True,related_name="children")

    def __str__(self):
        return self.name

class Product(models.Model):
    name = models.CharField(max_length=150, unique=True)
    description = models.TextField(blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    image_url = models.URLField(max_length=255, blank=True)
    reservable = models.BooleanField(default=True,choices=[(True, "จองได้"),(False, "จองไม่ได้")])
    created_at = models.DateTimeField(auto_now_add=True)

    category = models.ForeignKey(Category, on_delete=models.PROTECT,related_name="products")
    
    def __str__(self):
        return f"{self.name} - {self.price} - {'Reservable' if self.reservable else 'Not Reservable'}"

class ProductLocation(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    location = models.ForeignKey(Location, on_delete=models.CASCADE)
    stock = models.PositiveIntegerField(default=0)
    
    class Meta:
     constraints = [
        models.UniqueConstraint(
            fields=['product', 'location'],
            name='unique_product_location'
        )
    ]

    def __str__(self):
        return f"{self.product.name} - {self.location.name} - Stock: {self.stock}"