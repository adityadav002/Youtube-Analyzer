import sys
import os
import json
import unittest

sys.path.insert(0, os.path.abspath('backend'))

class TestSentimentAndAIPipeline(unittest.TestCase):
    def setUp(self):
        self.fixtures_dir = os.path.join(os.path.dirname(__file__), 'fixtures')

    def test_sentiment_library_installed_or_imported(self):
        """
        Stage 3 Audit: Check whether any sentiment analysis or NLP libraries
        are installed, imported, or referenced in requirements.txt or backend code.
        """
        requirements_path = os.path.abspath('backend/requirements.txt')
        with open(requirements_path, 'r', encoding='utf-8') as f:
            reqs = f.read().lower()

        nlp_libraries = ['vader', 'textblob', 'nltk', 'spacy', 'transformers', 'torch', 'scikit-learn']
        found_in_reqs = [lib for lib in nlp_libraries if lib in reqs]
        
        print("\n--- [AUDIT FINDING] NLP & Sentiment Libraries in requirements.txt ---")
        print(f"Searched: {nlp_libraries}")
        print(f"Found in requirements.txt: {found_in_reqs}")
        print("--------------------------------------------------------------------\n")
        
        self.assertEqual(len(found_in_reqs), 0, "No NLP or sentiment libraries exist in requirements.txt")

    def test_comment_extraction_and_storage_pipeline(self):
        """
        Stage 2 & 3 Audit: Check whether comments are extracted from YouTube Data API
        or stored into the comments table.
        """
        from app.models.comment import Comment
        from app.services.youtube_api_service import YouTubeApiService
        
        api = YouTubeApiService()
        # Verify if api has any method for comments
        has_comment_method = hasattr(api, 'fetch_comments') or hasattr(api, 'get_comments')
        print(f"[AUDIT FINDING] YouTubeApiService has comment extraction method: {has_comment_method}")
        self.assertFalse(has_comment_method, "YouTubeApiService has NO method to fetch comments from YouTube Data API (commentThreads.list)")

    def test_ai_llm_service_presence(self):
        """
        Stage 4 Audit: Verify AI / LLM integration status.
        Check if any LLM API provider (OpenAI, Gemini, Anthropic) or AIAnalysisService exists.
        """
        from app.models.ai import AIAnalysis
        
        services_dir = os.path.abspath('backend/app/services')
        services = os.listdir(services_dir)
        has_ai_service = any('ai' in s.lower() for s in services)
        
        print(f"[AUDIT FINDING] AI Analysis Service in app/services: {has_ai_service} (Available: {services})")
        self.assertFalse(has_ai_service, "AIAnalysisService is missing from app/services")

if __name__ == '__main__':
    unittest.main()

