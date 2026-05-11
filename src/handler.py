"""
Lambda handler: Fetches Sentinel-2 COG bands from AWS Open Data,
computes NDVI, exports GeoTIFF + GeoJSON polygons to S3.
"""
import os
import json
import numpy as np
import rasterio
from rasterio.features import shapes
from rasterio.transform import from_bounds
from shapely.geometry import shape, mapping
import boto3

S3 = boto3.client("s3")
OUTPUT_BUCKET = os.environ["OUTPUT_BUCKET"]
# Sentinel-2 COG base URL (AWS Open Data)
SENTINEL2_BASE = os.environ.get(
    "SENTINEL2_BASE",
    "https://sentinel-cogs.s3.us-west-2.amazonaws.com/sentinel-s2-l2a-cogs",
)


def compute_ndvi(red: np.ndarray, nir: np.ndarray) -> np.ndarray:
    """NDVI = (NIR - Red) / (NIR + Red)"""
    with np.errstate(divide="ignore", invalid="ignore"):
        ndvi = (nir.astype(float) - red.astype(float)) / (nir.astype(float) + red.astype(float))
        ndvi = np.nan_to_num(ndvi, nan=0.0)
    return ndvi


def ndvi_to_geojson(ndvi: np.ndarray, transform, threshold: float = 0.4):
    """Convert high-NDVI areas to GeoJSON polygons."""
    mask = (ndvi >= threshold).astype(np.uint8)
    features = []
    for geom, value in shapes(mask, transform=transform):
        if value == 1:
            features.append({
                "type": "Feature",
                "properties": {"ndvi_class": "vegetation", "threshold": threshold},
                "geometry": geom,
            })
    return {"type": "FeatureCollection", "features": features}


def handler(event, context):
    """
    Event can contain:
      - tile: Sentinel-2 tile ID (e.g., "36/R/UU")
      - date: acquisition date (e.g., "2024-01")
    Falls back to a demo tile if not provided.
    """
    tile = event.get("tile", "36/R/UU")
    date = event.get("date", "2024-01")
    prefix = f"{tile}/{date}"

    # For demo: use local sample or S3 input
    input_bucket = os.environ.get("INPUT_BUCKET")

    if input_bucket:
        # Read from S3 input bucket
        red_key = f"input/{prefix}/B04.tif"
        nir_key = f"input/{prefix}/B08.tif"
        red_path = f"/tmp/B04.tif"
        nir_path = f"/tmp/B08.tif"
        S3.download_file(input_bucket, red_key, red_path)
        S3.download_file(input_bucket, nir_key, nir_path)
    else:
        # Use Sentinel-2 COG directly via HTTPS (rasterio supports vsicurl)
        red_path = f"/vsicurl/{SENTINEL2_BASE}/{prefix}/B04.tif"
        nir_path = f"/vsicurl/{SENTINEL2_BASE}/{prefix}/B08.tif"

    # Read bands
    with rasterio.open(red_path) as src:
        red = src.read(1)
        profile = src.profile.copy()
        transform = src.transform

    with rasterio.open(nir_path) as src:
        nir = src.read(1)

    # Compute NDVI
    ndvi = compute_ndvi(red, nir)

    # Write NDVI GeoTIFF
    profile.update(dtype=rasterio.float32, count=1, compress="deflate")
    ndvi_tif_path = "/tmp/ndvi.tif"
    with rasterio.open(ndvi_tif_path, "w", **profile) as dst:
        dst.write(ndvi.astype(np.float32), 1)

    # Write GeoJSON
    geojson = ndvi_to_geojson(ndvi, transform)
    geojson_path = "/tmp/ndvi_vegetation.geojson"
    with open(geojson_path, "w") as f:
        json.dump(geojson, f)

    # Upload to S3
    output_prefix = f"output/{prefix}"
    S3.upload_file(ndvi_tif_path, OUTPUT_BUCKET, f"{output_prefix}/ndvi.tif")
    S3.upload_file(geojson_path, OUTPUT_BUCKET, f"{output_prefix}/ndvi_vegetation.geojson")

    return {
        "statusCode": 200,
        "body": json.dumps({
            "message": "NDVI processed",
            "output_tif": f"s3://{OUTPUT_BUCKET}/{output_prefix}/ndvi.tif",
            "output_geojson": f"s3://{OUTPUT_BUCKET}/{output_prefix}/ndvi_vegetation.geojson",
            "vegetation_polygons": len(geojson["features"]),
        }),
    }
