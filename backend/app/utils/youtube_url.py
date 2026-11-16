import re
from urllib.parse import urlparse, parse_qs
from typing import Optional, Tuple

YOUTUBE_DOMAINS = {
    'youtube.com',
    'www.youtube.com',
    'm.youtube.com',
    'music.youtube.com',
    'youtu.be'
}

VIDEO_ID_REGEX = re.compile(r'^[A-Za-z0-9_-]{11}$')
CHANNEL_ID_REGEX = re.compile(r'^UC[A-Za-z0-9_-]{22}$')
HANDLE_REGEX = re.compile(r'^@[A-Za-z0-9_.-]+$')

def parse_youtube_video_id(url_or_id: str) -> Optional[str]:
    """
    Extracts and validates an 11-character YouTube video ID.
    Supports bare 11-char IDs, watch?v=, youtu.be/, /shorts/, /embed/, /live/, /v/.
    Rejects lookalike domains and SSRF vectors.
    """
    if not url_or_id or not isinstance(url_or_id, str):
        return None

    cleaned = url_or_id.strip()
    if not cleaned:
        return None

    # Check if input is already a raw 11-character video ID
    if VIDEO_ID_REGEX.match(cleaned):
        return cleaned

    # Add scheme if missing for proper urllib.parse handling
    if not (cleaned.startswith('http://') or cleaned.startswith('https://')):
        # Avoid treating protocol-relative or bare hosts incorrectly
        if cleaned.startswith('//'):
            cleaned = 'https:' + cleaned
        else:
            cleaned = 'https://' + cleaned

    try:
        parsed = urlparse(cleaned)
    except Exception:
        return None

    hostname = (parsed.hostname or '').lower()
    if hostname not in YOUTUBE_DOMAINS:
        return None

    path = parsed.path.rstrip('/')
    query_params = parse_qs(parsed.query)

    video_id = None

    if hostname == 'youtu.be':
        # youtu.be/<video_id>
        parts = [p for p in path.split('/') if p]
        if parts:
            video_id = parts[0]
    else:
        # Check query parameter ?v=
        if 'v' in query_params and query_params['v']:
            video_id = query_params['v'][0].rstrip('/')
        else:
            # Check path segments: /shorts/<id>, /embed/<id>, /live/<id>, /v/<id>
            parts = [p for p in path.split('/') if p]
            if len(parts) >= 2 and parts[0] in ('shorts', 'embed', 'live', 'v'):
                video_id = parts[1]

    if video_id:
        video_id = video_id.rstrip('/')
        if VIDEO_ID_REGEX.match(video_id):
            return video_id

    return None

def get_canonical_video_url(url_or_id: str) -> Optional[str]:
    """
    Returns canonical 'https://www.youtube.com/watch?v={video_id}' or None.
    """
    video_id = parse_youtube_video_id(url_or_id)
    if video_id:
        return f"https://www.youtube.com/watch?v={video_id}"
    return None

def parse_youtube_channel_url(url_or_id: str) -> Optional[Tuple[str, str]]:
    """
    Extracts and validates a YouTube channel identifier and canonical URL.
    Returns (identifier, canonical_url) or None.
    Identifier can be a Channel ID (UC...) or @handle.
    """
    if not url_or_id or not isinstance(url_or_id, str):
        return None

    cleaned = url_or_id.strip()
    if not cleaned:
        return None

    # Direct Channel ID
    if CHANNEL_ID_REGEX.match(cleaned):
        return cleaned, f"https://www.youtube.com/channel/{cleaned}"

    # Direct @handle
    if HANDLE_REGEX.match(cleaned):
        return cleaned, f"https://www.youtube.com/{cleaned}"

    if not (cleaned.startswith('http://') or cleaned.startswith('https://')):
        if cleaned.startswith('//'):
            cleaned = 'https:' + cleaned
        else:
            cleaned = 'https://' + cleaned

    try:
        parsed = urlparse(cleaned)
    except Exception:
        return None

    hostname = (parsed.hostname or '').lower()
    if hostname not in ('youtube.com', 'www.youtube.com', 'm.youtube.com'):
        return None

    path = parsed.path.rstrip('/')
    parts = [p for p in path.split('/') if p]

    if not parts:
        return None

    # Handle /channel/UC...
    if parts[0] == 'channel' and len(parts) >= 2:
        cid = parts[1]
        if CHANNEL_ID_REGEX.match(cid):
            return cid, f"https://www.youtube.com/channel/{cid}"

    # Handle /@handle
    if parts[0].startswith('@'):
        handle = parts[0]
        if HANDLE_REGEX.match(handle):
            return handle, f"https://www.youtube.com/{handle}"

    # Handle /c/name or /user/name
    if parts[0] in ('c', 'user') and len(parts) >= 2:
        name = parts[1]
        return name, f"https://www.youtube.com/{parts[0]}/{name}"

    return None

def is_valid_youtube_channel_url(url: str) -> bool:
    return parse_youtube_channel_url(url) is not None
