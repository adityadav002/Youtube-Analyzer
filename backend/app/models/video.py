from app import db
from sqlalchemy import Column, String, Integer, Boolean, Float, Index
from .base import TimestampMixin

class Video(TimestampMixin, db.Model):
    __tablename__ = 'videos'
    
    id = Column(String(20), primary_key=True)
    channel_id = Column(String(50), db.ForeignKey('channels.id', ondelete='CASCADE'), nullable=False)
    title = Column(String(255), nullable=False)
    description = Column(db.Text, nullable=True)
    duration = Column(Integer, default=0)
    view_count = Column(db.BigInteger, default=0)
    like_count = Column(Integer, nullable=True)
    comment_count = Column(Integer, nullable=True)
    upload_date = Column(db.DateTime, nullable=True)
    is_short = Column(Boolean, default=False)
    is_live = Column(Boolean, default=False)
    live_status = Column(String(20), default='not_live')
    availability = Column(String(20), default='public')
    age_limit = Column(Integer, default=0)
    has_transcript = Column(Boolean, default=False)
    comments_disabled = Column(Boolean, default=False)
    thumbnail_url = Column(String(255), nullable=True)
    _tags = Column('tags', db.Text, nullable=True)
    _categories = Column('categories', db.Text, nullable=True)
    _formats = Column('formats', db.Text, nullable=True)
    _chapters = Column('chapters', db.Text, nullable=True)
    _heatmap = Column('heatmap', db.Text, nullable=True)
    
    transcripts = db.relationship('Transcript', backref='video', cascade='all, delete-orphan')
    comments = db.relationship('Comment', backref='video', cascade='all, delete-orphan')
    snapshots = db.relationship('VideoSnapshot', backref='video', cascade='all, delete-orphan')
    download_history = db.relationship('DownloadHistory', backref='video', cascade='all, delete-orphan')

    __table_args__ = (
        Index('idx_videos_channel_upload', 'channel_id', 'upload_date'),
        Index('idx_videos_channel_views', 'channel_id', 'view_count'),
        Index('idx_videos_channel_shorts', 'channel_id', 'is_short'),
        # FULLTEXT index is added via alembic for title and description
    )

    @property
    def tags(self):
        import json
        return json.loads(self._tags) if self._tags else []

    @tags.setter
    def tags(self, value):
        import json
        self._tags = json.dumps(value) if value else None

    @property
    def categories(self):
        import json
        return json.loads(self._categories) if self._categories else []

    @categories.setter
    def categories(self, value):
        import json
        self._categories = json.dumps(value) if value else None
        
    @property
    def formats(self):
        import json
        return json.loads(self._formats) if self._formats else []

    @formats.setter
    def formats(self, value):
        import json
        self._formats = json.dumps(value) if value else None

    @property
    def chapters(self):
        import json
        return json.loads(self._chapters) if self._chapters else []

    @chapters.setter
    def chapters(self, value):
        import json
        self._chapters = json.dumps(value) if value else None

    @property
    def heatmap(self):
        import json
        return json.loads(self._heatmap) if self._heatmap else []

    @heatmap.setter
    def heatmap(self, value):
        import json
        self._heatmap = json.dumps(value) if value else None
