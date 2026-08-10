from app import db
from sqlalchemy import Column, Integer, Boolean, String, Float
from .base import TimestampMixin

class UserSettings(TimestampMixin, db.Model):
    __tablename__ = 'user_settings'
    
    id = Column(Integer, primary_key=True)  # Only one row, id=1
    auto_extract_transcript = Column(Boolean, default=False)
    auto_extract_comments = Column(Boolean, default=False)
    auto_extract_thumbnail = Column(Boolean, default=True)
    max_comments_per_video = Column(Integer, default=500)
    default_video_quality = Column(String(20), default='best')
    default_audio_format = Column(String(20), default='mp3')
    default_audio_quality = Column(String(20), default='192k')
    max_concurrent_downloads = Column(Integer, default=2)
    ytdlp_player_client = Column(String(20), default='ios')
    ytdlp_rate_limit = Column(String(20), default='500K')
    ytdlp_proxy = Column(String(255), nullable=True)
    cookies_file_path = Column(String(500), nullable=True)
    rss_poll_interval_minutes = Column(Integer, default=60)
    snapshot_enabled = Column(Boolean, default=True)
