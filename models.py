from django.contrib.gis.db import models
import tempfile
import json
import os
import datetime
from django.conf import settings


class SatelliteImage(models.Model):

    SENSOR_CHOICES = (
        ("Sentinel 2A", "s2a"),
        ("Sentinel 2B", "s2b"),
    )

    title = models.CharField(max_length=128)
    link = models.URLField()
    link_alternative = models.URLField()
    link_icon = models.URLField()
    summary = models.TextField()
    beginposition = models.DateTimeField()
    endposition = models.DateTimeField()
    ingestiondate = models.DateTimeField()
    orbitnumber = models.IntegerField()
    relativeorbitnumber = models.IntegerField()
    cloudcoverpercentage = models.FloatField()
    sensoroperationalmode = models.CharField(max_length=16)
    footprint = models.MultiPolygonField()
    tileid = models.CharField(max_length=16)
    hv_order_tileid = models.CharField(max_length=16)
    frmt = models.CharField(max_length=16)
    processingbaseline = models.FloatField()
    platformname = models.CharField(max_length=16)
    filename = models.CharField(max_length=256)
    instrumentname = models.CharField(max_length=128)
    instrumentshortname = models.CharField(max_length=16)
    size = models.CharField(max_length=16)
    s2datatakeid = models.CharField(max_length=128)
    producttype = models.CharField(max_length=16)
    platformidentifier = models.CharField(max_length=16)
    orbitdirection = models.CharField(max_length=16)
    platformserialidentifier = models.CharField(max_length=16)
    processinglevel = models.CharField(max_length=16)
    identifier = models.CharField(max_length=128)
    level1cpdiidentifier = models.CharField(max_length=128)
    uuid = models.UUIDField()
    #clouds = models.MultiPolygonField()

    def __str__(self):
        return self.title

def call_week_upload_to(instance, filename):
    return instance.upload_to(filename)

class Week(models.Model):
    date = models.DateField(help_text="First day of the week")
    area = models.ForeignKey("Area", on_delete=models.CASCADE)
    satellite_image = models.ManyToManyField("SatelliteImage")

    # data are too big to be stored in the database
    #red = models.RasterField(blank=True)
    #green = models.RasterField(blank=True)
    #blue = models.RasterField(blank=True)
    #nir = models.RasterField(blank=True)
    #ndvi = models.RasterField(blank=True)
    #ndwi = models.RasterField(blank=True)

    red = models.FileField(upload_to=call_week_upload_to)
    green = models.FileField(upload_to=call_week_upload_to)
    blue = models.FileField(upload_to=call_week_upload_to)
    nir = models.FileField(upload_to=call_week_upload_to)
    ndvi = models.FileField(upload_to=call_week_upload_to)
    ndwi = models.FileField(upload_to=call_week_upload_to)

    def upload_to(self, filename):

        target = os.path.join(settings.MEDIA_ROOT, "varanus", "week", 
                              "{}-{}".format(self.date.year), str(self.week))
        os.mkdirs(target, exist_ok=True)

        return os.path.join("varanus", "week", str(self.week), filename)

    @property
    def week(self):
        return self.date.isocalendar()[1]

    @property
    def firstday(self):
        return self.date

    @property
    def lastday(self):
        return self.date + datetime.timedelta(days=7)

    @property
    def month(self):
        return self.date.month

    @property
    def season(self):
        # "day of year" ranges for the northern hemisphere
        spring = range(80, 172)
        summer = range(172, 264)
        fall = range(264, 355)
        # winter = everything else
        if doy in spring:
            season = 'spring'
        elif doy in summer:
            season = 'summer'
        elif doy in fall:
            season = 'fall'
        else:
            season = 'winter'
        return season

    def __str__(self):
        return str(self.date)


class Area(models.Model):
    area = models.PolygonField()
    name = models.CharField(max_length=20)


    def to_geojson(self, target=None):
        if not target:
            target = tempfile.mkdtemp()

        target_file = "{}.geojson".format(os.path.join(target, self.name))
        with open(target_file, "w") as out:
            data = {
                "type":"FeatureCollection",
                "features": [{
                    "properties": {"name":self.name},
                    "geometry": json.loads(self.area.json)
                }]
            }
            json.dump(data, out)
        return target_file



    def __str__(self):
        return self.name
