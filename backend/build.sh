#!/usr/bin/env bash
# Exit on error
set -o errexit

# Install Python requirements
pip install -r requirements.txt

# Download and extract FFmpeg static binary if not present (optional fallback)
FFMPEG_DIR="/opt/render/project/src/ffmpeg"
if [ ! -d "$FFMPEG_DIR" ]; then
  echo "Downloading FFmpeg static build..."
  mkdir -p "$FFMPEG_DIR"
  cd "$FFMPEG_DIR"
  # Attempt static release download, continue gracefully if external host is unavailable
  (curl -f -L --connect-timeout 15 --max-time 120 https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-amd64-static.tar.xz | tar -xJ --strip-components=1 && chmod +x ffmpeg ffprobe && echo "FFmpeg installed successfully in $FFMPEG_DIR") || echo "Notice: Could not download static FFmpeg; continuing."
else
  echo "FFmpeg already exists, skipping download."
fi
