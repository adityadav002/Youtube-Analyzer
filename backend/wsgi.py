import os
import sys

# Add custom FFmpeg path to PATH if present (e.g. for Render deployments)
ffmpeg_render_path = "/opt/render/project/src/ffmpeg"
if os.path.exists(ffmpeg_render_path):
    os.environ['PATH'] = ffmpeg_render_path + os.pathsep + os.environ['PATH']

from app import create_app

config_name = os.environ.get('FLASK_ENV', 'development')
app = create_app(config_name)

if __name__ == '__main__':
    host = os.environ.get('FLASK_RUN_HOST', '0.0.0.0')
    port = int(os.environ.get('FLASK_RUN_PORT', 5000))
    print(f"Starting YouTube Analyzer development server on http://localhost:{port}")
    app.run(host=host, port=port, debug=True)



