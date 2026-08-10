from app import db
from sqlalchemy import Column, String, Integer, Text, Boolean
from .base import TimestampMixin

class Playlist(TimestampMixin, db.Model):
    __tablename__ = 'playlists'
    
    id = Column(String(50), primary_key=True)
    channel_id = Column(String(50), db.ForeignKey('channels.id', ondelete='CASCADE'), nullable=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    video_count = Column(Integer, default=0)
    thumbnail_url = Column(String(255), nullable=True)
    last_crawled_at = Column(db.DateTime, nullable=True)
    
    playlist_videos = db.relationship('PlaylistVideo', backref='playlist', cascade='all, delete-orphan')

class PlaylistVideo(db.Model):
    __tablename__ = 'playlist_videos'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    playlist_id = Column(String(50), db.ForeignKey('playlists.id', ondelete='CASCADE'), nullable=False)
    video_id = Column(String(20), db.ForeignKey('videos.id', ondelete='CASCADE'), nullable=False)
    position = Column(Integer, nullable=False)
    added_at = Column(db.DateTime, nullable=True)
