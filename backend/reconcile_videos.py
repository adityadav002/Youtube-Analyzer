import sys
import os
import json
sys.path.append(os.path.abspath('.'))

from app import create_app, db
from app.models.video import Video
from app.repositories.video_repository import VideoRepository

def reconcile_database():
    app = create_app('development')
    with app.app_context():
        print("Fetching all videos from database...")
        videos = Video.query.all()
        print(f"Total videos to check: {len(videos)}")
        
        updated_count = 0
        live_count = 0
        short_count = 0
        normal_count = 0
        
        for video in videos:
            orig_is_short = video.is_short
            orig_is_live = video.is_live
            orig_live_status = video.live_status
            
            # --- Resolve Classification ---
            
            # 1. Determine if LIVE
            is_live_signal = (
                orig_is_live or 
                orig_live_status in ['is_live', 'was_live', 'post_live']
            )
            
            # 2. Determine if SHORT
            is_short_signal = False
            if not is_live_signal:
                # Check tags and categories
                categories_list = []
                if video._categories:
                    try:
                        categories_list = json.loads(video._categories)
                    except Exception:
                        pass
                
                has_shorts_tag = False
                tags_list = []
                if video._tags:
                    try:
                        tags_list = json.loads(video._tags)
                    except Exception:
                        pass
                
                # Check for shorts indicator in title, description, categories, tags
                title_lower = (video.title or "").lower()
                desc_lower = (video.description or "").lower()
                
                has_shorts_hashtag = (
                    "#shorts" in title_lower or 
                    "#shorts" in desc_lower or 
                    "shorts" in [t.lower() for t in tags_list]
                )
                
                has_shorts_category = "Shorts" in categories_list
                
                # Fallback on duration (between 1 and 59 seconds)
                has_short_duration = video.duration and 0 < video.duration < 60
                
                is_short_signal = (
                    orig_is_short or
                    has_shorts_hashtag or
                    has_shorts_category or
                    has_short_duration
                )
            
            # Use VideoRepository.resolve_classification on the collected signals
            resolved_short, resolved_live, resolved_status = VideoRepository.resolve_classification(
                is_short=is_short_signal,
                is_live=is_live_signal,
                live_status=orig_live_status,
                duration=video.duration
            )
            
            # Check if flags or status changed
            if (
                orig_is_short != resolved_short or 
                orig_is_live != resolved_live or 
                orig_live_status != resolved_status
            ):
                video.is_short = resolved_short
                video.is_live = resolved_live
                video.live_status = resolved_status
                
                orig_class = "LIVE" if orig_is_live else ("SHORT" if orig_is_short else "NORMAL")
                new_class = "LIVE" if resolved_live else ("SHORT" if resolved_short else "NORMAL")
                
                print(
                    f"Reclassified Video {video.id} ({video.title[:40]}):\n"
                    f"  Before: {orig_class} (is_short={orig_is_short}, is_live={orig_is_live}, live_status='{orig_live_status}', duration={video.duration})\n"
                    f"  After : {new_class} (is_short={resolved_short}, is_live={resolved_live}, live_status='{resolved_status}')"
                )
                updated_count += 1
                
            if resolved_live:
                live_count += 1
            elif resolved_short:
                short_count += 1
            else:
                normal_count += 1
                
        if updated_count > 0:
            print(f"Commiting updates for {updated_count} videos...")
            db.session.commit()
            print("Database updates committed successfully.")
        else:
            print("No reconciliation changes were required.")
            
        print("\nFinal Classification Summary:")
        print(f"  Live Streams: {live_count}")
        print(f"  Shorts:       {short_count}")
        print(f"  Normal:       {normal_count}")
        print(f"  Total:        {len(videos)}")

if __name__ == '__main__':
    reconcile_database()
