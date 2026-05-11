"""
Generate sample NDVI GeoTIFF and GeoJSON for demo purposes.
Run: python generate_sample.py
Outputs to: data-sample/
"""
import numpy as np
import json
import os

try:
    import rasterio
    from rasterio.transform import from_bounds
    HAS_RASTERIO = True
except ImportError:
    HAS_RASTERIO = False

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "..", "data-sample")
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Perth, WA bounding box (small area)
WEST, SOUTH, EAST, NORTH = 115.8, -32.0, 116.0, -31.85
WIDTH, HEIGHT = 200, 200

# Generate synthetic NDVI (gradient + noise to simulate vegetation patterns)
np.random.seed(42)
x = np.linspace(0, 3 * np.pi, WIDTH)
y = np.linspace(0, 3 * np.pi, HEIGHT)
xx, yy = np.meshgrid(x, y)
ndvi = 0.3 + 0.4 * np.sin(xx) * np.cos(yy) + 0.1 * np.random.randn(HEIGHT, WIDTH)
ndvi = np.clip(ndvi, -1, 1).astype(np.float32)

if HAS_RASTERIO:
    transform = from_bounds(WEST, SOUTH, EAST, NORTH, WIDTH, HEIGHT)
    profile = {
        "driver": "GTiff",
        "dtype": "float32",
        "width": WIDTH,
        "height": HEIGHT,
        "count": 1,
        "crs": "EPSG:4326",
        "transform": transform,
        "compress": "deflate",
    }
    tif_path = os.path.join(OUTPUT_DIR, "ndvi_sample.tif")
    with rasterio.open(tif_path, "w", **profile) as dst:
        dst.write(ndvi, 1)
    print(f"Written: {tif_path}")
else:
    print("rasterio not installed — skipping GeoTIFF generation")
    print("Install with: pip install rasterio")

# Generate sample GeoJSON (vegetation polygons)
features = []
# Create a few rectangular "vegetation" polygons
veg_areas = [
    (115.85, -31.95, 115.90, -31.90),
    (115.92, -31.98, 115.97, -31.93),
    (115.82, -31.88, 115.87, -31.86),
]
for i, (w, s, e, n) in enumerate(veg_areas):
    features.append({
        "type": "Feature",
        "properties": {"id": i + 1, "ndvi_class": "vegetation", "mean_ndvi": round(0.5 + 0.1 * i, 2)},
        "geometry": {
            "type": "Polygon",
            "coordinates": [[[w, s], [e, s], [e, n], [w, n], [w, s]]],
        },
    })

geojson = {"type": "FeatureCollection", "features": features}
geojson_path = os.path.join(OUTPUT_DIR, "ndvi_vegetation_sample.geojson")
with open(geojson_path, "w") as f:
    json.dump(geojson, f, indent=2)
print(f"Written: {geojson_path}")
