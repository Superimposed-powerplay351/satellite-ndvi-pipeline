"""
Download real Sentinel-2 bands from AWS Open Data (free, public, no auth needed)
and compute actual NDVI over Perth, WA.

Usage: python download_real_ndvi.py
Output: data-sample/ndvi_real.tif, data-sample/ndvi_real_vegetation.geojson
"""
import os
import json
import numpy as np
import rasterio
from rasterio.windows import Window
from rasterio.features import shapes

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "..", "data-sample")
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Sentinel-2 L2A COG on AWS Open Data (free, no credentials needed)
# This is a real tile covering Perth, Western Australia
# Tile: S2B_55HBU (covers Perth metro area)
# Using a known good scene from 2023
COG_BASE = "https://sentinel-cogs.s3.us-west-2.amazonaws.com/sentinel-s2-l2a-cogs/55/H/BU/2023/1/S2B_55HBU_20230115_0_L2A"

RED_URL = f"{COG_BASE}/B04.tif"   # Red band (10m)
NIR_URL = f"{COG_BASE}/B08.tif"   # NIR band (10m)

# Read a small window (500x500 pixels = 5km x 5km at 10m resolution)
# This keeps download fast while showing real vegetation patterns
WINDOW = Window(col_off=4000, row_off=4000, width=500, height=500)


def main():
    print(f"Reading Red band from:\n  {RED_URL}")
    print(f"  Window: {WINDOW}")

    with rasterio.open(f"/vsicurl/{RED_URL}") as src:
        red = src.read(1, window=WINDOW).astype(float)
        profile = src.profile.copy()
        transform = src.window_transform(WINDOW)

    print(f"Reading NIR band from:\n  {NIR_URL}")
    with rasterio.open(f"/vsicurl/{NIR_URL}") as src:
        nir = src.read(1, window=WINDOW).astype(float)

    # Compute NDVI
    print("Computing NDVI...")
    with np.errstate(divide="ignore", invalid="ignore"):
        ndvi = (nir - red) / (nir + red)
        ndvi = np.nan_to_num(ndvi, nan=0.0)

    ndvi = ndvi.astype(np.float32)
    print(f"  NDVI range: {ndvi.min():.3f} to {ndvi.max():.3f}")
    print(f"  Pixels with NDVI >= 0.4: {(ndvi >= 0.4).sum()} / {ndvi.size}")

    # Write GeoTIFF
    profile.update(
        dtype="float32", count=1, compress="deflate",
        width=WINDOW.width, height=WINDOW.height,
        transform=transform,
    )
    tif_path = os.path.join(OUTPUT_DIR, "ndvi_real.tif")
    with rasterio.open(tif_path, "w", **profile) as dst:
        dst.write(ndvi, 1)
    print(f"Written: {tif_path}")

    # Vectorize vegetation (NDVI >= 0.4)
    mask = (ndvi >= 0.4).astype(np.uint8)
    features = []
    for geom, value in shapes(mask, transform=transform):
        if value == 1:
            features.append({
                "type": "Feature",
                "properties": {"class": "vegetation", "ndvi_threshold": 0.4},
                "geometry": geom,
            })

    geojson = {"type": "FeatureCollection", "features": features}
    geojson_path = os.path.join(OUTPUT_DIR, "ndvi_real_vegetation.geojson")
    with open(geojson_path, "w") as f:
        json.dump(geojson, f)
    print(f"Written: {geojson_path} ({len(features)} polygons)")
    print("\nDone! Open these in QGIS to see real vegetation patterns near Perth.")


if __name__ == "__main__":
    main()
