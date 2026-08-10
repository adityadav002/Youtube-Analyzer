import os
import sys

# Add custom FFmpeg path to PATH if present (e.g. for Render deployments)
ffmpeg_render_path = "/opt/render/project/src/ffmpeg"
if os.path.exists(ffmpeg_render_path):
    os.environ['PATH'] = ffmpeg_render_path + os.pathsep + os.environ['PATH']

from app import create_app

config_name = os.environ.get('FLASK_ENV', 'development')
app = create_app(config_name)


