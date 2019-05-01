import rasterio as rio
import subprocess
import os
import copy
from rasterio.windows import Window


def analyse(bands, target_dir=None):
    """Create NDVI index
    """

    raster_out = os.path.join(target_dir, "ndvi.tif")
    tiles_out = os.path.join(target_dir, "ndvi")
    image_out = os.path.join(target_dir, "ndvi.png")

    with rio.open(bands["B04"]) as red:
        with rio.open(bands["B08"]) as nir:
            step = 8192
            kwargs = copy.deepcopy(red.meta)
            kwargs.update(dtype=rio.float64, count=1, compress='lzw')
            with rio.open(raster_out, "w", **kwargs) as outndvi:
                kwargs.update(dtype=rio.int8, count=1, driver='PNG')
                with rio.open(image_out, "w", **kwargs) as outndviimg:
                    slices = [
                        (col_start, row_start, step, step)
                        for col_start in list(range(0, red.width, step))
                        for row_start in list(range(0, red.height, step))
                    ]
                    for slc in slices:
                        win = Window(*slc)

                        nir_data = nir.read(1, window=win).astype(float)
                        vis_data = red.read(1, window=win).astype(float)

                        ndvi = (nir_data - vis_data) / (nir_data + vis_data)
                        ndvi_hist = (ndvi + 1) * (255/(-2))
                        #ndvi_bands = get_bands(ndvi)

                        write_win = Window(
                            slc[0], slc[1],
                            ndvi.shape[1], ndvi.shape[0]
                        )
                        outndvi.write_band(1, ndvi.astype(rio.float64),
                                        window=write_win)
                        outndviimg.write_band(1, ndvi_hist.astype(rio.uint8),
                                        window=write_win)

    subprocess.call([
        "gdal2tiles.py", "-w", "leaflet", "-t",
        "NDVI index", image_out, tiles_out
    ])

    return {
        "raster": raster_out,
        "image": image_out,
        "tiles": tiles_out,
        "vector": None
    }


def get_bands(ndvi):
    values = [-0.2, 0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]
    colors = [[0, 0, 0],           #  < -.2 = #000000 (black)
        [165/255, 0, 38/255],         #  -> 0 = #a50026
        [215/255, 48/255, 39/255],    #  -> .1 = #d73027
        [244/255, 109/255, 67/255],   #  -> .2 = #f46d43
        [253/255, 174/255, 97/255],   #  -> .3 = #fdae61
        [254/255, 224/255, 139/255],  #  -> .4 = #fee08b
        [255/255, 255/255, 191/255],  #  -> .5 = #ffffbf
        [217/255, 239/255, 139/255],  #  -> .6 = #d9ef8b
        [166/255, 217/255, 106/255],  #  -> .7 = #a6d96a
        [102/255, 189/255, 99/255],   #  -> .8 = #66bd63
        [26/255, 152/255, 80/255],    #  -> .9 = #1a9850
        [0, 104/255, 55/255]         #  -> 1.0 = #006837
    ]

    red, green, blue = [
        numpy.ndvi,
        numpy.ndvi,
        numpy.ndvi
    ]

