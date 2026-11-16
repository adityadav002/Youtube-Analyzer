import os
import sys
import unittest
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.abspath('backend'))

from app.utils.youtube_url import (
    parse_youtube_video_id,
    get_canonical_video_url,
    parse_youtube_channel_url,
    is_valid_youtube_channel_url
)
from app.services.youtube_api_service import (
    YouTubeAPIError,
    YouTubeQuotaExceededError,
    YouTubeConfigError,
    YouTubeTimeoutError,
    YouTubeNetworkError
)

class TestYouTubeURLAndSecurity(unittest.TestCase):
    def test_valid_video_urls(self):
        valid_cases = [
            ("dQw4w9WgXcQ", "dQw4w9WgXcQ"),
            ("https://www.youtube.com/watch?v=dQw4w9WgXcQ", "dQw4w9WgXcQ"),
            ("http://youtube.com/watch?v=dQw4w9WgXcQ", "dQw4w9WgXcQ"),
            ("https://youtu.be/dQw4w9WgXcQ", "dQw4w9WgXcQ"),
            ("https://www.youtube.com/shorts/dQw4w9WgXcQ", "dQw4w9WgXcQ"),
            ("https://www.youtube.com/embed/dQw4w9WgXcQ", "dQw4w9WgXcQ"),
            ("https://www.youtube.com/live/dQw4w9WgXcQ", "dQw4w9WgXcQ"),
            ("https://m.youtube.com/watch?v=dQw4w9WgXcQ", "dQw4w9WgXcQ"),
            ("https://music.youtube.com/watch?v=dQw4w9WgXcQ", "dQw4w9WgXcQ"),
            ("https://www.youtube.com/watch?v=dQw4w9WgXcQ&t=120s&list=PL123&si=xyz", "dQw4w9WgXcQ"),
            ("  https://WWW.YOUTUBE.COM/watch?v=dQw4w9WgXcQ/  ", "dQw4w9WgXcQ"),
        ]
        for url_input, expected_id in valid_cases:
            with self.subTest(url=url_input):
                extracted = parse_youtube_video_id(url_input)
                self.assertEqual(extracted, expected_id)
                canonical = get_canonical_video_url(url_input)
                self.assertEqual(canonical, f"https://www.youtube.com/watch?v={expected_id}")

    def test_ssrf_and_invalid_urls_rejected(self):
        invalid_cases = [
            "https://youtube.com.attacker.com/watch?v=dQw4w9WgXcQ",
            "https://attacker.com/watch?v=dQw4w9WgXcQ",
            "http://169.254.169.254/latest/meta-data/",
            "file:///etc/passwd",
            "javascript:alert(1)",
            "https://youtube.com/watch?v=short",  # too short
            "https://youtube.com/watch?v=toolongvideoidentifier123",  # too long
            "https://youtube.com/watch?v=invalid$char",
            "",
            None,
            "not a url at all"
        ]
        for bad_url in invalid_cases:
            with self.subTest(url=bad_url):
                self.assertIsNone(parse_youtube_video_id(bad_url))

    def test_channel_url_parser(self):
        valid_channels = [
            ("UC_x5XG1OV2P6uZZ5FSM9Ttw", "UC_x5XG1OV2P6uZZ5FSM9Ttw"),
            ("https://www.youtube.com/channel/UC_x5XG1OV2P6uZZ5FSM9Ttw", "UC_x5XG1OV2P6uZZ5FSM9Ttw"),
            ("@GoogleDevelopers", "@GoogleDevelopers"),
            ("https://www.youtube.com/@GoogleDevelopers", "@GoogleDevelopers"),
            ("https://youtube.com/c/CreatorInsider", "CreatorInsider"),
        ]
        for channel_input, expected_id in valid_channels:
            with self.subTest(channel=channel_input):
                res = parse_youtube_channel_url(channel_input)
                self.assertIsNotNone(res)
                identifier, canonical_url = res
                self.assertEqual(identifier, expected_id)
                self.assertTrue(canonical_url.startswith("https://www.youtube.com/"))

        invalid_channels = [
            "https://evil.com/channel/UC_x5XG1OV2P6uZZ5FSM9Ttw",
            "http://169.254.169.254/channel/UC123",
            "https://youtube.com/notachannelpath",
            "",
            None
        ]
        for bad_chan in invalid_channels:
            with self.subTest(bad_channel=bad_chan):
                self.assertIsNone(parse_youtube_channel_url(bad_chan))

    def test_open_file_location_disabled_in_remote_env(self):
        from app import create_app, db
        from app.models.history import DownloadHistory
        from app.models.video import Video
        app = create_app('testing')
        app.config['ENABLE_LOCAL_FILE_OPEN'] = False

        client = app.test_client()
        with app.app_context():
            db.create_all()
            v = Video(id="dQw4w9WgXcQ", title="Test", channel_id="UC123")
            db.session.add(v)
            hist = DownloadHistory(video_id="dQw4w9WgXcQ", download_type="video", quality="best", status="complete", file_path="downloads/test.mp4")
            db.session.add(hist)
            db.session.commit()
            
            res = client.post(f'/api/downloads/{hist.id}/open')
            self.assertEqual(res.status_code, 501)
            self.assertIn("not supported", res.get_json().get('error', '').lower())

    def test_open_file_location_blocks_path_traversal(self):
        from app import create_app, db
        from app.models.history import DownloadHistory
        from app.models.video import Video
        app = create_app('testing')
        app.config['ENABLE_LOCAL_FILE_OPEN'] = True
        app.config['DOWNLOAD_DIR'] = os.path.abspath('downloads')

        client = app.test_client()
        with app.app_context():
            db.create_all()
            # Path outside DOWNLOAD_DIR, within workspace
            traversal_dir = os.path.abspath('temp_test_outside')
            os.makedirs(traversal_dir, exist_ok=True)
            traversal_path = os.path.join(traversal_dir, 'secret.txt')
            with open(traversal_path, 'w') as f:
                f.write("secret")
            try:
                v = Video(id="dQw4w9WgXcQ", title="Test", channel_id="UC123")
                db.session.add(v)
                hist = DownloadHistory(video_id="dQw4w9WgXcQ", download_type="video", quality="best", status="complete", file_path=traversal_path)
                db.session.add(hist)
                db.session.commit()

                res = client.post(f'/api/downloads/{hist.id}/open')
                self.assertEqual(res.status_code, 403)
                self.assertIn("denied", res.get_json().get('error', '').lower())
            finally:
                if os.path.exists(traversal_path):
                    os.remove(traversal_path)
                if os.path.exists(traversal_dir):
                    os.rmdir(traversal_dir)

    def test_downloads_disabled_returns_503(self):
        from app import create_app
        app = create_app('testing')
        app.config['ENABLE_DOWNLOADS'] = False

        client = app.test_client()
        res = client.post('/api/downloads', json={'url': 'https://youtube.com/watch?v=dQw4w9WgXcQ'})
        self.assertEqual(res.status_code, 503)
        self.assertIn("disabled", res.get_json().get('message', '').lower())

    def test_search_error_status_mapping(self):
        from app import create_app
        from app.services.search_service import SearchService
        app = create_app('testing')
        client = app.test_client()

        with patch.object(SearchService, 'search_youtube', side_effect=YouTubeQuotaExceededError("Quota exceeded")):
            res = client.get('/api/search/youtube?q=test')
            self.assertEqual(res.status_code, 503)

        with patch.object(SearchService, 'search_youtube', side_effect=YouTubeConfigError("Invalid API key")):
            res = client.get('/api/search/youtube?q=test')
            self.assertEqual(res.status_code, 503)

        with patch.object(SearchService, 'search_youtube', side_effect=YouTubeTimeoutError("Timed out")):
            res = client.get('/api/search/youtube?q=test')
            self.assertEqual(res.status_code, 504)

        with patch.object(SearchService, 'search_youtube', side_effect=YouTubeNetworkError("Network failed")):
            res = client.get('/api/search/youtube?q=test')
            self.assertEqual(res.status_code, 502)
