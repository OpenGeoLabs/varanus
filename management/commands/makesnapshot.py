from django.core.management.base import BaseCommand, CommandError
from django.contrib.gis.gdal import GDALRaster
from django.core.files import File

from varanus.models import SatelliteImage,  Area, Week

from sentinelsat.sentinel import SentinelAPI, read_geojson, geojson_to_wkt

import datetime
import tempfile
from zipfile import ZipFile
import os
import json
import subprocess
import sys
import copy
import shutil

from shapely.geometry import shape, mapping
from shapely.ops import unary_union
import shapely.wkt
from shapely.geometry import MultiPolygon
import fiona.transform
from osgeo import gdal, ogr
import rasterio as rio

sys.path.append("/home/jachym/venvs/lifemonitor/bin/")
import gdal_merge as gm
import atexit
import importlib

import pprint

_TO_BE_CLEANED = []

def _clean():
    for d in _TO_BE_CLEANED:
        shutil.rmtree(d)

atexit.register(_clean)


PERIOD=6


class Command(BaseCommand):
    help = 'Download and process data'

    def add_arguments(self, parser):
        parser.description = """Download and process satellite data for given
        time period."""
        parser.description = """
        User has to setup username and password for scihub.copernicus.eu
        service.

        Either --year and --week or --date has to be specified.
        """
        parser.add_argument('--user', required=True, type=str,
                           help="Copernicus SciHub user name")
        parser.add_argument('--password', required=True, type=str,
                           help="Copernicus SciHub user password")
        parser.add_argument('--date', required=False, type=str,
                           help="""Any day within required week in format
                            YYYYMMDD""")
        parser.add_argument('--week', required=False, type=str,
                            help="Number of week in required year")
        parser.add_argument('--year', required=False, type=str)
        parser.add_argument('--area', required=True, type=str,
                           help="Area name or id")
        parser.add_argument('--clouds', required=True, type=float,
                           help="Cloud coverage")


    def handle(self, *args, **options):
        """
        main method
        """

        user = options['user']
        passw = options['password']
        required_date = required_week = required_year = required_date = 0
        if options['date']:
            required_date = int(options['date'])
        if options['week']:
            required_week = int(options['week'])
        if options['year']:
            required_year = int(options['year'])
        area_name = options['area']
        clouds = options['clouds']

        self.api = SentinelAPI(user, passw, 'https://scihub.copernicus.eu/dhus')


        try:
            self.area = Area.objects.get(id=int(area_name))
        except:
            try:
                self.area = Area.objects.get(name=area_name)
            except:
                self.stdout.write(
                    self.style.ERROR('Given area <{}> does not exist'.format(area_name)))
                sys.exit(1)

        (starting_date, end_date, week_nr) = self._get_dates(required_year,
                                                             required_week,
                                                             required_date)

        products = self.get_products(starting_date, end_date, self.area,
                                     clouds=clouds)

        if not len(products.items()):
            # TODO save empty week maybe?
            self.stdout.write(
                self.style.WARNING('There is no data for given time period ' +
                '<{start}, {end}>, '.format(start=starting_date, end=end_date) +
                'maximal cloud cover <{cloud}%> and area <{area}>'.format(
                    area=area_name, cloud=clouds)
            ))
            return

        #self.tempdir = tempfile.mkdtemp(dir="/home/jachym/data/opengeolabs/lifemonitor/")
        self.tempdir = "/home/jachym/data/opengeolabs/lifemonitor/tmpq8_15z8f/"

        #!self.api.download_all(products, self.tempdir)
        products_data = self.get_bands(products)
        patched_bands = self._patch_rasters(products_data)

        analysed_data = self._analyse(patched_bands)

        pprint.pprint(analysed_data)
        raise Exception("###x")
        if Week.objects.filter(date=starting_date, area=area).count() == 0:
            week = Week(
                date=starting_date,
                area=area,
            )
            #week.red = GDALRaster(resulting_bands["red"], write=True)
            #week.save()
            #week.green = GDALRaster(resulting_bands["green"], write=True)
            #week.save()
            #week.blue = GDALRaster(resulting_bands["blue"], write=True)
            #week.save()
            #week.nir = GDALRaster(resulting_bands["nir"], write=True)
            #week.save()
            #week.ndvi = GDALRaster(analysis[0], write=True)
            #week.save()
            #week.ndwi = GDALRaster(analysis[1], write=True)
            #week.save()
            week.red.save(os.path.basename(resulting_bands["red"]),
                          File(open(resulting_bands["red"], "rb")), save=True)
            week.green.save(os.path.basename(resulting_bands["green"]),
                          File(open(resulting_bands["green"], "rb")), save=True)
            week.blue.save(os.path.basename(resulting_bands["blue"]),
                          File(open(resulting_bands["blue"], "rb")), save=True)
            week.nir.save(os.path.basename(resulting_bands["nir"]),
                          File(open(resulting_bands["nir"], "rb")), save=True)
            week.ndvi.save(os.path.basename(analysis[0]),
                          File(open(analysis[0], "rb")), save=True)
            week.ndwi.save(os.path.basename(analysis[1]),
                          File(open(analysis[1], "rb")), save=True)
            week.save()
        else:
            week = Week.objects.get(date=week_date, area=area)

        self.stdout.write(self.style.SUCCESS('Successfully create data for week {}'.format(week.week)))


    def save_satellite_image(self, product):
        kwargs = copy.deepcopy(product)
        kwargs.pop("highprobacloudspercentage")
        kwargs.pop("notvegetatedpercentage")
        kwargs.pop("snowicepercentage")
        kwargs.pop("unclassifiedpercentage")
        kwargs.pop("vegetationpercentage")
        kwargs.pop("waterpercentage")
        kwargs.pop("gmlfootprint")
        if kwargs["footprint"].find("POLYGON") == 0:
            geom = shapely.wkt.loads(kwargs["footprint"])
            geom = MultiPolygon([geom])
            kwargs["footprint"] = geom.wkt
        kwargs["frmt"] = kwargs.pop("format")
        kwargs["cloudcoverpercentage"] = kwargs.pop("mediumprobacloudspercentage")
        if SatelliteImage.objects.filter(title=kwargs["title"]).count() == 0:
            img =  SatelliteImage(
                **kwargs
            )
            img.save()
        else:
            img = SatelliteImage.objects.get(title=kwargs["title"])
        return img


    def _analyse(self, bands):
        """Perform required analysis for given area


        :param bands: dict will all available raster bands
        :return: dict with resulting analysis each analysis should have raster,
        image, vector keys
        """

        data = {}
        for analysis in ["ndvi", "ndwi"]: # self.area.characteristics:
            mod_analysis = importlib.import_module("varanus.methods.{}".format(analysis))
            data[analysis] = mod_analysis.analyse(bands, self.tempdir)

        return data



    def _patch_rasters(self, products_data):
        """Patch bands together from more products

        :param products_data: dict {product: {band: file_name}}

        :return: dict {band: file_name}
        """

        target_dir = os.path.join(self.tempdir, self.area.name, "merged")
        if not os.path.isdir(target_dir):
            os.makedirs(target_dir)

        products = products_data.keys()

        data = {}
        for band in products_data[list(products)[0]].keys():
            input_files = []

            for product in products_data:
                input_files.append(products_data[product][band])

            output = os.path.join(target_dir, "{}.tif".format(band))

            merge_command = ["-n", "0", "-a_nodata", "0", "-o", output, "-co", 
                                "COMPRESS=DEFLATE"  ] + input_files
            gm.main(merge_command)

            data[band] = output
        return data


    def _get_final_cutline(self, target, cutline, crs):
        """
        Get final cutline based on input cutline and cloud mask

        :param target: name of target working directory
        :param cultine: geojson file name with input cutline
        :param crs: EPSG:CODE cutline's coordinate reference system

        :return: file name with resulting cutline
        """

        granule = os.path.join(target, "GRANULE")
        qi_data = os.path.join(granule, os.listdir(granule)[0], "QI_DATA")
        clouds_file = os.path.join(qi_data, "MSK_CLOUDS_B00.gml")

        clouds_vectors = []
        clouds_ds = ogr.Open(clouds_file)
        layer = clouds_ds.GetLayer()
        if not layer:
            return cutline
        feature = layer.GetNextFeature()

        while feature is not None:

            geom = feature.GetGeometryRef()
            json_geom = geom.ExportToJson()
            cloud_vectors = shape(json.loads(json_geom))
            feature = layer.GetNextFeature()

        cloud_vectors = unary_union(cloud_vectors)
        cloud_vectors = fiona.transform.transform_geom(
            crs, "EPSG:4326", mapping(cloud_vectors))

        cutline_features = []
        with fiona.open(cutline) as cutline:
            for f in cutline:
                cutline_features.append(shape(f["geometry"]))
        cutline_features = unary_union(cutline_features)

        final_cutline = cutline_features.difference(shape(cloud_vectors))

        target_file = "{}.geojson".format(os.path.join(target, "cloud_cutline"))
        with open(target_file, "w") as out:
            data = {
                "type":"FeatureCollection",
                "features": [{
                    "geometry": mapping(final_cutline)
                }]
            }
            json.dump(data, out)
        return target_file

    def _get_all_band_files(self, target):
        """Create list of all available band files for given product target
        directory

        resulting data structure:

            ```
            {
                "res10m": {
                    "B01": "/path/to/file.jp2",
                    "B02": ...
                },
                "res20m": {
                    ...
                },
                ...
            }
            ```

        :return: data structure
        """

        data = {}
        granule = os.path.join(target, "GRANULE")
        granule_name = os.listdir(granule)[0]

        resolutions = os.listdir(
            os.path.join(granule, granule_name, "IMG_DATA")
        )


        for res in resolutions:
            data[res] = {}
            images = os.listdir(
                os.path.join(granule, granule_name, "IMG_DATA", res))
            for image in images:
                band_name = image.split("_")[2]
                data[res][band_name] = os.path.join(granule, granule_name,
                                                    "IMG_DATA", res, image)

        return data


    def _cut_bands(self, bands, cutline, target):
        """Cut area of interest based on given cutline

        :param bands: data structure of all bands as returned by
            _get_all_band_files
        :param cutline: filename of required cutline
        :param target: directory, where the resulting data should be uploaded
            to

        :return: same structure as input `bands`, but with cut raster files
        """

        area_dir = os.path.join(target, self.area.name)
        if not os.path.isdir(area_dir):
            os.mkdir(area_dir)

        data = {}
        for res in bands:
            for band in bands[res]:

                new_file = os.path.join(area_dir, "{}.jp2".format(band))
                gdal.Warp(
                    new_file,
                    os.path.join(bands[res][band]),
                    dstSRS="+init=epsg:4326",
                    cropToCutline=True,
                    resampleAlg="near",
                    format="GTiff",
                    cutlineDSName=cutline,
                    dstNodata=0,
                    creationOptions=["COMPRESS=DEFLATE"]
                )

                data[band] = new_file

        return data


    def _get_dates(self, year=None, week=None, date=None):
        """
        :param year: required year
        :param week: required week
        :param date: date as integer

        :return: (start_date, end_date, week_number)
        """

        week_number = None
        start_date = None
        end_date = None

        date = int(date)
        if date < 10000000:
                self.stdout.write(
                    self.style.ERROR('Date <{}> is not in required format YYYYMMDD'.format(date)))
                sys.exit(1)

        if date:
            year = date//10000
            month = (date - (year*10000))//100
            day = (date - year*10000 - month*100)
            date = datetime.datetime(year, month, day)
            year, week, weekday = date.isocalendar()
            firstday = datetime.timedelta(days=weekday-1)
            lastday = datetime.timedelta(days=PERIOD - weekday)
            start_date = date - firstday
            end_date = date + lastday
        else:
           first_day_in_year = datetime.date(year, 1, 1) 
           first_day_in_week = datetime.timedelta(days=(week-1)*7)
           last_day_in_week = datetime.timedelta(days=PERIOD)
           start_date = first_day_in_year+first_day_in_week
           end_date = start_date+last_day_in_week

        return(start_date, end_date, week)

    def get_bands(self, products):
        """
        Get dict with raster bands from downloaded Sentinel products

        :param products: list of products
        :return: dict of raster files for each band
        """

        data = {}
        for pid in products:
            product = products[pid]

            self.save_satellite_image(product)

            title = product["title"]
            filename = product["filename"]
            zipfname = os.path.join(self.tempdir, "{}.zip".format(title))

            #!with ZipFile(zipfname, 'r') as zipObj:
            #!    zipObj.extractall(path=self.tempdir)

            cutline = self.area.to_geojson_file(self.tempdir)

            product_dir = os.path.join(self.tempdir, filename)

            all_bands = self._get_all_band_files(product_dir)
            crs = self._get_crs_from_band(all_bands["R10m"]["B02"])

            clouds_cutline = self._get_final_cutline(product_dir, cutline, crs)

            bands = self._cut_bands(all_bands, clouds_cutline, product_dir)
            data[product_dir] = bands

        return data

    def _get_crs_from_band(self, raster):
        """Get  EPSG:CODE text string based on input raster file

        :param raster: full file name
        :return: crs "EPSG:<CODE>" text string
        """

        with rio.open(raster) as r:
            return "EPSG:{code}".format(code=r.read_crs().to_epsg())


    def get_products(self, start_date, end_date, area, clouds=100):
        """
        :param start_date: starting date object
        :param end_date: end date object
        :param area: required area object
        """

        products = self.api.query(area.area.wkt,
                     date = (start_date, end_date),
                     platformname = 'Sentinel-2',
                     cloudcoverpercentage = (0, clouds),
                     producttype="S2MSI2A")

        return products


