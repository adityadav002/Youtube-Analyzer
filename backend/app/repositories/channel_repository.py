from typing import List, Optional, Tuple
from app import db
from app.models.channel import Channel

class ChannelRepository:
    @staticmethod
    def get_by_id(channel_id: str) -> Optional[Channel]:
        return db.session.query(Channel).filter_by(id=channel_id).first()
        
    @staticmethod
    def get_all(page: int = 1, per_page: int = 20, sort_by: str = 'name') -> Tuple[List[Channel], int]:
        query = db.session.query(Channel)
        
        # Sort
        if sort_by == 'subscribers':
            query = query.order_by(Channel.subscriber_count.desc())
        elif sort_by == 'recent':
            query = query.order_by(Channel.last_crawled_at.desc())
        else:
            query = query.order_by(Channel.display_name.asc())
            
        total = query.count()
        items = query.offset((page - 1) * per_page).limit(per_page).all()
        return items, total

    @staticmethod
    def create(data: dict) -> Channel:
        channel = Channel(**data)
        db.session.add(channel)
        db.session.commit()
        return channel

    @staticmethod
    def update(channel: Channel, data: dict) -> Channel:
        for key, value in data.items():
            if hasattr(channel, key):
                setattr(channel, key, value)
        db.session.commit()
        return channel

    @staticmethod
    def delete(channel: Channel) -> None:
        db.session.delete(channel)
        db.session.commit()
