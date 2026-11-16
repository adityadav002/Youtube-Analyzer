import os
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.abspath('backend'))

from app.extraction.ytdlp_client import configure_ytdlp_options, SafeYoutubeDL

class TestYtdlpConfigAndFallback(unittest.TestCase):
    def test_configure_ytdlp_options_defaults(self):
        ydl_opts = {}
        opts = configure_ytdlp_options(ydl_opts)
        
        # Player client should default to android (not ios)
        self.assertEqual(opts['extractor_args']['youtube']['player_client'], ['android'])
        
        # No PO token provider should be injected by default
        self.assertNotIn('youtubepot-bgutilhttp', opts.get('extractor_args', {}))
        
        # Browser cookies should not be automatically injected
        self.assertNotIn('cookiesfrombrowser', opts)

    def test_configure_ytdlp_options_replaces_ios(self):
        class MockSettings:
            ytdlp_proxy = None
            cookies_file_path = None
            ytdlp_player_client = 'ios'
            
        ydl_opts = {}
        opts = configure_ytdlp_options(ydl_opts, MockSettings())
        # 'ios' should be safely mapped to 'android'
        self.assertEqual(opts['extractor_args']['youtube']['player_client'], ['android'])

    def test_safe_ytdlp_catches_permission_error_and_retries(self):
        params = {'cookiesfrombrowser': ('chrome',)}
        safe_ydl = SafeYoutubeDL(params)
        
        # Simulate extract_info failing with PermissionError on cookies, then succeeding without cookies
        with patch('app.extraction.ytdlp_client.YoutubeDL.extract_info') as mock_super_extract:
            mock_super_extract.side_effect = [
                PermissionError("[Errno 13] Permission denied: 'Cookies'"),
                {'id': 'test_video', 'title': 'Test'}
            ]
            res = safe_ydl.extract_info('https://youtube.com/watch?v=12345678901', download=False)
            self.assertEqual(res['id'], 'test_video')
            self.assertNotIn('cookiesfrombrowser', safe_ydl.params)

if __name__ == '__main__':
    unittest.main()
