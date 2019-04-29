from django.shortcuts import render
from .models import Area, Week
from django.shortcuts import redirect

from osgeo import gdal
from django.http import HttpResponse
import tempfile
import rasterio


# Create your views here.

def index(request):
    data = {
        "areas": Area.objects.all()
    }
    return render(request, "index.html", data)

def area(request, area):
    area = Area.objects.get(id=area)
    data = {
        "weeks": Week.objects.filter(area=area),
        "area": area
    }
    return render(request, "area.html", data)

def week(request, area, week):

    data = {
        "week": Week.objects.get(id=week),
        "area": Area.objects.get(id=area)
    }
    return render(request, "colors.html", data)

def color(request, area, week, color):
    return redirect(getattr(Week.objects.get(id=week), color).url)

def color_png(request, area, week, color):
    color_field = getattr(Week.objects.get(id=week), color)

    fn = tempfile.mktemp(prefix=color, suffix=".png")

    print(color_field.file)
    with rasterio.open(color_field.file) as colorfile:
        data = colorfile.read().astype(float)
        print(data[0][0])
        data = (data-(-1))*((255)/(2))
        print(data.min())
        print(data.max())


    print("#######", fn, color_field.file, "|")
    #gdal.Translate(
    #    fn,
    #    color_field.file,
    #    format="PNG"
    #)

    gdal.Translate(fn, str(color_field.file), format="PNG")

    with open(fn, "rb") as f:
        return HttpResponse(f.read(), content_type="image/png")


