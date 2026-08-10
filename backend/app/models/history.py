from app import db
from sqlalchemy import Column, String, Integer, Index
from .base import TimestampMixin

class DownloadHistory(TimestampMixin, db.Model):
    __tablename__ = 'download_history'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    video_id = Column(String(20), db.ForeignKey('videos.id', ondelete='CASCADE'), nullable=False)
    download_type = Column(String(20), nullable=False)  # video, audio, subtitle, thumbnail
    quality = Column(String(50), nullable=False)
    file_path = Column(String(500), nullable=True)
    file_size_bytes = Column(db.BigInteger, nullable=True)
    status = Column(String(20), default='pending')  # pending, downloading, complete, failed, cancelled
    error_message = Column(db.Text, nullable=True)
    progress_percent = Column(Integer, default=0)

    __table_args__ = (
        Index('idx_downloads_video_type', 'video_id', 'download_type', 'status'),
    )

class SearchHistory(TimestampMixin, db.Model):
    __tablename__ = 'search_history'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    query = Column(String(255), nullable=False)
    search_type = Column(String(20), nullable=False)
    result_count = Column(Integer, default=0)
    expires_at = Column(db.DateTime, nullable=False)
    results_json = Column(db.Text, nullable=True)

