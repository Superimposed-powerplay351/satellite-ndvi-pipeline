#!/usr/bin/env python3
"""
Demo client for the Satellite NDVI SaaS API.

Usage:
    python client_demo.py --api-url https://xxx.execute-api.ap-southeast-2.amazonaws.com/prod --api-key YOUR_KEY

    # Or set environment variables:
    export NDVI_API_URL=https://xxx.execute-api.ap-southeast-2.amazonaws.com/prod
    export NDVI_API_KEY=your-api-key
    python client_demo.py
"""
import argparse
import json
import os
import requests


def process_ndvi(api_url, api_key, tile, date, threshold=0.4):
    """Call the NDVI API to process a tile."""
    resp = requests.post(
        f"{api_url}/ndvi",
        headers={"x-api-key": api_key, "Content-Type": "application/json"},
        json={"tile": tile, "date": date, "threshold": threshold},
    )
    resp.raise_for_status()
    return resp.json()


def health_check(api_url, api_key):
    """Check API health."""
    resp = requests.get(f"{api_url}/health", headers={"x-api-key": api_key})
    resp.raise_for_status()
    return resp.json()


def main():
    parser = argparse.ArgumentParser(description="NDVI SaaS API Client")
    parser.add_argument("--api-url", default=os.environ.get("NDVI_API_URL"))
    parser.add_argument("--api-key", default=os.environ.get("NDVI_API_KEY"))
    parser.add_argument("--tile", default="36/R/UU")
    parser.add_argument("--date", default="2024-01")
    parser.add_argument("--threshold", type=float, default=0.4)
    args = parser.parse_args()

    if not args.api_url or not args.api_key:
        print("Error: --api-url and --api-key required (or set NDVI_API_URL / NDVI_API_KEY)")
        return

    print(f"API: {args.api_url}")
    print(f"Tile: {args.tile}, Date: {args.date}, Threshold: {args.threshold}\n")

    # Health check
    print("--- Health Check ---")
    print(json.dumps(health_check(args.api_url, args.api_key), indent=2))

    # Process NDVI
    print("\n--- Process NDVI ---")
    result = process_ndvi(args.api_url, args.api_key, args.tile, args.date, args.threshold)
    print(f"Status: {result['status']}")
    print(f"Vegetation polygons: {result['vegetation_polygons']}")
    print(f"GeoTIFF: {result['output_tif']}")
    print(f"GeoJSON: {result['output_geojson']}")

    # Save GeoJSON locally
    if "geojson" in result:
        out_path = "ndvi_result.geojson"
        with open(out_path, "w") as f:
            json.dump(result["geojson"], f, indent=2)
        print(f"\nGeoJSON saved to: {out_path} (open in QGIS)")


if __name__ == "__main__":
    main()
