#ฝั่งลูกค้า ประมาณว่าเป็นหน้าร้าน
from django.shortcuts import get_object_or_404, render, redirect
from django.db.models import Q, Sum
from shop.models import Category, Location, Product, ProductLocation

def home(request):
    products = Product.objects.annotate(
        stock=Sum("productlocation__stock", default=0)
    ).order_by("-created_at")
    return render(request, "shop/home.html", {
        "products": products,
        "categories": Category.objects.all(),
        "locations": Location.objects.all(),
    })


def product_list(request):
    search_query = request.GET.get("q", "").strip()
    category_id = request.GET.get("category", "")
    location_id = request.GET.get("location", "")

    products = Product.objects.all()
    if search_query:
        products = products.filter(
            Q(name__icontains=search_query)
            | Q(description__icontains=search_query)
        )
    if category_id.isdigit():
        products = products.filter(category_id=category_id)
    else:
        category_id = ""

    stock_filter = Q()
    if location_id.isdigit():
        products = products.filter(productlocation__location_id=location_id)
        stock_filter = Q(productlocation__location_id=location_id)
    else:
        location_id = ""

    products = products.annotate(
        stock=Sum("productlocation__stock", filter=stock_filter, default=0)
    ).order_by("-created_at")

    return render(request, "shop/products.html", {
        "products": products,
        "categories": Category.objects.all(),
        "locations": Location.objects.all(),
        "search_query": search_query,
        "selected_category": category_id,
        "selected_location": location_id,
    })


def product_detail(request, product_id):
    product = get_object_or_404(
        Product.objects.select_related("category").annotate(
            stock=Sum("productlocation__stock", default=0)
        ),
        pk=product_id,
    )
    product_locations = ProductLocation.objects.filter(
        product=product
    ).select_related("location").order_by("location__name")

    return render(request, "shop/product_detail.html", {
        "product": product,
        "product_locations": product_locations,
    })