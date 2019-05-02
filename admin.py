from django.contrib import admin

from .models import *
from django.utils.safestring import mark_safe
from django.template.loader import render_to_string
from leaflet.admin import LeafletGeoAdmin

class AreaAdmin(LeafletGeoAdmin):
    pass

class ProductAdmin(admin.ModelAdmin):
    list_display = ("title", "footprint")

class WeekAdmin(admin.ModelAdmin):
    list_display = ("name", "week")

    def name(self, item):
        return str(item)

    def week(self, item):
        return item.week

    def ndvi_image(self, obj):
        return  render_to_string('thumb.html',{
                    'image': obj.as_jpeg_thumb(obj.ndvi)
                })

    ndvi_image.allow_tags = True


admin.site.register(SatelliteImage, ProductAdmin)
admin.site.register(Area, AreaAdmin)
admin.site.register(Week, WeekAdmin)
admin.site.register(AnalysisType)
admin.site.register(Analysis)
