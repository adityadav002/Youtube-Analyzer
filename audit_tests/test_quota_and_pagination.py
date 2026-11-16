import sys
import os
import json
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.abspath('backend'))

from app.services.youtube_api_service import YouTubeApiService
from app.repositories.video_repository import VideoRepository
from app import create_app, db

class TestQuotaAndPaginationCrawler(unittest.TestCase):
    def setUp(self):
        self.app = create_app('testing')
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()

        os.environ['YOUTUBE_API_KEY'] = 'test_dummy_key'
        self.api = YouTubeApiService()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def test_crawler_bucket_bug_exhaustion_on_channels_without_live_streams(self):
        """
        REPRODUCTION of Crawler Quota Exhaustion Bug:
        When crawling a channel that has normal videos but NO live streams,
        the crawler continues paginating through every single page of the uploads playlist
        because target_live is never satisfied.
        """
        # Create a channel in DB
        from app.models.channel import Channel
        test_channel = Channel(id='UCtestChannelWithoutLive', display_name='Test Creator')
        db.session.add(test_channel)
        db.session.commit()

        # Simulate a channel with 150 normal videos across 3 pages (50 videos each)
        # All are normal videos (duration 600s, no #shorts, liveBroadcastContent='none')
        def mock_get(endpoint, params):
            if endpoint == 'playlistItems':
                page_token = params.get('pageToken')
                if not page_token:
                    # Page 1
                    return {
                        'nextPageToken': 'PAGE_2',
                        'items': [{'contentDetails': {'videoId': f'vid_{i:03d}'}} for i in range(1, 51)]
                    }
                elif page_token == 'PAGE_2':
                    return {
                        'nextPageToken': 'PAGE_3',
                        'items': [{'contentDetails': {'videoId': f'vid_{i:03d}'}} for i in range(51, 101)]
                    }
                elif page_token == 'PAGE_3':
                    return {
                        'items': [{'contentDetails': {'videoId': f'vid_{i:03d}'}} for i in range(101, 151)]
                    }
            elif endpoint == 'videos':
                ids = params.get('id', '').split(',')
                return {
                    'items': [{
                        'id': vid,
                        'snippet': {
                            'title': f'Video {vid}',
                            'description': 'Normal long form content',
                            'publishedAt': '2026-01-01T12:00:00Z',
                            'liveBroadcastContent': 'none',
                            'categoryId': '27'
                        },
                        'contentDetails': {
                            'duration': 'PT10M0S',  # 600 seconds -> normal video
                            'caption': 'true'
                        },
                        'statistics': {
                            'viewCount': '1000',
                            'likeCount': '50',
                            'commentCount': '10'
                        },
                        'status': {'privacyStatus': 'public'}
                    } for vid in ids]
                }
            return {}

        with patch.object(self.api, '_get', side_effect=mock_get):
            # User asks for limit=20 (default)
            videos_data, inserted, updated, result_counts = self.api.crawl_channel_videos(
                channel_id='UCtestChannelWithoutLive',
                start_index=1,
                limit=20,
                refresh_mode=False
            )

            print("\n--- [REPRODUCTION OUTPUT] Crawler with limit=20 on channel with no live streams ---")
            print(f"Target counts: normal={result_counts['target_normal']}, shorts={result_counts['target_shorts']}, live={result_counts['target_live']}")
            print(f"Result counts: normal={result_counts['normal']}, shorts={result_counts['shorts']}, live={result_counts['live']}")
            print(f"Total videos returned / saved: {len(videos_data)}")
            print("----------------------------------------------------------------------------------\n")

            # DEFECT CONFIRMATION:
            # 1. Target was 20: 12 normal, 4 shorts, 4 live.
            # 2. Because channel had 0 live and 0 shorts, the crawler fetched ALL 3 pages (150 videos)
            #    consuming 3 playlistItems calls and 3 videos.list calls (6 API calls instead of 1).
            # 3. Only 12 normal videos were saved! The other 138 videos were DISCARDED!
            self.assertEqual(result_counts['target_live'], 4)
            self.assertEqual(result_counts['live'], 0)
            self.assertEqual(result_counts['normal'], 12)
            self.assertEqual(len(videos_data), 12) # Discarded all other videos!

if __name__ == '__main__':
    unittest.main()

