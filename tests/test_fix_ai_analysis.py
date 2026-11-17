import os
import sys
import json
import unittest
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.abspath('backend'))

from app import create_app, db
from app.models.video import Video
from app.models.ai import AIAnalysis
from app.models.transcript import Transcript
from app.services.ai_service import AIAnalysisService, AIAnalysisError

class TestAIAnalysisPipeline(unittest.TestCase):
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

    def test_ai_status_endpoint(self):
        with patch.dict(os.environ, {'GEMINI_API_KEY': 'test_key', 'AI_PROVIDER': 'gemini'}):
            res = self.client.get('/api/ai/status')
            self.assertEqual(res.status_code, 200)
            data = res.get_json()
            self.assertTrue(data['enabled'])
            self.assertEqual(data['provider'], 'gemini')

    def test_ai_analyze_fails_without_api_key(self):
        v = Video(id="vid_ai_01", title="AI Test", channel_id="UC123")
        db.session.add(v)
        db.session.commit()

        with patch.dict(os.environ, {}, clear=True):
            res = self.client.post('/api/ai/analyze/vid_ai_01')
            self.assertEqual(res.status_code, 503)
            self.assertIn("key", res.get_json().get('message', '').lower())

    def test_ai_analyze_and_store_pipeline(self):
        v = Video(id="vid_ai_02", title="Machine Learning 101", channel_id="UC123", description="A great tutorial")
        db.session.add(v)
        
        t = Transcript(
            video_id="vid_ai_02",
            language_code="en",
            full_text="Machine learning is fascinating and empowers modern applications."
        )
        t.segments = [{'start': 0.0, 'duration': 5.0, 'text': 'Machine learning is fascinating'}]
        db.session.add(t)
        db.session.commit()

        mock_gemini_payload = {
            "candidates": [
                {
                    "content": {
                        "parts": [
                            {
                                "text": json.dumps({
                                    "summary": "This video covers core principles of machine learning.",
                                    "topics": [
                                        {"topic": "Machine Learning", "description": "Overview of models and applications"}
                                    ],
                                    "key_takeaways": [
                                        "Foundations of algorithms",
                                        "Modern AI landscape"
                                    ],
                                    "sentiment": {
                                        "overall": "positive",
                                        "score": 0.9,
                                        "summary": "Audience reception is overwhelmingly supportive.",
                                        "positive_pct": 85,
                                        "neutral_pct": 10,
                                        "negative_pct": 5
                                    }
                                })
                            }
                        ]
                    }
                }
            ]
        }

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = mock_gemini_payload

        with patch.dict(os.environ, {'GEMINI_API_KEY': 'test_gemini_key'}):
            with patch('requests.post', return_value=mock_resp):
                res = self.client.post('/api/ai/analyze/vid_ai_02')
                self.assertEqual(res.status_code, 200)
                data = res.get_json()
                self.assertEqual(data['video_id'], 'vid_ai_02')
                self.assertIn('summary', data['result'])
                self.assertEqual(data['result']['sentiment']['overall'], 'positive')

                # Verify database record
                db_record = db.session.query(AIAnalysis).filter(AIAnalysis.video_id == 'vid_ai_02').first()
                self.assertIsNotNone(db_record)
                self.assertEqual(db_record.result['sentiment']['score'], 0.9)

                # Verify GET endpoint retrieves stored analysis
                get_res = self.client.get('/api/ai/analysis/vid_ai_02')
                self.assertEqual(get_res.status_code, 200)
                get_data = get_res.get_json()
                self.assertEqual(get_data['result']['summary'], "This video covers core principles of machine learning.")

    def test_ai_analyze_cascades_on_404_model_not_found(self):
        v = Video(id="vid_ai_03", title="Fallback Test", channel_id="UC123")
        db.session.add(v)
        db.session.commit()

        # Reset cached model
        AIAnalysisService._cached_model = None

        # Simulate first model returning 404, second model succeeding
        resp_404 = MagicMock()
        resp_404.status_code = 404
        resp_404.json.return_value = {
            'error': {'message': 'models/gemini-1.5-flash is not found for API version v1beta'}
        }

        resp_200 = MagicMock()
        resp_200.status_code = 200
        resp_200.json.return_value = {
            "candidates": [
                {
                    "content": {
                        "parts": [
                            {"text": json.dumps({"summary": "Fallback worked!", "topics": [], "key_takeaways": [], "sentiment": {"overall": "neutral"}})}
                        ]
                    }
                }
            ]
        }

        with patch.dict(os.environ, {'GEMINI_API_KEY': 'test_gemini_key'}):
            with patch('requests.post', side_effect=[resp_404, resp_200]) as mock_post:
                res = self.client.post('/api/ai/analyze/vid_ai_03')
                self.assertEqual(res.status_code, 200)
                data = res.get_json()
                self.assertEqual(data['result']['summary'], "Fallback worked!")
                self.assertGreaterEqual(mock_post.call_count, 2)

    def test_ai_parse_markdown_json_response(self):
        # Verify markdown fences (```json ... ```) like Gemma returns do not crash the parser
        markdown_text = "```json\n{\n  \"summary\": \"Parsed from markdown code fences\",\n  \"topics\": [],\n  \"key_takeaways\": [],\n  \"sentiment\": {\"overall\": \"positive\"}\n}\n```"
        payload = {
            "candidates": [
                {
                    "content": {
                        "parts": [{"text": markdown_text}]
                    }
                }
            ]
        }
        parsed = AIAnalysisService._parse_gemini_json_response(payload, "test_vid")
        self.assertEqual(parsed['summary'], "Parsed from markdown code fences")

    def test_ai_parse_prose_and_multiple_parts(self):
        # Verify text with leading thought/explanation and multiple parts extracts the JSON object correctly
        payload = {
            "candidates": [
                {
                    "content": {
                        "parts": [
                            {"text": "Here is the comprehensive analysis you requested:\n\n```json\n"},
                            {"text": "{\"summary\": \"Multi-part JSON extracted successfully\", \"topics\": [], \"key_takeaways\": [], \"sentiment\": {\"overall\": \"neutral\"}}"},
                            {"text": "\n```\nHope this is useful!"}
                        ]
                    }
                }
            ]
        }
        parsed = AIAnalysisService._parse_gemini_json_response(payload, "test_vid")
        self.assertEqual(parsed['summary'], "Multi-part JSON extracted successfully")

    def test_ai_analyze_cascades_on_timeout(self):
        import requests
        v = Video(id="vid_ai_timeout", title="Timeout Test", channel_id="UC123")
        db.session.add(v)
        db.session.commit()

        AIAnalysisService._cached_model = None

        timeout_err = requests.exceptions.Timeout("Read timed out")
        resp_200 = MagicMock()
        resp_200.status_code = 200
        resp_200.json.return_value = {
            "candidates": [
                {
                    "content": {
                        "parts": [
                            {"text": json.dumps({"summary": "Worked after timeout!", "topics": [], "key_takeaways": [], "sentiment": {"overall": "neutral"}})}
                        ]
                    }
                }
            ]
        }

        with patch.dict(os.environ, {'GEMINI_API_KEY': 'test_gemini_key'}):
            with patch('requests.post', side_effect=[timeout_err, resp_200]) as mock_post:
                res = self.client.post('/api/ai/analyze/vid_ai_timeout')
                self.assertEqual(res.status_code, 200)
                data = res.get_json()
                self.assertEqual(data['result']['summary'], "Worked after timeout!")
                self.assertGreaterEqual(mock_post.call_count, 2)



