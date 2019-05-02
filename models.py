from django.contrib.gis.db import models
import tempfile
import json
import os
import datetime
from django.conf import settings
from . import methods

def call_upload_to(instance, filename):
    return instance.upload_to(filename)

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

    aot = models.FileField(upload_to=call_week_upload_to)
    b01 = models.FileField(upload_to=call_week_upload_to)
    b02 = models.FileField(upload_to=call_week_upload_to)
    b03 = models.FileField(upload_to=call_week_upload_to)
    b04 = models.FileField(upload_to=call_week_upload_to)
    b05 = models.FileField(upload_to=call_week_upload_to)
    b06 = models.FileField(upload_to=call_week_upload_to)
    b07 = models.FileField(upload_to=call_week_upload_to)
    b08 = models.FileField(upload_to=call_week_upload_to)
    b09 = models.FileField(upload_to=call_week_upload_to)
    b11 = models.FileField(upload_to=call_week_upload_to)
    b12 = models.FileField(upload_to=call_week_upload_to)
    b8a = models.FileField(upload_to=call_week_upload_to)
    scl = models.FileField(upload_to=call_week_upload_to)
    tci = models.FileField(upload_to=call_week_upload_to)
    wvp = models.FileField(upload_to=call_week_upload_to)

    cutline = models.MultiPolygonField()

    def upload_to(self, filename):

        target = os.path.join(settings.MEDIA_ROOT, "varanus", "week",
                              "{}-{}".format(self.date.year, str(self.week)))
        os.makedirs(target, exist_ok=True)

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

    def to_geojson_file(self, target_dir=None):
        if not target_dir:
            target_dir = tempfile.mkdtemp()

        target_file = "{}.geojson".format(os.path.join(target_dir, self.name))
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


class AnalysisType(models.Model):

    TYPES = map(lambda m: (m, m), methods.__all__)

    name = models.CharField(max_length=20, choices=TYPES)
    description = models.TextField(blank=True)

    def __str__(self):
        return self.name


def call_upload_to_dir(instance, filename):
    return instance.upload_to_dir(filename)


class Analysis(models.Model):

    type = models.ForeignKey("AnalysisType", on_delete=models.PROTECT)
    week = models.ForeignKey("Week", on_delete=models.PROTECT)

    raster = models.FileField(help_text="Raster data", blank=True,
                              upload_to=call_upload_to)
    vector = models.FileField(help_text="Vector data", blank=True,
                              upload_to=call_upload_to)
    image = models.FileField(help_text="Image representation", blank=True,
                             upload_to=call_upload_to)
    tiles = models.CharField(help_text="Dir to tiled data", blank=True,
                             max_length=256)

    def upload_to(self, filename):

        target = os.path.join(settings.MEDIA_ROOT, "varanus", "week",
                              "{}-{}".format(self.week.date.year,
                                             str(self.week.week)))
        os.makedirs(target, exist_ok=True)

        return os.path.join("varanus", "week", str(self.week), filename)

    def __str__(self):
        return "{year}-{week} {area} {type}".format(
            year=self.week.date.year, week=self.week.week,
            area=self.week.area.name, type=self.type.name)
