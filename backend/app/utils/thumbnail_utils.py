import os
import requests
import logging
from urllib.parse import urlparse
from app.config import Config

logger = logging.getLogger(__name__)

def download_thumbnail(video_id: str, url: str) -> str:
    """
    Downloads a thumbnail from the given URL and saves it to the THUMBNAILS_DIR.
    Returns the relative path for serving (e.g., /thumbnails/{video_id}.jpg)
    """
    if not url:
        return None
        
    try:
        # Check if dir exists
        os.makedirs(Config.THUMBNAIL_DIR, exist_ok=True)
        
        # Get extension from URL or default to .jpg
        parsed = urlparse(url)
        ext = os.path.splitext(parsed.path)[1]
        if not ext:
            ext = '.jpg'
            
        filename = f"{video_id}{ext}"
        filepath = os.path.join(Config.THUMBNAIL_DIR, filename)
        
        # Download
        response = requests.get(url, stream=True, timeout=10)
        response.raise_for_status()
        
        with open(filepath, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
                
        # Nginx is configured to serve /thumbnails/ alias to /data/thumbnails/
        return f"/thumbnails/{filename}"
        
    except Exception as e:
        logger.error(f"Failed to download thumbnail for {video_id}: {str(e)}")
        return url # fallback to external url if download fails
