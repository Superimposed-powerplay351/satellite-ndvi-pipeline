"""
API Gateway handler for the NDVI processing pipeline.
Accepts HTTP requests, validates input, invokes NDVI processing, returns results.
"""
import json
import os
from handler import compute_ndvi, ndvi_to_geojson

import numpy as np
import rasterio
import boto3

S3 = boto3.client("s3")
OUTPUT_BUCKET = os.environ["OUTPUT_BUCKET"]
INPUT_BUCKET = os.environ.get("INPUT_BUCKET")


def api_handler(event, context):
    """API Gateway Lambda proxy handler."""
    try:
        body = json.loads(event.get("body") or "{}")
    except json.JSONDecodeError:
        return _response(400, {"error": "Invalid JSON body"})

    tile = body.get("tile")
    date = body.get("date")
    threshold = body.get("threshold", 0.4)

    if not tile or not date:
        return _response(400, {"error": "Required fields: tile, date"})

    prefix = f"{tile}/{date}"

    try:
        # Check if already processed (cache)
        output_prefix = f"output/{prefix}"
        try:
            S3.head_object(Bucket=OUTPUT_BUCKET, Key=f"{output_prefix}/ndvi.tif")
            # Already exists — return cached result
            geojson_obj = S3.get_object(Bucket=OUTPUT_BUCKET, Key=f"{output_prefix}/ndvi_vegetation.geojson")
            geojson = json.loads(geojson_obj["Body"].read())
            return _response(200, {
                "status": "cached",
                "tile": tile,
                "date": date,
                "output_tif": f"s3://{OUTPUT_BUCKET}/{output_prefix}/ndvi.tif",
                "output_geojson": f"s3://{OUTPUT_BUCKET}/{output_prefix}/ndvi_vegetation.geojson",
                "vegetation_polygons": len(geojson["features"]),
                "geojson": geojson,
            })
        except S3.exceptions.ClientError:
            pass  # Not cached, process it

        # Read bands
        if INPUT_BUCKET:
            red_path = f"/tmp/B04.tif"
            nir_path = f"/tmp/B08.tif"
            S3.download_file(INPUT_BUCKET, f"input/{prefix}/B04.tif", red_path)
            S3.download_file(INPUT_BUCKET, f"input/{prefix}/B08.tif", nir_path)
        else:
            base = os.environ.get("SENTINEL2_BASE", "https://sentinel-cogs.s3.us-west-2.amazonaws.com/sentinel-s2-l2a-cogs")
            red_path = f"/vsicurl/{base}/{prefix}/B04.tif"
            nir_path = f"/vsicurl/{base}/{prefix}/B08.tif"

        with rasterio.open(red_path) as src:
            red = src.read(1)
            profile = src.profile.copy()
            transform = src.transform

        with rasterio.open(nir_path) as src:
            nir = src.read(1)

        # Compute NDVI
        ndvi = compute_ndvi(red, nir)

        # Write outputs
        profile.update(dtype=rasterio.float32, count=1, compress="deflate")
        ndvi_tif_path = "/tmp/ndvi.tif"
        with rasterio.open(ndvi_tif_path, "w", **profile) as dst:
            dst.write(ndvi.astype(np.float32), 1)

        geojson = ndvi_to_geojson(ndvi, transform, threshold=threshold)
        geojson_path = "/tmp/ndvi_vegetation.geojson"
        with open(geojson_path, "w") as f:
            json.dump(geojson, f)

        # Upload to S3
        S3.upload_file(ndvi_tif_path, OUTPUT_BUCKET, f"{output_prefix}/ndvi.tif")
        S3.upload_file(geojson_path, OUTPUT_BUCKET, f"{output_prefix}/ndvi_vegetation.geojson")

        return _response(200, {
            "status": "processed",
            "tile": tile,
            "date": date,
            "threshold": threshold,
            "output_tif": f"s3://{OUTPUT_BUCKET}/{output_prefix}/ndvi.tif",
            "output_geojson": f"s3://{OUTPUT_BUCKET}/{output_prefix}/ndvi_vegetation.geojson",
            "vegetation_polygons": len(geojson["features"]),
            "geojson": geojson,
        })

    except Exception as e:
        return _response(500, {"error": str(e)})


def _response(status_code, body):
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
        },
        "body": json.dumps(body),
    }
