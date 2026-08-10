from app import db
from sqlalchemy import Column, String, Integer, Boolean, Text
from .base import TimestampMixin

class Transcript(TimestampMixin, db.Model):
    __tablename__ = 'transcripts'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    video_id = Column(String(20), db.ForeignKey('videos.id', ondelete='CASCADE'), nullable=False)
    language_code = Column(String(10), nullable=False)
    is_generated = Column(Boolean, default=False)
    full_text = Column(Text, nullable=False)
    _segments = Column('segments', Text, nullable=False)

    @property
    def segments(self):
        import json
        return json.loads(self._segments) if self._segments else []

    @segments.setter
    def segments(self, value):
        import json
        self._segments = json.dumps(value) if value else None
