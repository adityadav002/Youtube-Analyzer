#!/usr/bin/env bash
set -o errexit

# Add custom FFmpeg path if available
if [ -d "/opt/render/project/src/ffmpeg" ]; then
  export PATH="/opt/render/project/src/ffmpeg:$PATH"
fi

# Run database migrations
echo "Running database migrations..."
flask db upgrade

# Start Gunicorn WSGI server
echo "Starting Gunicorn on port $PORT..."
exec gunicorn --timeout 90 --workers 1 --threads 4 --bind 0.0.0.0:${PORT:-5000} wsgi:app
