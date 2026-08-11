import sys
import os

# Add the current directory to python path
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

from app import create_app, db
from app.models.video import Video
from app.services.youtube_api_service import YouTubeApiService

def enrich_existing():
    app = create_app('development')
    with app.app_context():
        # Fetch all videos in database
        videos = Video.query.all()
        print(f"Total videos in DB: {len(videos)}")
        
        client = YouTubeApiService()
        count = 0
        for video in videos:
            # If formats are empty, let's extract them
            if not video.formats or len(video.formats) == 0:
                print(f"Enriching formats & chapters for video: {video.title} ({video.id})...")
                url = f"https://youtube.com/watch?v={video.id}"
                try:
                    data = client.fetch_video_metadata(video.id)
                    
                    # Update formats and chapters
                    video.formats = data.get('formats', [])
                    video.chapters = data.get('chapters', [])
                    db.session.commit()
                    print(f"  -> Successfully enriched {len(video.formats)} formats and {len(video.chapters)} chapters.")
                    count += 1
                except Exception as e:
                    print(f"  -> Error: failed to extract metadata for {video.id}: {e}")
                    db.session.rollback()
                    
        print(f"Enrichment complete! Enriched {count} videos.")

if __name__ == '__main__':
    enrich_existing()
