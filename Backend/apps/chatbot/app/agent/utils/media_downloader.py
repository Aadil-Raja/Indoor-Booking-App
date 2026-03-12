"""
Media downloader utility - downloads images/videos and converts to base64.

Used for returning media in chatbot responses (works for WhatsApp, web, etc.)
"""

import logging
import base64
import asyncio
import aiohttp
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

# Configuration
MAX_IMAGE_SIZE_MB = 5  # Maximum image size to download
DOWNLOAD_TIMEOUT = 10  # Timeout in seconds
MAX_CONCURRENT_DOWNLOADS = 5  # Max parallel downloads


async def download_and_encode_media(url: str) -> Optional[Dict[str, Any]]:
    """
    Download a single media file and convert to base64.
    
    Args:
        url: URL of the media file
        
    Returns:
        {
            "data": "data:image/jpeg;base64,/9j/4AAQ...",
            "size": 12345,
            "error": None
        }
        or None if download fails
    """
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=DOWNLOAD_TIMEOUT)) as response:
                if response.status != 200:
                    logger.warning(f"Failed to download media from {url}: HTTP {response.status}")
                    return None
                
                # Check content type
                content_type = response.headers.get('Content-Type', 'image/jpeg')
                
                # Check size
                content_length = response.headers.get('Content-Length')
                if content_length:
                    size_mb = int(content_length) / (1024 * 1024)
                    if size_mb > MAX_IMAGE_SIZE_MB:
                        logger.warning(f"Media too large: {size_mb:.2f}MB from {url}")
                        return None
                
                # Download content
                content = await response.read()
                
                # Encode to base64
                base64_data = base64.b64encode(content).decode('utf-8')
                
                # Create data URI
                data_uri = f"data:{content_type};base64,{base64_data}"
                
                logger.info(f"Downloaded and encoded media: {len(content)} bytes from {url}")
                
                return {
                    "data": data_uri,
                    "size": len(content),
                    "error": None
                }
                
    except asyncio.TimeoutError:
        logger.error(f"Timeout downloading media from {url}")
        return None
    except Exception as e:
        logger.error(f"Error downloading media from {url}: {e}")
        return None


async def download_media_batch(media_items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Download multiple media files concurrently.
    
    Args:
        media_items: List of media items with 'url', 'type', 'caption'
        
    Returns:
        List of media items with added 'data' field (base64)
    """
    if not media_items:
        return []
    
    logger.info(f"Starting batch download of {len(media_items)} media items")
    
    # Create download tasks
    tasks = []
    for item in media_items:
        url = item.get('url')
        if url:
            tasks.append(download_and_encode_media(url))
        else:
            tasks.append(asyncio.sleep(0, result=None))  # Placeholder for missing URL
    
    # Download concurrently with limit
    results = []
    for i in range(0, len(tasks), MAX_CONCURRENT_DOWNLOADS):
        batch = tasks[i:i + MAX_CONCURRENT_DOWNLOADS]
        batch_results = await asyncio.gather(*batch, return_exceptions=True)
        results.extend(batch_results)
    
    # Combine results with original items
    processed_items = []
    for item, result in zip(media_items, results):
        if result and isinstance(result, dict) and result.get('data'):
            processed_items.append({
                "type": item.get('type', 'image'),
                "data": result['data'],
                "caption": item.get('caption', ''),
                "size": result['size']
            })
        else:
            # Failed download - skip or include URL as fallback
            logger.warning(f"Skipping failed media download: {item.get('url')}")
    
    logger.info(f"Successfully downloaded {len(processed_items)}/{len(media_items)} media items")
    
    return processed_items
