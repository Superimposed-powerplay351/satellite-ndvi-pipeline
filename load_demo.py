"""
Run this inside QGIS Python Console (Plugins > Python Console):
    exec(open('/Users/00110138/Library/CloudStorage/OneDrive-UWA/Project/2026/AWS-Kiro/LocationIntelligence/satellite-ndvi-pipeline/load_demo.py').read())
"""
from qgis.core import QgsProject, QgsRasterLayer, QgsVectorLayer

BASE = "/Users/00110138/Library/CloudStorage/OneDrive-UWA/Project/2026/AWS-Kiro/LocationIntelligence/satellite-ndvi-pipeline/data-sample"

# Load NDVI raster
raster = QgsRasterLayer(f"{BASE}/ndvi_sample.tif", "NDVI Sample")
if raster.isValid():
    QgsProject.instance().addMapLayer(raster)
    print("✓ NDVI raster loaded")
else:
    print("✗ Failed to load raster")

# Load vegetation polygons
vector = QgsVectorLayer(f"{BASE}/ndvi_vegetation_sample.geojson", "Vegetation Polygons", "ogr")
if vector.isValid():
    QgsProject.instance().addMapLayer(vector)
    print("✓ Vegetation polygons loaded")
else:
    print("✗ Failed to load vector")

# Zoom to raster extent
iface.mapCanvas().setExtent(raster.extent())
iface.mapCanvas().refresh()
print("Done! You should see the NDVI raster over Perth, WA.")
