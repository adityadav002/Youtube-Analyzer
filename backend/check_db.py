import os
import sys
from datetime import datetime

# Add the current directory to python path
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

from app import create_app, db
from app.models.channel import Channel
from app.models.video import Video

app = create_app('development')
with app.app_context():
    channels = Channel.query.all()
    print(f"Total channels in DB: {len(channels)}")
    for c in channels:
        # Count actual videos in db for this channel
        actual_video_count = Video.query.filter_by(channel_id=c.id).count()
        print(f"Channel ID: {c.id}")
        print(f"  Display Name: {c.display_name}")
        print(f"  Handle: {c.handle}")
        print(f"  Subscriber Count: {c.subscriber_count}")
        print(f"  Video Count (DB field): {c.video_count}")
        print(f"  Actual Video Count (linked rows): {actual_video_count}")
        print(f"  View Count (DB field): {c.view_count}")
        print(f"  Join Date: {c.join_date}")
        print("-" * 40)
