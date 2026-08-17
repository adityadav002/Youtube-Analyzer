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
    pass

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
            raise YouTubeAPIError("YouTube API key configuration is missing. Please set YOUTUBE_API_KEY in your environment.")
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
        except requests.exceptions.RequestException as e:
            logger.error(f"Network error connecting to YouTube API: {e}")
            raise YouTubeAPIError("Unable to connect to YouTube Data API due to network error.") from e
            
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
            if reason == 'quotaExceeded':
                raise YouTubeAPIError("YouTube Data API quota exceeded.")
            raise YouTubeAPIError(f"YouTube API returned HTTP 403: {msg}")
        elif resp.status_code == 400:
            if reason == 'keyInvalid':
                raise YouTubeAPIError("Invalid YouTube API key.")
            raise YouTubeAPIError(f"YouTube API returned HTTP 400: {msg}")
        elif resp.status_code == 404:
            raise YouTubeAPIError("YouTube resource not found.")
        else:
            raise YouTubeAPIError(f"YouTube API returned HTTP {resp.status_code}: {msg}")

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

        if limit == 50:
            target_normal = 30
            target_shorts = 10
            target_live = 10
        else:
            # Proportional distribution: 60% normal, 20% shorts, 20% live
            target_shorts = max(1, int(limit * 0.2)) if limit >= 5 else 0
            target_live = max(1, int(limit * 0.2)) if limit >= 5 else 0
            target_normal = limit - target_shorts - target_live

        logger.info(f"[Crawler] Target: {target_normal} normal, {target_shorts} shorts, {target_live} live")

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
                elif resolved_short:
                    if len(shorts_videos) < target_shorts:
                        shorts_videos.append(video_record)
                else:
                    if len(normal_videos) < target_normal:
                        normal_videos.append(video_record)

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
                logger.info("[Crawler] Target reached")
                break

            if stop_crawl or not res.get('nextPageToken'):
                logger.info("[Crawler] Stop condition reached or end of playlist.")
                break
                
            next_page_token = res.get('nextPageToken')

        # Combine all selected videos
        videos_data = normal_videos + shorts_videos + live_videos
        
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
