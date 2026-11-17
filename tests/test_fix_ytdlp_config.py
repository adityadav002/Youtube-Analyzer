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

    def test_safe_ytdlp_save_cookies_ignores_oserror(self):
        from yt_dlp import YoutubeDL
        safe_ydl = SafeYoutubeDL({'cookiefile': '/etc/secrets/cookies.txt'})
        with patch.object(YoutubeDL, 'save_cookies') as mock_save:
            mock_save.side_effect = OSError(30, "Read-only file system: '/etc/secrets/cookies.txt'")
            # Should not raise an exception
            safe_ydl.save_cookies()
            mock_save.assert_called_once()

    def test_configure_ytdlp_copies_cookie_file_to_temp(self):
        import tempfile
        with tempfile.NamedTemporaryFile(delete=False) as tf:
            tf.write(b"# Netscape HTTP Cookie File\n")
            test_cookie_path = tf.name

        try:
            with patch.dict(os.environ, {'YTDLP_COOKIES_FILE': test_cookie_path}):
                opts = configure_ytdlp_options({})
                self.assertIn('cookiefile', opts)
                self.assertNotEqual(opts['cookiefile'], test_cookie_path)
                self.assertTrue(os.path.exists(opts['cookiefile']))
        finally:
            if os.path.exists(test_cookie_path):
                os.remove(test_cookie_path)

    def test_configure_ytdlp_options_with_cookies_uses_authenticated_clients(self):
        opts = configure_ytdlp_options({'cookiefile': '/tmp/cookies.txt'})
        clients = opts['extractor_args']['youtube']['player_client']
        self.assertIn('default', clients)
        self.assertNotIn('android', clients)

    def test_safe_ytdlp_retries_on_stale_cookiefile(self):
        from yt_dlp.utils import DownloadError
        params = {'cookiefile': '/tmp/test_stale_cookies.txt'}
        safe_ydl = SafeYoutubeDL(params)

        with patch('app.extraction.ytdlp_client.YoutubeDL.extract_info') as mock_super_extract:
            mock_super_extract.side_effect = [
                DownloadError("ERROR: [youtube] 12345: Failed to extract any player response"),
                {'id': 'test_video_2', 'title': 'Retry Success'}
            ]
            res = safe_ydl.extract_info('https://youtube.com/watch?v=12345678901', download=False)
            self.assertEqual(res['id'], 'test_video_2')
            self.assertEqual(mock_super_extract.call_count, 2)


if __name__ == '__main__':
    unittest.main()
