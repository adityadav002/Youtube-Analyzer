from yt_dlp import YoutubeDL
from yt_dlp.utils import DownloadError
import logging
import os
from typing import Dict, Any

logger = logging.getLogger(__name__)

class SafeYoutubeDL(YoutubeDL):
    """
    Subclass of YoutubeDL that automatically falls back to downloading/extracting
    without browser cookies if a cookie loading/decryption error occurs.
    """
    def extract_info(self, *args, **kwargs):
        try:
            return super().extract_info(*args, **kwargs)
        except DownloadError as de:
            err_msg = str(de)
            cookie_error_terms = [
                "cookie",
                "dpapi",
                "decrypt",
                "keyring",
                "failed to load cookies"
            ]
            if 'cookiesfrombrowser' in self.params and any(term in err_msg.lower() for term in cookie_error_terms):
                logger.warning(f"[SafeYoutubeDL] Cookie loading or decryption failed: {err_msg}. Retrying without browser cookies.")
                self.params.pop('cookiesfrombrowser', None)
                
                # Instantiate a new YoutubeDL without browser cookies to execute the retry safely
                with YoutubeDL(self.params) as ydl:
                    return ydl.extract_info(*args, **kwargs)
            else:
                raise

# ---------------------------------------------------------------------------
# Disable bgutil script-based PO Token providers.
# The bgutil package registers both an HTTP provider (uses the running server
# on :4416) and script providers that shell out to generate_once.js.
# On Windows the script provider's is_available() hangs for 15 seconds trying
# to run `generate_once.js --version`, so we disable them at import time.
# The HTTP provider alone is sufficient when the bgutil server is running.
# ---------------------------------------------------------------------------
try:
    from yt_dlp_plugins.extractor.getpot_bgutil_script import (
        BgUtilScriptNodePTP,
        BgUtilScriptDenoPTP,
    )
    BgUtilScriptNodePTP.is_available = lambda self: False
    BgUtilScriptDenoPTP.is_available = lambda self: False
    logger.info("[YtdlpConfig] Disabled bgutil script PO token providers (using HTTP server instead)")
except ImportError:
    pass  # Plugin not installed, nothing to disable

def configure_ytdlp_options(ydl_opts: dict, settings=None) -> dict:
    """Centralized function to apply yt-dlp configurations, cookies, PO token provider, and runtimes."""
    # Ensure quiet/no_warnings/ignoreerrors are respected or set defaults
    ydl_opts.setdefault('quiet', True)
    ydl_opts.setdefault('no_warnings', True)
    
    # 1. Enable Node.js EJS challenge solver
    ydl_opts['js_runtimes'] = {'node': {}}
    logger.info("[YtdlpConfig] js runtime = node")

    # 2. Configure proxy if present
    proxy = settings.ytdlp_proxy if settings else None
    if proxy:
        ydl_opts['proxy'] = proxy

    # 3. Determine environment (local vs Render production)
    is_render = os.environ.get('RENDER') == 'true'

    # 4. Configure cookies
    cookies_file = settings.cookies_file_path if settings else None
    
    if is_render:
        # Render/Production: Use cookie file from environment variable if provided, or database settings
        ytdlp_cookies_env = os.environ.get('YTDLP_COOKIES_FILE')
        if ytdlp_cookies_env and os.path.exists(ytdlp_cookies_env):
            ydl_opts['cookiefile'] = ytdlp_cookies_env
            logger.info(f"[YtdlpConfig] Using Render production cookies file from env: {ytdlp_cookies_env}")
        elif cookies_file and os.path.exists(cookies_file):
            ydl_opts['cookiefile'] = cookies_file
            logger.info(f"[YtdlpConfig] Using production cookies file from DB path: {cookies_file}")
        else:
            logger.info("[YtdlpConfig] No production cookies file configured.")
        logger.info("[YtdlpConfig] local browser cookies = disabled")
    else:
        # Local Development: Use cookies-from-browser chrome if no database cookie file is configured
        if cookies_file and os.path.exists(cookies_file):
            ydl_opts['cookiefile'] = cookies_file
            logger.info(f"[YtdlpConfig] Using local cookies file: {cookies_file}")
            logger.info("[YtdlpConfig] local browser cookies = disabled")
        else:
            # Automatically use chrome's authenticated session
            ydl_opts['cookiesfrombrowser'] = ('chrome',)
            logger.info("[YtdlpConfig] local browser cookies = enabled")

    # 5. Extractor args for player clients
    client_name = settings.ytdlp_player_client if settings else 'ios'
    # Ensure extractor_args dict exists
    ydl_opts.setdefault('extractor_args', {})
    # Ensure youtube dict exists under extractor_args
    ydl_opts['extractor_args'].setdefault('youtube', {})
    # Set the player_client order
    ydl_opts['extractor_args']['youtube']['player_client'] = [client_name, 'default']

    # 6. PO Token Provider URL Configuration
    pot_provider_url = os.environ.get('POT_PROVIDER_URL') or os.environ.get('BGUTIL_POT_PROVIDER_URL')
    if not pot_provider_url and not is_render:
        pot_provider_url = 'http://127.0.0.1:4416'
        
    if pot_provider_url:
        ydl_opts['extractor_args']['youtubepot-bgutilhttp'] = {
            'base_url': [pot_provider_url]
        }
        logger.info("[YtdlpConfig] PO provider = enabled")
    else:
        logger.info("[YtdlpConfig] PO provider = disabled")

    return ydl_opts

class YtdlpError(Exception):
    """Base exception for yt-dlp client operations."""
    pass

class YtdlpRateLimitError(YtdlpError):
    """Exception raised when YouTube blocks requests (rate limits, bot detection)."""
    pass

class YtdlpClient:

    def __init__(self, proxy: str = None, cookies_file: str = None, client: str = 'ios'):
        class MockSettings:
            def __init__(self, p, c_f, cl):
                self.ytdlp_proxy = p
                self.cookies_file_path = c_f
                self.ytdlp_player_client = cl
        
        settings = MockSettings(proxy, cookies_file, client)
        self.base_options = configure_ytdlp_options({
            'quiet': True,
            'no_warnings': True,
            'ignoreerrors': True,
        }, settings)

    def _get_ydl(self, custom_opts: Dict[str, Any] = None) -> SafeYoutubeDL:
        opts = self.base_options.copy()
        if custom_opts:
            opts.update(custom_opts)
        return SafeYoutubeDL(opts)

    def extract_channel_metadata(self, url: str) -> Dict[str, Any]:
        """
        Extract channel metadata. We only want the channel's about/profile info.
        To avoid extracting all videos in a channel, we use playlistend=0 or playlist_items='0'.
        """
        opts = {
            'extract_flat': True,
            'playlist_items': '0', # Don't fetch the videos right now
        }
        
        try:
            with self._get_ydl(opts) as ydl:
                info = ydl.extract_info(url, download=False)
                if not info:
                    raise Exception("Failed to extract channel metadata")

                # Separate banners and avatars
                banners = []
                avatars = []
                
                thumbnails = info.get('thumbnails') or []
                if isinstance(thumbnails, list):
                    for t in thumbnails:
                        t_id = str(t.get('id', '')).lower()
                        t_url = str(t.get('url', ''))
                        width = t.get('width') or 0
                        height = t.get('height') or 0
                        
                        is_banner = (
                            'banner' in t_id 
                            or 'banner' in t_url 
                            or 'fcrop' in t_url 
                            or '=w' in t_url 
                            or (width > 0 and height > 0 and width / height > 2.5)
                        )
                        if is_banner:
                            banners.append(t)
                        else:
                            avatars.append(t)

                # Select banner
                banner_url = info.get('banner') or info.get('banner_url')
                if not banner_url and banners:
                    banner_url = self._get_best_banner(banners)

                # Select avatar
                avatar_url = self._get_best_avatar(avatars)
                if not avatar_url:
                    default_thumb = info.get('thumbnail')
                    if default_thumb:
                        is_default_banner = (
                            'fcrop' in default_thumb 
                            or '=w' in default_thumb 
                            or 'banner' in default_thumb.lower()
                        )
                        if not is_default_banner:
                            avatar_url = default_thumb
                
                # Ultimate safe fallback: pick any non-banner thumbnail
                if not avatar_url and isinstance(thumbnails, list):
                    for t in thumbnails:
                        t_url = str(t.get('url', ''))
                        is_banner = 'fcrop' in t_url or '=w' in t_url or 'banner' in t_url.lower()
                        if not is_banner:
                            avatar_url = t_url
                            break


                # Map yt-dlp fields to our schema
                channel_id = info.get('channel_id') or info.get('id')
                video_count = 0
                if channel_id and channel_id.startswith('UC'):
                    playlist_id = 'UU' + channel_id[2:]
                    playlist_url = f"https://www.youtube.com/playlist?list={playlist_id}"
                    try:
                        playlist_opts = {
                            'extract_flat': True,
                            'playlist_items': '0',
                        }
                        with self._get_ydl(playlist_opts) as playlist_ydl:
                            playlist_info = playlist_ydl.extract_info(playlist_url, download=False)
                            video_count = playlist_info.get('playlist_count') or 0
                    except Exception as pe:
                        logger.warning(f"Failed to fetch uploads playlist count for {channel_id}: {pe}")

                # Try to scrape the Join Date and view count using requests and ytInitialData
                scrape_view_count = None
                scrape_join_date = None
                
                if channel_id:
                    scrape_url = f"https://www.youtube.com/channel/{channel_id}"
                    headers = {
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36",
                        "Accept-Language": "en-US,en;q=0.9",
                    }
                    try:
                        import requests
                        import re
                        import json
                        from datetime import datetime
                        
                        resp = requests.get(scrape_url, headers=headers, timeout=10)
                        if resp.status_code == 200:
                            html = resp.text
                            match = re.search(r'ytInitialData\s*=\s*({.+?});', html)
                            if not match:
                                match = re.search(r'window\["ytInitialData"\]\s*=\s*({.+?});', html)
                            
                            if match:
                                data = json.loads(match.group(1))
                                
                                def find_key_recursive(d, target_key):
                                    if isinstance(d, dict):
                                        if target_key in d:
                                            return d[target_key]
                                        for k, v in d.items():
                                            res = find_key_recursive(v, target_key)
                                            if res is not None:
                                                return res
                                    elif isinstance(d, list):
                                        for item in d:
                                            res = find_key_recursive(item, target_key)
                                            if res is not None:
                                                return res
                                    return None
                                    
                                joined_obj = find_key_recursive(data, "joinedDateText")
                                if isinstance(joined_obj, dict) and "runs" in joined_obj:
                                    runs = joined_obj["runs"]
                                    if runs and len(runs) > 0:
                                        joined_text = runs[0].get("text", "")
                                        date_str = joined_text.replace("Joined ", "").strip()
                                        if date_str:
                                            for fmt in ("%b %d, %Y", "%d %b %Y", "%B %d, %Y", "%d %B %Y"):
                                                try:
                                                    scrape_join_date = datetime.strptime(date_str, fmt)
                                                    break
                                                except Exception:
                                                    pass
                                
                                view_obj = find_key_recursive(data, "viewCountText")
                                view_text = ""
                                if isinstance(view_obj, dict):
                                    view_text = view_obj.get("simpleText", "") or (view_obj.get("runs")[0].get("text", "") if view_obj.get("runs") else "")
                                elif isinstance(view_obj, str):
                                    view_text = view_obj
                                    
                                if view_text:
                                    digits = re.sub(r'\D', '', view_text)
                                    if digits:
                                        scrape_view_count = int(digits)
                    except Exception as se:
                        logger.warning(f"Failed to scrape channel About metadata: {se}")

                return {
                    'id': channel_id,
                    'handle': info.get('uploader_id'),
                    'display_name': info.get('uploader') or info.get('title'),
                    'description': info.get('description'),
                    'avatar_url': avatar_url,
                    'banner_url': banner_url,
                    'subscriber_count': info.get('channel_follower_count', 0),
                    'video_count': video_count,
                    'is_verified': info.get('channel_is_verified', False),
                    'view_count': scrape_view_count or info.get('view_count'),
                    'join_date': scrape_join_date,
                    'external_links': [url.get('url') for url in info.get('urls', [])] if isinstance(info.get('urls'), list) else []
                }
        except Exception as e:
            logger.error(f"yt-dlp channel extraction failed for {url}: {str(e)}")
            raise

    def _get_best_thumbnail(self, thumbnails: list) -> str:
        if not isinstance(thumbnails, list):
            return None
        # Sort by resolution (width * height)
        sorted_thumbs = sorted(
            [t for t in thumbnails if t.get('url')],
            key=lambda t: (t.get('width', 0) or 0) * (t.get('height', 0) or 0),
            reverse=True
        )
        return sorted_thumbs[0]['url'] if sorted_thumbs else None

    def _get_avatar_resolution(self, t: dict) -> int:
        width = t.get('width')
        height = t.get('height')
        if width and height:
            return width * height
        
        # Estimate size from URL (e.g., =s176-c... or -s176-c...)
        url = t.get('url', '')
        import re
        match = re.search(r'[=\-]s(\d+)', url)
        if match:
            size = int(match.group(1))
            return size * size
        return 0

    def _get_best_avatar(self, avatars: list) -> str:
        if not avatars:
            return None
        sorted_avatars = sorted(
            [t for t in avatars if t.get('url')],
            key=self._get_avatar_resolution,
            reverse=True
        )
        return sorted_avatars[0]['url'] if sorted_avatars else None

    def _get_banner_resolution(self, t: dict) -> int:
        width = t.get('width')
        height = t.get('height')
        if width and height:
            return width * height
        
        # Estimate width from URL (e.g., =w2560-fcrop64... or -w2560-fcrop64...)
        url = t.get('url', '')
        import re
        match = re.search(r'[=\-]w(\d+)', url)
        if match:
            w = int(match.group(1))
            return w * int(w / 3)  # estimate height to compute pseudo-resolution
        return 0

    def _get_best_banner(self, banners: list) -> str:
        if not banners:
            return None
        sorted_banners = sorted(
            [t for t in banners if t.get('url')],
            key=self._get_banner_resolution,
            reverse=True
        )
        return sorted_banners[0]['url'] if sorted_banners else None


    def extract_flat_playlist(self, url: str, start_index: int = None, end_index: int = None) -> list:
        """
        Extracts video IDs and basic info from a channel or playlist quickly.
        Handles nested tab structures (channel -> tabs -> videos) and filters
        out non-video entries (channels, playlists) by validating ID length.
        """
        opts = {
            'extract_flat': True,
        }
        if start_index is not None:
            opts['playliststart'] = start_index
        if end_index is not None:
            opts['playlistend'] = end_index
        
        try:
            with self._get_ydl(opts) as ydl:
                info = ydl.extract_info(url, download=False)
                if not info or 'entries' not in info:
                    return []
                
                videos = []
                self._collect_videos(info.get('entries', []), videos)
                return videos
        except Exception as e:
            logger.error(f"yt-dlp flat extraction failed for {url}: {str(e)}")
            raise

    def _collect_videos(self, entries, videos: list):
        """
        Recursively collects video entries from potentially nested yt-dlp output.
        Only includes entries with an 11-character ID (standard YouTube video ID).
        Skips channels (24 chars), playlists (34 chars), and tab entries.
        """
        for entry in entries:
            if not entry:
                continue
            
            entry_id = entry.get('id', '')
            entry_type = entry.get('_type', '')
            
            # If this entry has nested entries (e.g., a tab or playlist), recurse
            if 'entries' in entry:
                self._collect_videos(entry['entries'], videos)
                continue
            
            # Standard YouTube video IDs are exactly 11 characters
            if len(entry_id) == 11:
                videos.append({
                    'id': entry_id,
                    'title': entry.get('title'),
                    'url': entry.get('url'),
                    'duration': entry.get('duration')
                })
            else:
                logger.debug(f"Skipping non-video entry: id={entry_id}, type={entry_type}, title={entry.get('title')}")

    def extract_video_metadata(self, url: str) -> Dict[str, Any]:
        """
        Deep extraction of video metadata.
        """
        video_id = url.split('=')[-1] if '=' in url else url
        info = None
        try:
            with self._get_ydl() as ydl:
                try:
                    info = ydl.extract_info(url, download=False)
                except Exception as ext_err:
                    logger.error(f"[Extraction Stage] yt-dlp execution failed for video {video_id} (URL: {url}): {str(ext_err)}")
                    raise ext_err
                
                if not info:
                    raise Exception("Failed to extract video metadata: yt-dlp returned empty info")
                
                try:
                    from datetime import datetime
                    upload_date = info.get('upload_date') # YYYYMMDD
                    if upload_date:
                        upload_date = datetime.strptime(upload_date, '%Y%m%d')

                    # Extract formats
                    raw_formats = info.get('formats')
                    if not isinstance(raw_formats, list):
                        raw_formats = []
                    formats = []
                    for f in raw_formats:
                        if not f:
                            continue
                        formats.append({
                            'format_id': f.get('format_id'),
                            'format_note': f.get('format_note'),
                            'resolution': f.get('resolution') or (f"{f.get('width')}x{f.get('height')}" if f.get('width') and f.get('height') else None),
                            'width': f.get('width'),
                            'height': f.get('height'),
                            'ext': f.get('ext'),
                            'filesize': f.get('filesize') or f.get('filesize_approx')
                        })
                    # Limit to first 30 formats to prevent database overhead
                    formats = formats[:30]

                    # Extract chapters
                    raw_chapters = info.get('chapters')
                    if not isinstance(raw_chapters, list):
                        raw_chapters = []
                    chapters = []
                    for c in raw_chapters:
                        if not c or not isinstance(c, dict):
                            continue
                        chapters.append({
                            'title': c.get('title'),
                            'start_time': c.get('start_time'),
                            'end_time': c.get('end_time')
                        })

                    # Safe duration
                    duration = info.get('duration')
                    duration = int(duration) if duration is not None else 0

                    # Safe tags and categories
                    raw_tags = info.get('tags')
                    tags = raw_tags if isinstance(raw_tags, list) else []
                    
                    raw_categories = info.get('categories')
                    categories = raw_categories if isinstance(raw_categories, list) else []

                    # Safe thumbnails
                    raw_thumbnails = info.get('thumbnails')
                    if not isinstance(raw_thumbnails, list):
                        raw_thumbnails = []
                    thumbnail_url = self._get_best_thumbnail(raw_thumbnails)

                    return {
                        'id': info.get('id'),
                        'channel_id': info.get('channel_id') or info.get('uploader_id'),
                        'channel_name': info.get('uploader') or info.get('channel'),
                        'title': info.get('title'),
                        'description': info.get('description'),
                        'duration': duration,

                        'view_count': info.get('view_count', 0),
                        'like_count': info.get('like_count'),
                        'comment_count': info.get('comment_count'),
                        'upload_date': upload_date,
                        'is_short': (
                            info.get('is_short', False) or
                            'shorts' in (info.get('webpage_url') or '').lower() or
                            'Shorts' in (info.get('categories') or [])
                        ),
                        'is_live': info.get('is_live', False),
                        'live_status': info.get('live_status', 'not_live'),
                        'availability': info.get('availability', 'public'),
                        'age_limit': info.get('age_limit', 0),
                        'has_transcript': bool(info.get('subtitles') or info.get('automatic_captions')),
                        'thumbnail_url': thumbnail_url,
                        'tags': tags,
                        'categories': categories,
                        'formats': formats,
                        'chapters': chapters,
                        'heatmap': []
                    }
                except Exception as norm_err:
                    logger.error(f"[Normalization Stage] Failed to parse extracted metadata for video {video_id} (URL: {url}): {str(norm_err)}")
                    raise norm_err
        except Exception as e:
            raise e

    def search_youtube(self, query: str, search_type: str = 'video', max_results: int = 20) -> list:
        """
        Search YouTube for videos, channels, or playlists.
        
        For videos: uses yt-dlp's native ytsearch prefix.
        For channels/playlists: uses YouTube search URL with sp filter parameter,
        since yt-dlp does not support ytsearchchannel or ytsearchplaylist prefixes.
        """
        import urllib.parse
        
        if search_type == 'channel':
            # sp=EgIQAg%3D%3D is the YouTube filter for "Channels"
            encoded_query = urllib.parse.quote_plus(query)
            search_query = f"https://www.youtube.com/results?search_query={encoded_query}&sp=EgIQAg%3D%3D"
        elif search_type == 'playlist':
            # sp=EgIQAw%3D%3D is the YouTube filter for "Playlists"
            encoded_query = urllib.parse.quote_plus(query)
            search_query = f"https://www.youtube.com/results?search_query={encoded_query}&sp=EgIQAw%3D%3D"
        else:
            # Standard video search using yt-dlp's native ytsearch prefix
            search_query = f"ytsearch{max_results}:{query}"
        
        opts = {
            'extract_flat': True,
            'skip_download': True,
            'playlistend': max_results,
        }
        
        try:
            with self._get_ydl(opts) as ydl:
                logger.info(f"yt-dlp search_query: {search_query}")
                info = ydl.extract_info(search_query, download=False)
                if not info or 'entries' not in info:
                    logger.warning(f"yt-dlp returned no entries. info keys: {list(info.keys()) if info else 'None'}")
                    return []
                
                entries_list = list(info.get('entries', []))
                logger.info(f"yt-dlp returned {len(entries_list)} entries for search_type={search_type}")
                if entries_list and len(entries_list) > 0:
                    # Log first entry for debugging
                    first = entries_list[0]
                    if first:
                        logger.info(f"First entry keys: {list(first.keys())}")
                        logger.info(f"First entry sample: id={first.get('id')}, url={first.get('url')}, _type={first.get('_type')}, title={first.get('title')}, ie_key={first.get('ie_key')}")
                
                results = []
                for entry in entries_list:
                    if not entry:
                        continue
                    
                    entry_id = entry.get('id')
                    entry_url = entry.get('url', '')
                    entry_type = entry.get('_type', '')
                        
                    if search_type == 'video':
                        if not entry_id:
                            continue
                        # Standard Video stub
                        upload_date_raw = entry.get('upload_date')
                        upload_date = None
                        if upload_date_raw:
                            try:
                                from datetime import datetime
                                upload_date = datetime.strptime(upload_date_raw, '%Y%m%d').strftime('%Y-%m-%d')
                            except Exception:
                                pass
                        
                        results.append({
                            'video_id': entry_id,
                            'title': entry.get('title'),
                            'channel': entry.get('uploader') or entry.get('channel'),
                            'channel_id': entry.get('uploader_id') or entry.get('channel_id'),
                            'thumbnail_url': entry.get('thumbnail') or (entry.get('thumbnails')[-1]['url'] if entry.get('thumbnails') else None),
                            'duration_seconds': entry.get('duration'),
                            'view_count': entry.get('view_count'),
                            'upload_date': upload_date
                        })
                    elif search_type == 'channel':
                        # Channel entries from YouTube search page may have:
                        #   id: channel_id (UCxxx) or channel handle
                        #   url: https://www.youtube.com/channel/UCxxx or /@handle
                        #   _type: 'url'
                        channel_id = entry_id
                        
                        # Try to extract UC-prefix channel_id from url if id isn't one
                        if entry_url and (not channel_id or not channel_id.startswith('UC')):
                            import re as _re
                            uc_match = _re.search(r'/channel/(UC[a-zA-Z0-9_-]+)', entry_url)
                            if uc_match:
                                channel_id = uc_match.group(1)
                        
                        # Skip entries that don't look like channels
                        if not channel_id and not entry_url:
                            continue
                        
                        # Use channel_id or fallback to entry_id
                        if not channel_id:
                            channel_id = entry_id or entry_url
                        
                        results.append({
                            'channel_id': channel_id,
                            'title': entry.get('title') or entry.get('uploader') or entry.get('channel'),
                            'handle': entry.get('uploader_id') or entry.get('channel_id') or entry_id,
                            'thumbnail_url': entry.get('thumbnail') or (entry.get('thumbnails')[-1]['url'] if entry.get('thumbnails') else None),
                            'view_count': entry.get('view_count'),
                            'video_count': entry.get('playlist_count') or entry.get('video_count')
                        })
                    elif search_type == 'playlist':
                        if not entry_id:
                            continue
                        results.append({
                            'playlist_id': entry_id,
                            'title': entry.get('title'),
                            'channel': entry.get('uploader') or entry.get('channel'),
                            'channel_id': entry.get('uploader_id') or entry.get('channel_id'),
                            'thumbnail_url': entry.get('thumbnail') or (entry.get('thumbnails')[-1]['url'] if entry.get('thumbnails') else None),
                            'video_count': entry.get('playlist_count') or entry.get('video_count')
                        })
                return results
        except Exception as e:
            err_msg = str(e)
            logger.error(f"yt-dlp search failed for query '{query}': {err_msg}")
            
            # Identify rate limit or bot detection patterns
            rate_limit_keywords = [
                '429', 'too many requests', 'confirm you are not a bot',
                'bot detection', 'sign in to confirm', 'captcha', 'rate limit'
            ]
            if any(kw in err_msg.lower() for kw in rate_limit_keywords):
                raise YtdlpRateLimitError(err_msg) from e
            else:
                raise YtdlpError(err_msg) from e


