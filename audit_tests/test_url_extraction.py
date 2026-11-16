import sys
import os
import unittest

sys.path.insert(0, os.path.abspath('backend'))

from app.controllers.download_controller import extract_video_id
from app.services.youtube_api_service import YouTubeApiService

class TestURLExtractionAndValidation(unittest.TestCase):
    def setUp(self):
        # We can test extract_channel_id_or_handle without an API key
        # by creating an instance with a dummy key for parsing methods
        os.environ['YOUTUBE_API_KEY'] = 'test_dummy_key'
        self.api_service = YouTubeApiService()

    def test_standard_watch_url(self):
        url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        self.assertEqual(extract_video_id(url), "dQw4w9WgXcQ")

    def test_short_youtu_be_url(self):
        url = "https://youtu.be/dQw4w9WgXcQ"
        self.assertEqual(extract_video_id(url), "dQw4w9WgXcQ")

    def test_shorts_url(self):
        url = "https://www.youtube.com/shorts/dQw4w9WgXcQ"
        self.assertEqual(extract_video_id(url), "dQw4w9WgXcQ")

    def test_embed_url(self):
        url = "https://www.youtube.com/embed/dQw4w9WgXcQ"
        self.assertEqual(extract_video_id(url), "dQw4w9WgXcQ")

    def test_live_url_bug(self):
        """CRITICAL: Test if /live/ URLs are supported."""
        url = "https://www.youtube.com/live/dQw4w9WgXcQ"
        extracted = extract_video_id(url)
        # YouTube uses /live/<id> for live streams. The regex currently fails to extract this.
        print(f"[REPRODUCTION] /live/ URL '{url}' -> extracted: {extracted}")
        # We document the actual bug:
        self.assertIsNone(extracted, "Known defect: /live/ URL is not supported by extract_video_id regex")

    def test_m_and_music_subdomains(self):
        m_url = "https://m.youtube.com/watch?v=dQw4w9WgXcQ"
        music_url = "https://music.youtube.com/watch?v=dQw4w9WgXcQ"
        self.assertEqual(extract_video_id(m_url), "dQw4w9WgXcQ")
        self.assertEqual(extract_video_id(music_url), "dQw4w9WgXcQ")

    def test_tracking_and_extra_parameters(self):
        url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ&t=120s&list=PL12345&si=abc&feature=share"
        self.assertEqual(extract_video_id(url), "dQw4w9WgXcQ")

    def test_bare_11_char_id(self):
        self.assertEqual(extract_video_id("dQw4w9WgXcQ"), "dQw4w9WgXcQ")

    def test_whitespace_and_trailing_slash(self):
        url = "   https://www.youtube.com/watch?v=dQw4w9WgXcQ/   "
        self.assertEqual(extract_video_id(url), "dQw4w9WgXcQ")

    def test_ssrf_and_domain_allowlist_vulnerability(self):
        """CRITICAL: extract_video_id extracts video ID from arbitrary non-YouTube domains."""
        evil_url = "https://evil-phishing-site.com/watch?v=dQw4w9WgXcQ"
        extracted = extract_video_id(evil_url)
        print(f"[REPRODUCTION] SSRF non-allowlisted domain '{evil_url}' -> extracted: {extracted}")
        # The parser does NOT validate domain, it extracts dQw4w9WgXcQ from evil-phishing-site.com!
        self.assertEqual(extracted, "dQw4w9WgXcQ")

    def test_channel_urls_rejected_by_video_extractor(self):
        self.assertIsNone(extract_video_id("https://www.youtube.com/channel/UC_x5XG1OV2P6uZZ5FSM9Ttw"))
        self.assertIsNone(extract_video_id("https://www.youtube.com/@mkbhd"))
        self.assertIsNone(extract_video_id("https://www.youtube.com/c/CreatorName"))
        self.assertIsNone(extract_video_id("https://www.youtube.com/user/LegacyUser"))
        self.assertIsNone(extract_video_id("https://www.youtube.com/playlist?list=PL1234567890abcdef"))

    def test_channel_parser_variations(self):
        # 1. Channel ID
        cid, handle, username, q = self.api_service.extract_channel_id_or_handle("https://www.youtube.com/channel/UC_x5XG1OV2P6uZZ5FSM9Ttw")
        self.assertEqual(cid, "UC_x5XG1OV2P6uZZ5FSM9Ttw")

        # 2. Handle
        cid, handle, username, q = self.api_service.extract_channel_id_or_handle("https://www.youtube.com/@mkbhd")
        self.assertEqual(handle, "@mkbhd")

        # 3. Legacy User
        cid, handle, username, q = self.api_service.extract_channel_id_or_handle("https://www.youtube.com/user/olduser")
        self.assertEqual(username, "olduser")

        # 4. Custom /c/ URL
        cid, handle, username, q = self.api_service.extract_channel_id_or_handle("https://www.youtube.com/c/SomeCreator")
        print(f"[REPRODUCTION] /c/ URL parsed as: cid={cid}, handle={handle}, username={username}, q={q}")
        # Notice: /c/ URLs are NOT matched by regex, so they fall back to query search (which consumes 100 quota units!)
        self.assertEqual(q, "https://www.youtube.com/c/SomeCreator")

if __name__ == '__main__':
    unittest.main()

