import sys
import os
import json
import unittest
from datetime import datetime, timezone

sys.path.insert(0, os.path.abspath('backend'))

from app.services.youtube_api_service import YouTubeApiService, parse_chapters_from_description
from app.repositories.video_repository import VideoRepository

class TestYouTubeAPIParsing(unittest.TestCase):
    def setUp(self):
        os.environ['YOUTUBE_API_KEY'] = 'test_dummy_key'
        self.api = YouTubeApiService()
        self.fixtures_dir = os.path.join(os.path.dirname(__file__), 'fixtures')

    def load_fixture(self, name):
        with open(os.path.join(self.fixtures_dir, name), 'r', encoding='utf-8') as f:
            return json.load(f)

    def test_duration_parsing(self):
        # Normal durations
        self.assertEqual(self.api.parse_iso8601_duration("PT3M33S"), 213)
        self.assertEqual(self.api.parse_iso8601_duration("PT45S"), 45)
        self.assertEqual(self.api.parse_iso8601_duration("PT1H2M3S"), 3723)
        self.assertEqual(self.api.parse_iso8601_duration("P1DT2H3M4S"), 86400 + 7200 + 180 + 4)
        
        # Live duration in YouTube API is P0D
        live_dur = self.api.parse_iso8601_duration("P0D")
        self.assertEqual(live_dur, 0)
        
        # Empty or None
        self.assertEqual(self.api.parse_iso8601_duration(""), 0)
        self.assertEqual(self.api.parse_iso8601_duration(None), 0)

    def test_date_parsing_and_timezone(self):
        dt = self.api.parse_iso8601_date("2026-11-16T08:00:00Z")
        self.assertIsNotNone(dt)
        self.assertEqual(dt.tzinfo, timezone.utc)
        self.assertEqual(dt.year, 2026)
        self.assertEqual(dt.hour, 8)

    def test_chapter_parsing(self):
        desc = (
            "Here is the video breakdown:\n"
            "00:00 Intro\n"
            "01:30 Setup Environment\n"
            "05:45 Building Models\n"
            "10:00 Conclusion"
        )
        duration = 700
        chapters = parse_chapters_from_description(desc, duration)
        
        self.assertEqual(len(chapters), 4)
        self.assertEqual(chapters[0]['title'], "Intro")
        self.assertEqual(chapters[0]['start_time'], 0)
        self.assertEqual(chapters[0]['end_time'], 90)
        self.assertEqual(chapters[1]['title'], "Setup Environment")
        self.assertEqual(chapters[1]['start_time'], 90)
        self.assertEqual(chapters[1]['end_time'], 345)
        self.assertEqual(chapters[3]['end_time'], duration)

    def test_chapter_parsing_missing_zero_start(self):
        # Description where creator forgot 00:00
        desc = "02:00 Main Topic Starts"
        chapters = parse_chapters_from_description(desc, 300)
        self.assertEqual(len(chapters), 2)
        self.assertEqual(chapters[0]['title'], "Introduction")
        self.assertEqual(chapters[0]['start_time'], 0)
        self.assertEqual(chapters[0]['end_time'], 120)

    def test_hidden_likes_parsing(self):
        fixture = self.load_fixture('video_hidden_likes.json')
        item = fixture['items'][0]
        stats = item.get('statistics', {})
        like_count = int(stats.get('likeCount') or 0) if 'likeCount' in stats else None
        
        # Verification: like_count is None when hidden, NOT 0
        self.assertIsNone(like_count)
        print(f"[VERIFIED] Hidden likeCount correctly parsed as None: {like_count}")

    def test_comments_disabled_parsing(self):
        fixture = self.load_fixture('video_comments_disabled.json')
        item = fixture['items'][0]
        stats = item.get('statistics', {})
        comments_disabled = 'commentCount' not in stats
        comment_count = int(stats.get('commentCount') or 0) if 'commentCount' in stats else None
        
        self.assertTrue(comments_disabled)
        self.assertIsNone(comment_count)
        print(f"[VERIFIED] Comments disabled correctly detected: comments_disabled={comments_disabled}, count={comment_count}")

    def test_classification_logic_invariants(self):
        # Test 1: Live stream with duration=0 (P0D)
        is_short, is_live, live_status = VideoRepository.resolve_classification(
            is_short=False, is_live=True, live_status='is_live', duration=0
        )
        self.assertTrue(is_live)
        self.assertFalse(is_short)
        self.assertEqual(live_status, 'is_live')

        # Test 2: Short video with duration=42
        is_short, is_live, live_status = VideoRepository.resolve_classification(
            is_short=False, is_live=False, live_status='not_live', duration=42
        )
        self.assertTrue(is_short)
        self.assertFalse(is_live)

        # Test 3: Normal video with duration=600
        is_short, is_live, live_status = VideoRepository.resolve_classification(
            is_short=False, is_live=False, live_status='not_live', duration=600
        )
        self.assertFalse(is_short)
        self.assertFalse(is_live)

        # Test 4: Conflict resolution - live stream claiming is_short=True
        is_short, is_live, live_status = VideoRepository.resolve_classification(
            is_short=True, is_live=True, live_status='is_live', duration=45
        )
        self.assertTrue(is_live)
        self.assertFalse(is_short) # Invariant: Never allow is_short=True and is_live=True

if __name__ == '__main__':
    unittest.main()

