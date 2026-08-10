import sys
import os

# Add the current directory to python path
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

from app import create_app, db
from app.models.channel import Channel
from app.models.video import Video

def reconcile_channels():
    app = create_app('development')
    with app.app_context():
        print("Fetching all channels from database...")
        channels = Channel.query.all()
        print(f"Total channels to reconcile: {len(channels)}")
        
        for channel in channels:
            print(f"Reconciling channel: {channel.display_name} ({channel.id})...")
            
            # Fetch raw metadata from YouTube
            from app.extraction.ytdlp_client import YtdlpClient
            client = YtdlpClient()
            yt_data = {}
            try:
                print("  Fetching live metadata from YouTube (true video count, view count, and join date)...")
                yt_data = client.extract_channel_metadata(f"https://www.youtube.com/channel/{channel.id}")
            except Exception as e:
                print(f"  Warning: failed to fetch YouTube metadata: {e}")
                
            db_video_count = db.session.query(db.func.count(Video.id)).filter(Video.channel_id == channel.id).scalar() or 0
            db_view_count = db.session.query(db.func.sum(Video.view_count)).filter(Video.channel_id == channel.id).scalar() or 0
            db_join_date = db.session.query(db.func.min(Video.upload_date)).filter(Video.channel_id == channel.id).scalar()
            
            yt_video_count = yt_data.get('video_count') or 0
            yt_view_count = yt_data.get('view_count') or 0
            yt_join_date = yt_data.get('join_date')
            
            # Choose best values: YouTube-sourced > Database-sourced
            target_video_count = yt_video_count if yt_video_count > 0 else db_video_count
            target_view_count = yt_view_count if yt_view_count > 0 else db_view_count
            target_join_date = yt_join_date if yt_join_date else db_join_date
            
            print(f"  Existing stats in DB field:    video_count={channel.video_count}, view_count={channel.view_count}, join_date={channel.join_date}")
            print(f"  Live YouTube stats:            video_count={yt_video_count}, view_count={yt_view_count}, join_date={yt_join_date}")
            print(f"  Calculated from video records: video_count={db_video_count}, view_count={db_view_count}, join_date={db_join_date}")
            print(f"  Target resolved stats:         video_count={target_video_count}, view_count={target_view_count}, join_date={target_join_date}")
            
            updated = False
            if channel.video_count != target_video_count:
                channel.video_count = target_video_count
                updated = True
            if channel.view_count != target_view_count:
                channel.view_count = target_view_count
                updated = True
            if channel.join_date != target_join_date:
                channel.join_date = target_join_date
                updated = True
                
            # Update other metadata fields if they are missing and we have live data
            if yt_data:
                if not channel.avatar_url and yt_data.get('avatar_url'):
                    channel.avatar_url = yt_data.get('avatar_url')
                    updated = True
                if not channel.banner_url and yt_data.get('banner_url'):
                    channel.banner_url = yt_data.get('banner_url')
                    updated = True
                if not channel.description and yt_data.get('description'):
                    channel.description = yt_data.get('description')
                    updated = True
                if not channel.handle and yt_data.get('handle'):
                    channel.handle = yt_data.get('handle')
                    updated = True
                if (not channel.subscriber_count or channel.subscriber_count == 0) and yt_data.get('subscriber_count'):
                    channel.subscriber_count = yt_data.get('subscriber_count')
                    updated = True
                
            if updated:
                db.session.commit()
                print("  -> Channel statistics updated in database.")
            else:
                print("  -> Channel statistics are already up-to-date.")
            print("-" * 50)
                
        print("Reconciliation complete!")

if __name__ == '__main__':
    reconcile_channels()
