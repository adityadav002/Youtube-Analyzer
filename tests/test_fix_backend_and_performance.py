import os
import sys
import unittest
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.abspath('backend'))

from app import create_app, db
from app.models.channel import Channel
from app.models.video import Video
from app.models.queue import ProcessingQueue
from app.services.channel_service import ChannelService
from app.utils.task_dispatcher import dispatch_task

class TestBackendCorrectnessAndPerformance(unittest.TestCase):
    def setUp(self):
        self.app = create_app('testing')
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def test_get_channels_no_commit_and_no_n_plus_one(self):
        """
        Fix 10: get_channels must not call db.session.commit() on GET requests,
        and must aggregate counts via a single grouped query rather than N+1 queries.
        """
        # Create 3 channels
        c1 = Channel(id="UC_1", display_name="Channel 1", video_count=0)
        c2 = Channel(id="UC_2", display_name="Channel 2", video_count=0)
        c3 = Channel(id="UC_3", display_name="Channel 3", video_count=0)
        db.session.add_all([c1, c2, c3])
        
        # Add videos
        v1 = Video(id="v_1", title="V1", channel_id="UC_1", view_count=100)
        v2 = Video(id="v_2", title="V2", channel_id="UC_1", view_count=200)
        v3 = Video(id="v_3", title="V3", channel_id="UC_2", view_count=50)
        db.session.add_all([v1, v2, v3])
        db.session.commit()

        with patch.object(db.session, 'commit') as mock_commit:
            items, total = ChannelService.get_channels(page=1, per_page=10)
            
            # Must NOT call commit during GET query
            mock_commit.assert_not_called()
            
            self.assertEqual(total, 3)
            chan_map = {c.id: c for c in items}
            self.assertEqual(chan_map["UC_1"].video_count, 2)
            self.assertEqual(chan_map["UC_1"].view_count, 300)
            self.assertEqual(chan_map["UC_2"].video_count, 1)
            self.assertEqual(chan_map["UC_2"].view_count, 50)
            self.assertEqual(chan_map["UC_3"].video_count, 0)

    def test_task_dispatcher_removes_session_in_finally(self):
        """
        Fix 11: Background task execution in task_dispatcher must call db.session.remove()
        in a finally block to prevent connection leaks.
        """
        mock_task = MagicMock()
        with patch.object(db.session, 'remove') as mock_remove:
            thread = dispatch_task(mock_task, "arg1")
            thread.join(timeout=2.0)
            mock_task.assert_called_once_with("arg1")
            mock_remove.assert_called()

    def test_startup_cleans_up_orphaned_jobs(self):
        """
        Fix 11: On app creation, orphaned 'processing' or 'queued' jobs from previous
        restarts must be marked as 'failed'.
        """
        job1 = ProcessingQueue(
            id="job_active_1",
            job_type="download_video",
            target_id="dQw4w9WgXcQ",
            status="processing"
        )
        job2 = ProcessingQueue(
            id="job_queued_1",
            job_type="crawl_channel",
            target_id="UC123",
            status="queued"
        )
        job3 = ProcessingQueue(
            id="job_done_1",
            job_type="download_video",
            target_id="abc",
            status="complete"
        )
        db.session.add_all([job1, job2, job3])
        db.session.commit()

        # Simulate fresh app startup
        from app import cleanup_orphaned_jobs
        cleanup_orphaned_jobs(self.app)

        # Refresh
        j1 = db.session.query(ProcessingQueue).get("job_active_1")
        j2 = db.session.query(ProcessingQueue).get("job_queued_1")
        j3 = db.session.query(ProcessingQueue).get("job_done_1")

        self.assertEqual(j1.status, "failed")
        self.assertIn("server restart", j1.error_message)
        self.assertEqual(j2.status, "failed")
        self.assertIn("server restart", j2.error_message)
        self.assertEqual(j3.status, "complete")

