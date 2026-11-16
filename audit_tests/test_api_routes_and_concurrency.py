import sys
import os
import json
import unittest
import threading
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.abspath('backend'))

from app import create_app, db
from app.models.channel import Channel
from app.models.video import Video

class TestAPIRoutesAndConcurrency(unittest.TestCase):
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

    def test_health_check_endpoint(self):
        res = self.client.get('/api/health')
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data.get('status'), 'ok')
        self.assertEqual(data.get('db'), 'ok')
        print(f"[REPRODUCED] GET /api/health -> {data}")

    def test_dashboard_stats_endpoint(self):
        res = self.client.get('/api/dashboard/stats')
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertIn('stats', data)
        self.assertIn('recent_activity', data)
        self.assertEqual(data['stats']['total_channels'], 0)
        self.assertEqual(data['stats']['total_videos'], 0)
        print(f"[REPRODUCED] GET /api/dashboard/stats -> {data['stats']}")

    def test_video_import_validation(self):
        # 1. Missing URL/ID
        res1 = self.client.post('/api/videos', json={})
        self.assertEqual(res1.status_code, 400)
        self.assertIn('error', res1.get_json())

        # 2. Invalid identifier (channel URL passed to video import)
        res2 = self.client.post('/api/videos', json={'url': 'https://www.youtube.com/channel/UC_x5XG1OV2P6uZZ5FSM9Ttw'})
        self.assertEqual(res2.status_code, 400)
        self.assertEqual(res2.get_json().get('error'), 'Invalid video identifier')
        print(f"[REPRODUCED] POST /api/videos with channel URL -> 400 {res2.get_json()}")

    def test_channel_create_validation(self):
        # Missing url field
        res = self.client.post('/api/channels', json={})
        self.assertEqual(res.status_code, 422)
        print(f"[REPRODUCED] POST /api/channels empty payload -> 422 {res.get_json()}")

    def test_download_subtitles_unsupported(self):
        res = self.client.post('/api/downloads', json={
            'url': 'https://www.youtube.com/watch?v=dQw4w9WgXcQ',
            'download_type': 'subtitle'
        })
        self.assertEqual(res.status_code, 400)
        data = res.get_json()
        self.assertFalse(data.get('success'))
        self.assertIn('Subtitle downloads are no longer supported', data.get('message', ''))
        print(f"[REPRODUCED] POST /api/downloads with subtitle -> 400 {data}")

    def test_concurrency_read_write(self):
        """
        Concurrency Audit: 10 parallel requests querying and creating stubs.
        Verify if thread safety or SQLite/DB locking occurs.
        """
        # Prepopulate 2 channels and 10 videos
        channel = Channel(id='UC_concurrent_test', display_name='Concurrency Channel')
        db.session.add(channel)
        for i in range(10):
            v = Video(
                id=f'conc_vid_{i:02d}',
                channel_id=channel.id,
                title=f'Concurrent Video {i}',
                view_count=100 * i
            )
            db.session.add(v)
        db.session.commit()

        channel_id = 'UC_concurrent_test'
        results = []
        errors = []

        def worker(req_id):
            try:
                # Alternate between dashboard, videos list, and channels list
                if req_id % 3 == 0:
                    r = self.client.get('/api/dashboard/stats')
                elif req_id % 3 == 1:
                    r = self.client.get('/api/videos?per_page=10')
                else:
                    r = self.client.get(f'/api/channels/{channel_id}')
                return r.status_code
            except Exception as e:
                return str(e)

        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(worker, i) for i in range(20)]
            for f in futures:
                res = f.result()
                if res == 200:
                    results.append(res)
                else:
                    errors.append(res)

        print(f"[REPRODUCED] Concurrency: 20 parallel requests -> {len(results)} succeeded, {len(errors)} errors")
        self.assertEqual(len(results), 20)
        self.assertEqual(len(errors), 0)

    def test_side_effect_commit_in_get_channel(self):
        """
        REPRODUCTION: Verifies that GET /api/channels/<id> mutates the database
        via db.session.commit() even on read-only GET requests.
        """
        channel = Channel(id='UC_reconcile_test', display_name='Reconcile Channel', video_count=0)
        db.session.add(channel)
        v = Video(id='rec_vid_01', channel_id=channel.id, title='Vid 1', view_count=500)
        db.session.add(v)
        db.session.commit()

        # Before GET: video_count in DB is 0
        self.assertEqual(channel.video_count, 0)

        # Call GET endpoint
        res = self.client.get(f'/api/channels/{channel.id}')
        self.assertEqual(res.status_code, 200)

        # After GET: verify database was mutated by the GET request
        db.session.expire_all()
        reloaded = db.session.query(Channel).get(channel.id)
        print(f"[REPRODUCED] GET /api/channels/<id> mutated video_count from 0 to {reloaded.video_count}")
        self.assertEqual(reloaded.video_count, 1)

if __name__ == '__main__':
    unittest.main()
