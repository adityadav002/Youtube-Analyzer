import json
import os

fixtures_dir = os.path.join(os.path.dirname(__file__), 'fixtures')
os.makedirs(fixtures_dir, exist_ok=True)

# 1. Normal Video
video_normal = {
    "kind": "youtube#videoListResponse",
    "etag": "etag_normal_123",
    "items": [{
        "kind": "youtube#video",
        "etag": "etag_item_123",
        "id": "dQw4w9WgXcQ",
        "snippet": {
            "publishedAt": "2009-10-25T06:57:33Z",
            "channelId": "UCuAXFkgsw1L7xaCfnd5JJOw",
            "title": "Rick Astley - Never Gonna Give You Up (Official Music Video)",
            "description": "The official video for “Never Gonna Give You Up” by Rick Astley.\n\nChapters:\n00:00 - Introduction\n00:43 - Verse 1\n01:10 - Chorus\n02:20 - Bridge\n03:15 - Outro",
            "thumbnails": {
                "default": {"url": "https://i.ytimg.com/vi/dQw4w9WgXcQ/default.jpg", "width": 120, "height": 90},
                "medium": {"url": "https://i.ytimg.com/vi/dQw4w9WgXcQ/mqdefault.jpg", "width": 320, "height": 180},
                "high": {"url": "https://i.ytimg.com/vi/dQw4w9WgXcQ/hqdefault.jpg", "width": 480, "height": 360},
                "maxres": {"url": "https://i.ytimg.com/vi/dQw4w9WgXcQ/maxresdefault.jpg", "width": 1280, "height": 720}
            },
            "channelTitle": "Rick Astley",
            "tags": ["rick astley", "never gonna give you up", "nggyu", "pop"],
            "categoryId": "10",
            "liveBroadcastContent": "none"
        },
        "contentDetails": {
            "duration": "PT3M33S",
            "dimension": "2d",
            "definition": "hd",
            "caption": "true",
            "licensedContent": True
        },
        "status": {
            "uploadStatus": "processed",
            "privacyStatus": "public",
            "license": "youtube",
            "embeddable": True,
            "publicStatsViewable": True
        },
        "statistics": {
            "viewCount": "1500000000",
            "likeCount": "17000000",
            "favoriteCount": "0",
            "commentCount": "2500000"
        }
    }],
    "pageInfo": {"totalResults": 1, "resultsPerPage": 1}
}

# 2. Hidden Likes
video_hidden_likes = {
    "kind": "youtube#videoListResponse",
    "etag": "etag_hidden_likes",
    "items": [{
        "kind": "youtube#video",
        "id": "hidLikes001",
        "snippet": {
            "publishedAt": "2023-01-15T12:00:00Z",
            "channelId": "UCuAXFkgsw1L7xaCfnd5JJOw",
            "title": "Controversial Video with Hidden Likes",
            "description": "This video has like count hidden by the creator.",
            "thumbnails": {"high": {"url": "https://i.ytimg.com/vi/hidLikes001/hqdefault.jpg"}},
            "channelTitle": "Creator Channel",
            "tags": ["opinion"],
            "categoryId": "22",
            "liveBroadcastContent": "none"
        },
        "contentDetails": {"duration": "PT10M0S", "caption": "false"},
        "status": {"privacyStatus": "public", "publicStatsViewable": False},
        "statistics": {
            "viewCount": "250000",
            # likeCount is deliberately absent from API when hidden
            "commentCount": "1500"
        }
    }]
}

# 3. Comments Disabled
video_comments_disabled = {
    "kind": "youtube#videoListResponse",
    "etag": "etag_comments_disabled",
    "items": [{
        "kind": "youtube#video",
        "id": "noComments01",
        "snippet": {
            "publishedAt": "2022-05-10T08:30:00Z",
            "channelId": "UCuAXFkgsw1L7xaCfnd5JJOw",
            "title": "Kids Content Video with Comments Disabled",
            "description": "Comments are turned off for COPPA compliance.",
            "thumbnails": {"high": {"url": "https://i.ytimg.com/vi/noComments01/hqdefault.jpg"}},
            "channelTitle": "Kids Channel",
            "categoryId": "1",
            "liveBroadcastContent": "none"
        },
        "contentDetails": {"duration": "PT5M12S", "caption": "true"},
        "status": {"privacyStatus": "public"},
        "statistics": {
            "viewCount": "89000",
            "likeCount": "1200"
            # commentCount is absent when comments are disabled
        }
    }]
}

# 4. No Comments (commentCount = 0)
video_no_comments = {
    "kind": "youtube#videoListResponse",
    "items": [{
        "kind": "youtube#video",
        "id": "zeroComm001",
        "snippet": {
            "publishedAt": "2026-11-15T10:00:00Z",
            "channelId": "UCuAXFkgsw1L7xaCfnd5JJOw",
            "title": "Brand New Video - Zero Comments",
            "description": "Just uploaded 2 minutes ago.",
            "thumbnails": {"default": {"url": "https://i.ytimg.com/vi/zeroComm001/default.jpg"}},
            "channelTitle": "New Creator",
            "categoryId": "27"
        },
        "contentDetails": {"duration": "PT2M45S", "caption": "false"},
        "status": {"privacyStatus": "public"},
        "statistics": {
            "viewCount": "5",
            "likeCount": "1",
            "commentCount": "0"
        }
    }]
}

# 5. Deleted / Private / Empty Items
video_deleted_private = {
    "kind": "youtube#videoListResponse",
    "etag": "etag_empty",
    "items": [],
    "pageInfo": {"totalResults": 0, "resultsPerPage": 0}
}

# 6. Live Stream & Premiere
video_live_stream = {
    "kind": "youtube#videoListResponse",
    "items": [{
        "kind": "youtube#video",
        "id": "liveStream01",
        "snippet": {
            "publishedAt": "2026-11-16T08:00:00Z",
            "channelId": "UCLiveStreamChannel123",
            "title": "🔴 24/7 Lofi Chill Radio - Live Stream",
            "description": "Welcome to the live stream!",
            "thumbnails": {"high": {"url": "https://i.ytimg.com/vi/liveStream01/hqdefault.jpg"}},
            "channelTitle": "Lofi Radio",
            "categoryId": "10",
            "liveBroadcastContent": "live"
        },
        "contentDetails": {
            "duration": "P0D",  # Live duration is P0D
            "caption": "false"
        },
        "status": {"privacyStatus": "public"},
        "statistics": {
            "viewCount": "120340",
            "likeCount": "8900"
        },
        "liveStreamingDetails": {
            "actualStartTime": "2026-11-16T08:05:00Z",
            "concurrentViewers": "4520"
        }
    }]
}

# 7. Shorts
video_shorts = {
    "kind": "youtube#videoListResponse",
    "items": [{
        "kind": "youtube#video",
        "id": "shortsVid001",
        "snippet": {
            "publishedAt": "2026-08-01T14:20:00Z",
            "channelId": "UCShortsCreator12345678",
            "title": "Crazy Coding Hack! #shorts #viral",
            "description": "Watch until the end! #shorts",
            "thumbnails": {"high": {"url": "https://i.ytimg.com/vi/shortsVid001/hqdefault.jpg"}},
            "channelTitle": "Code Ninja",
            "tags": ["coding", "shorts", "python"],
            "categoryId": "28"
        },
        "contentDetails": {
            "duration": "PT42S",
            "caption": "true"
        },
        "status": {"privacyStatus": "public"},
        "statistics": {
            "viewCount": "450000",
            "likeCount": "32000",
            "commentCount": "512"
        }
    }]
}

# 8. Very Long Description & Chapters
video_long_description = {
    "kind": "youtube#videoListResponse",
    "items": [{
        "kind": "youtube#video",
        "id": "longDescVid1",
        "snippet": {
            "publishedAt": "2026-03-10T12:00:00Z",
            "channelId": "UCCourseProvider1234567",
            "title": "Full 12-Hour Python Deep Dive Masterclass",
            "description": "Complete Python masterclass.\n\n" + "\n".join([f"{h:02d}:00:00 - Masterclass Chapter {h}" for h in range(1, 12)]),
            "thumbnails": {"maxres": {"url": "https://i.ytimg.com/vi/longDescVid1/maxresdefault.jpg"}},
            "channelTitle": "Python Academy",
            "categoryId": "27"
        },
        "contentDetails": {
            "duration": "PT12H0M0S",
            "caption": "true"
        },
        "status": {"privacyStatus": "public"},
        "statistics": {
            "viewCount": "980000",
            "likeCount": "54000",
            "commentCount": "4200"
        }
    }]
}

# 9. Unicode, Emoji, and Non-English
video_emoji_non_english = {
    "kind": "youtube#videoListResponse",
    "items": [{
        "kind": "youtube#video",
        "id": "unicodeVid01",
        "snippet": {
            "publishedAt": "2026-06-15T18:00:00Z",
            "channelId": "UCGlobalCreator12345678",
            "title": "🔥🚀 मशीन लर्निंग सीखें! AI Explained in Hindi & English (हिंदी) - 日本語字幕付き 🎉",
            "description": "नमस्ते दोस्तों! आज हम AI और Deep Learning सीखेंगे।\n\n00:00 - परिचय (Intro) 🎬\n05:30 - न्यूरल नेटवर्क (Neural Networks) 🧠\n15:45 - निष्कर्ष (Conclusion) ✨",
            "thumbnails": {"high": {"url": "https://i.ytimg.com/vi/unicodeVid01/hqdefault.jpg"}},
            "channelTitle": "Global Tech हिन्दी",
            "tags": ["AI", "मशीन लर्निंग", "Python", "हिंदी", "Tech"],
            "categoryId": "28"
        },
        "contentDetails": {
            "duration": "PT22M15S",
            "caption": "true"
        },
        "status": {"privacyStatus": "public"},
        "statistics": {
            "viewCount": "125000",
            "likeCount": "9800",
            "commentCount": "1420"
        }
    }]
}

# 10. Quota Exceeded Error Body
error_quota_exceeded = {
    "error": {
        "code": 403,
        "message": "The request cannot be completed because you have exceeded your quota.",
        "errors": [{
            "message": "The request cannot be completed because you have exceeded your quota.",
            "domain": "youtube.quota",
            "reason": "quotaExceeded"
        }]
    }
}

# 11. Key Invalid Error Body
error_key_invalid = {
    "error": {
        "code": 400,
        "message": "API key not valid. Please pass a valid API key.",
        "errors": [{
            "message": "API key not valid. Please pass a valid API key.",
            "domain": "global",
            "reason": "keyInvalid"
        }]
    }
}

# 12. Channel Normal
channel_normal = {
    "kind": "youtube#channelListResponse",
    "items": [{
        "kind": "youtube#channel",
        "id": "UC_x5XG1OV2P6uZZ5FSM9Ttw",
        "snippet": {
            "title": "Google Developers",
            "description": "The Google Developers channel features talks and tutorials from Google developers.",
            "customUrl": "@googledevelopers",
            "publishedAt": "2007-08-23T00:34:43Z",
            "thumbnails": {
                "default": {"url": "https://yt3.ggpht.com/default.jpg"},
                "high": {"url": "https://yt3.ggpht.com/high.jpg"}
            },
            "country": "US"
        },
        "contentDetails": {
            "relatedPlaylists": {
                "likes": "",
                "uploads": "UU_x5XG1OV2P6uZZ5FSM9Ttw"
            }
        },
        "statistics": {
            "viewCount": "215000000",
            "subscriberCount": "2350000",
            "hiddenSubscriberCount": False,
            "videoCount": "6200"
        },
        "brandingSettings": {
            "image": {
                "bannerExternalUrl": "https://yt3.ggpht.com/banner"
            }
        }
    }]
}

# 13. Channel Hidden Subscribers
channel_hidden_subscribers = {
    "kind": "youtube#channelListResponse",
    "items": [{
        "kind": "youtube#channel",
        "id": "UCHiddenSubs12345678901",
        "snippet": {
            "title": "Secret Channel",
            "publishedAt": "2020-01-01T00:00:00Z"
        },
        "statistics": {
            "viewCount": "50000",
            "videoCount": "12",
            "hiddenSubscriberCount": True
            # subscriberCount is absent or 0 when hidden
        }
    }]
}

# 14. Playlist Pagination Page 1 & 2
playlist_pagination_page1 = {
    "kind": "youtube#playlistItemListResponse",
    "nextPageToken": "CAUQAA",
    "items": [
        {"contentDetails": {"videoId": f"vid_page1_{i:03d}"}} for i in range(1, 51)
    ],
    "pageInfo": {"totalResults": 75, "resultsPerPage": 50}
}

playlist_pagination_page2 = {
    "kind": "youtube#playlistItemListResponse",
    "items": [
        {"contentDetails": {"videoId": f"vid_page2_{i:03d}"}} for i in range(51, 76)
    ],
    "pageInfo": {"totalResults": 75, "resultsPerPage": 25}
}

# 15. 100 Labelled Comments for Sentiment Evaluation (Stage 3)
# Labels: POSITIVE, NEGATIVE, NEUTRAL
comments_100_labelled = [
    {"text": "This is the absolute best explanation of Python I have ever seen! Thank you so much!", "label": "POSITIVE", "category": "English Praise"},
    {"text": "Incredible content as always, keep up the amazing work brother!", "label": "POSITIVE", "category": "English Praise"},
    {"text": "Super helpful video, solved my bug in 2 minutes flat! 🎉", "label": "POSITIVE", "category": "English Praise"},
    {"text": "Worst tutorial ever. Complete waste of 20 minutes.", "label": "NEGATIVE", "category": "English Criticism"},
    {"text": "The audio is terrible, his voice hurts my ears.", "label": "NEGATIVE", "category": "English Criticism"},
    {"text": "Totally outdated information, does not work with modern libraries.", "label": "NEGATIVE", "category": "English Criticism"},
    {"text": "What version of Python is used at 04:30?", "label": "NEUTRAL", "category": "Question / Inactive"},
    {"text": "At 12:15 you forgot to import os module.", "label": "NEUTRAL", "category": "Fact / Feedback"},
    {"text": "The video is 14 minutes and 32 seconds long.", "label": "NEUTRAL", "category": "Statement"},
    {"text": "Oh great, another crypto bro teaching machine learning. Just what the world needed. 🙄", "label": "NEGATIVE", "category": "Sarcasm"},
    {"text": "Wow, what a genius! You figured out how to write a for-loop! Nobel prize incoming!", "label": "NEGATIVE", "category": "Sarcasm"},
    {"text": "Nice", "label": "POSITIVE", "category": "Very Short"},
    {"text": "good", "label": "POSITIVE", "category": "Very Short"},
    {"text": "bad", "label": "NEGATIVE", "category": "Very Short"},
    {"text": "ok", "label": "NEUTRAL", "category": "Very Short"},
    {"text": "😂", "label": "POSITIVE", "category": "Emoji Only"},
    {"text": "🔥🔥🔥", "label": "POSITIVE", "category": "Emoji Only"},
    {"text": "❤️❤️", "label": "POSITIVE", "category": "Emoji Only"},
    {"text": "💩", "label": "NEGATIVE", "category": "Emoji Only"},
    {"text": "🤮", "label": "NEGATIVE", "category": "Emoji Only"},
    {"text": "👍", "label": "POSITIVE", "category": "Emoji Only"},
    {"text": "😐", "label": "NEUTRAL", "category": "Emoji Only"},
    {"text": "FIRST!", "label": "NEUTRAL", "category": "Spam / First"},
    {"text": "first comment here", "label": "NEUTRAL", "category": "Spam / First"},
    {"text": "Check out my channel for free crypto signals 🚀🚀🚀 whatsapp: +12345678", "label": "NEGATIVE", "category": "Spam / Bot"},
    {"text": "I made $5000 in 2 days using this strategy visit investment-scam.xyz", "label": "NEGATIVE", "category": "Spam / Bot"},
    {"text": "Bhai ekdum mast video tha, maza aa gaya! ❤️", "label": "POSITIVE", "category": "Hinglish"},
    {"text": "Ye code kaam nahi kar raha hai, bohot bekaar tutorial hai.", "label": "NEGATIVE", "category": "Hinglish"},
    {"text": "Bhai 10:20 pe kya kiya samajh nahi aaya, please reply.", "label": "NEUTRAL", "category": "Hinglish"},
    {"text": "बहुत ही शानदार और ज्ञानवर्धक वीडियो। धन्यवाद गुरुजी!", "label": "POSITIVE", "category": "Hindi"},
    {"text": "समय बर्बाद कर दिया, कुछ नया नहीं सिखाया।", "label": "NEGATIVE", "category": "Hindi"},
    {"text": "यह वीडियो 2026 में देखा जा रहा है।", "label": "NEUTRAL", "category": "Hindi"},
    {"text": "THIS IS THE GREATEST VIDEO IN THE HISTORY OF YOUTUBE!!!!", "label": "POSITIVE", "category": "All-Caps"},
    {"text": "I ABSOLUTELY HATE THIS GARBAGE DELETE YOUR CHANNEL", "label": "NEGATIVE", "category": "All-Caps"},
    {"text": "WHY ARE YOU SHOUTING AT 05:00", "label": "NEUTRAL", "category": "All-Caps"},
]

# Expand to 100 items by generating variations of these core patterns
all_100_comments = []
for i in range(100):
    base = comments_100_labelled[i % len(comments_100_labelled)]
    all_100_comments.append({
        "id": f"comment_{i+1:03d}",
        "author": f"User_{i+1}",
        "text": base["text"] if i < len(comments_100_labelled) else f"{base['text']} (#{i+1})",
        "ground_truth_sentiment": base["label"],
        "category": base["category"]
    })

# 16. 5,000 Generated Comments
comments_5000 = [
    {
        "id": f"c_5k_{i}",
        "text": f"Generated comment {i}: {'Great video!' if i % 3 == 0 else ('Terrible quality' if i % 5 == 0 else 'Just watching')} with emoji {'👍' if i % 2 == 0 else '🔥'}",
        "like_count": i % 100,
        "published_at": "2026-08-10T12:00:00Z"
    } for i in range(5000)
]

fixtures = {
    'video_normal.json': video_normal,
    'video_hidden_likes.json': video_hidden_likes,
    'video_comments_disabled.json': video_comments_disabled,
    'video_no_comments.json': video_no_comments,
    'video_deleted_private.json': video_deleted_private,
    'video_live_stream.json': video_live_stream,
    'video_shorts.json': video_shorts,
    'video_long_description.json': video_long_description,
    'video_emoji_non_english.json': video_emoji_non_english,
    'error_quota_exceeded.json': error_quota_exceeded,
    'error_key_invalid.json': error_key_invalid,
    'channel_normal.json': channel_normal,
    'channel_hidden_subscribers.json': channel_hidden_subscribers,
    'playlist_pagination_page1.json': playlist_pagination_page1,
    'playlist_pagination_page2.json': playlist_pagination_page2,
    'comments_100_labelled.json': all_100_comments,
    'comments_5000_generated.json': comments_5000
}

for name, data in fixtures.items():
    path = os.path.join(fixtures_dir, name)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"Wrote fixture: {name} ({os.path.getsize(path)} bytes)")

