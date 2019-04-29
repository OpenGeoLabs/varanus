# Varanus land monitor

System for monitoring chaning on the Earth surface based on satellite data
(currently supporting [Copernicus](https://www.copernicus.eu/en)
[Sentinel program](https://scihub.copernicus.eu/) only).

## How it works

1. Define are on Earth surface
2. Let the `python manage.py download` command download satellite images of
   the area for you, and let it calculate various [indexes](https://www.indexdatabase.de/)
3. Resulting images are stored in Django database in models for later evaluation

## How area is covered

Basic unit for observed area is **1 week** because there are two satellites on the orbit and
[orbit cycle takes 10 days for each satellite](https://sentinel.esa.int/web/sentinel/missions/sentinel-2/satellite-description/orbit). Every place on Earth should be covered within 5 days periods.

The *area of interest* is usually covered by several images during this one week
period. For every area of interest, the `python3 manage.py download` command
will do following:

1. Collect satellite images for given week covering at least part of required
   area
2. Download the data
3. Unzip, join area's cutline with mask representing cloud coverage, as result
   we shold have vector cutline representing area of intereset without potencial
   cloud coverage
4. Apply cutline on each band of input raster data
5. Join resulting data together into single seamless raster map
6. Calculate required analysis (ndvi, ndwi, ...)
7. Create and store `varanus.models.Week` object with everything stored in it.
8. Clean temporary files

## Satellite data used for Earth observation

In current version the system uses:

* [Sentinel-2](https://www.esa.int/Our_Activities/Observing_the_Earth/Copernicus/Sentinel-2) satellite images ([wikipedia](https://en.wikipedia.org/wiki/Sentinel-2))
* Processed on [level-2A](https://en.wikipedia.org/wiki/Sentinel-2#Products)
  (bottom of atmosphere)
* Downloaded directly from [Scihub platform](https://scihub.copernicus.eu/)

At the moment, no additional atmospheric correction is performed

## Installation and usage

This is Python-[Django](https://django.org) application. 

1. Download the `varanus` package from GITHub
2. Add `varanus` to `INSTALLED_APPS`
3. Install dependencies (those are usually standard geospatial packages) using
   `pip install -r requirements.txt` (or using other alternative more advanced
   methods)
4. Make sure, you are using spatially-enabled database backend, that means,
   either [Spatialite](https://docs.djangoproject.com/en/2.2/ref/contrib/gis/install/spatialite/) or [PostgreSQL with PostGIS](https://docs.djangoproject.com/en/2.2/ref/contrib/gis/install/postgis/)

This was tested on Linux. May all your gods be with you, if you are trying to
use this on other platforms.

## License

BSD
