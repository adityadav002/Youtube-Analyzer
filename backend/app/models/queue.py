from app import db
from sqlalchemy import Column, String, Integer, Text, Index
from .base import TimestampMixin

class ProcessingQueue(TimestampMixin, db.Model):
    __tablename__ = 'processing_queue'
    
    id = Column(String(50), primary_key=True)  # UUID
    job_type = Column(String(50), nullable=False)
    target_id = Column(String(255), nullable=False)
    status = Column(String(20), default='queued')  # queued, processing, complete, failed, cancelled
    priority = Column(Integer, default=1)
    error_message = Column(Text, nullable=True)
    retry_count = Column(Integer, default=0)
    _payload = Column('payload', Text, nullable=True)

    __table_args__ = (
        Index('idx_queue_status_priority', 'status', 'priority', 'created_at'),
    )

    @property
    def payload(self):
        import json
        return json.loads(self._payload) if self._payload else {}

    @payload.setter
    def payload(self, value):
        import json
        self._payload = json.dumps(value) if value else None
