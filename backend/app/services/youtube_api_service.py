import os
import requests
import logging
from datetime import datetime
import re

logger = logging.getLogger(__name__)

YOUTUBE_CATEGORIES = {
    "1": "Film & Animation",
    "2": "Autos & Vehicles",
    "10": "Music",
    "15": "Pets & Animals",
    "17": "Sports",
    "19": "Travel & Events",
    "20": "Gaming",
    "22": "People & Blogs",
    "23": "Comedy",
    "24": "Entertainment",
    "25": "News & Politics",
    "26": "Howto & Style",
    "27": "Education",
    "28": "Science & Technology",
    "29": "Nonprofits & Activism"
}

class YouTubeAPIError(Exception):
    def __init__(self, message="YouTube API Error", status_code=500, reason=None):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.reason = reason

class YouTubeQuotaExceededError(YouTubeAPIError):
    def __init__(self, message="YouTube Data API daily quota exceeded."):
        super().__init__(message, status_code=503, reason='quotaExceeded')

class YouTubeConfigError(YouTubeAPIError):
    def __init__(self, message="YouTube API key configuration is missing or invalid."):
        super().__init__(message, status_code=503, reason='keyInvalid')

class YouTubeNotFoundError(YouTubeAPIError):
    def __init__(self, message="YouTube resource not found."):
        super().__init__(message, status_code=404, reason='notFound')

class YouTubeNetworkError(YouTubeAPIError):
    def __init__(self, message="Unable to connect to YouTube Data API due to network error."):
        super().__init__(message, status_code=502, reason='networkError')

class YouTubeTimeoutError(YouTubeAPIError):
    def __init__(self, message="YouTube Data API request timed out."):
        super().__init__(message, status_code=504, reason='timeout')

def parse_chapters_from_description(description: str, duration: int) -> list:
    if not description:
        return []
    
    # Matches formats like: 00:00, 12:34, 1:23:45, 01:23:45 with optional trailing space/hyphen/text
    timestamp_pattern = re.compile(
        r'(?:^|\b)(?:(?P<hours>\d{1,2}):)?(?P<minutes>\d{2}):(?P<seconds>\d{2})\b'
    )
    
    lines = description.split('\n')
    chapters_found = []
    
    for line in lines:
        match = timestamp_pattern.search(line)
        if match:
            # Extract timestamp in seconds
            parts = match.groupdict()
            h = int(parts.get('hours') or 0)
            m = int(parts.get('minutes') or 0)
            s = int(parts.get('seconds') or 0)
            seconds = h * 3600 + m * 60 + s
            
            # Extract title by removing the matched timestamp and any hyphens/colons/spaces
            clean_title = timestamp_pattern.sub('', line).strip()
            clean_title = re.sub(r'^[-\s:|()]+|[-\s:|()]+$', '', clean_title).strip()
            if not clean_title:
                clean_title = f"Chapter at {match.group(0)}"
                
            chapters_found.append({
                'title': clean_title,
                'start_time': seconds
            })
            
    # Sort by start_time
    chapters_found.sort(key=lambda x: x['start_time'])
    
    # Filter out invalid sequences (e.g. if start_time is greater than duration)
    if duration > 0:
        chapters_found = [c for c in chapters_found if c['start_time'] < duration]
        
    # Calculate end_time for each chapter
    for i in range(len(chapters_found)):
        start = chapters_found[i]['start_time']
        if i < len(chapters_found) - 1:
            end = chapters_found[i+1]['start_time']
        else:
            end = duration if duration > 0 else start + 300 # fallback if duration is 0
        chapters_found[i]['end_time'] = end
        
    # Ensure there is at least a 00:00 start (standard YouTube rule: first chapter must start at 00:00)
    if chapters_found and chapters_found[0]['start_time'] > 0:
        chapters_found.insert(0, {
            'title': 'Introduction',
            'start_time': 0,
            'end_time': chapters_found[0]['start_time']
        })
        
    return chapters_found


class YouTubeApiService:
    def __init__(self):
        self.api_key = os.environ.get('YOUTUBE_API_KEY')
        if not self.api_key:
            raise YouTubeConfigError("YouTube API key configuration is missing. Please set YOUTUBE_API_KEY in your environment.")
        self.base_url = "https://www.googleapis.com/youtube/v3"

    def _get(self, endpoint: str, params: dict) -> dict:
        url = f"{self.base_url}/{endpoint}"
        params = params.copy()
        params['key'] = self.api_key
        
        # Log outgoing API request (excluding key for security)
        logged_params = {k: v for k, v in params.items() if k != 'key'}
        logger.info(f"YouTube API request: /{endpoint} params={logged_params}")
        
        try:
            resp = requests.get(url, params=params, timeout=15)
        except requests.exceptions.Timeout as e:
            logger.error(f"Timeout connecting to YouTube API: {e}")
            raise YouTubeTimeoutError("YouTube Data API request timed out.") from e
        except requests.exceptions.RequestException as e:
            logger.error(f"Network error connecting to YouTube API: {e}")
            raise YouTubeNetworkError("Unable to connect to YouTube Data API due to network error.") from e
            
        if resp.status_code == 200:
            return resp.json()
            
        # Parse error response
        try:
            error_data = resp.json()
            err_details = error_data.get('error', {})
            msg = err_details.get('message', 'Unknown API Error')
            errors = err_details.get('errors', [])
            reason = errors[0].get('reason') if errors else None
        except Exception:
            msg = resp.text
            reason = None
            
        logger.error(f"YouTube API error: HTTP {resp.status_code} - {msg} (Reason: {reason})")
        
        if resp.status_code == 403:
            if reason in ('quotaExceeded', 'dailyLimitExceeded', 'rateLimitExceeded'):
                raise YouTubeQuotaExceededError("YouTube Data API daily quota exceeded.")
            raise YouTubeAPIError(f"YouTube API access forbidden: {msg}", status_code=403, reason=reason)
        elif resp.status_code == 400:
            if reason in ('keyInvalid', 'badRequest'):
                raise YouTubeConfigError(f"Invalid YouTube API key or parameters: {msg}")
            raise YouTubeAPIError(f"YouTube API returned HTTP 400: {msg}", status_code=400, reason=reason)
        elif resp.status_code == 404:
            raise YouTubeNotFoundError("YouTube resource not found.")
        else:
            raise YouTubeAPIError(f"YouTube API returned HTTP {resp.status_code}: {msg}", status_code=resp.status_code, reason=reason)

    def parse_iso8601_duration(self, duration_str: str) -> int:
        if not duration_str:
            return 0
        pattern = re.compile(r'P?(?:(?P<days>\d+)D)?T?(?:(?P<hours>\d+)H)?(?:(?P<minutes>\d+)M)?(?:(?P<seconds>\d+)S)?')
        match = pattern.match(duration_str)
        if not match:
            return 0
        parts = match.groupdict()
        days = int(parts.get('days') or 0)
        hours = int(parts.get('hours') or 0)
        minutes = int(parts.get('minutes') or 0)
        seconds = int(parts.get('seconds') or 0)
        return days * 86400 + hours * 3600 + minutes * 60 + seconds

    def parse_iso8601_date(self, date_str: str) -> datetime:
        if not date_str:
            return None
        try:
            date_str = date_str.replace('Z', '+00:00')
            return datetime.fromisoformat(date_str)
        except Exception as e:
            logger.warning(f"Failed to parse date string '{date_str}': {e}")
            return None

    def extract_channel_id_or_handle(self, url: str) -> tuple:
        if not url:
            return None, None, None, None
            
        url = url.strip()
        
        # Raw ID (e.g. UCxxxx)
        if re.match(r'^UC[a-zA-Z0-9_-]{22}$', url):
            return url, None, None, None
            
        # Channel URL with ID (e.g. /channel/UCxxxx)
        id_match = re.search(r'/channel/(UC[a-zA-Z0-9_-]{22})', url)
        if id_match:
            return id_match.group(1), None, None, None
            
        # Handle URL (e.g. /@username)
        handle_match = re.search(r'/@([a-zA-Z0-9_\-\.]+)', url)
        if handle_match:
            return None, f"@{handle_match.group(1)}", None, None
            
        # Legacy user URL (e.g. /user/username)
        user_match = re.search(r'/user/([a-zA-Z0-9_\-]+)', url)
        if user_match:
            return None, None, user_match.group(1), None
            
        # If it starts with @ but isn't a full URL
        if url.startswith('@'):
            return None, url, None, None
            
        # Otherwise treat as generic search query
        return None, None, None, url

    def fetch_channel_metadata(self, url_or_id: str) -> dict:
        cid, handle, username, query = self.extract_channel_id_or_handle(url_or_id)
        
        params = {
            'part': 'snippet,contentDetails,statistics,brandingSettings'
        }
        
        if cid:
            params['id'] = cid
        elif handle:
            params['forHandle'] = handle
        elif username:
            params['forUsername'] = username
        elif query:
            search_params = {
                'part': 'snippet',
                'q': query,
                'type': 'channel',
                'maxResults': 1
            }
            search_res = self._get('search', search_params)
            items = search_res.get('items', [])
            if not items:
                raise YouTubeAPIError(f"YouTube channel not found for query: {query}")
            params['id'] = items[0]['id']['channelId']
        else:
            raise YouTubeAPIError("Invalid channel URL or ID format.")
            
        res = self._get('channels', params)
        items = res.get('items', [])
        if not items:
            raise YouTubeAPIError(f"YouTube channel not found for: {url_or_id}")
            
        item = items[0]
        snippet = item.get('snippet', {})
        stats = item.get('statistics', {})
        branding = item.get('brandingSettings', {})
        
        banner_url = branding.get('image', {}).get('bannerExternalUrl')
        thumbnails = snippet.get('thumbnails', {})
        avatar_url = thumbnails.get('high', {}).get('url') or thumbnails.get('default', {}).get('url')
        published_at = snippet.get('publishedAt')
        join_date = self.parse_iso8601_date(published_at)
        
        return {
            'id': item['id'],
            'handle': snippet.get('customUrl'),
            'display_name': snippet.get('title', 'YouTube Channel'),
            'description': snippet.get('description'),
            'avatar_url': avatar_url,
            'banner_url': banner_url,
            'subscriber_count': int(stats.get('subscriberCount') or 0),
            'video_count': int(stats.get('videoCount') or 0),
            'view_count': int(stats.get('viewCount') or 0),
            'country': snippet.get('country'),
            'join_date': join_date,
            'is_verified': False,
            'external_links': []
        }

    def crawl_channel_videos(self, channel_id: str, start_index: int = 1, limit: int = 20, refresh_mode: bool = False) -> tuple:
        from app import db
        from app.models.video import Video
        from app.repositories.video_repository import VideoRepository
        
        uploads_playlist_id = 'UU' + channel_id[2:]
        existing_video_ids = {v[0] for v in db.session.query(Video.id).filter(Video.channel_id == channel_id).all()}
        
        # Target buckets
        normal_videos = []
        shorts_videos = []
        live_videos = []
        fallback_pool = []

        if limit == 50:
            target_normal = 30
            target_shorts = 10
            target_live = 10
        else:
            # Proportional distribution: 60% normal, 20% shorts, 20% live
            target_shorts = max(1, int(limit * 0.2)) if limit >= 5 else 0
            target_live = max(1, int(limit * 0.2)) if limit >= 5 else 0
            target_normal = limit - target_shorts - target_live

        # Hard cap on pages to protect YouTube API quota
        max_pages = max(3, (limit + 49) // 50 + 2)

        logger.info(f"[Crawler] Target: {target_normal} normal, {target_shorts} shorts, {target_live} live (max_pages={max_pages})")

        next_page_token = None
        current_index = 0
        total_quota_playlist = 0
        total_quota_videos = 0
        page_num = 0
        
        while True:
            # Check if all buckets are filled
            if (len(normal_videos) >= target_normal and 
                len(shorts_videos) >= target_shorts and 
                len(live_videos) >= target_live):
                logger.info("[Crawler] Target reached")
                break

            page_num += 1
            logger.info(f"[Crawler] Fetching uploads page {page_num}")
            
            params = {
                'part': 'snippet,contentDetails',
                'playlistId': uploads_playlist_id,
                'maxResults': 50
            }
            if next_page_token:
                params['pageToken'] = next_page_token
                
            res = self._get('playlistItems', params)
            total_quota_playlist += 1
            
            items = res.get('items', [])
            if not items:
                logger.info("[Crawler] No more uploads available in channel playlist.")
                break
                
            # Filter and collect video IDs for the current page
            page_video_ids = []
            stop_crawl = False
            for item in items:
                video_id = item.get('contentDetails', {}).get('videoId')
                if not video_id:
                    continue
                    
                current_index += 1
                    
                # Skip if we haven't reached the start_index yet (1-based)
                if current_index < start_index:
                    continue
                    
                page_video_ids.append(video_id)

            logger.info(f"[Crawler] Retrieved {len(page_video_ids)} upload IDs")

            if not page_video_ids:
                if stop_crawl or not res.get('nextPageToken'):
                    break
                next_page_token = res.get('nextPageToken')
                continue

            # Fetch details for the page's videos in chunks of 50
            page_videos_details = []
            for i in range(0, len(page_video_ids), 50):
                batch_ids = page_video_ids[i:i+50]
                
                v_params = {
                    'part': 'snippet,contentDetails,statistics,status,liveStreamingDetails',
                    'id': ','.join(batch_ids)
                }
                
                v_res = self._get('videos', v_params)
                total_quota_videos += 1
                page_videos_details.extend(v_res.get('items', []))

            # Classify and fill buckets
            num_normal = 0
            num_shorts = 0
            num_live = 0
            
            for item in page_videos_details:
                vid = item['id']
                snippet = item.get('snippet', {})
                content_details = item.get('contentDetails', {})
                stats = item.get('statistics', {})
                status = item.get('status', {})
                live_details = item.get('liveStreamingDetails')
                
                title = snippet.get('title', 'YouTube Video')
                description = snippet.get('description', '')
                duration = self.parse_iso8601_duration(content_details.get('duration'))
                
                view_count = int(stats.get('viewCount') or 0)
                like_count = int(stats.get('likeCount') or 0) if 'likeCount' in stats else None
                comment_count = int(stats.get('commentCount') or 0) if 'commentCount' in stats else None
                comments_disabled = 'commentCount' not in stats
                
                thumbs = snippet.get('thumbnails', {})
                thumb_url = (
                    thumbs.get('maxres', {}).get('url') or 
                    thumbs.get('high', {}).get('url') or 
                    thumbs.get('medium', {}).get('url') or 
                    thumbs.get('default', {}).get('url')
                )
                
                published_at = snippet.get('publishedAt')
                upload_date = self.parse_iso8601_date(published_at)
                
                cat_id = snippet.get('categoryId')
                cat_name = YOUTUBE_CATEGORIES.get(cat_id)
                categories = [cat_name] if cat_name else ([cat_id] if cat_id else [])
                tags = snippet.get('tags') or []
                
                availability = status.get('privacyStatus', 'public')
                
                # Check live
                live_content = snippet.get('liveBroadcastContent', 'none')
                is_live = False
                live_status = 'not_live'
                if live_content == 'live':
                    is_live = True
                    live_status = 'is_live'
                elif live_content == 'upcoming':
                    is_live = False
                    live_status = 'upcoming'
                elif live_details:
                    is_live = True
                    live_status = 'was_live'
                    
                # Check shorts
                is_short = False
                title_lower = title.lower()
                desc_lower = description.lower()
                tags_lower = [t.lower() for t in tags]
                if 'shorts' in tags_lower or '#shorts' in title_lower or '#shorts' in desc_lower:
                    is_short = True
                
                # Resolve classification using the exact repository rules
                resolved_short, resolved_live, resolved_status = VideoRepository.resolve_classification(
                    is_short, is_live, live_status, duration
                )
                
                if resolved_live:
                    num_live += 1
                elif resolved_short:
                    num_shorts += 1
                else:
                    num_normal += 1

                video_record = {
                    'id': vid,
                    'channel_id': channel_id,
                    'title': title,
                    'description': description,
                    'duration': duration,
                    'view_count': view_count,
                    'like_count': like_count,
                    'comment_count': comment_count,
                    'comments_disabled': comments_disabled,
                    'upload_date': upload_date,
                    'thumbnail_url': thumb_url,
                    'is_short': resolved_short,
                    'is_live': resolved_live,
                    'live_status': resolved_status,
                    'availability': availability,
                    'age_limit': 0,
                    'has_transcript': content_details.get('caption') == 'true',
                    'tags': tags,
                    'categories': categories,
                    'formats': [],
                    'chapters': parse_chapters_from_description(description, duration),
                    'heatmap': []
                }

                # Place into appropriate bucket
                if resolved_live:
                    if len(live_videos) < target_live:
                        live_videos.append(video_record)
                    else:
                        fallback_pool.append(video_record)
                elif resolved_short:
                    if len(shorts_videos) < target_shorts:
                        shorts_videos.append(video_record)
                    else:
                        fallback_pool.append(video_record)
                else:
                    if len(normal_videos) < target_normal:
                        normal_videos.append(video_record)
                    else:
                        fallback_pool.append(video_record)

            logger.info(f"[Crawler] Classified: {num_normal} normal, {num_shorts} shorts, {num_live} live")
            logger.info(
                f"[Crawler] Current buckets: "
                f"{len(normal_videos)}/{target_normal} normal, "
                f"{len(shorts_videos)}/{target_shorts} shorts, "
                f"{len(live_videos)}/{target_live} live"
            )

            # Check if all buckets are filled
            if (len(normal_videos) >= target_normal and 
                len(shorts_videos) >= target_shorts and 
                len(live_videos) >= target_live):
                logger.info("[Crawler] Target reached for all buckets")
                break

            if page_num >= max_pages:
                logger.info(f"[Crawler] Hard page cap ({max_pages}) reached. Stopping pagination to protect quota.")
                break

            if stop_crawl or not res.get('nextPageToken'):
                logger.info("[Crawler] Stop condition reached or end of playlist.")
                break
                
            next_page_token = res.get('nextPageToken')

        # Combine all selected videos
        videos_data = normal_videos + shorts_videos + live_videos

        # If any bucket was under-filled (e.g. channel has 0 live streams), fill remaining slots from fallback pool
        needed = limit - len(videos_data)
        if needed > 0 and fallback_pool:
            fill_items = fallback_pool[:needed]
            for item in fill_items:
                if item.get('is_live'):
                    live_videos.append(item)
                elif item.get('is_short'):
                    shorts_videos.append(item)
                else:
                    normal_videos.append(item)
            videos_data = normal_videos + shorts_videos + live_videos
            logger.info(f"[Crawler] Filled {len(fill_items)} under-allocated slots from available video fallback pool.")
        
        # Save to database
        inserted, updated = VideoRepository.bulk_create_stubs_tracked(videos_data)
        logger.info(f"[Crawler] Saved: Inserted={inserted}, Updated={updated}")
        logger.info(
            f"YouTube API quota usage summary:\n"
            f"  playlistItems.list requests: {total_quota_playlist} (quota units: {total_quota_playlist})\n"
            f"  videos.list requests: {total_quota_videos} (quota units: {total_quota_videos})\n"
            f"  Total API quota consumed: {total_quota_playlist + total_quota_videos} units"
        )
        
        # Log final report
        logger.info(f"[Crawler] Final: {len(normal_videos)} normal, {len(shorts_videos)} shorts, {len(live_videos)} live")
        logger.info(f"[Crawler] Total imported: {len(videos_data)}")
        
        result_counts = {
            'normal': len(normal_videos),
            'shorts': len(shorts_videos),
            'live': len(live_videos),
            'total': len(videos_data),
            'target_normal': target_normal,
            'target_shorts': target_shorts,
            'target_live': target_live,
            'target_total': target_normal + target_shorts + target_live
        }
        
        return videos_data, inserted, updated, result_counts

    def fetch_video_metadata(self, url_or_id: str) -> dict:
        from app.controllers.download_controller import extract_video_id
        video_id = extract_video_id(url_or_id)
        if not video_id:
            raise YouTubeAPIError("Invalid YouTube video URL or ID.")
            
        params = {
            'part': 'snippet,contentDetails,statistics,status,liveStreamingDetails',
            'id': video_id
        }
        res = self._get('videos', params)
        items = res.get('items', [])
        if not items:
            raise YouTubeAPIError(f"YouTube video not found for ID: {video_id}")
            
        item = items[0]
        snippet = item.get('snippet', {})
        content_details = item.get('contentDetails', {})
        stats = item.get('statistics', {})
        status = item.get('status', {})
        live_details = item.get('liveStreamingDetails')
        
        title = snippet.get('title', 'YouTube Video')
        description = snippet.get('description', '')
        duration = self.parse_iso8601_duration(content_details.get('duration'))
        
        view_count = int(stats.get('viewCount') or 0)
        like_count = int(stats.get('likeCount') or 0) if 'likeCount' in stats else None
        comment_count = int(stats.get('commentCount') or 0) if 'commentCount' in stats else None
        comments_disabled = 'commentCount' not in stats
        
        thumbs = snippet.get('thumbnails', {})
        thumb_url = (
            thumbs.get('maxres', {}).get('url') or 
            thumbs.get('high', {}).get('url') or 
            thumbs.get('medium', {}).get('url') or 
            thumbs.get('default', {}).get('url')
        )
        
        upload_date = self.parse_iso8601_date(snippet.get('publishedAt'))
        
        cat_id = snippet.get('categoryId')
        cat_name = YOUTUBE_CATEGORIES.get(cat_id)
        categories = [cat_name] if cat_name else ([cat_id] if cat_id else [])
        tags = snippet.get('tags') or []
        
        availability = status.get('privacyStatus', 'public')
        
        live_content = snippet.get('liveBroadcastContent', 'none')
        is_live = False
        live_status = 'not_live'
        if live_content == 'live':
            is_live = True
            live_status = 'is_live'
        elif live_content == 'upcoming':
            is_live = False
            live_status = 'upcoming'
        elif live_details:
            is_live = True
            live_status = 'was_live'
            
        is_short = False
        title_lower = title.lower()
        desc_lower = description.lower()
        tags_lower = [t.lower() for t in tags]
        if 'shorts' in tags_lower or '#shorts' in title_lower or '#shorts' in desc_lower:
            is_short = True
            
        return {
            'id': video_id,
            'channel_id': snippet.get('channelId'),
            'channel_name': snippet.get('channelTitle'),
            'title': title,
            'description': description,
            'duration': duration,
            'view_count': view_count,
            'like_count': like_count,
            'comment_count': comment_count,
            'comments_disabled': comments_disabled,
            'upload_date': upload_date,
            'thumbnail_url': thumb_url,
            'is_short': is_short,
            'is_live': is_live,
            'live_status': live_status,
            'availability': availability,
            'age_limit': 0,
            'has_transcript': content_details.get('caption') == 'true',
            'tags': tags,
            'categories': categories,
            'formats': [],
            'chapters': parse_chapters_from_description(description, duration),
            'heatmap': []
        }

    def search_youtube(self, query: str, search_type: str = 'video', max_results: int = 20) -> list:
        api_type = search_type
        if api_type not in ['video', 'channel', 'playlist']:
            api_type = 'video'
            
        params = {
            'part': 'snippet',
            'q': query,
            'type': api_type,
            'maxResults': max_results
        }
        
        res = self._get('search', params)
        items = res.get('items', [])
        
        results = []
        
        if api_type == 'video':
            video_ids = [item['id']['videoId'] for item in items if item.get('id', {}).get('videoId')]
            
            details_dict = {}
            if video_ids:
                try:
                    details = self._get('videos', {
                        'part': 'contentDetails,statistics',
                        'id': ','.join(video_ids)
                    })
                    for d_item in details.get('items', []):
                        details_dict[d_item['id']] = d_item
                except Exception as de:
                    logger.warning(f"Failed to fetch detail statistics for search results: {de}")
                    
            for item in items:
                vid = item.get('id', {}).get('videoId')
                if not vid:
                    continue
                snippet = item.get('snippet', {})
                d_item = details_dict.get(vid, {})
                stats = d_item.get('statistics', {})
                content_details = d_item.get('contentDetails', {})
                
                duration = self.parse_iso8601_duration(content_details.get('duration'))
                published_at = snippet.get('publishedAt')
                upload_date = published_at[:10] if published_at else None
                
                thumbs = snippet.get('thumbnails', {})
                thumb_url = (
                    thumbs.get('high', {}).get('url') or 
                    thumbs.get('medium', {}).get('url') or 
                    thumbs.get('default', {}).get('url')
                )
                
                results.append({
                    'video_id': vid,
                    'title': snippet.get('title'),
                    'channel': snippet.get('channelTitle'),
                    'channel_id': snippet.get('channelId'),
                    'thumbnail_url': thumb_url,
                    'duration_seconds': duration,
                    'view_count': int(stats.get('viewCount') or 0),
                    'upload_date': upload_date
                })
                
        elif api_type == 'channel':
            channel_ids = [item['id']['channelId'] for item in items if item.get('id', {}).get('channelId')]
            
            details_dict = {}
            if channel_ids:
                try:
                    details = self._get('channels', {
                        'part': 'statistics',
                        'id': ','.join(channel_ids)
                    })
                    for d_item in details.get('items', []):
                        details_dict[d_item['id']] = d_item
                except Exception as de:
                    logger.warning(f"Failed to fetch stats for search channels: {de}")
                    
            for item in items:
                cid = item.get('id', {}).get('channelId')
                if not cid:
                    continue
                snippet = item.get('snippet', {})
                d_item = details_dict.get(cid, {})
                stats = d_item.get('statistics', {})
                
                thumbs = snippet.get('thumbnails', {})
                thumb_url = (
                    thumbs.get('high', {}).get('url') or 
                    thumbs.get('medium', {}).get('url') or 
                    thumbs.get('default', {}).get('url')
                )
                
                results.append({
                    'channel_id': cid,
                    'title': snippet.get('title'),
                    'handle': snippet.get('customUrl') or snippet.get('title'),
                    'thumbnail_url': thumb_url,
                    'view_count': int(stats.get('viewCount') or 0),
                    'video_count': int(stats.get('videoCount') or 0)
                })
                
        elif api_type == 'playlist':
            playlist_ids = [item['id']['playlistId'] for item in items if item.get('id', {}).get('playlistId')]
            
            details_dict = {}
            if playlist_ids:
                try:
                    details = self._get('playlists', {
                        'part': 'contentDetails',
                        'id': ','.join(playlist_ids)
                    })
                    for d_item in details.get('items', []):
                        details_dict[d_item['id']] = d_item
                except Exception as de:
                    logger.warning(f"Failed to fetch details for search playlists: {de}")
                    
            for item in items:
                pid = item.get('id', {}).get('playlistId')
                if not pid:
                    continue
                snippet = item.get('snippet', {})
                d_item = details_dict.get(pid, {})
                content_details = d_item.get('contentDetails', {})
                
                thumbs = snippet.get('thumbnails', {})
                thumb_url = (
                    thumbs.get('high', {}).get('url') or 
                    thumbs.get('medium', {}).get('url') or 
                    thumbs.get('default', {}).get('url')
                )
                
                results.append({
                    'playlist_id': pid,
                    'title': snippet.get('title'),
                    'channel': snippet.get('channelTitle'),
                    'channel_id': snippet.get('channelId'),
                    'thumbnail_url': thumb_url,
                    'video_count': int(content_details.get('itemCount') or 0)
                })
                
        return results

    def fetch_video_transcript(self, video_id: str, languages: list = None) -> dict:
        """
        Fetches transcript for video using youtube-transcript-api.
        Returns dict with keys: video_id, language_code, is_generated, full_text, segments,
        or None if no transcript is available.
        """
        from app.utils.youtube_url import parse_youtube_video_id
        canonical_id = parse_youtube_video_id(video_id) or video_id
        if not canonical_id:
            return None

        from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled, NoTranscriptFound, CouldNotRetrieveTranscript
        if languages is None:
            languages = ['en', 'en-US', 'en-GB']

        try:
            transcript_list = YouTubeTranscriptApi.list_transcripts(canonical_id)
            transcript = None
            is_generated = False
            lang_code = 'en'

            try:
                transcript = transcript_list.find_manually_created_transcript(languages)
                is_generated = False
                lang_code = transcript.language_code
            except Exception:
                try:
                    transcript = transcript_list.find_generated_transcript(languages)
                    is_generated = True
                    lang_code = transcript.language_code
                except Exception:
                    for t in transcript_list:
                        transcript = t
                        is_generated = t.is_generated
                        lang_code = t.language_code
                        break

            if not transcript:
                logger.info(f"No transcript found for video {canonical_id}")
                return None

            raw_segments = transcript.fetch()
            segments = []
            text_parts = []
            for s in raw_segments:
                seg_text = s.get('text', '').strip()
                if seg_text:
                    segments.append({
                        'start': round(float(s.get('start', 0)), 2),
                        'duration': round(float(s.get('duration', 0)), 2),
                        'text': seg_text
                    })
                    text_parts.append(seg_text)

            full_text = " ".join(text_parts)
            return {
                'video_id': canonical_id,
                'language_code': lang_code,
                'is_generated': is_generated,
                'full_text': full_text,
                'segments': segments
            }
        except (TranscriptsDisabled, NoTranscriptFound, CouldNotRetrieveTranscript) as te:
            logger.info(f"Transcript unavailable for video {canonical_id}: {te}")
            return None
        except Exception as e:
            logger.warning(f"Unexpected error fetching transcript for video {canonical_id}: {e}")
            return None

    def save_video_transcript(self, transcript_data: dict):
        if not transcript_data:
            return None
        from app import db
        from app.models.transcript import Transcript
        from app.models.video import Video

        vid = transcript_data['video_id']
        existing = db.session.query(Transcript).filter(Transcript.video_id == vid).first()
        if existing:
            existing.language_code = transcript_data.get('language_code', 'en')
            existing.is_generated = transcript_data.get('is_generated', False)
            existing.full_text = transcript_data.get('full_text', '')
            existing.segments = transcript_data.get('segments', [])
            record = existing
        else:
            record = Transcript(
                video_id=vid,
                language_code=transcript_data.get('language_code', 'en'),
                is_generated=transcript_data.get('is_generated', False),
                full_text=transcript_data.get('full_text', '')
            )
            record.segments = transcript_data.get('segments', [])
            db.session.add(record)

        video = db.session.query(Video).filter(Video.id == vid).first()
        if video:
            video.has_transcript = True

        db.session.commit()
        return record

    def fetch_video_comments(self, video_id: str, max_results: int = 50) -> list:
        """
        Fetches top-level comments for video using YouTube Data API commentThreads.list.
        Returns list of parsed comment dicts.
        """
        from app.utils.youtube_url import parse_youtube_video_id
        canonical_id = parse_youtube_video_id(video_id) or video_id
        if not canonical_id:
            return []

        params = {
            'part': 'snippet',
            'videoId': canonical_id,
            'maxResults': min(max_results, 100),
            'textFormat': 'plainText',
            'order': 'relevance'
        }

        try:
            res = self._get('commentThreads', params)
        except YouTubeAPIError as e:
            logger.info(f"Comments unavailable or error for video {canonical_id}: {e}")
            return []

        items = res.get('items', [])
        comments = []
        for item in items:
            c_snippet = item.get('snippet', {}).get('topLevelComment', {}).get('snippet', {})
            cid = item.get('id')
            if not cid or not c_snippet:
                continue

            pub_at_str = c_snippet.get('publishedAt')
            published_at = self.parse_iso8601_date(pub_at_str) or datetime.utcnow()

            comments.append({
                'id': cid,
                'video_id': canonical_id,
                'parent_id': None,
                'author_name': c_snippet.get('authorDisplayName', 'Anonymous'),
                'author_id': c_snippet.get('authorChannelId', {}).get('value'),
                'author_thumbnail': c_snippet.get('authorProfileImageUrl'),
                'text': c_snippet.get('textDisplay', ''),
                'like_count': int(c_snippet.get('likeCount') or 0),
                'published_at': published_at,
                'is_favorited': False,
                'is_pinned': False,
                'author_is_creator': False
            })

        return comments

    def save_video_comments(self, comments_data: list):
        if not comments_data:
            return []
        from app import db
        from app.models.comment import Comment

        saved_records = []
        for c in comments_data:
            existing = db.session.query(Comment).filter(Comment.id == c['id']).first()
            if existing:
                existing.text = c.get('text', existing.text)
                existing.like_count = c.get('like_count', existing.like_count)
                saved_records.append(existing)
            else:
                record = Comment(
                    id=c['id'],
                    video_id=c['video_id'],
                    parent_id=c.get('parent_id'),
                    author_name=c['author_name'],
                    author_id=c.get('author_id'),
                    author_thumbnail=c.get('author_thumbnail'),
                    text=c['text'],
                    like_count=c.get('like_count', 0),
                    published_at=c.get('published_at', datetime.utcnow()),
                    is_favorited=c.get('is_favorited', False),
                    is_pinned=c.get('is_pinned', False),
                    author_is_creator=c.get('author_is_creator', False)
                )
                db.session.add(record)
                saved_records.append(record)

        db.session.commit()
        return saved_records

    @staticmethod
    def calculate_engagement_rate(like_count: int, comment_count: int, view_count: int) -> float:
        """
        Calculates engagement rate percentage: (likes + comments) / views * 100.
        Returns 0.0 if view_count is 0 or None.
        """
        if not view_count or view_count <= 0:
            return 0.0
        likes = like_count or 0
        comments = comment_count or 0
        rate = ((likes + comments) / view_count) * 100.0
        return round(rate, 2)
