# Generated by Django 2.2 on 2019-04-28 02:58

import django.contrib.gis.db.models.fields
from django.db import migrations, models
import django.db.models.deletion
import varanus.models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Area',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('area', django.contrib.gis.db.models.fields.PolygonField(srid=4326)),
                ('name', models.CharField(max_length=20)),
            ],
        ),
        migrations.CreateModel(
            name='SatelliteImage',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=128)),
                ('link', models.URLField()),
                ('link_alternative', models.URLField()),
                ('link_icon', models.URLField()),
                ('summary', models.TextField()),
                ('beginposition', models.DateTimeField()),
                ('endposition', models.DateTimeField()),
                ('ingestiondate', models.DateTimeField()),
                ('orbitnumber', models.IntegerField()),
                ('relativeorbitnumber', models.IntegerField()),
                ('cloudcoverpercentage', models.FloatField()),
                ('sensoroperationalmode', models.CharField(max_length=16)),
                ('footprint', django.contrib.gis.db.models.fields.MultiPolygonField(srid=4326)),
                ('tileid', models.CharField(max_length=16)),
                ('hv_order_tileid', models.CharField(max_length=16)),
                ('frmt', models.CharField(max_length=16)),
                ('processingbaseline', models.FloatField()),
                ('platformname', models.CharField(max_length=16)),
                ('filename', models.CharField(max_length=256)),
                ('instrumentname', models.CharField(max_length=128)),
                ('instrumentshortname', models.CharField(max_length=16)),
                ('size', models.CharField(max_length=16)),
                ('s2datatakeid', models.CharField(max_length=128)),
                ('producttype', models.CharField(max_length=16)),
                ('platformidentifier', models.CharField(max_length=16)),
                ('orbitdirection', models.CharField(max_length=16)),
                ('platformserialidentifier', models.CharField(max_length=16)),
                ('processinglevel', models.CharField(max_length=16)),
                ('identifier', models.CharField(max_length=128)),
                ('level1cpdiidentifier', models.CharField(max_length=128)),
                ('uuid', models.UUIDField()),
            ],
        ),
        migrations.CreateModel(
            name='Week',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date', models.DateField()),
                ('red', models.FileField(upload_to=varanus.models.call_week_upload_to)),
                ('green', models.FileField(upload_to=varanus.models.call_week_upload_to)),
                ('blue', models.FileField(upload_to=varanus.models.call_week_upload_to)),
                ('nir', models.FileField(upload_to=varanus.models.call_week_upload_to)),
                ('ndvi', models.FileField(upload_to=varanus.models.call_week_upload_to)),
                ('ndwi', models.FileField(upload_to=varanus.models.call_week_upload_to)),
                ('area',
                 models.ForeignKey(on_delete=django.db.models.deletion.CASCADE,
                                   to='varanus.Area')),
                ('satellite_image', models.ManyToManyField(to='varanus.SatelliteImage')),
            ],
        ),
    ]
