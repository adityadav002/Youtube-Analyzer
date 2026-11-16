import os
import sys
import unittest
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.abspath('backend'))

from app import create_app, db
from app.models.history import SearchHistory, DownloadHistory
from app.models.video import Video
from app.repositories.search_repository import SearchRepository
from app.services.search_service import SearchService
from app.services.youtube_api_service import YouTubeApiService

class TestCrawlerAndQuota(unittest.TestCase):
    def setUp(self):
        self.app = create_app('testing')
        self.client = self.app.test_client()
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def test_search_query_normalization_and_24h_ttl(self):
        """
        Fix 8: Queries must be normalized (whitespace, lowercased) and saved with 24h TTL.
        """
        raw_query = "  Python   Machine  Learning   "
        normalized = SearchRepository.normalize_query(raw_query)
        self.assertEqual(normalized, "python machine learning")

        # Save cache with default 24h TTL
        dummy_results = [{'video_id': 'vid123', 'title': 'Test ML'}]
        record = SearchRepository.save_query_cache(raw_query, 'video', 1, dummy_results, ttl_hours=24)
        self.assertEqual(record.query, "python machine learning")

        # Check TTL is approximately 24 hours
        time_diff = record.expires_at - datetime.utcnow()
        self.assertTrue(timedelta(hours=23, minutes=50) <= time_diff <= timedelta(hours=24, minutes=10))

        # Lookup with different casing and whitespace must hit cache
        lookup_query = "PYTHON   machine LEARNING"
        cached = SearchRepository.get_cached_query(lookup_query, 'video')
        self.assertIsNotNone(cached)
        self.assertEqual(cached.id, record.id)

    def test_crawler_stops_and_fills_slots_when_no_live_streams(self):
        """
        Fix 7: When channel has 0 live streams, crawler must not loop infinitely;
        it must fill remaining slots from available normal/shorts and terminate cleanly.
        """
        api_service = YouTubeApiService.__new__(YouTubeApiService)
        api_service.api_key = "test_key"
        api_service.base_url = "https://www.googleapis.com/youtube/v3"

        # Mock playlistItems response with 25 normal videos (no live streams)
        playlist_items = [
            {'contentDetails': {'videoId': f'vid_{i:02d}'}} for i in range(25)
        ]
        
        # Mock videos.list response
        videos_items = []
        for i in range(25):
            videos_items.append({
                'id': f'vid_{i:02d}',
                'snippet': {
                    'title': f'Video {i}',
                    'description': 'Description',
                    'publishedAt': '2025-01-01T00:00:00Z',
                    'categoryId': '28',
                    'liveBroadcastContent': 'none',
                    'thumbnails': {'high': {'url': 'https://example.com/thumb.jpg'}}
                },
                'contentDetails': {
                    'duration': 'PT10M0S',
                    'caption': 'false'
                },
                'statistics': {
                    'viewCount': '1000',
                    'likeCount': '50',
                    'commentCount': '5'
                },
                'status': {
                    'privacyStatus': 'public'
                }
            })

        def mock_get(endpoint, params):
            if endpoint == 'playlistItems':
                return {'items': playlist_items, 'nextPageToken': None}
            elif endpoint == 'videos':
                requested_ids = params['id'].split(',')
                return {'items': [v for v in videos_items if v['id'] in requested_ids]}
            return {}

        with patch.object(api_service, '_get', side_effect=mock_get):
            # Request limit=20
            videos_data, inserted, updated, result_counts = api_service.crawl_channel_videos(
                channel_id="UC1234567890123456789012",
                start_index=1,
                limit=20
            )

            # Even with 0 live streams, total imported must reach requested limit 20
            self.assertEqual(len(videos_data), 20)
            self.assertEqual(result_counts['total'], 20)
            self.assertEqual(result_counts['live'], 0)
            self.assertEqual(result_counts['normal'], 20)

    def test_missing_download_file_reconciled_as_expired(self):
        """
        Fix 9: get_downloads must reconcile missing physical files as 'expired'.
        """
        v = Video(id="vid_test_123", title="Test Video", channel_id="UC123")
        db.session.add(v)
        
        # Complete history whose physical file does not exist on disk
        missing_file = os.path.abspath("downloads/non_existent_file_123.mp4")
        hist = DownloadHistory(
            video_id="vid_test_123",
            download_type="video",
            quality="best",
            status="complete",
            file_path=missing_file
        )
        db.session.add(hist)
        db.session.commit()

        res = self.client.get('/api/downloads')
        self.assertEqual(res.status_code, 200)
        items = res.get_json()
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]['status'], 'expired')
        self.assertIn("expired", items[0]['error_message'].lower())

