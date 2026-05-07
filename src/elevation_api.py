from itertools import islice
from pathlib import Path
from typing import Any, Dict, List, Tuple, Iterator, Optional
import requests
import time
import json
import os
import logging
import config

CACHE_FILE_NAME = "elevation_cache.json"
logger = logging.getLogger(__name__)


class ElevationAPI:
    def __init__(self, cache_directory: Path) -> None:
        self.api_url: str = config.ELEVATION_API_URL
        self.max_locations_per_request: int = config.MAX_LOCATIONS_PER_REQUEST
        self.max_calls_per_day: int = config.MAX_CALLS_PER_DAY
        self.calls_made: int = 0
        self.cache_file = cache_directory.joinpath(CACHE_FILE_NAME)

        # Load cache from file if it exists
        self.cache: Dict[str, Optional[float]] = self._load_cache()

    def get_elevation(
        self, locations: List[Tuple[float, float]]
    ) -> List[Optional[float]]:
        """
        Get the elevation for a list of locations in batches, using a caching layer and respecting API limitations.

        :param locations: A list of tuples where each tuple contains (latitude, longitude)
        :return: A list of elevations corresponding to each location
        """
        results: Dict[str, Optional[float]] = {}
        locations_to_query: List[Tuple[float, float]] = []

        # Identify which locations need to be queried
        for loc in locations:
            lat, lon = loc
            key: str = f"{lat},{lon}"
            if key in self.cache:
                results[key] = self.cache[key]
            else:
                locations_to_query.append(loc)

        # Process only locations that were not found in cache
        location_batches: Iterator[List[Tuple[float, float]]] = self._chunks(
            locations_to_query, self.max_locations_per_request
        )

        for batch in location_batches:
            if self.calls_made >= self.max_calls_per_day:
                logger.warning("Reached the maximum number of API calls for today.")
                break

            # Prepare the locations string for the API request
            locations_param: str = "|".join([f"{lat},{lon}" for lat, lon in batch])
            url: str = f"{self.api_url}?locations={locations_param}"

            try:
                response = requests.get(url)
                response.raise_for_status()
                data: Dict[str, Any] = response.json()

                if "results" in data:
                    for loc, result in zip(batch, data["results"]):
                        lat, lon = loc
                        elevation: Optional[float] = result.get("elevation")
                        key = f"{lat},{lon}"
                        results[key] = elevation
                        self.cache[key] = elevation
                else:
                    for loc in batch:
                        lat, lon = loc
                        results[f"{lat},{lon}"] = None

                self.calls_made += 1
                time.sleep(1)

            except requests.exceptions.RequestException as e:
                logger.error(f"An error occurred: {e}")
                for loc in batch:
                    lat, lon = loc
                    results[f"{lat},{lon}"] = None

        # Save updated cache to file
        self._save_cache()

        # Reconstruct the list in the original order
        return [results.get(f"{loc[0]},{loc[1]}") for loc in locations]

    def _chunks(
        self, data: List[Tuple[float, float]], size: int
    ) -> Iterator[List[Tuple[float, float]]]:
        """
        Yield successive n-sized chunks from a list.
        """
        iterator = iter(data)
        for first in iterator:
            yield [first] + list(islice(iterator, size - 1))

    def _load_cache(self) -> Dict[str, Optional[float]]:
        """
        Load the cache from a JSON file if it exists, otherwise return an empty dictionary.
        """
        if os.path.exists(self.cache_file):
            with open(self.cache_file, "r") as f:
                return json.load(f)
        return {}

    def _save_cache(self) -> None:
        """
        Save the cache to a JSON file.
        """
        with open(self.cache_file, "w") as f:
            json.dump(self.cache, f)
