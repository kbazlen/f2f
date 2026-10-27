"""File paths shared by the Quarto reports."""

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT.parent / "data" / "f2f_benchmark_v1.0.0-rc2"
STATE_SHAPEFILE = (
    PROJECT_ROOT / "data" / "cb_2018_us_state_500k 2" / "cb_2018_us_state_500k.shp"
)

CATCHMENT_FIRE_PATH = DATA_DIR / "fire/catchment_fire.parquet"
CATCHMENT_SEVERITY_PATH = DATA_DIR / "fire/catchment_severity.parquet"
UPSTREAM_FIRE_PATH = DATA_DIR / "fire/upstream_fire_by_comid.parquet"
UPSTREAM_SEVERITY_PATH = DATA_DIR / "fire/upstream_severity_by_comid.parquet"
SITE_UPSTREAM_FIRE_PATH = DATA_DIR / "fire/site_upstream_fire.parquet"
SITE_NHD_PATH = DATA_DIR / "sites/site_nhd.parquet"
PANEL_PATH = DATA_DIR / "panel/site_year_panel.parquet"
