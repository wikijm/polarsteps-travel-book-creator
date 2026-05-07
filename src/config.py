from pathlib import Path

# Paths
SRC_PATH = Path(__file__).resolve().parent
PROJECT_ROOT = SRC_PATH.parent
DATA_PATH = PROJECT_ROOT / "data"
TRIP_DATA_PATH = DATA_PATH / "polarsteps-trip"
OUTPUT_PATH = PROJECT_ROOT / "travel_book"
ASSETS_PATH = PROJECT_ROOT / "assets"

# File Names
HTML_FILE_NAME = "travel_book.html"
PDF_FILE_NAME = "travel_book.pdf"

# API Settings
ELEVATION_API_URL = "https://api.opentopodata.org/v1/aster30m"
MAX_LOCATIONS_PER_REQUEST = 100
MAX_CALLS_PER_DAY = 1000

# Locale Settings
DEFAULT_LOCALE = "fr_FR.UTF-8"
WINDOWS_LOCALE = "French_France.1252"
