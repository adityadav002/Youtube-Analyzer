from app import db
from sqlalchemy import Column, String, Integer, Boolean, Text
from .base import TimestampMixin

class Comment(TimestampMixin, db.Model):
    __tablename__ = 'comments'
    
    id = Column(String(100), primary_key=True)
    video_id = Column(String(20), db.ForeignKey('videos.id', ondelete='CASCADE'), nullable=False)
    parent_id = Column(String(100), db.ForeignKey('comments.id', ondelete='CASCADE'), nullable=True)
    author_name = Column(String(255), nullable=False)
    author_id = Column(String(50), nullable=True)
    author_thumbnail = Column(String(255), nullable=True)
    text = Column(Text, nullable=False)
    like_count = Column(Integer, default=0)
    is_favorited = Column(Boolean, default=False)
    is_pinned = Column(Boolean, default=False)
    author_is_creator = Column(Boolean, default=False)
    published_at = Column(db.DateTime, nullable=False)
    
    replies = db.relationship('Comment', backref=db.backref('parent', remote_side=[id]), cascade='all, delete-orphan')
