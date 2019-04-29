from django.core.management.base import BaseCommand, CommandError
from satellite.models import SatelliteImage,  Area, Week

from sentinelsat.sentinel import SentinelAPI, read_geojson, geojson_to_wkt
from datetime import date, timedelta
import tempfile
from zipfile import ZipFile
import os
from shapely.geometry import shape, mapping
from shapely.ops import unary_union
from osgeo import gdal, ogr
import json
import fiona.transform
import subprocess
import sys
sys.path.append("/home/jachym/venvs/lifemonitor/bin/")
import gdal_merge as gm
import rasterio as rio
import copy
from rasterio.windows import Window
from django.contrib.gis.gdal import GDALRaster
from django.core.files import File
import shutil
import shapely.wkt
from shapely.geometry import MultiPolygon

PERIOD=6

class Command(BaseCommand):
    help = 'Download data'

    def add_arguments(self, parser):
        parser.add_argument('--user', required=True, type=str)
        parser.add_argument('--password', required=True, type=str)
        parser.add_argument('--date', required=True, type=str)
        parser.add_argument('--area', required=True, type=str)
        parser.add_argument('--clouds', required=True, type=float)

    def handle(self, *args, **options):
        user = options['user']
        passw = options['password']
        mydate = int(options['date'])
        area = options['area']
        clouds = options['clouds']

        area = Area.objects.get(name=area)

        api = SentinelAPI(user, passw, 'https://scihub.copernicus.eu/dhus')


        strmydate = str(mydate)
        enddate = date(int(strmydate[0:4]), int(strmydate[4:6]), int(strmydate[6:8]))
        startdate = enddate - timedelta(days=PERIOD)
        products = api.query(area.area.wkt,
                     date = (startdate, enddate),
                     platformname = 'Sentinel-2',
                     cloudcoverpercentage = (0, clouds),
                     producttype="S2MSI2A")

        tempdir = tempfile.mkdtemp()
        #tempdir = "/home/jachym/data/opengeolabs/lifemonitor/tmpxq6rx00w/"
        #tempdir = "/home/jachym/data/opengeolabs/lifemonitor/0days/"
        #tempdir = "/home/jachym/data/opengeolabs/lifemonitor/6days/"
        #tempdir = "/home/jachym/data/opengeolabs/lifemonitor/14days/"
        #tempdir = "/home/jachym/data/opengeolabs/lifemonitor/21days/"
        #tempdir = "/tmp/tmpodaogqzc"

        products_bands = {}
        if len(products):
            print(products.keys())
            api.download_all(products, tempdir)
            for product in products:
                image = self._get_satellite_image(products[product])
                #for k in products[product]:
                #    print(k, products[product][k])
                title = products[product]["title"]
                frmt = products[product]["format"]
                filename = products[product]["filename"]
                zipfname = os.path.join(tempdir, "{}.zip".format(title))
                with ZipFile(zipfname, 'r') as zipObj:
                    # Extract all the contents of zip file in current directory
                    zipObj.extractall(path=tempdir)
                cutline = area.to_geojson(tempdir)

                target = os.path.join(tempdir, filename)

                clouds = self._get_final_clouds_file(target, cutline)

                bands = self._cut_bands(title, clouds , target)
                products_bands[target] = bands
        else:
            return

        whole_bands = {
            "red": None,
            "green": None,
            "blue": None,
            "nir": None
        }

        resulting_bands = self._patch_rasters(tempdir, products_bands, whole_bands)

        analysis = self._analyse(tempdir, resulting_bands)

        mydate = str(mydate)
        week_date = date(int(mydate[0:4]), int(mydate[4:6]), int(mydate[6:8]))
        if Week.objects.filter(date=week_date, area=area).count() == 0:
            week = Week(
                date=week_date,
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

        shutil.rmtree(tempdir)


    def _get_satellite_image(self, product):
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


    def _analyse(self, tempdir, bands):

        if not os.path.isdir(os.path.join(tempdir, "indexes")):
            os.mkdir(os.path.join(tempdir, "indexes"))
        out_ndvi = os.path.join(tempdir, "indexes", "ndvi.tiff")
        out_ndwi = os.path.join(tempdir, "indexes", "ndwi.tiff")

        with rio.open(bands["red"]) as red:
            with rio.open(bands["nir"]) as nir:
                with rio.open(bands["green"]) as green:
                    step = int(red.width/5)
                    kwargs = copy.deepcopy(red.meta)
                    kwargs.update(dtype=rio.float64, count=1, compress='lzw')
                    with rio.open(out_ndvi, "w", **kwargs) as outndvi:
                        with rio.open(out_ndwi, "w", **kwargs) as outndwi:
                            slices = [(col_start, row_start, step, step) \
                                for col_start in list(range(0, red.width, step)) \
                                for row_start in list(range(0, red.height, step))
                            ]
                            for slc in slices:
                                win = Window(*slc)

                                nir_data = nir.read(1, window=win).astype(float)
                                vis_data = red.read(1, window=win).astype(float)
                                green_data = green.read(1, window=win).astype(float)

                                ndvi = (nir_data - vis_data) / (nir_data + vis_data)
                                ndwi = (green_data - nir_data) / (green_data + nir_data)

                                write_win = Window(slc[0], slc[1], ndvi.shape[1], ndvi.shape[0])

                                outndvi.write_band(1, ndvi.astype(rio.float64), window=write_win)
                                outndwi.write_band(1, ndwi.astype(rio.float64), window=write_win)

        self.stdout.write(self.style.WARNING("Raster IO should use windowed style of reading and writing"))

        return [out_ndvi, out_ndwi]



    def _patch_rasters(self, tempdir, products_bands, whole_bands):

        target_dir = os.path.join(tempdir, "merged")
        if not os.path.isdir(target_dir):
            os.mkdir(target_dir)

        for color in  ("red", "green", "blue", "nir"):
            inputs = []
            for target in products_bands:
                inputs.append(os.path.join(target, "area", products_bands[target][color]))

            output = os.path.join(target_dir, "{}.tif".format(color))

            merge_command = ["-n", "0", "-a_nodata", "0", "-o", output, "-co", 
                                "COMPRESS=DEFLATE"  ] + inputs
            gm.main(merge_command)

            whole_bands[color] = output
        return whole_bands


    def _get_final_clouds_file(self, target, cutline):

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
            "EPSG:3263", "EPSG:4326", mapping(cloud_vectors))
        self.stdout.write(self.style.WARNING('Using default EPSG:3263 for clouds'))

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

    def _cut_bands(self, title, cutline, target):

        file_names = "{}_{}".format(title.split("_")[5], title.split("_")[2])
        granule = os.path.join(target, "GRANULE")
        img_data = os.path.join(granule, os.listdir(granule)[0], "IMG_DATA",
                                "R10m")
        data = os.listdir(img_data)

        bandnames = {
            "blue": "{}_B02_10m.jp2".format(file_names),
            "green": "{}_B03_10m.jp2".format(file_names),
            "red": "{}_B04_10m.jp2".format(file_names),
            "nir": "{}_B08_10m.jp2".format(file_names),
        }


        area_dir = os.path.join(target, "area")
        if not os.path.isdir(area_dir):
            os.mkdir(area_dir)
        for color in bandnames:
            print("warping", bandnames[color])
            gdal.Warp(
                os.path.join(target, "area", bandnames[color]),
                os.path.join(img_data, bandnames[color]),
                dstSRS="+init=epsg:4326",
                cropToCutline=True,
                resampleAlg="near",
                format="GTiff",
                cutlineDSName=cutline,
                dstNodata=0,
                creationOptions=["COMPRESS=DEFLATE"]
            )

        return bandnames

