"""Content scrapers for premium platform."""

from src.scraper.pornhub import PornHubScraper
from src.scraper.lustpress import LustPressScraper
from src.scraper.nsfw_api2 import NSFWAPI2Client
from src.scraper.xhamster import XHamsterScraper

__all__ = ["PornHubScraper", "LustPressScraper", "NSFWAPI2Client", "XHamsterScraper"]
