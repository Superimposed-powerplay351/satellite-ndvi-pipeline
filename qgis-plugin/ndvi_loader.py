"""
QGIS Plugin: NDVI Satellite Processor (Production)
Features: Date picker, Multi-index (NDVI/NDWI/NBR), Change detection, Alerts, WA tile selector
"""
import os
import json
import tempfile
from datetime import datetime, timedelta
from qgis.PyQt.QtWidgets import (
    QAction, QDialog, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QLineEdit, QPushButton, QComboBox, QMessageBox,
    QApplication, QGroupBox, QProgressBar, QTabWidget, QWidget,
    QSlider, QSpinBox, QDateEdit, QCheckBox, QTextEdit, QCalendarWidget,
)
from qgis.PyQt.QtCore import Qt, QThread, pyqtSignal, QDate
from qgis.PyQt.QtGui import QColor, QFont, QTextCharFormat, QBrush
from qgis.core import (
    QgsProject, QgsRasterLayer, QgsVectorLayer,
    QgsColorRampShader, QgsRasterShader, QgsSingleBandPseudoColorRenderer,
)

# WA Sentinel-2 tiles
WA_TILES = {
    "Perth Metro (55HBU)": "55/H/BU",
    "Perth South (55HCU)": "55/H/CU",
    "Mandurah/Bunbury (55HCV)": "55/H/CV",
    "Geraldton (50HMH)": "50/H/MH",
    "Kalgoorlie (51HXC)": "51/H/XC",
    "Albany (55HDA)": "55/H/DA",
    "Esperance (51HXD)": "51/H/XD",
    "Broome (51LUE)": "51/L/UE",
    "Karratha (50HLH)": "50/H/LH",
    "Margaret River (50HMJ)": "50/H/MJ",
}

AOI_PRESETS = {
    "Kings Park & Botanic Garden": (5200, 5400, 300, 300),
    "Swan River (Matilda Bay)": (5100, 5600, 400, 300),
    "Perth Northern Suburbs": (4000, 4000, 500, 500),
    "Darling Scarp (Hills)": (7000, 5000, 500, 500),
    "Joondalup Wetlands": (4500, 3200, 400, 400),
    "Custom": (4000, 4000, 500, 500),
}

INDEX_INFO = {
    "NDVI (Vegetation)": {
        "bands": ("B04", "B08"),
        "formula": "(NIR - Red) / (NIR + Red)",
        "description": "Vegetation health and density",
        "colors": [(-1, (165, 0, 38)), (0, (255, 255, 190)), (0.3, (173, 221, 142)), (0.6, (50, 160, 44)), (1, (0, 104, 55))],
    },
    "NDWI (Water)": {
        "bands": ("B03", "B08"),
        "formula": "(Green - NIR) / (Green + NIR)",
        "description": "Water bodies and moisture stress",
        "colors": [(-1, (165, 0, 38)), (-0.3, (255, 255, 190)), (0, (173, 221, 242)), (0.3, (50, 130, 200)), (1, (0, 50, 150))],
    },
    "NBR (Burn Ratio)": {
        "bands": ("B08", "B12"),
        "formula": "(NIR - SWIR) / (NIR + SWIR)",
        "description": "Fire scars and burn severity",
        "colors": [(-1, (165, 0, 38)), (-0.2, (255, 100, 50)), (0, (255, 255, 190)), (0.3, (173, 221, 142)), (1, (0, 104, 55))],
    },
}

STYLESHEET = """
QDialog { background-color: #1e1e2e; color: #cdd6f4; }
QGroupBox {
    font-weight: bold; border: 1px solid #45475a; border-radius: 8px;
    margin-top: 12px; padding-top: 16px; color: #cdd6f4;
}
QGroupBox::title { subcontrol-origin: margin; left: 12px; padding: 0 6px; }
QPushButton {
    background-color: #89b4fa; color: #1e1e2e; border: none;
    border-radius: 6px; padding: 8px 16px; font-weight: bold;
}
QPushButton:hover { background-color: #b4d0fb; }
QPushButton:pressed { background-color: #74c7ec; }
QPushButton#btnProcess { background-color: #a6e3a1; font-size: 14px; padding: 12px; }
QPushButton#btnProcess:hover { background-color: #c6f0c2; }
QPushButton#btnCompare { background-color: #fab387; font-size: 13px; padding: 10px; }
QPushButton#btnCompare:hover { background-color: #fcc8a8; }
QComboBox {
    background-color: #313244; color: #cdd6f4;
    border: 1px solid #45475a; border-radius: 6px; padding: 6px;
}
QComboBox QAbstractItemView { background-color: #313244; color: #cdd6f4; selection-background-color: #89b4fa; }
QLineEdit, QSpinBox, QDateEdit {
    background-color: #313244; color: #cdd6f4;
    border: 1px solid #45475a; border-radius: 6px; padding: 6px; min-height: 20px;
}
QLineEdit:focus, QSpinBox:focus, QDateEdit:focus { border: 1px solid #89b4fa; }
QLabel { color: #cdd6f4; }
QLabel#title { font-size: 18px; font-weight: bold; color: #89b4fa; }
QLabel#subtitle { color: #a6adc8; font-size: 11px; }
QLabel#description { color: #a6adc8; font-style: italic; }
QLabel#alert { color: #f38ba8; font-weight: bold; }
QProgressBar {
    border: 1px solid #45475a; border-radius: 6px;
    text-align: center; color: #1e1e2e; background-color: #313244;
}
QProgressBar::chunk { background-color: #a6e3a1; border-radius: 5px; }
QTabWidget::pane { border: 1px solid #45475a; border-radius: 8px; background-color: #1e1e2e; }
QTabBar::tab {
    background-color: #313244; color: #cdd6f4;
    padding: 8px 16px; border-top-left-radius: 6px; border-top-right-radius: 6px; margin-right: 2px;
}
QTabBar::tab:selected { background-color: #89b4fa; color: #1e1e2e; }
QSlider::groove:horizontal { height: 6px; background: #45475a; border-radius: 3px; }
QSlider::handle:horizontal { background: #89b4fa; width: 16px; margin: -5px 0; border-radius: 8px; }
QTextEdit { background-color: #313244; color: #cdd6f4; border: 1px solid #45475a; border-radius: 6px; }
QCheckBox { color: #cdd6f4; }
QCheckBox::indicator { width: 16px; height: 16px; }
"""


def get_sentinel2_dates(tile, year):
    """
    Generate likely Sentinel-2 acquisition dates for a tile.
    Sentinel-2A and 2B together give ~5-day revisit over Australia.
    We use known orbit patterns to estimate available dates.
    """
    # Known reference dates for S2A and S2B over Perth (55HBU)
    # S2A reference: 2023-01-05, S2B reference: 2023-01-10
    from datetime import date
    ref_a = date(2023, 1, 5)
    ref_b = date(2023, 1, 10)
    start = date(year, 1, 1)
    end = date(year, 12, 31)

    dates = set()
    # S2A: every 10 days from reference
    d = ref_a
    while d <= end:
        if d >= start:
            dates.add(d)
        d += timedelta(days=10)
    # Go backwards too
    d = ref_a - timedelta(days=10)
    while d >= start:
        dates.add(d)
        d -= timedelta(days=10)

    # S2B: every 10 days from reference
    d = ref_b
    while d <= end:
        if d >= start:
            dates.add(d)
        d += timedelta(days=10)
    d = ref_b - timedelta(days=10)
    while d >= start:
        dates.add(d)
        d -= timedelta(days=10)

    return sorted(dates)


class Sentinel2Calendar(QCalendarWidget):
    """Calendar that highlights available Sentinel-2 dates and greys out others."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.available_dates = set()
        self.setGridVisible(True)
        self._update_year(self.yearShown())
        self.currentPageChanged.connect(self._on_page_changed)

    def set_tile(self, tile):
        """Update available dates when tile changes."""
        self._update_year(self.yearShown())

    def _on_page_changed(self, year, month):
        self._update_year(year)

    def _update_year(self, year):
        self.available_dates = set(get_sentinel2_dates("", year))
        self._apply_formatting()

    def _apply_formatting(self):
        # Reset all
        default_fmt = QTextCharFormat()
        available_fmt = QTextCharFormat()
        available_fmt.setBackground(QBrush(QColor(166, 227, 161)))  # green
        available_fmt.setForeground(QBrush(QColor(30, 30, 46)))

        unavailable_fmt = QTextCharFormat()
        unavailable_fmt.setForeground(QBrush(QColor(88, 91, 112)))  # grey

        # Apply to all dates in current view
        year = self.yearShown()
        month = self.monthShown()
        from datetime import date
        import calendar
        days_in_month = calendar.monthrange(year, month)[1]

        for day in range(1, days_in_month + 1):
            d = date(year, month, day)
            qd = QDate(year, month, day)
            if d in self.available_dates:
                self.setDateTextFormat(qd, available_fmt)
            else:
                self.setDateTextFormat(qd, unavailable_fmt)

    def paintCell(self, painter, rect, date):
        """Override to ensure formatting is applied."""
        super().paintCell(painter, rect, date)


class Sentinel2DateEdit(QWidget):
    """Date picker with Sentinel-2 aware calendar."""
    dateChanged = pyqtSignal(QDate)

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)

        self.date_edit = QDateEdit()
        self.date_edit.setDate(QDate(2023, 1, 15))
        self.date_edit.setDisplayFormat("yyyy-MM-dd")
        self.date_edit.setCalendarPopup(True)

        # Replace default calendar with our custom one
        self.calendar = Sentinel2Calendar()
        self.date_edit.setCalendarWidget(self.calendar)
        self.date_edit.dateChanged.connect(self.dateChanged.emit)

        layout.addWidget(self.date_edit)
        self.setLayout(layout)

    def date(self):
        return self.date_edit.date()

    def setDate(self, qdate):
        self.date_edit.setDate(qdate)


class ProcessWorker(QThread):
    """Background thread for downloading and processing satellite data."""
    progress = pyqtSignal(int, str)
    finished = pyqtSignal(str, str, int, str)  # tif_path, geojson_path, polygon_count, index_name
    error = pyqtSignal(str)

    def __init__(self, tile, date_str, window, threshold, index_name):
        super().__init__()
        self.tile = tile
        self.date_str = date_str
        self.window = window
        self.threshold = threshold
        self.index_name = index_name

    def _find_scene(self):
        """Construct scene URL from tile and date, trying both S2A and S2B."""
        import rasterio
        dt = datetime.strptime(self.date_str, "%Y-%m-%d")
        tile_id = self.tile.replace("/", "")
        base = "https://sentinel-cogs.s3.us-west-2.amazonaws.com/sentinel-s2-l2a-cogs"
        for sat in ["S2B", "S2A"]:
            scene = f"{self.tile}/{dt.year}/{dt.month}/{sat}_{tile_id}_{dt.strftime('%Y%m%d')}_0_L2A"
            url = f"/vsicurl/{base}/{scene}/B04.tif"
            try:
                with rasterio.open(url) as src:
                    pass
                return scene
            except Exception:
                continue
        raise RuntimeError(f"No Sentinel-2 scene found for {self.tile} on {self.date_str}. Try a nearby date (green in calendar).")

    def run(self):
        try:
            import numpy as np
            import rasterio
            from rasterio.windows import Window
            from rasterio.features import shapes

            index_cfg = INDEX_INFO[self.index_name]
            band1_name, band2_name = index_cfg["bands"]

            scene = self._find_scene()
            cog_base = f"https://sentinel-cogs.s3.us-west-2.amazonaws.com/sentinel-s2-l2a-cogs/{scene}"

            col_off, row_off, width, height = self.window
            window = Window(col_off=col_off, row_off=row_off, width=width, height=height)

            self.progress.emit(15, f"Downloading {band1_name}...")
            band1_url = f"/vsicurl/{cog_base}/{band1_name}.tif"
            with rasterio.open(band1_url) as src:
                band1 = src.read(1, window=window).astype(float)
                profile = src.profile.copy()
                transform = src.window_transform(window)

            self.progress.emit(45, f"Downloading {band2_name}...")
            band2_url = f"/vsicurl/{cog_base}/{band2_name}.tif"
            with rasterio.open(band2_url) as src:
                band2 = src.read(1, window=window).astype(float)

            self.progress.emit(70, f"Computing {self.index_name.split(' ')[0]}...")
            with np.errstate(divide="ignore", invalid="ignore"):
                if "NDWI" in self.index_name:
                    index = (band1 - band2) / (band1 + band2)  # (Green - NIR)
                else:
                    index = (band2 - band1) / (band2 + band1)  # (NIR - Red) or (NIR - SWIR)
                index = np.nan_to_num(index, nan=0.0).astype(np.float32)

            self.progress.emit(85, "Vectorizing...")
            tmp_dir = tempfile.mkdtemp(prefix="ndvi_")
            profile.update(dtype="float32", count=1, compress="deflate",
                           width=width, height=height, transform=transform)

            tif_path = os.path.join(tmp_dir, "index.tif")
            with rasterio.open(tif_path, "w", **profile) as dst:
                dst.write(index, 1)

            mask = (index >= self.threshold).astype(np.uint8)
            features = []
            for geom, value in shapes(mask, transform=transform):
                if value == 1:
                    features.append({"type": "Feature",
                                     "properties": {"class": "detected", "index": self.index_name},
                                     "geometry": geom})

            geojson_path = os.path.join(tmp_dir, "detected.geojson")
            with open(geojson_path, "w") as f:
                json.dump({"type": "FeatureCollection", "features": features}, f)

            self.progress.emit(100, "Done!")
            self.finished.emit(tif_path, geojson_path, len(features), self.index_name)

        except Exception as e:
            self.error.emit(str(e))


class ChangeDetectionWorker(QThread):
    """Compare two dates and detect change."""
    progress = pyqtSignal(int, str)
    finished = pyqtSignal(str, str, int, float)  # tif_path, geojson_path, alert_count, mean_change
    error = pyqtSignal(str)

    def __init__(self, tile, date1, date2, window, index_name, alert_threshold):
        super().__init__()
        self.tile = tile
        self.date1 = date1
        self.date2 = date2
        self.window = window
        self.index_name = index_name
        self.alert_threshold = alert_threshold

    def _scene_url(self, date_str):
        import rasterio
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        tile_id = self.tile.replace("/", "")
        base = "https://sentinel-cogs.s3.us-west-2.amazonaws.com/sentinel-s2-l2a-cogs"
        for sat in ["S2B", "S2A"]:
            scene = f"{self.tile}/{dt.year}/{dt.month}/{sat}_{tile_id}_{dt.strftime('%Y%m%d')}_0_L2A"
            url = f"{base}/{scene}"
            try:
                with rasterio.open(f"/vsicurl/{url}/B04.tif") as src:
                    pass
                return url
            except Exception:
                continue
        raise RuntimeError(f"No scene found for {self.tile} on {date_str}. Try a nearby date.")

    def run(self):
        try:
            import numpy as np
            import rasterio
            from rasterio.windows import Window
            from rasterio.features import shapes

            index_cfg = INDEX_INFO[self.index_name]
            band1_name, band2_name = index_cfg["bands"]
            col_off, row_off, width, height = self.window
            window = Window(col_off=col_off, row_off=row_off, width=width, height=height)

            # Process date 1
            self.progress.emit(10, f"Downloading {self.date1} bands...")
            base1 = self._scene_url(self.date1)
            with rasterio.open(f"/vsicurl/{base1}/{band1_name}.tif") as src:
                b1_d1 = src.read(1, window=window).astype(float)
                profile = src.profile.copy()
                transform = src.window_transform(window)
            with rasterio.open(f"/vsicurl/{base1}/{band2_name}.tif") as src:
                b2_d1 = src.read(1, window=window).astype(float)

            self.progress.emit(40, f"Downloading {self.date2} bands...")
            base2 = self._scene_url(self.date2)
            with rasterio.open(f"/vsicurl/{base2}/{band1_name}.tif") as src:
                b1_d2 = src.read(1, window=window).astype(float)
            with rasterio.open(f"/vsicurl/{base2}/{band2_name}.tif") as src:
                b2_d2 = src.read(1, window=window).astype(float)

            self.progress.emit(70, "Computing change...")
            with np.errstate(divide="ignore", invalid="ignore"):
                if "NDWI" in self.index_name:
                    idx1 = (b1_d1 - b2_d1) / (b1_d1 + b2_d1)
                    idx2 = (b1_d2 - b2_d2) / (b1_d2 + b2_d2)
                else:
                    idx1 = (b2_d1 - b1_d1) / (b2_d1 + b1_d1)
                    idx2 = (b2_d2 - b1_d2) / (b2_d2 + b1_d2)
                idx1 = np.nan_to_num(idx1, nan=0.0).astype(np.float32)
                idx2 = np.nan_to_num(idx2, nan=0.0).astype(np.float32)

            change = idx2 - idx1  # positive = gain, negative = loss
            mean_change = float(np.mean(change))

            self.progress.emit(85, "Detecting alerts...")
            tmp_dir = tempfile.mkdtemp(prefix="change_")
            profile.update(dtype="float32", count=1, compress="deflate",
                           width=width, height=height, transform=transform)

            tif_path = os.path.join(tmp_dir, "change.tif")
            with rasterio.open(tif_path, "w", **profile) as dst:
                dst.write(change, 1)

            # Alert: areas where index dropped more than threshold
            alert_mask = (change <= -self.alert_threshold).astype(np.uint8)
            features = []
            for geom, value in shapes(alert_mask, transform=transform):
                if value == 1:
                    features.append({"type": "Feature",
                                     "properties": {"alert": "significant_loss",
                                                    "index": self.index_name,
                                                    "dates": f"{self.date1} → {self.date2}"},
                                     "geometry": geom})

            geojson_path = os.path.join(tmp_dir, "alerts.geojson")
            with open(geojson_path, "w") as f:
                json.dump({"type": "FeatureCollection", "features": features}, f)

            self.progress.emit(100, "Done!")
            self.finished.emit(tif_path, geojson_path, len(features), mean_change)

        except Exception as e:
            self.error.emit(str(e))


class NdviDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("NDVI Satellite Processor")
        self.setMinimumSize(650, 620)
        self.resize(670, 640)
        self.setStyleSheet(STYLESHEET)
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout()
        layout.setSpacing(10)

        title = QLabel("🛰️  Satellite Index Processor")
        title.setObjectName("title")
        layout.addWidget(title)

        subtitle = QLabel("Process Sentinel-2 imagery across Western Australia")
        subtitle.setObjectName("subtitle")
        layout.addWidget(subtitle)

        tabs = QTabWidget()
        tabs.addTab(self._build_process_tab(), "🌍 Process")
        tabs.addTab(self._build_change_tab(), "📊 Change Detection")
        tabs.addTab(self._build_alerts_tab(), "🚨 Alerts")
        layout.addWidget(tabs)

        # Close
        close_layout = QHBoxLayout()
        close_layout.addStretch()
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.reject)
        close_layout.addWidget(close_btn)
        layout.addLayout(close_layout)

        self.setLayout(layout)

    def _build_process_tab(self):
        tab = QWidget()
        layout = QVBoxLayout()

        # Tile selector
        tile_group = QGroupBox("Tile & Location")
        tg_layout = QGridLayout()
        tg_layout.addWidget(QLabel("WA Tile:"), 0, 0)
        self.tile_combo = QComboBox()
        self.tile_combo.addItems(WA_TILES.keys())
        tg_layout.addWidget(self.tile_combo, 0, 1)

        tg_layout.addWidget(QLabel("Area of Interest:"), 1, 0)
        self.aoi_combo = QComboBox()
        self.aoi_combo.addItems(AOI_PRESETS.keys())
        self.aoi_combo.currentTextChanged.connect(self._on_aoi_changed)
        tg_layout.addWidget(self.aoi_combo, 1, 1)

        # Custom window
        self.custom_group = QGroupBox("Custom Window (pixels)")
        cg_layout = QGridLayout()
        self.spin_x = QSpinBox(); self.spin_x.setRange(0, 10980); self.spin_x.setValue(4000); self.spin_x.setMinimumWidth(80)
        self.spin_y = QSpinBox(); self.spin_y.setRange(0, 10980); self.spin_y.setValue(4000); self.spin_y.setMinimumWidth(80)
        self.spin_w = QSpinBox(); self.spin_w.setRange(100, 2000); self.spin_w.setValue(500); self.spin_w.setMinimumWidth(80)
        self.spin_h = QSpinBox(); self.spin_h.setRange(100, 2000); self.spin_h.setValue(500); self.spin_h.setMinimumWidth(80)
        cg_layout.addWidget(QLabel("X:"), 0, 0); cg_layout.addWidget(self.spin_x, 0, 1)
        cg_layout.addWidget(QLabel("Y:"), 0, 2); cg_layout.addWidget(self.spin_y, 0, 3)
        cg_layout.addWidget(QLabel("W:"), 1, 0); cg_layout.addWidget(self.spin_w, 1, 1)
        cg_layout.addWidget(QLabel("H:"), 1, 2); cg_layout.addWidget(self.spin_h, 1, 3)
        self.custom_group.setLayout(cg_layout)
        self.custom_group.setVisible(False)
        tg_layout.addWidget(self.custom_group, 2, 0, 1, 2)

        tile_group.setLayout(tg_layout)
        layout.addWidget(tile_group)

        # Date & Index
        opts_group = QGroupBox("Date & Index")
        og_layout = QGridLayout()

        og_layout.addWidget(QLabel("Date:"), 0, 0)
        self.date_edit = Sentinel2DateEdit()
        self.date_edit.setDate(QDate(2023, 1, 15))
        og_layout.addWidget(self.date_edit, 0, 1)

        og_layout.addWidget(QLabel("Index:"), 1, 0)
        self.index_combo = QComboBox()
        self.index_combo.addItems(INDEX_INFO.keys())
        og_layout.addWidget(self.index_combo, 1, 1)

        og_layout.addWidget(QLabel("Threshold:"), 2, 0)
        self.threshold_slider = QSlider(Qt.Horizontal)
        self.threshold_slider.setRange(10, 80)
        self.threshold_slider.setValue(40)
        self.threshold_slider.valueChanged.connect(self._on_threshold_changed)
        og_layout.addWidget(self.threshold_slider, 2, 1)
        self.threshold_label = QLabel("0.40")
        og_layout.addWidget(self.threshold_label, 2, 2)

        opts_group.setLayout(og_layout)
        layout.addWidget(opts_group)

        # Process button + progress
        self.process_btn = QPushButton("⚡  Process Area")
        self.process_btn.setObjectName("btnProcess")
        self.process_btn.setCursor(Qt.PointingHandCursor)
        layout.addWidget(self.process_btn)

        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)
        self.status_label = QLabel("")
        self.status_label.setObjectName("subtitle")
        layout.addWidget(self.status_label)

        layout.addStretch()
        tab.setLayout(layout)
        return tab

    def _build_change_tab(self):
        tab = QWidget()
        layout = QVBoxLayout()

        info = QLabel("Compare two dates to detect vegetation loss/gain")
        info.setObjectName("subtitle")
        layout.addWidget(info)

        dates_group = QGroupBox("Date Comparison")
        dg_layout = QGridLayout()

        dg_layout.addWidget(QLabel("Before:"), 0, 0)
        self.date1_edit = Sentinel2DateEdit()
        self.date1_edit.setDate(QDate(2023, 1, 15))
        dg_layout.addWidget(self.date1_edit, 0, 1)

        dg_layout.addWidget(QLabel("After:"), 1, 0)
        self.date2_edit = Sentinel2DateEdit()
        self.date2_edit.setDate(QDate(2023, 6, 15))
        dg_layout.addWidget(self.date2_edit, 1, 1)

        dg_layout.addWidget(QLabel("Index:"), 2, 0)
        self.change_index_combo = QComboBox()
        self.change_index_combo.addItems(INDEX_INFO.keys())
        dg_layout.addWidget(self.change_index_combo, 2, 1)

        dates_group.setLayout(dg_layout)
        layout.addWidget(dates_group)

        self.compare_btn = QPushButton("📊  Detect Changes")
        self.compare_btn.setObjectName("btnCompare")
        self.compare_btn.setCursor(Qt.PointingHandCursor)
        layout.addWidget(self.compare_btn)

        self.change_progress = QProgressBar()
        self.change_progress.setVisible(False)
        layout.addWidget(self.change_progress)
        self.change_status = QLabel("")
        self.change_status.setObjectName("subtitle")
        layout.addWidget(self.change_status)

        layout.addStretch()
        tab.setLayout(layout)
        return tab

    def _build_alerts_tab(self):
        tab = QWidget()
        layout = QVBoxLayout()

        info = QLabel("Configure alerts for significant index changes")
        info.setObjectName("subtitle")
        layout.addWidget(info)

        alert_group = QGroupBox("Alert Settings")
        ag_layout = QGridLayout()

        ag_layout.addWidget(QLabel("Alert when drop exceeds:"), 0, 0)
        self.alert_threshold_slider = QSlider(Qt.Horizontal)
        self.alert_threshold_slider.setRange(10, 50)
        self.alert_threshold_slider.setValue(30)
        self.alert_threshold_slider.valueChanged.connect(self._on_alert_threshold_changed)
        ag_layout.addWidget(self.alert_threshold_slider, 0, 1)
        self.alert_threshold_label = QLabel("0.30")
        ag_layout.addWidget(self.alert_threshold_label, 0, 2)

        self.alert_veg_cb = QCheckBox("Vegetation loss (NDVI drop)")
        self.alert_veg_cb.setChecked(True)
        ag_layout.addWidget(self.alert_veg_cb, 1, 0, 1, 2)

        self.alert_water_cb = QCheckBox("Water change (NDWI shift)")
        ag_layout.addWidget(self.alert_water_cb, 2, 0, 1, 2)

        self.alert_fire_cb = QCheckBox("Burn detection (NBR drop)")
        ag_layout.addWidget(self.alert_fire_cb, 3, 0, 1, 2)

        alert_group.setLayout(ag_layout)
        layout.addWidget(alert_group)

        # Alert log
        layout.addWidget(QLabel("Alert Log:"))
        self.alert_log = QTextEdit()
        self.alert_log.setReadOnly(True)
        self.alert_log.setMaximumHeight(150)
        self.alert_log.setPlaceholderText("Alerts will appear here after change detection...")
        layout.addWidget(self.alert_log)

        layout.addStretch()
        tab.setLayout(layout)
        return tab

    def _on_aoi_changed(self, name):
        self.custom_group.setVisible("Custom" in name)

    def _on_threshold_changed(self, value):
        self.threshold_label.setText(f"{value / 100:.2f}")

    def _on_alert_threshold_changed(self, value):
        self.alert_threshold_label.setText(f"{value / 100:.2f}")


class NdviPipelineLoader:
    def __init__(self, iface):
        self.iface = iface
        self.action = None
        self.dialog = None
        self.worker = None
        self.change_worker = None

    def initGui(self):
        self.action = QAction("🛰️ NDVI Processor", self.iface.mainWindow())
        self.action.triggered.connect(self.run)
        self.iface.addToolBarIcon(self.action)
        self.iface.addPluginToRasterMenu("NDVI Pipeline", self.action)

    def unload(self):
        self.iface.removeToolBarIcon(self.action)
        self.iface.removePluginRasterMenu("NDVI Pipeline", self.action)

    def run(self):
        self.dialog = NdviDialog(self.iface.mainWindow())
        self.dialog.process_btn.clicked.connect(self._process)
        self.dialog.compare_btn.clicked.connect(self._compare)
        self.dialog.show()

    def _get_window(self):
        aoi_name = self.dialog.aoi_combo.currentText()
        if "Custom" in aoi_name:
            return (self.dialog.spin_x.value(), self.dialog.spin_y.value(),
                    self.dialog.spin_w.value(), self.dialog.spin_h.value())
        return AOI_PRESETS[aoi_name]

    def _get_tile(self):
        tile_name = self.dialog.tile_combo.currentText()
        return WA_TILES[tile_name]

    def _process(self):
        tile = self._get_tile()
        date_str = self.dialog.date_edit.date().toString("yyyy-MM-dd")
        window = self._get_window()
        threshold = self.dialog.threshold_slider.value() / 100.0
        index_name = self.dialog.index_combo.currentText()

        self.dialog.progress_bar.setVisible(True)
        self.dialog.progress_bar.setValue(0)
        self.dialog.process_btn.setEnabled(False)
        self.dialog.status_label.setText("Starting...")

        self.worker = ProcessWorker(tile, date_str, window, threshold, index_name)
        self.worker.progress.connect(self._on_progress)
        self.worker.finished.connect(self._on_process_finished)
        self.worker.error.connect(self._on_process_error)
        self.worker.start()

    def _on_progress(self, value, msg):
        self.dialog.progress_bar.setValue(value)
        self.dialog.status_label.setText(msg)

    def _on_process_finished(self, tif_path, geojson_path, count, index_name):
        date_str = self.dialog.date_edit.date().toString("yyyy-MM-dd")
        aoi_name = self.dialog.aoi_combo.currentText()
        idx_short = index_name.split(" ")[0]

        raster = QgsRasterLayer(tif_path, f"{idx_short} — {aoi_name} ({date_str})")
        if raster.isValid():
            self._apply_style(raster, index_name)
            QgsProject.instance().addMapLayer(raster)

        vector = QgsVectorLayer(geojson_path, f"{idx_short} Detected — {aoi_name} ({date_str})", "ogr")
        if vector.isValid():
            QgsProject.instance().addMapLayer(vector)

        self.iface.mapCanvas().setExtent(raster.extent())
        self.iface.mapCanvas().refresh()

        self.dialog.process_btn.setEnabled(True)
        self.dialog.status_label.setText(f"✓ {count} polygons detected")
        self.iface.messageBar().pushSuccess("NDVI Processor", f"{idx_short}: {count} polygons")

    def _on_process_error(self, msg):
        self.dialog.process_btn.setEnabled(True)
        self.dialog.progress_bar.setVisible(False)
        QMessageBox.critical(self.dialog, "Error", msg)

    def _compare(self):
        tile = self._get_tile()
        date1 = self.dialog.date1_edit.date().toString("yyyy-MM-dd")
        date2 = self.dialog.date2_edit.date().toString("yyyy-MM-dd")
        window = self._get_window()
        index_name = self.dialog.change_index_combo.currentText()
        alert_threshold = self.dialog.alert_threshold_slider.value() / 100.0

        self.dialog.change_progress.setVisible(True)
        self.dialog.change_progress.setValue(0)
        self.dialog.compare_btn.setEnabled(False)
        self.dialog.change_status.setText("Starting comparison...")

        self.change_worker = ChangeDetectionWorker(tile, date1, date2, window, index_name, alert_threshold)
        self.change_worker.progress.connect(self._on_change_progress)
        self.change_worker.finished.connect(self._on_change_finished)
        self.change_worker.error.connect(self._on_change_error)
        self.change_worker.start()

    def _on_change_progress(self, value, msg):
        self.dialog.change_progress.setValue(value)
        self.dialog.change_status.setText(msg)

    def _on_change_finished(self, tif_path, geojson_path, alert_count, mean_change):
        date1 = self.dialog.date1_edit.date().toString("yyyy-MM-dd")
        date2 = self.dialog.date2_edit.date().toString("yyyy-MM-dd")
        index_name = self.dialog.change_index_combo.currentText()
        idx_short = index_name.split(" ")[0]

        # Add change raster (red = loss, green = gain)
        raster = QgsRasterLayer(tif_path, f"{idx_short} Change ({date1} → {date2})")
        if raster.isValid():
            self._apply_change_style(raster)
            QgsProject.instance().addMapLayer(raster)

        # Add alert polygons
        if alert_count > 0:
            vector = QgsVectorLayer(geojson_path, f"⚠️ ALERTS ({date1} → {date2})", "ogr")
            if vector.isValid():
                QgsProject.instance().addMapLayer(vector)

        self.iface.mapCanvas().setExtent(raster.extent())
        self.iface.mapCanvas().refresh()

        self.dialog.compare_btn.setEnabled(True)
        direction = "↓" if mean_change < 0 else "↑"
        self.dialog.change_status.setText(
            f"✓ Mean change: {direction} {abs(mean_change):.3f} | {alert_count} alert zones")

        # Log alerts
        if alert_count > 0:
            log_msg = f"[{datetime.now().strftime('%H:%M')}] {idx_short} {date1}→{date2}: {alert_count} alert zones (drop > {self.dialog.alert_threshold_slider.value()}%)\n"
            self.dialog.alert_log.append(log_msg)
            self.iface.messageBar().pushWarning("ALERT", f"{alert_count} areas with significant {idx_short} loss!")
        else:
            self.dialog.alert_log.append(f"[{datetime.now().strftime('%H:%M')}] No significant changes detected.\n")

    def _on_change_error(self, msg):
        self.dialog.compare_btn.setEnabled(True)
        self.dialog.change_progress.setVisible(False)
        QMessageBox.critical(self.dialog, "Error", msg)

    def _apply_style(self, layer, index_name):
        colors = INDEX_INFO[index_name]["colors"]
        shader = QgsRasterShader()
        ramp = QgsColorRampShader()
        ramp.setColorRampType(QgsColorRampShader.Interpolated)
        items = [QgsColorRampShader.ColorRampItem(val, QColor(*rgb), "") for val, rgb in colors]
        ramp.setColorRampItemList(items)
        shader.setRasterShaderFunction(ramp)
        renderer = QgsSingleBandPseudoColorRenderer(layer.dataProvider(), 1, shader)
        layer.setRenderer(renderer)

    def _apply_change_style(self, layer):
        shader = QgsRasterShader()
        ramp = QgsColorRampShader()
        ramp.setColorRampType(QgsColorRampShader.Interpolated)
        ramp.setColorRampItemList([
            QgsColorRampShader.ColorRampItem(-0.5, QColor(165, 0, 38), "Major Loss"),
            QgsColorRampShader.ColorRampItem(-0.2, QColor(255, 100, 50), "Loss"),
            QgsColorRampShader.ColorRampItem(0, QColor(255, 255, 200), "No Change"),
            QgsColorRampShader.ColorRampItem(0.2, QColor(100, 200, 100), "Gain"),
            QgsColorRampShader.ColorRampItem(0.5, QColor(0, 104, 55), "Major Gain"),
        ])
        shader.setRasterShaderFunction(ramp)
        renderer = QgsSingleBandPseudoColorRenderer(layer.dataProvider(), 1, shader)
        layer.setRenderer(renderer)
