from app import db
from app.models.channel import Channel
from app.models.video import Video
from app.models.history import DownloadHistory
from app.models.queue import ProcessingQueue
from sqlalchemy import desc

class DashboardService:
    @staticmethod
    def get_dashboard_stats():
        # Aggregates
        total_channels = db.session.query(db.func.count(Channel.id)).scalar() or 0
        total_videos = db.session.query(db.func.count(Video.id)).scalar() or 0
        
        total_downloads = db.session.query(db.func.count(DownloadHistory.id))\
            .filter(DownloadHistory.status == 'complete').scalar() or 0
            
        total_download_bytes = db.session.query(db.func.sum(DownloadHistory.file_size_bytes))\
            .filter(DownloadHistory.status == 'complete').scalar() or 0
        total_download_bytes = int(total_download_bytes) if total_download_bytes else 0

        total_active_jobs = db.session.query(db.func.count(ProcessingQueue.id))\
            .filter(ProcessingQueue.status.in_(['queued', 'processing'])).scalar() or 0

        # Recent Activity
        recent_channels = db.session.query(Channel)\
            .order_by(desc(Channel.created_at))\
            .limit(5).all()
            
        recent_videos = db.session.query(Video)\
            .order_by(desc(Video.upload_date))\
            .limit(5).all()

        return {
            'stats': {
                'total_channels': total_channels,
                'total_videos': total_videos,
                'total_downloads': total_downloads,
                'total_storage_bytes': total_download_bytes,
                'active_jobs': total_active_jobs
            },
            'recent_activity': {
                'channels': [
                    {
                        'id': c.id,
                        'name': c.display_name,
                        'custom_url': c.handle,
                        'thumbnail_url': c.avatar_url,
                        'subscriber_count': c.subscriber_count,
                        'created_at': c.created_at.isoformat() if c.created_at else None
                    } for c in recent_channels
                ],
                'videos': [
                    {
                        'id': v.id,
                        'title': v.title,
                        'thumbnail_url': v.thumbnail_url,
                        'view_count': v.view_count,
                        'upload_date': v.upload_date.isoformat() if v.upload_date else None,
                        'channel_id': v.channel_id
                    } for v in recent_videos
                ]
            }
        }
