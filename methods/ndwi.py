import rasterio as rio
import subprocess
import os
import copy
from rasterio.windows import Window


def analyse(bands, target_dir=None):
    """Create NDWI index
    """

    raster_out = os.path.join(target_dir, "ndwi.tif")
    image_out = os.path.join(target_dir, "ndwi.png")
    tiles_out = os.path.join(target_dir, "ndwi")

    with rio.open(bands["B03"]) as green:
        with rio.open(bands["B08"]) as nir:
            step = 8192
            kwargs = copy.deepcopy(green.meta)
            kwargs.update(dtype=rio.float64, count=1, compress='lzw')
            with rio.open(raster_out, "w", **kwargs) as outndwi:
                kwargs.update(dtype=rio.int8, count=1, driver='PNG')
                with rio.open(image_out, "w", **kwargs) as outndwiimg:
                    slices = [
                        (col_start, row_start, step, step)
                        for col_start in list(range(0, green.width, step))
                        for row_start in list(range(0, green.height, step))
                    ]
                    for slc in slices:
                        win = Window(*slc)

                        nir_data = nir.read(1, window=win).astype(float)
                        vis_data = green.read(1, window=win).astype(float)

                        ndwi = (nir_data - vis_data) / (nir_data + vis_data)
                        ndwi_hist = (ndwi + 1) * (255/(-2))

                        write_win = Window(
                            slc[0], slc[1],
                            ndwi.shape[1], ndwi.shape[0]
                        )
                        outndwi.write_band(1, ndwi.astype(rio.float64),
                                        window=write_win)
                        outndwiimg.write_band(1, ndwi_hist.astype(rio.uint8),
                                        window=write_win)

    subprocess.call([
        "gdal2tiles.py", "-w", "leaflet", "-t",
        "NDWI index", image_out, tiles_out
    ])

    return {
        "raster": raster_out,
        "image": image_out,
        "tiles": tiles_out,
        "vector": None
    }
