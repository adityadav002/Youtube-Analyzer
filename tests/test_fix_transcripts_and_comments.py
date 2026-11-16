import os
import sys
import unittest
from datetime import datetime
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.abspath('backend'))

from app import create_app, db
from app.models.video import Video
from app.models.transcript import Transcript
from app.models.comment import Comment
from app.services.youtube_api_service import YouTubeApiService

class TestTranscriptsAndComments(unittest.TestCase):
    def setUp(self):
        self.app = create_app('testing')
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def test_fetch_and_save_video_transcript(self):
        """
        Fix YA-007: Fetch and store video transcript using youtube-transcript-api.
        """
        v = Video(id="vid_transcript_1", title="Transcript Test", channel_id="UC123")
        db.session.add(v)
        db.session.commit()

        api_service = YouTubeApiService.__new__(YouTubeApiService)
        api_service.api_key = "test_key"
        api_service.base_url = "https://www.googleapis.com/youtube/v3"

        mock_segment_data = [
            {'start': 0.0, 'duration': 2.5, 'text': 'Hello world'},
            {'start': 2.5, 'duration': 3.0, 'text': 'Welcome to YouTube analyzer'}
        ]

        mock_transcript_obj = MagicMock()
        mock_transcript_obj.language_code = 'en'
        mock_transcript_obj.is_generated = False
        mock_transcript_obj.fetch.return_value = mock_segment_data

        mock_transcript_list = MagicMock()
        mock_transcript_list.find_manually_created_transcript.return_value = mock_transcript_obj

        with patch('youtube_transcript_api.YouTubeTranscriptApi.list_transcripts', return_value=mock_transcript_list):
            data = api_service.fetch_video_transcript("vid_transcript_1")
            self.assertIsNotNone(data)
            self.assertEqual(data['video_id'], "vid_transcript_1")
            self.assertEqual(data['full_text'], "Hello world Welcome to YouTube analyzer")
            self.assertEqual(len(data['segments']), 2)

            # Test saving to database
            record = api_service.save_video_transcript(data)
            self.assertIsNotNone(record)
            
            # Verify database record
            saved = db.session.query(Transcript).filter(Transcript.video_id == "vid_transcript_1").first()
            self.assertIsNotNone(saved)
            self.assertEqual(saved.full_text, "Hello world Welcome to YouTube analyzer")
            self.assertEqual(len(saved.segments), 2)
            
            # Verify video flag was updated
            v_refreshed = db.session.query(Video).filter(Video.id == "vid_transcript_1").first()
            self.assertTrue(v_refreshed.has_transcript)

    def test_transcript_disabled_returns_none(self):
        """
        Fix YA-007: When transcript is disabled or not found, return None without crashing.
        """
        from youtube_transcript_api import TranscriptsDisabled
        api_service = YouTubeApiService.__new__(YouTubeApiService)
        api_service.api_key = "test_key"
        api_service.base_url = "https://www.googleapis.com/youtube/v3"

        with patch('youtube_transcript_api.YouTubeTranscriptApi.list_transcripts', side_effect=TranscriptsDisabled("vid_no_transcript")):
            res = api_service.fetch_video_transcript("vid_no_transcript")
            self.assertIsNone(res)

    def test_fetch_and_save_video_comments(self):
        """
        Fix YA-007: Fetch and store top comments via YouTube Data API commentThreads.
        """
        v = Video(id="vid_comments_1", title="Comments Test", channel_id="UC123")
        db.session.add(v)
        db.session.commit()

        api_service = YouTubeApiService.__new__(YouTubeApiService)
        api_service.api_key = "test_key"
        api_service.base_url = "https://www.googleapis.com/youtube/v3"

        mock_api_response = {
            'items': [
                {
                    'id': 'comm_01',
                    'snippet': {
                        'topLevelComment': {
                            'snippet': {
                                'authorDisplayName': 'Jane Doe',
                                'authorChannelId': {'value': 'UC_jane'},
                                'authorProfileImageUrl': 'https://example.com/avatar.jpg',
                                'textDisplay': 'Great analysis video!',
                                'likeCount': 42,
                                'publishedAt': '2025-01-01T12:00:00Z'
                            }
                        }
                    }
                }
            ]
        }

        with patch.object(api_service, '_get', return_value=mock_api_response):
            comments = api_service.fetch_video_comments("vid_comments_1")
            self.assertEqual(len(comments), 1)
            self.assertEqual(comments[0]['id'], 'comm_01')
            self.assertEqual(comments[0]['author_name'], 'Jane Doe')
            self.assertEqual(comments[0]['like_count'], 42)

            saved = api_service.save_video_comments(comments)
            self.assertEqual(len(saved), 1)

            db_comment = db.session.query(Comment).filter(Comment.id == 'comm_01').first()
            self.assertIsNotNone(db_comment)
            self.assertEqual(db_comment.text, 'Great analysis video!')
            self.assertEqual(db_comment.like_count, 42)

    def test_calculate_engagement_rate(self):
        """
        Fix YA-007: Engagement rate calculation = (likes + comments) / views * 100.
        """
        rate = YouTubeApiService.calculate_engagement_rate(like_count=500, comment_count=100, view_count=10000)
        self.assertEqual(rate, 6.0)

        # 0 views must return 0.0 without ZeroDivisionError
        rate_zero = YouTubeApiService.calculate_engagement_rate(like_count=50, comment_count=10, view_count=0)
        self.assertEqual(rate_zero, 0.0)

        # None values handled gracefully
        rate_none = YouTubeApiService.calculate_engagement_rate(like_count=None, comment_count=None, view_count=1000)
        self.assertEqual(rate_none, 0.0)

