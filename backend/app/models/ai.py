from app import db
from sqlalchemy import Column, String, Integer, Text
from .base import TimestampMixin

class AIAnalysis(TimestampMixin, db.Model):
    __tablename__ = 'ai_analysis'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    video_id = Column(String(20), db.ForeignKey('videos.id', ondelete='CASCADE'), nullable=False)
    analysis_type = Column(String(50), nullable=False)
    prompt_used = Column(Text, nullable=True)
    _result = Column('result', Text, nullable=False)

    @property
    def result(self):
        import json
        return json.loads(self._result) if self._result else {}

    @result.setter
    def result(self, value):
        import json
        self._result = json.dumps(value) if value else None
