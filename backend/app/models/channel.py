from app import db
from sqlalchemy import Column, String, Integer, Boolean
from .base import TimestampMixin

class Channel(TimestampMixin, db.Model):
    __tablename__ = 'channels'
    
    id = Column(String(50), primary_key=True)  # UCxxxx
    handle = Column(String(100), nullable=True)
    display_name = Column(String(255), nullable=False)
    description = Column(db.Text, nullable=True)
    avatar_url = Column(String(255), nullable=True)
    banner_url = Column(String(255), nullable=True)
    subscriber_count = Column(Integer, default=0)
    video_count = Column(Integer, default=0)
    view_count = Column(db.BigInteger, default=0)
    is_verified = Column(Boolean, default=False)
    country = Column(String(2), nullable=True)
    join_date = Column(db.DateTime, nullable=True)
    rss_monitoring = Column(Boolean, default=False)
    last_crawled_at = Column(db.DateTime, nullable=True)
    _external_links = Column('external_links', db.Text, nullable=True)
    
    videos = db.relationship('Video', backref='channel', cascade='all, delete-orphan')
    playlists = db.relationship('Playlist', backref='channel_rel', cascade='all, delete-orphan')
    snapshots = db.relationship('ChannelSnapshot', backref='channel', cascade='all, delete-orphan')

    @property
    def external_links(self):
        import json
        return json.loads(self._external_links) if self._external_links else []

    @external_links.setter
    def external_links(self, value):
        import json
        self._external_links = json.dumps(value) if value else None
