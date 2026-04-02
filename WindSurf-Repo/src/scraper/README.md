# Content Scrapers

Professional scrapers for aggregating content from various sources.

## Available Scrapers

### PornHub Scraper

Advanced scraper with multiple methods:

- **Dual Method**: Uses official API when available, falls back to web scraping
- **Advanced Filtering**: Duration, category, ordering options
- **Video Details**: Get detailed information about specific videos
- **Trending Content**: Get trending videos by period
- **Category Browsing**: Browse videos by category

### LustPress Scraper

Web scraping scraper for LustPress:

- HTML parsing with multiple fallback methods
- Embedded JSON extraction
- Category browsing
- Video metadata extraction

### NSFW-API2 Client

Client for Swag666baby's NSFW-API2 service:

- **Hentai Content**: Search hentai images and videos
- **Real Content**: Search real videos and images
- **Tag-based Search**: Search images by tag (110+ tags available)
- **Unified Search**: Search across all content types

## Usage Examples

### PornHub Scraper

```python
from src.scraper.pornhub import PornHubScraper

async def example():
    scraper = PornHubScraper()
    
    # Search videos
    videos = await scraper.search(
        query="squirting lesbian",
        category="lesbian",
        limit=50,
        min_duration=300,  # At least 5 minutes
        ordering="mostviewed"
    )
    
    await scraper.close()
```

### LustPress Scraper

```python
from src.scraper.lustpress import LustPressScraper

async def example():
    scraper = LustPressScraper()
    
    # Search videos
    videos = await scraper.search(
        query="lesbian",
        category="lesbian",
        limit=50
    )
    
    await scraper.close()
```

### NSFW-API2 Client

```python
from src.scraper.nsfw_api2 import NSFWAPI2Client

async def example():
    client = NSFWAPI2Client()
    
    # Search hentai videos
    hentai = await client.search_hentai_videos("lesbian", limit=20)
    
    # Search real videos
    real = await client.search_real_videos("lesbian", limit=20)
    
    # Search images by tag
    images = await client.search_real_images_by_tag("lesbian", limit=20)
    
    # Search all content types
    all_content = await client.search_all("lesbian", limit_per_type=10)
    
    # Get available tags
    tags = await client.get_available_tags()
    
    await client.close()
```

## Integration

All scrapers integrate with the content aggregator:

```python
from core.content_apis import ContentAggregator

aggregator = ContentAggregator()
videos = await aggregator.search_all("query", category="lesbian")
```

The aggregator automatically:
- Searches all available sources
- Deduplicates results
- Merges and normalizes data
- Returns unified format

## Error Handling

All scrapers include comprehensive error handling:
- API failures fall back to web scraping (where applicable)
- Invalid responses return empty lists
- All errors are logged for debugging
- Graceful degradation

## Rate Limiting

Be respectful:
- Add delays between requests in production
- Use official APIs when possible
- Respect robots.txt
- Implement exponential backoff for retries

## Testing

Test scripts are available for each scraper:

```bash
python src/scraper/test_scraper.py      # PornHub
python src/scraper/test_lustpress.py    # LustPress
python src/scraper/test_nsfw_api2.py    # NSFW-API2
```
