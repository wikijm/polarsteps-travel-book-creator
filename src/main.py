import locale
import logging
import sys
import io
from pathlib import Path
from tqdm import tqdm

from arguments_manager import ArgumentManager
from data_parser import DataParser
from elevation_api import ElevationAPI
from html_generator import HTMLGenerator
from map_manager import MapManager
from pdf_generator import PDFGenerator
from photo_manager import PhotoManager
import config

# Setup logging
log_handler = logging.StreamHandler(sys.stdout)
log_handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
try:
    log_handler.stream.reconfigure(encoding='utf-8')
except (AttributeError, io.UnsupportedOperation):
    pass # Not all streams support reconfiguration

logging.basicConfig(
    level=logging.INFO,
    handlers=[log_handler],
)
logger = logging.getLogger(__name__)


class TravelBookCreator:
    def __init__(self):
        self.args = ArgumentManager()
        self.data_parser = DataParser()
        self.html_generator = HTMLGenerator()
        self.map_manager = MapManager()
        self.pdf_generator = PDFGenerator()
        self.photo_manager = PhotoManager()

        self._setup_locale()

    def _setup_locale(self):
        try:
            locale.setlocale(locale.LC_TIME, config.DEFAULT_LOCALE)
        except locale.Error:
            try:
                # Fallback for Windows
                locale.setlocale(locale.LC_TIME, config.WINDOWS_LOCALE)
            except locale.Error:
                logger.warning(
                    f"Could not set locale to {config.DEFAULT_LOCALE} or {config.WINDOWS_LOCALE}. "
                    "Falling back to default locale."
                )

    def run(self):
        logger.info("🚀 Starting Travel Book generation...")

        if not config.TRIP_DATA_PATH.exists() or not config.TRIP_DATA_PATH.joinpath("trip.json").exists():
            logger.error(f"Trip data not found in {config.TRIP_DATA_PATH}. Please ensure trip.json exists there.")
            sys.exit(1)

        # Parse data
        logger.info("Parsing trip data...")
        trip = self.data_parser.load(config.TRIP_DATA_PATH)

        # Filter steps if requested
        if self.args.step_indices:
            logger.info(f"Filtering for steps: {self.args.step_indices}")
            trip.steps = [s for i, s in enumerate(trip.steps, 1) if i in self.args.step_indices]

        # Load photos
        logger.info("Processing photos...")
        self.photo_manager.load_from_polarsteps_export(
            config.TRIP_DATA_PATH, config.OUTPUT_PATH / "assets/images/photos", trip
        )
        self.photo_manager.load_photos_pages(trip, config.OUTPUT_PATH)
        self.photo_manager.save_photos_pages(trip, config.OUTPUT_PATH)

        # Get elevation
        logger.info("Fetching elevation data...")
        locations = [step.get_lat_lon_as_tuple() for step in trip.steps]
        elevation_api = ElevationAPI(cache_directory=config.OUTPUT_PATH)
        
        elevations = []
        # Process in chunks to show progress
        for i in tqdm(range(0, len(locations), config.MAX_LOCATIONS_PER_REQUEST), desc="Elevations"):
            chunk = locations[i : i + config.MAX_LOCATIONS_PER_REQUEST]
            elevations.extend(elevation_api.get_elevation(chunk))

        for step, elevation in zip(trip.steps, elevations):
            if elevation is not None:
                step.elevation = int(elevation)

        # Maps management
        logger.info("Downloading and updating maps...")
        self.map_manager.download_maps_from_trip(
            trip, config.OUTPUT_PATH / "assets/images/maps"
        )
        self.map_manager.update_style(config.OUTPUT_PATH / "assets/images/maps")

        for step in trip.steps:
            step.position_percentage = self.map_manager.calculate_position_percentage(step)

        # HTML generation
        logger.info("Generating HTML...")
        self.html_generator.generate(trip, config.OUTPUT_PATH / config.HTML_FILE_NAME)

        # PDF generation
        if not self.args.no_pdf:
            logger.info("Generating PDF (this may take a while)...")
            self.pdf_generator.generate(
                config.OUTPUT_PATH / config.HTML_FILE_NAME,
                config.OUTPUT_PATH / config.PDF_FILE_NAME,
            )

        logger.info("✅ Travel book has been successfully generated!")


if __name__ == "__main__":
    creator = TravelBookCreator()
    creator.run()
