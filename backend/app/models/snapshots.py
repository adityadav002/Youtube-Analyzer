from app import db
from sqlalchemy import Column, String, Integer, Date, Index
from .base import TimestampMixin

class ChannelSnapshot(TimestampMixin, db.Model):
    __tablename__ = 'channel_snapshots'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    channel_id = Column(String(50), db.ForeignKey('channels.id', ondelete='CASCADE'), nullable=False)
    snapshot_date = Column(Date, nullable=False)
    subscriber_count = Column(Integer, default=0)
    video_count = Column(Integer, default=0)
    view_count = Column(db.BigInteger, default=0)

    __table_args__ = (
        Index('idx_channel_snapshots_range', 'channel_id', 'snapshot_date'),
    )

class VideoSnapshot(TimestampMixin, db.Model):
    __tablename__ = 'video_snapshots'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    video_id = Column(String(20), db.ForeignKey('videos.id', ondelete='CASCADE'), nullable=False)
    snapshot_date = Column(Date, nullable=False)
    view_count = Column(db.BigInteger, default=0)
    like_count = Column(Integer, default=0)
    comment_count = Column(Integer, default=0)

    __table_args__ = (
        Index('idx_video_snapshots_range', 'video_id', 'snapshot_date'),
    )
