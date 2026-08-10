# YouTube Analyzer — Architecture & Planning Specification

**Document Type:** Software Architecture Document (SAD)  
**Version:** 1.0  
**Date:** July 2026  
**Status:** Final — Implementation Ready  
**Prepared For:** Antigravity (AI Implementation Agent)  
**Based On:** YouTube Analyzer Platform Engineering Research Document v1.0

---

> **Instructions for the implementing agent:** This document makes every architectural decision in advance. Do not substitute libraries, frameworks, or patterns without explicit justification. Every section is authoritative. When two sections appear to conflict, the more specific section takes precedence.

---

## Table of Contents

1. [Project Vision](#1-project-vision)
2. [Functional Requirements](#2-functional-requirements)
3. [Non-Functional Requirements](#3-non-functional-requirements)
4. [Final Technology Stack](#4-final-technology-stack)
5. [Folder Structure](#5-folder-structure)
6. [Backend Architecture](#6-backend-architecture)
7. [Frontend Architecture](#7-frontend-architecture)
8. [Database Design](#8-database-design)
9. [API Design](#9-api-design)
10. [Background Jobs](#10-background-jobs)
11. [Caching Strategy](#11-caching-strategy)
12. [Error Handling](#12-error-handling)
13. [Performance Strategy](#13-performance-strategy)
14. [UI Planning](#14-ui-planning)
15. [Implementation Roadmap](#15-implementation-roadmap)
16. [Testing Strategy](#16-testing-strategy)
17. [Deployment Strategy](#17-deployment-strategy)
18. [Future Extensions](#18-future-extensions)

---

## 1. Project Vision

### 1.1 Purpose

The YouTube Analyzer is a self-hosted, open-source web application that extracts, stores, analyzes, and presents publicly available YouTube data — without requiring any official API keys, Google OAuth credentials, or paid services. It serves as a personal intelligence platform for YouTube content research, enabling deep analysis of videos, channels, playlists, and transcripts through a clean browser-based interface.

The platform is a single-user application by design. All data is stored locally in the user's own database. All extraction is performed by the user's own server using open-source tooling. No data is sent to third-party analytics or tracking services.

### 1.2 Scope

**In scope:**
- Full video metadata extraction and storage (title, description, tags, categories, view count, like count, duration, upload date, chapters, thumbnails, formats, language, availability, live status, shorts detection)
- Channel metadata extraction and storage (name, ID, handle, description, subscriber count, video count, avatar, banner, verification status, external links)
- Playlist metadata extraction and full video membership crawling
- Transcript and subtitle extraction with structured time-aligned segments
- Video and audio file downloads in user-selected quality/format
- YouTube search via yt-dlp
- Channel monitoring via YouTube RSS feeds (new video detection)
- Comment extraction with threading support
- Historical metric snapshots (channel and video growth tracking)
- Background job queue for all asynchronous operations
- Real-time job progress via Server-Sent Events (SSE)
- Settings management (download preferences, monitoring intervals, proxy config)
- Download history and file management

**Out of scope (by design — see Research Document Section 7):**
- YouTube Analytics data (watch time, CTR, impressions, audience retention)
- Revenue, monetization, or ad data
- Audience demographics
- Historical subscriber tracking (beyond point-in-time snapshots)
- Private or member-only video content
- Multi-user authentication or account management (Phase 1)
- Any paid API or SaaS service

### 1.3 Target Users

The primary user is a technically capable individual — a developer, researcher, content creator, or data analyst — who wants to:
- Analyze YouTube channels and videos without API quota limits
- Download videos and audio for archival or research purposes
- Extract and search transcripts across multiple videos
- Track channel growth metrics over time
- Build a private database of YouTube content for analysis

The user is running this application on their own hardware or a personal VPS. They understand that the application interacts with YouTube and have chosen to accept the associated terms of service implications.

### 1.4 Known Limitations

The following limitations are permanent and result from YouTube's platform design:

1. **PoToken requirement (2025–2026 critical constraint):** All yt-dlp operations against YouTube require Proof-of-Origin Token management. Datacenter IPs are more aggressively blocked than residential IPs. The application includes cookie management and player client rotation as mitigations, with optional bgutil sidecar support.
2. **Rate limiting:** YouTube rate-limits requests from the same IP. All extraction is queued and rate-limited to avoid triggering blocks.
3. **Data accuracy:** Subscriber counts may be rounded or absent. Some fields (join date, banner URL) are inconsistently available. Like counts are hidden on some videos.
4. **Comment extraction is slow:** Extracting thousands of comments requires many paginated requests and is subject to bot detection.
5. **No real-time data:** All data reflects the state at extraction time. Views and likes are not live.

### 1.5 Future Scalability

The architecture supports these future expansions without structural change:
- Official YouTube Data API as an alternative data source (via Repository interface pattern)
- OAuth-based channel owner analytics
- Multi-user authentication and per-user data isolation
- AI/LLM transcript analysis pipeline
- Vector database for semantic search across transcripts
- Cloud storage for downloaded files (S3-compatible)
- Social Blade supplementary data source

---

## 2. Functional Requirements

All features are grouped into modules. Each feature specifies purpose, inputs, outputs, dependencies, errors, and edge cases.

---

### 2.1 Channel Module

#### Feature: Add Channel

**Purpose:** Register a YouTube channel in the platform by providing a URL or handle. Triggers initial metadata extraction.

**Inputs:**
- YouTube channel URL in any supported format: `https://youtube.com/@handle`, `https://youtube.com/channel/UCxxxxx`, `https://youtube.com/c/name`, or bare `@handle`
- Option: whether to immediately queue a full video list crawl (default: false)

**Outputs:**
- Channel record created or updated in the `channels` table
- Background job queued for metadata extraction
- Job ID returned to frontend for polling
- On completion: channel profile page rendered with all available fields

**Dependencies:** yt-dlp, ProcessingQueue, ChannelService, ChannelRepository

**Errors:**
- Invalid URL format → HTTP 422 with validation message
- Channel not found on YouTube → HTTP 404 with message
- yt-dlp extraction failure → job marked as failed, retry queued
- Duplicate channel → return existing channel record, optionally trigger refresh

**Edge cases:**
- Handle with spaces or special characters → URL-encode before passing to yt-dlp
- Channel with 0 videos → extract metadata only, no crawl needed
- Live channel (@handle redirects to /channel/UCxxxx) → normalize to channel_id before storage

---

#### Feature: View Channel Profile

**Purpose:** Display all stored metadata for a tracked channel including profile info, stats, and video list summary.

**Inputs:** channel_id (internal DB ID or YouTube channel ID)

**Outputs:**
- Channel name, handle, avatar, banner, description, subscriber count, video count, total views, join date, verification status, external links
- Last crawled timestamp
- Link to full video list
- Link to snapshots/growth chart

**Dependencies:** ChannelRepository, VideoRepository (count only)

**Errors:** Channel not found → HTTP 404

**Edge cases:** Fields absent from YouTube (join date, banner) → display "Not available" gracefully without error

---

#### Feature: Refresh Channel Metadata

**Purpose:** Re-extract a channel's metadata from YouTube to update stored values.

**Inputs:** channel_id

**Outputs:** Background job queued; returns job_id

**Dependencies:** ProcessingQueue, ChannelService

**Errors:** Channel not found → HTTP 404; extraction failure → job failed status

**Edge cases:** Concurrent refresh requests for same channel → deduplicate, return existing job_id if already queued

---

#### Feature: Crawl Channel Videos

**Purpose:** Extract all video IDs for a channel using yt-dlp flat-playlist and queue metadata extraction for each.

**Inputs:**
- channel_id
- Options: max_videos (default: unlimited), crawl_type (all|uploads|shorts|live)

**Outputs:**
- Background job created with sub-jobs per video
- Progress available via SSE stream
- On completion: all discovered videos added to the `videos` table stub records

**Dependencies:** yt-dlp (--flat-playlist), ProcessingQueue, VideoService

**Errors:** Channel not found, rate-limit triggered, network failure → retry with backoff

**Edge cases:**
- Channel with 10,000+ videos → paginated extraction, progress tracked by video count
- Some videos may be unavailable (deleted, private) → mark as unavailable, continue
- Shorts mixed with regular videos → detect and flag `is_short` field

---

#### Feature: Monitor Channel via RSS

**Purpose:** Automatically detect new videos published to a tracked channel using YouTube's RSS feed.

**Inputs:** channel_id (must have valid YouTube channel_id for RSS URL construction)

**Outputs:**
- Periodic background check (configurable interval, default 60 minutes)
- New videos detected → metadata extraction job queued automatically
- No user action required after monitoring is enabled

**Dependencies:** feedparser (or stdlib xml.etree), ChannelRepository, ProcessingQueue, RSSMonitorJob

**Errors:** RSS fetch failure → log and retry next cycle; do not alert user

**Edge cases:**
- Channel with @handle that doesn't map to a UC-prefixed ID → resolve handle to channel_id first using yt-dlp, then construct RSS URL
- RSS returns video already in DB → skip, no duplicate
- RSS returns video in DB but not yet fully extracted → check if metadata is complete, re-queue if stub only

---

#### Feature: Channel Snapshots

**Purpose:** Record daily snapshots of channel metrics to enable historical growth charts.

**Inputs:** Automated — no user input; triggered by scheduler

**Outputs:** One `channel_snapshots` row per tracked channel per day

**Dependencies:** Scheduler (APScheduler/Celery Beat), ChannelRepository, SnapshotJob

**Errors:** Extraction failure → skip day, log warning; do not create partial snapshot

**Edge cases:** Multiple snapshot runs in same day → idempotent: check date before inserting, skip if exists

---

#### Feature: Delete Channel

**Purpose:** Remove a channel and all associated data from the platform.

**Inputs:** channel_id; confirmation flag

**Outputs:** Cascading delete of channel, all its videos, transcripts, comments, snapshots, download history entries, playlist associations

**Dependencies:** ChannelRepository

**Errors:** Channel not found → HTTP 404; confirmation not provided → HTTP 422

**Edge cases:** Videos in active download jobs → cancel jobs, then delete

---

### 2.2 Video Module

#### Feature: Extract Video Metadata

**Purpose:** Extract and store all publicly available metadata for a single YouTube video.

**Inputs:** YouTube video URL or video_id

**Outputs:**
- Complete `videos` table record with all extractable fields
- Associated thumbnails stored in filesystem
- Job status returned

**Dependencies:** yt-dlp, VideoService, VideoRepository, ThumbnailService

**Errors:** Private/deleted video → mark availability="unavailable"; age-restricted → mark age_limit; PoToken failure → retry with alternate client

**Edge cases:**
- Video already in DB → update if `last_extracted_at` older than 24 hours, else return cached
- Live video → mark `is_live=true`; extract available metadata but skip format list (formats change during live)
- Short video (< 60 seconds) → detect and set `is_short=true`

---

#### Feature: View Video Details

**Purpose:** Display all stored metadata for a video including stats, chapters, formats, and embedded transcript/comments if available.

**Inputs:** video_id

**Outputs:**
- All stored video metadata
- Chapter list if present
- Heatmap data if present
- Available formats list
- Links to transcript, comments, download

**Dependencies:** VideoRepository, TranscriptRepository, CommentRepository

**Errors:** Video not found → HTTP 404

**Edge cases:** Video with no chapters → show "No chapters available"; heatmap absent → don't show heatmap section

---

#### Feature: Refresh Video Metadata

**Purpose:** Re-extract video metadata to update view count, like count, and other changing fields.

**Inputs:** video_id

**Outputs:** Background job queued, job_id returned

**Dependencies:** ProcessingQueue, VideoService

**Errors:** Video not found, extraction failure → job failed

---

#### Feature: Video Snapshot

**Purpose:** Record a daily metric snapshot for a video (views, likes, comment count).

**Inputs:** Automated — triggered by scheduler for tracked videos

**Outputs:** One `video_snapshots` row per tracked video per day

**Dependencies:** Scheduler, VideoRepository, SnapshotJob

**Errors / Edge cases:** Same as Channel Snapshots — idempotent, skip if date already exists

---

#### Feature: Delete Video

**Purpose:** Remove a video record and all associated data.

**Inputs:** video_id; confirmation flag

**Outputs:** Video and all associated transcripts, comments, download history, snapshots removed. Playlist associations removed.

**Dependencies:** VideoRepository

**Errors:** Active download → cancel job first; video not found → HTTP 404

---

### 2.3 Search Module

#### Feature: YouTube Search

**Purpose:** Search YouTube without an API key and display results.

**Inputs:**
- query string
- search_type: video (default), channel, playlist
- max_results: 10, 20, 50 (default 20)

**Outputs:**
- List of search result stubs: video_id, title, channel, thumbnail, duration, view_count, upload_date
- Results cached in `search_history` table for 1 hour

**Dependencies:** yt-dlp (`ytsearch{n}:`), SearchService, SearchRepository

**Errors:** yt-dlp search failure → HTTP 503 with retry guidance; empty results → 200 with empty array

**Edge cases:**
- Same query within cache TTL → return cached results, do not re-hit YouTube
- Very long queries → truncate to 200 characters before passing to yt-dlp
- Special characters in query → pass as-is; yt-dlp handles URL encoding

---

#### Feature: Internal Search

**Purpose:** Search the local database of extracted videos and channels.

**Inputs:**
- query string
- entity_type: video, channel, transcript
- filters: channel_id, date_range, min_views, has_transcript, is_short

**Outputs:**
- Matching records from DB with relevance sort
- Pagination: page, per_page (default 20)

**Dependencies:** VideoRepository, ChannelRepository, TranscriptRepository (full-text search on MySQL FULLTEXT index)

**Errors:** Empty results → 200 with empty array; invalid filter values → HTTP 422

**Edge cases:** Transcript search matches mid-text → highlight matched segment and its timestamp; return video_id, timestamp, excerpt

---

### 2.4 Transcript Module

#### Feature: Extract Transcript

**Purpose:** Fetch and store the time-aligned transcript for a video.

**Inputs:**
- video_id
- language_code (default: "en"; "auto" to use auto-generated if manual unavailable)
- auto_translate_to (optional: target language code for translation)

**Outputs:**
- `transcripts` table record with segments JSON and full_text
- Job ID for async tracking

**Dependencies:** youtube-transcript-api (primary), yt-dlp (fallback for subtitle download), TranscriptService

**Errors:**
- No captions available → TranscriptNotAvailableError; mark `has_transcript=false` on video record
- Language not available → return available languages list with HTTP 409
- youtube-transcript-api timeout → fall back to yt-dlp subtitle extraction; if both fail, job failed

**Edge cases:**
- Video with only auto-generated captions → allow with warning in response
- Very long video (3+ hours) → transcript may have thousands of segments; ensure no truncation
- Multiple languages available → extract all if `language_code="all"`

---

#### Feature: View Transcript

**Purpose:** Display the full transcript for a video with timestamps.

**Inputs:** video_id, language_code (default: "en")

**Outputs:**
- Full_text as readable formatted text
- Segments array with `{text, start_seconds, duration_seconds}` for time-linked display
- Available languages list

**Dependencies:** TranscriptRepository

**Errors:** Transcript not found in DB → HTTP 404 with option to extract

---

#### Feature: Search Within Transcript

**Purpose:** Find specific text within a video's transcript and return the timestamp.

**Inputs:** video_id, search_term

**Outputs:** Array of matches: `{text_excerpt, start_seconds, context_before, context_after}`

**Dependencies:** TranscriptRepository

**Errors:** No transcript → HTTP 404; no matches → empty array

---

#### Feature: Export Transcript

**Purpose:** Download transcript as plain text, SRT subtitle file, or JSON.

**Inputs:** video_id, format (txt|srt|json), language_code

**Outputs:** File download response with appropriate Content-Type header

**Dependencies:** TranscriptRepository, TranscriptFormatter (internal utility)

**Errors:** Transcript not found → HTTP 404

---

### 2.5 Download Module

#### Feature: Queue Video Download

**Purpose:** Download a video file in a user-specified format and quality.

**Inputs:**
- video_id or YouTube URL
- quality: best, 1080p, 720p, 480p, 360p, worst
- format: mp4, webm (default: mp4)
- output_path (optional; defaults to configured download directory)

**Outputs:**
- Download job created with job_id
- Progress streamed via SSE: percentage, speed, ETA
- On completion: file path stored in `download_history`

**Dependencies:** yt-dlp + FFmpeg, DownloadService, DownloadRepository, ProcessingQueue

**Errors:**
- Video unavailable → HTTP 404
- Disk space insufficient → HTTP 507 with available space
- FFmpeg not found → HTTP 503 with installation instructions
- Download interrupted → partial file cleaned up; job status = failed

**Edge cases:**
- Already downloaded → check download_history; return existing file path if file still exists
- Concurrent downloads of same video → allow; yt-dlp writes to separate temp files

---

#### Feature: Queue Audio Download

**Purpose:** Download audio-only from a video in a specified format.

**Inputs:**
- video_id or YouTube URL
- format: mp3, m4a, opus, wav (default: mp3)
- quality: best, 192k, 128k, worst

**Outputs:** Same as video download — job_id, progress via SSE, file path on completion

**Dependencies:** yt-dlp + FFmpeg, DownloadService

**Errors / Edge cases:** Same as video download

---

#### Feature: Queue Subtitle Download

**Purpose:** Download subtitle/caption files for a video.

**Inputs:**
- video_id or YouTube URL
- language_code (or "all" for all available languages)
- format: srt, vtt, json (default: srt)

**Outputs:** Job ID, file path on completion (one file per language)

**Dependencies:** yt-dlp (`--write-subs --skip-download`), DownloadService

---

#### Feature: Queue Thumbnail Download

**Purpose:** Save a video's thumbnail to disk.

**Inputs:** video_id, resolution: maxres, high, medium, default (default: maxres)

**Outputs:** Job ID, file path on completion; also stores locally in `thumbnails/` directory

**Dependencies:** httpx (direct CDN download), ThumbnailService

**Errors:** Thumbnail URL expired (CDN expiry) → re-extract from yt-dlp, then download

---

#### Feature: View Download History

**Purpose:** List all completed and in-progress downloads with file paths and status.

**Inputs:**
- Filters: status (all|complete|failed|downloading), video_id, download_type
- Pagination: page, per_page

**Outputs:** Paginated list of download_history records

**Dependencies:** DownloadRepository

---

#### Feature: Cancel Download

**Purpose:** Cancel an in-progress download job.

**Inputs:** job_id

**Outputs:** Job cancelled; partial files cleaned up

**Dependencies:** ProcessingQueue, DownloadService

---

#### Feature: Delete Download Record

**Purpose:** Remove a download history entry. Optionally delete the file from disk.

**Inputs:** download_id; delete_file (boolean, default: false)

**Outputs:** Record removed; file optionally deleted

**Dependencies:** DownloadRepository

---

### 2.6 Playlist Module

#### Feature: Add Playlist

**Purpose:** Register a YouTube playlist and extract its metadata and video list.

**Inputs:** YouTube playlist URL (`https://youtube.com/playlist?list=PLxxxxx`)

**Outputs:**
- `playlists` table record with metadata
- All video IDs added as stub `videos` records via flat-playlist extraction
- junction records in `playlist_videos` table with ordinal positions

**Dependencies:** yt-dlp, PlaylistService, PlaylistRepository, VideoRepository

**Errors:** Playlist not found → HTTP 404; private playlist → HTTP 403 with message

**Edge cases:**
- Playlist with 500+ videos → paginated extraction; progress tracked
- Videos in playlist not yet in DB → create stub records; full metadata extracted lazily

---

#### Feature: View Playlist

**Purpose:** Display playlist metadata and all its videos.

**Inputs:** playlist_id

**Outputs:**
- Playlist title, description, uploader, video count, thumbnail
- Ordered list of videos with their stored metadata

**Dependencies:** PlaylistRepository, VideoRepository

---

#### Feature: Refresh Playlist

**Purpose:** Re-crawl a playlist to detect added or removed videos.

**Inputs:** playlist_id

**Outputs:** Background job queued; returns job_id

**Dependencies:** ProcessingQueue, PlaylistService

**Edge cases:**
- Videos removed from playlist → remove playlist_videos junction records; do not delete video records
- New videos added → add new video stubs and junction records

---

### 2.7 Comment Module

#### Feature: Extract Comments

**Purpose:** Fetch and store comments for a video using yt-dlp.

**Inputs:**
- video_id
- max_comments (default: 100, max: 10000)
- include_replies (default: true)

**Outputs:**
- Background job queued
- `comments` table populated with all retrieved comments
- Top-level comments linked to video; replies linked to parent comment

**Dependencies:** yt-dlp (getcomments=True), CommentService, CommentRepository

**Errors:**
- Comments disabled on video → mark video `comments_disabled=true`; return 409
- Bot detection during comment extraction → retry with backoff; max 3 retries

**Edge cases:**
- Very popular video (100,000+ comments) → cap at max_comments setting; log warning
- Pinned comments → set `is_pinned=true`
- Creator comments → set `is_creator_comment=true`

---

#### Feature: View Comments

**Purpose:** Display stored comments for a video in threaded format.

**Inputs:**
- video_id
- sort: top (default), newest
- page, per_page (default 50)
- include_replies (default: true)

**Outputs:** Paginated list of top-level comments with nested replies

**Dependencies:** CommentRepository

---

### 2.8 Analytics Module

#### Feature: Channel Growth Chart

**Purpose:** Visualize channel subscriber and view count over time using stored snapshots.

**Inputs:** channel_id, date_range (default: last 30 days)

**Outputs:** Time-series data: `[{date, subscriber_count, video_count, total_view_count}]`

**Dependencies:** ChannelRepository (snapshot queries)

**Errors:** No snapshots available → HTTP 404 with prompt to enable monitoring

---

#### Feature: Video Performance Chart

**Purpose:** Visualize view count changes over time for a specific video.

**Inputs:** video_id, date_range (default: last 30 days)

**Outputs:** Time-series data: `[{date, view_count, like_count, comment_count}]`

**Dependencies:** VideoRepository (snapshot queries)

---

#### Feature: Channel Video Statistics

**Purpose:** Aggregate statistics across all videos in a channel.

**Inputs:** channel_id

**Outputs:**
- Total views across all videos
- Average views per video
- Top 10 videos by views
- Top 10 videos by like count
- Upload frequency (videos per week/month)
- Duration distribution histogram
- Tag frequency analysis

**Dependencies:** VideoRepository (aggregate queries)

---

#### Feature: Dashboard Overview

**Purpose:** Platform-wide summary of all tracked data.

**Outputs:**
- Total channels tracked
- Total videos tracked
- Total transcripts extracted
- Total downloads
- Recent job activity (last 10 jobs)
- Channels with newest videos (RSS monitor updates)
- Storage usage (downloads directory size)

**Dependencies:** Multiple repositories, system filesystem

---

### 2.9 Settings Module

#### Feature: View/Update Settings

**Purpose:** Manage global platform preferences.

**Inputs/Outputs — Settings Fields:**

| Setting | Type | Default | Purpose |
|---|---|---|---|
| download_directory | string | `./downloads` | Base path for all downloaded files |
| default_video_quality | enum | `1080p` | Quality for video downloads |
| default_audio_format | enum | `mp3` | Format for audio downloads |
| default_audio_quality | enum | `192k` | Bitrate for audio |
| auto_extract_transcript | boolean | `false` | Extract transcript on video add |
| auto_extract_comments | boolean | `false` | Extract comments on video add |
| auto_extract_thumbnail | boolean | `true` | Save thumbnail on video add |
| rss_poll_interval_minutes | integer | 60 | How often to poll RSS feeds |
| max_concurrent_downloads | integer | 2 | Parallel download limit |
| max_comments_per_video | integer | 500 | Cap for comment extraction |
| yt_dlp_rate_limit | string | `500K` | yt-dlp rate limit (bytes/sec) |
| yt_dlp_cookies_path | string | null | Path to YouTube cookies file |
| yt_dlp_proxy | string | null | Proxy URL for yt-dlp requests |
| yt_dlp_player_client | string | `ios` | Player client for bot detection |
| pot_provider_url | string | null | URL for bgutil sidecar |
| metadata_cache_ttl_hours | integer | 24 | Staleness threshold for re-extraction |
| snapshot_enabled | boolean | `true` | Enable daily metric snapshots |
| monitored_channels | JSON | `[]` | Channel IDs with RSS monitoring on |

**Dependencies:** SettingsRepository

**Errors:** Invalid values → HTTP 422 with field-level errors

---

#### Feature: Cookie Management

**Purpose:** Upload and manage YouTube cookies file for bot detection mitigation.

**Inputs:**
- Upload: cookies.txt file (Netscape format)
- Actions: upload, delete, test (verify cookies are valid)

**Outputs:** Cookies saved to configured path; test action returns "valid" or "expired"

**Dependencies:** SettingsRepository, yt-dlp (for cookie validation test)

---

### 2.10 Job Queue Module

#### Feature: View Job Status

**Purpose:** Check the status of any background job.

**Inputs:** job_id

**Outputs:**
- status: queued, processing, complete, failed, cancelled
- progress_percent (0–100)
- current_operation string
- error_message if failed
- created_at, started_at, completed_at

**Dependencies:** QueueRepository

---

#### Feature: View Job List

**Purpose:** Browse all jobs with filters.

**Inputs:** Filters: status, job_type, date_range; Pagination: page, per_page

**Outputs:** Paginated job list

**Dependencies:** QueueRepository

---

#### Feature: Cancel Job

**Inputs:** job_id

**Outputs:** Job status → cancelled; any partial work cleaned up

---

#### Feature: Retry Failed Job

**Inputs:** job_id

**Outputs:** New job queued with same parameters; returns new job_id

---

#### Feature: SSE Job Progress Stream

**Purpose:** Stream real-time progress events for a job to the frontend.

**Inputs:** job_id (via SSE connection: `GET /api/jobs/{job_id}/stream`)

**Outputs:** Server-Sent Events stream with events:
- `progress`: `{percent, operation, speed, eta}`
- `complete`: `{result_url, summary}`
- `error`: `{message, retryable}`

**Dependencies:** Flask SSE (using `flask` response streaming + Redis pub/sub)

---

## 3. Non-Functional Requirements

### 3.1 Performance

- API response time for cached/DB queries: < 200ms at p95
- API response time for job submission: < 500ms (job is queued, not executed)
- Frontend initial load time: < 3 seconds on standard broadband
- Channel metadata extraction: complete within 10 seconds for single channel
- Playlist with 100 videos: flat extraction complete within 60 seconds
- Maximum concurrent yt-dlp worker processes: configurable, default 2 to avoid rate limiting
- Database queries must use indexes; no full table scans on tables with > 1000 rows

### 3.2 Scalability

- The platform must handle: 50 tracked channels, 10,000 tracked videos, 1 million transcript segments, 500 download history records without degradation
- All extraction jobs are queued — the API is never blocked by YouTube operations
- Background workers scale horizontally: multiple Celery worker processes can run against the same queue
- Database tables use appropriate indexing; pagination is mandatory for all list endpoints

### 3.3 Maintainability

- All Python code follows PEP 8 with Black formatting
- All functions and classes have docstrings
- No function exceeds 50 lines; extract helper functions when approaching limit
- Service layer and repository layer are strictly separated — repositories never contain business logic
- Configuration is entirely environment-variable-driven; no hardcoded secrets
- yt-dlp is the only YouTube extraction tool; any workaround for YouTube changes must go through yt-dlp options or the extraction layer, not ad-hoc requests

### 3.4 Security

- No authentication required in Phase 1 (single-user, self-hosted)
- All user inputs are validated via Marshmallow schemas before reaching service layer
- File paths returned in API responses must be within the configured download directory (path traversal prevention)
- Cookie files stored outside web root; never served directly
- SQL injection: prevented by SQLAlchemy ORM parameterized queries only (no raw SQL strings with f-strings)
- CORS: configured to allow only the configured frontend origin (default: `http://localhost:5173`)
- Rate limiting: Flask-Limiter on all extraction-triggering endpoints (30 requests/minute per IP)

### 3.5 Reliability

- All background jobs have retry logic with exponential backoff: initial 5s delay, max 3 retries, max 60s delay
- Job failures are recorded with full error messages and stack traces
- Database uses transactions for all multi-row operations
- yt-dlp is auto-updated via the scheduler weekly to maintain YouTube compatibility
- Partial file cleanup: any interrupted download deletes its temp file
- Redis is used for job queue; if Redis is unavailable, the queue falls back to the database queue table (ProcessingQueue)

### 3.6 Logging

- Structured JSON logging (via Python's `logging` module with JSON formatter)
- Log levels: DEBUG (dev), INFO (production default)
- All yt-dlp stderr output captured and stored with job records
- Logs include: timestamp, level, module, job_id (where applicable), video_id/channel_id (where applicable), duration_ms
- Log output to stdout (Docker standard); rotation handled by Docker log driver or OS
- Do not log: cookie file contents, proxy credentials, or any user PII

### 3.7 Testing

- Minimum 80% code coverage for service layer and repository layer
- All API endpoints have integration tests with both success and error cases
- yt-dlp calls are mocked in tests using a fixture that returns pre-recorded JSON responses
- Frontend components tested with Vitest + React Testing Library for critical paths
- No production tests against YouTube (all mocked)

### 3.8 Deployment

- Must run via `docker compose up` with zero additional configuration beyond `.env` file
- Must run locally without Docker (pip install, python run.py)
- Migrations run automatically on startup via Alembic `upgrade head`
- All environment variables have documented defaults; the application starts with defaults if `.env` is absent
- Container restarts: all services configured with `restart: unless-stopped`

### 3.9 Responsiveness

- Frontend responsive from 375px (mobile) to 2560px (wide monitor)
- Core workflows functional on tablet (768px+)
- Mobile view: simplified layouts, no data-dense tables (use cards instead)
- Tailwind CSS breakpoints: `sm:`, `md:`, `lg:`, `xl:` used consistently

### 3.10 Accessibility

- All interactive elements keyboard-navigable
- ARIA labels on icon-only buttons
- Color contrast ratio ≥ 4.5:1 for all text (WCAG AA)
- Semantic HTML: `<main>`, `<nav>`, `<section>`, `<article>` used appropriately
- Loading states announced via `aria-live` regions

### 3.11 Code Quality

- Python: Black (formatter), Ruff (linter), mypy (type checking optional but recommended)
- JavaScript/React: ESLint + Prettier
- Git: conventional commits format (`feat:`, `fix:`, `chore:`, `docs:`)
- No commented-out code in production
- All TODO comments include a ticket or issue reference

---

## 4. Final Technology Stack

### 4.1 Backend

| Technology | Version | Purpose | Why Selected |
|---|---|---|---|
| Python | 3.12 | Runtime | LTS; yt-dlp requires 3.9+; 3.12 brings performance improvements |
| Flask | 3.1+ | Web framework | Specified in requirements; lightweight; well-understood; excellent extension ecosystem |
| Flask-SQLAlchemy | 3.1+ | ORM integration | Integrates SQLAlchemy cleanly with Flask app context |
| Flask-Migrate | 4.0+ | Database migrations (Alembic wrapper) | Simplifies Alembic with Flask; provides CLI commands |
| Flask-CORS | 4.0+ | Cross-origin resource sharing | Required for React frontend on different port |
| Flask-Limiter | 3.5+ | Rate limiting | Protects extraction endpoints from abuse |
| Marshmallow | 3.21+ | Request/response serialization and validation | Schema-based validation; clean separation from models |
| Gunicorn | 22.0+ | WSGI production server | Standard production WSGI server for Flask |

### 4.2 Frontend

| Technology | Version | Purpose | Why Selected |
|---|---|---|---|
| React | 18.3+ | UI framework | Specified; component model suits complex dashboard |
| Vite | 5.3+ | Build tool | Fast HMR; modern ESM; standard for React projects |
| React Router | 6.26+ | Client-side routing | Industry standard for React SPA routing |
| TanStack Query | 5.56+ | Server state management | Handles caching, refetching, loading states for API calls |
| Zustand | 4.5+ | UI state management | Lightweight; simpler than Redux for this use case |
| Tailwind CSS | 3.4+ | Styling | Utility-first; fast development; responsive built-in |
| Recharts | 2.12+ | Charts | React-native charting; handles time-series for analytics |
| Lucide React | 0.383+ | Icons | Consistent icon set; tree-shakeable |
| Axios | 1.7+ | HTTP client | Interceptor support for error handling |

### 4.3 Database

| Technology | Version | Purpose | Why Selected |
|---|---|---|---|
| MySQL | 8.0+ | Primary database | Specified in requirements |
| SQLAlchemy | 2.0+ | ORM | Specified; provides clean abstraction over MySQL |
| PyMySQL | 1.1+ | MySQL driver for SQLAlchemy | Pure Python; no C extensions needed; works in Docker slim images |
| Alembic | 1.13+ | Schema migrations | Used via Flask-Migrate; manages schema evolution |

**Note on MySQL vs PostgreSQL:** The research document specified PostgreSQL in its architecture section. The specification requirements document overrides this with MySQL. The ORM and Repository pattern abstracts the difference — the repository layer is the only layer aware of the database engine. MySQL 8.0 provides JSON column type, FULLTEXT indexes, and window functions sufficient for all features in this specification.

### 4.4 Extraction Libraries

| Technology | Version | Purpose | Why Selected |
|---|---|---|---|
| yt-dlp | 2026.07.04+ | Video/channel/playlist/comment/search extraction | Research document primary engine; 181k stars; 12M monthly downloads |
| youtube-transcript-api | 1.2.3+ | Transcript extraction (primary) | Faster and cleaner than yt-dlp for transcript-only operations |
| feedparser | 6.0.11+ | YouTube RSS feed parsing | Lightweight; parses channel RSS for new video monitoring |

### 4.5 Background Jobs and Scheduling

| Technology | Version | Purpose | Why Selected |
|---|---|---|---|
| Celery | 5.4+ | Task queue and worker management | Production-standard; integrates with Redis; retry/retry-backoff built-in |
| Redis | 7.0+ | Celery broker + result backend + application cache | Required by Celery; dual-purpose as cache layer |
| Celery Beat | (included) | Scheduled periodic tasks | Built into Celery; avoids separate scheduler dependency |

### 4.6 Media Processing

| Technology | Version | Purpose | Why Selected |
|---|---|---|---|
| FFmpeg | 8.x (system binary) | A/V muxing and format conversion | Required by yt-dlp for DASH format muxing; industry standard |

FFmpeg is installed as a system binary via `apt-get install -y ffmpeg` in the Dockerfile. No Python wrapper is used; yt-dlp invokes FFmpeg directly via subprocess.

### 4.7 Utilities and Infrastructure

| Technology | Version | Purpose | Why Selected |
|---|---|---|---|
| python-dotenv | 1.0+ | Environment variable management | Standard; loads `.env` into `os.environ` |
| httpx | 0.27+ | HTTP client for thumbnail downloads and RSS | Async-capable; used for non-yt-dlp HTTP needs |
| structlog | 24.0+ | Structured JSON logging | Consistent log format; Docker-friendly stdout JSON |
| pytest | 8.0+ | Test runner | Industry standard for Python |
| pytest-flask | 1.3+ | Flask test utilities | Test client and app context fixtures |
| Black | 24.0+ | Code formatter | Non-negotiable style consistency |
| Ruff | 0.5+ | Fast linter | Replaces flake8; faster; more rules |

### 4.8 Docker

| Image | Purpose |
|---|---|
| `python:3.12-slim` | Backend base image |
| `node:20-alpine` | Frontend build image |
| `nginx:alpine` | Frontend static file serving (production) |
| `mysql:8.0` | Database |
| `redis:7-alpine` | Job queue and cache |
| `brainicism/bgutil-ytdlp-pot-provider` | Optional PoToken sidecar |

---

## 5. Folder Structure

```
youtube-analyzer/
│
├── backend/                        # Python Flask application
│   ├── app/                        # Application package
│   │   ├── __init__.py             # Flask app factory (create_app())
│   │   ├── config.py               # Configuration classes (Dev/Prod/Test)
│   │   │
│   │   ├── models/                 # SQLAlchemy ORM models
│   │   │   ├── __init__.py
│   │   │   ├── channel.py          # Channel model
│   │   │   ├── video.py            # Video model
│   │   │   ├── transcript.py       # Transcript model
│   │   │   ├── comment.py          # Comment model
│   │   │   ├── playlist.py         # Playlist + PlaylistVideo models
│   │   │   ├── download.py         # DownloadHistory model
│   │   │   ├── search.py           # SearchHistory model
│   │   │   ├── snapshot.py         # ChannelSnapshot + VideoSnapshot models
│   │   │   ├── queue.py            # ProcessingQueue model
│   │   │   ├── settings.py         # UserSettings model
│   │   │   └── ai_analysis.py      # AIAnalysis model (future-ready)
│   │   │
│   │   ├── schemas/                # Marshmallow serialization schemas
│   │   │   ├── __init__.py
│   │   │   ├── channel_schema.py
│   │   │   ├── video_schema.py
│   │   │   ├── transcript_schema.py
│   │   │   ├── comment_schema.py
│   │   │   ├── playlist_schema.py
│   │   │   ├── download_schema.py
│   │   │   ├── search_schema.py
│   │   │   ├── job_schema.py
│   │   │   └── settings_schema.py
│   │   │
│   │   ├── controllers/            # Flask Blueprints (route handlers only)
│   │   │   ├── __init__.py
│   │   │   ├── channel_controller.py
│   │   │   ├── video_controller.py
│   │   │   ├── transcript_controller.py
│   │   │   ├── comment_controller.py
│   │   │   ├── playlist_controller.py
│   │   │   ├── download_controller.py
│   │   │   ├── search_controller.py
│   │   │   ├── analytics_controller.py
│   │   │   ├── job_controller.py
│   │   │   └── settings_controller.py
│   │   │
│   │   ├── services/               # Business logic layer
│   │   │   ├── __init__.py
│   │   │   ├── channel_service.py
│   │   │   ├── video_service.py
│   │   │   ├── transcript_service.py
│   │   │   ├── comment_service.py
│   │   │   ├── playlist_service.py
│   │   │   ├── download_service.py
│   │   │   ├── search_service.py
│   │   │   ├── analytics_service.py
│   │   │   ├── snapshot_service.py
│   │   │   ├── rss_service.py
│   │   │   ├── settings_service.py
│   │   │   └── queue_service.py
│   │   │
│   │   ├── repositories/           # Data access layer (SQLAlchemy queries)
│   │   │   ├── __init__.py
│   │   │   ├── channel_repository.py
│   │   │   ├── video_repository.py
│   │   │   ├── transcript_repository.py
│   │   │   ├── comment_repository.py
│   │   │   ├── playlist_repository.py
│   │   │   ├── download_repository.py
│   │   │   ├── search_repository.py
│   │   │   ├── snapshot_repository.py
│   │   │   ├── queue_repository.py
│   │   │   └── settings_repository.py
│   │   │
│   │   ├── extraction/             # yt-dlp and transcript-api wrappers
│   │   │   ├── __init__.py
│   │   │   ├── ytdlp_client.py     # yt-dlp wrapper with options management
│   │   │   ├── transcript_client.py # youtube-transcript-api wrapper
│   │   │   ├── rss_client.py       # feedparser/RSS fetching
│   │   │   ├── cookie_manager.py   # Cookie file management
│   │   │   └── bot_mitigation.py   # Player client rotation, PoToken provider
│   │   │
│   │   ├── jobs/                   # Celery task definitions
│   │   │   ├── __init__.py
│   │   │   ├── celery_app.py       # Celery application instance
│   │   │   ├── metadata_jobs.py    # Video/channel/playlist metadata extraction tasks
│   │   │   ├── transcript_jobs.py  # Transcript extraction tasks
│   │   │   ├── comment_jobs.py     # Comment extraction tasks
│   │   │   ├── download_jobs.py    # Download tasks (video, audio, subtitle, thumbnail)
│   │   │   ├── snapshot_jobs.py    # Scheduled snapshot creation tasks
│   │   │   ├── rss_jobs.py         # RSS monitoring tasks
│   │   │   └── maintenance_jobs.py # Cache cleanup, yt-dlp update check
│   │   │
│   │   ├── middleware/             # Flask middleware and hooks
│   │   │   ├── __init__.py
│   │   │   ├── error_handlers.py   # Global exception handler registration
│   │   │   ├── rate_limiter.py     # Flask-Limiter configuration
│   │   │   └── request_logger.py   # Per-request structured logging
│   │   │
│   │   ├── utils/                  # Shared utilities
│   │   │   ├── __init__.py
│   │   │   ├── url_parser.py       # YouTube URL normalization and ID extraction
│   │   │   ├── file_manager.py     # Disk operations, path validation, space check
│   │   │   ├── time_utils.py       # Date/time formatting helpers
│   │   │   ├── pagination.py       # Pagination helper (page/per_page → offset/limit)
│   │   │   └── thumbnail_utils.py  # Thumbnail URL construction, download
│   │   │
│   │   └── exceptions/             # Custom exception classes
│   │       ├── __init__.py
│   │       └── youtube_errors.py   # YouTubeRateLimitError, BotDetectedError, etc.
│   │
│   ├── migrations/                 # Alembic migration files (managed by Flask-Migrate)
│   │   ├── env.py
│   │   ├── alembic.ini
│   │   └── versions/               # Auto-generated migration scripts
│   │
│   ├── tests/                      # Test suite
│   │   ├── conftest.py             # Fixtures: test app, test DB, mock yt-dlp
│   │   ├── unit/
│   │   │   ├── test_services/
│   │   │   └── test_utils/
│   │   ├── integration/
│   │   │   ├── test_channels_api.py
│   │   │   ├── test_videos_api.py
│   │   │   ├── test_downloads_api.py
│   │   │   └── test_search_api.py
│   │   └── fixtures/
│   │       ├── ytdlp_video_response.json    # Sample yt-dlp output for mocking
│   │       ├── ytdlp_channel_response.json
│   │       └── transcript_response.json
│   │
│   ├── requirements.txt            # Production dependencies
│   ├── requirements-dev.txt        # Development dependencies (black, ruff, pytest)
│   ├── .env.example                # Environment variable template
│   ├── run.py                      # Development server entry point
│   └── wsgi.py                     # Gunicorn entry point
│
├── frontend/                       # React + Vite application
│   ├── src/
│   │   ├── main.jsx                # React entry point
│   │   ├── App.jsx                 # Root component + router setup
│   │   │
│   │   ├── pages/                  # Route-level page components
│   │   │   ├── Dashboard.jsx
│   │   │   ├── ChannelList.jsx
│   │   │   ├── ChannelDetail.jsx
│   │   │   ├── VideoDetail.jsx
│   │   │   ├── PlaylistDetail.jsx
│   │   │   ├── Search.jsx
│   │   │   ├── Downloader.jsx
│   │   │   ├── Jobs.jsx
│   │   │   ├── Settings.jsx
│   │   │   └── NotFound.jsx
│   │   │
│   │   ├── components/             # Reusable UI components
│   │   │   ├── layout/
│   │   │   │   ├── AppShell.jsx    # Top nav + sidebar + content area
│   │   │   │   ├── Sidebar.jsx
│   │   │   │   └── TopBar.jsx
│   │   │   ├── channel/
│   │   │   │   ├── ChannelCard.jsx
│   │   │   │   ├── ChannelHeader.jsx
│   │   │   │   └── ChannelStats.jsx
│   │   │   ├── video/
│   │   │   │   ├── VideoCard.jsx
│   │   │   │   ├── VideoGrid.jsx
│   │   │   │   ├── VideoTable.jsx
│   │   │   │   └── VideoMetaPanel.jsx
│   │   │   ├── transcript/
│   │   │   │   ├── TranscriptViewer.jsx
│   │   │   │   └── TranscriptSearch.jsx
│   │   │   ├── comments/
│   │   │   │   ├── CommentThread.jsx
│   │   │   │   └── CommentCard.jsx
│   │   │   ├── charts/
│   │   │   │   ├── GrowthChart.jsx      # Line chart for snapshots
│   │   │   │   ├── ViewsBarChart.jsx
│   │   │   │   └── DurationHistogram.jsx
│   │   │   ├── jobs/
│   │   │   │   ├── JobStatusBadge.jsx
│   │   │   │   ├── JobProgressBar.jsx
│   │   │   │   └── JobCard.jsx
│   │   │   ├── download/
│   │   │   │   ├── FormatSelector.jsx
│   │   │   │   ├── QualityPicker.jsx
│   │   │   │   └── DownloadButton.jsx
│   │   │   └── common/
│   │   │       ├── Button.jsx
│   │   │       ├── Input.jsx
│   │   │       ├── Modal.jsx
│   │   │       ├── Toast.jsx
│   │   │       ├── Spinner.jsx
│   │   │       ├── EmptyState.jsx
│   │   │       ├── ErrorBoundary.jsx
│   │   │       ├── Pagination.jsx
│   │   │       ├── Badge.jsx
│   │   │       ├── Tooltip.jsx
│   │   │       ├── ConfirmDialog.jsx
│   │   │       └── DataTable.jsx
│   │   │
│   │   ├── hooks/                  # Custom React hooks
│   │   │   ├── useChannel.js
│   │   │   ├── useVideo.js
│   │   │   ├── useTranscript.js
│   │   │   ├── useDownload.js
│   │   │   ├── useJobProgress.js   # SSE connection for job progress
│   │   │   ├── useSearch.js
│   │   │   ├── useSettings.js
│   │   │   └── useToast.js
│   │   │
│   │   ├── api/                    # Axios API layer
│   │   │   ├── client.js           # Axios instance with interceptors
│   │   │   ├── channels.js
│   │   │   ├── videos.js
│   │   │   ├── transcripts.js
│   │   │   ├── comments.js
│   │   │   ├── playlists.js
│   │   │   ├── downloads.js
│   │   │   ├── search.js
│   │   │   ├── analytics.js
│   │   │   ├── jobs.js
│   │   │   └── settings.js
│   │   │
│   │   ├── store/                  # Zustand stores
│   │   │   ├── uiStore.js          # Sidebar open, active page, toast queue
│   │   │   ├── settingsStore.js    # Cached settings for instant access
│   │   │   └── jobStore.js         # Active job tracking
│   │   │
│   │   └── utils/
│   │       ├── formatters.js       # Number formatting, duration, date display
│   │       ├── youtubeHelpers.js   # Thumbnail URL construction, video ID detection
│   │       └── constants.js        # API base URL, default values
│   │
│   ├── public/
│   │   └── favicon.ico
│   ├── index.html
│   ├── vite.config.js
│   ├── tailwind.config.js
│   ├── postcss.config.js
│   ├── .eslintrc.js
│   └── package.json
│
├── docker/                         # Docker configuration files
│   ├── backend.Dockerfile
│   ├── frontend.Dockerfile
│   ├── nginx.conf                  # Nginx config for frontend serving
│   └── wait-for-it.sh              # DB readiness check script
│
├── scripts/                        # Utility scripts
│   ├── init_db.py                  # Manual DB initialization helper
│   ├── update_ytdlp.sh             # yt-dlp update script
│   └── export_data.py              # Data export utility
│
├── docs/                           # Documentation
│   ├── API.md                      # API endpoint documentation
│   ├── DEPLOYMENT.md               # Deployment guide
│   ├── CONFIGURATION.md            # Environment variable reference
│   └── LEGAL.md                    # Terms of service notice
│
├── docker-compose.yml              # Full stack (backend + frontend + MySQL + Redis)
├── docker-compose.dev.yml          # Development overrides (volume mounts, hot reload)
├── .env.example                    # Root environment template
├── .gitignore
└── README.md
```

### Directory Purpose Reference

| Directory | Purpose |
|---|---|
| `backend/app/models/` | SQLAlchemy declarative models; no business logic; field definitions and relationships only |
| `backend/app/schemas/` | Marshmallow schemas for serialization, deserialization, and validation of all API inputs/outputs |
| `backend/app/controllers/` | Flask Blueprints; HTTP request/response only; delegates all logic to service layer; no DB access |
| `backend/app/services/` | Business logic; orchestrates repositories and extraction layer; all decision-making lives here |
| `backend/app/repositories/` | All SQLAlchemy query logic; no business decisions; accepts and returns model instances or dicts |
| `backend/app/extraction/` | All yt-dlp, youtube-transcript-api, and RSS interactions; wraps external tools with consistent interface |
| `backend/app/jobs/` | Celery task functions; thin wrappers that call services; manage job lifecycle |
| `backend/app/middleware/` | Flask before/after request hooks and error handler registration |
| `backend/app/utils/` | Stateless helper functions with no dependencies on models or services |
| `backend/app/exceptions/` | All custom exception classes used across the codebase |
| `frontend/src/pages/` | Route-level components; one per URL route; compose smaller components |
| `frontend/src/components/` | All reusable components; categorized by domain |
| `frontend/src/hooks/` | Custom hooks encapsulating TanStack Query calls and SSE logic |
| `frontend/src/api/` | Axios functions for every API endpoint; one file per resource |
| `frontend/src/store/` | Zustand stores for client-side state that isn't server state |

---

## 6. Backend Architecture

### 6.1 Application Factory Pattern

The Flask application is created using the application factory pattern. The `create_app(config_name)` function in `backend/app/__init__.py` accepts a configuration name (`development`, `production`, `testing`) and returns a configured Flask app instance.

The factory performs in this order:
1. Load configuration from `config.py` based on `config_name`
2. Initialize SQLAlchemy (via Flask-SQLAlchemy)
3. Initialize Flask-Migrate (Alembic)
4. Initialize Flask-CORS
5. Initialize Flask-Limiter (Redis-backed)
6. Register all Blueprints (controllers)
7. Register global error handlers
8. Register request logging middleware
9. Run `db.create_all()` in test mode; in production, Alembic handles migration

### 6.2 Configuration

Three configuration classes in `config.py`:

**DevelopmentConfig:**
- `DEBUG = True`
- `SQLALCHEMY_DATABASE_URI` from `DATABASE_URL` env var (default: `mysql+pymysql://root:password@localhost/youtube_analyzer`)
- `CELERY_BROKER_URL` from `REDIS_URL` env var (default: `redis://localhost:6379/0`)
- `SQLALCHEMY_ECHO = True` (log all SQL queries)

**ProductionConfig:**
- `DEBUG = False`
- Same env var pattern; no SQL echo
- `SECRET_KEY` must be explicitly set (raises error if absent)

**TestingConfig:**
- `TESTING = True`
- Uses in-memory SQLite: `sqlite:///:memory:`
- `CELERY_TASK_ALWAYS_EAGER = True` (tasks run synchronously in tests)
- Rate limiter disabled

All configuration values are read from environment variables. Defaults are provided for development convenience only.

**Complete environment variable reference:**

```
# Application
FLASK_ENV=development
SECRET_KEY=change-me-in-production
LOG_LEVEL=INFO

# Database
DATABASE_URL=mysql+pymysql://ytanalyzer:password@mysql:3306/youtube_analyzer

# Redis / Celery
REDIS_URL=redis://redis:6379/0
CELERY_RESULT_BACKEND=redis://redis:6379/1

# Storage
DOWNLOAD_DIR=/data/downloads
THUMBNAIL_DIR=/data/thumbnails

# yt-dlp
YTDLP_COOKIES_PATH=               # optional; path to cookies.txt
YTDLP_PROXY=                      # optional; e.g. socks5://127.0.0.1:1080
YTDLP_PLAYER_CLIENT=ios           # fallback client for bot detection
YTDLP_RATE_LIMIT=500K             # bytes/sec rate limit for downloads
POT_PROVIDER_URL=                 # optional; http://bgutil:4416

# Frontend
CORS_ORIGINS=http://localhost:5173,http://localhost:3000

# Feature flags
AUTO_EXTRACT_TRANSCRIPT=false
AUTO_EXTRACT_THUMBNAIL=true
RSS_POLL_INTERVAL=60
MAX_CONCURRENT_DOWNLOADS=2
```

### 6.3 Controller Layer

Every controller is a Flask Blueprint registered with a URL prefix. Controllers contain only:
- Route decoration
- Request parsing (using Marshmallow schemas for validation)
- Service method invocation
- Response serialization (using Marshmallow schemas for output)
- HTTP status code selection

Controllers never access repositories directly. Controllers never contain business logic.

**Blueprint registration in `__init__.py`:**
```
/api/channels    → channel_controller blueprint
/api/videos      → video_controller blueprint
/api/transcripts → transcript_controller blueprint
/api/comments    → comment_controller blueprint
/api/playlists   → playlist_controller blueprint
/api/downloads   → download_controller blueprint
/api/search      → search_controller blueprint
/api/analytics   → analytics_controller blueprint
/api/jobs        → job_controller blueprint
/api/settings    → settings_controller blueprint
```

**Request handling pattern in every controller:**
1. Receive `request.json` or `request.args`
2. Load and validate through Marshmallow schema → raises `ValidationError` on invalid input
3. Call the appropriate service method with validated data
4. Serialize service result through output Marshmallow schema
5. Return `jsonify(result), status_code`

### 6.4 Service Layer

Services contain all business logic. Each service has one corresponding repository it primarily uses, but may read from others.

**Service responsibilities:**
- Validation beyond schema rules (e.g., "does this channel already exist?")
- Orchestration of multiple repository calls within a transaction
- Queue job creation via QueueService
- Mapping between domain objects and yt-dlp output dictionaries
- Cache read/write decisions

**Key service design rules:**
- Services do not import Flask request/response objects
- Services are instantiated once and reused (not re-instantiated per request)
- Services accept simple Python types (strings, dicts, ints); never Flask request objects
- All database writes are wrapped in `db.session` transactions
- If a service method queues a background job, it returns the job_id immediately

**Dependency injection approach:**
Flask-SQLAlchemy provides `db.session` as the application-scoped session. Services import `db` from the app package. Repositories receive `db.session` via their constructor. This allows easy mocking in tests.

Example service method signature:
```
channel_service.add_channel(url: str, crawl_videos: bool = False) -> dict
  Returns: {"channel_id": str, "job_id": str, "status": "created"|"existing"}
```

### 6.5 Repository Layer

Repositories contain all SQLAlchemy query code. No business logic.

**Repository pattern:**
- One repository class per primary entity (ChannelRepository, VideoRepository, etc.)
- All methods accept and return model instances or plain dicts (never Flask objects)
- Pagination: all list methods accept `page: int, per_page: int` → return `{"items": [...], "total": int, "page": int, "per_page": int, "pages": int}`
- Filters: methods accept filter kwargs appropriate to the entity

**Example repository methods:**
```
ChannelRepository:
  get_by_id(channel_id: str) -> Channel | None
  get_by_handle(handle: str) -> Channel | None
  create(data: dict) -> Channel
  update(channel_id: str, data: dict) -> Channel
  delete(channel_id: str) -> bool
  list(page, per_page, filters) -> PaginatedResult
  get_with_snapshot_count(channel_id: str) -> dict
  get_monitored_channels() -> list[Channel]
```

### 6.6 Extraction Layer

The extraction layer (`backend/app/extraction/`) wraps external tools and provides a clean, consistent interface to the service layer.

**`ytdlp_client.py`** — The central wrapper for all yt-dlp operations.

Provides these methods:
- `extract_video_metadata(url: str) -> dict` — `skip_download=True`, returns full info dict
- `extract_channel_metadata(url: str) -> dict` — channel-level info
- `extract_flat_playlist(url: str, progress_callback=None) -> list[dict]` — flat-playlist extraction
- `extract_search_results(query: str, n: int = 20, search_type: str = "video") -> list[dict]`
- `extract_comments(url: str, max_comments: int = 500) -> list[dict]`
- `download_video(url: str, output_path: str, quality: str, format: str, progress_hook=None) -> str`
- `download_audio(url: str, output_path: str, format: str, quality: str, progress_hook=None) -> str`
- `download_subtitles(url: str, output_path: str, lang: str, format: str) -> list[str]`

The client applies these options on every call:
```python
base_opts = {
    "quiet": True,
    "no_warnings": True,
    "extractor_args": {"youtube": {"player_client": [settings.YTDLP_PLAYER_CLIENT]}},
    "ratelimit": settings.YTDLP_RATE_LIMIT,
}
if settings.YTDLP_COOKIES_PATH:
    base_opts["cookiefile"] = settings.YTDLP_COOKIES_PATH
if settings.YTDLP_PROXY:
    base_opts["proxy"] = settings.YTDLP_PROXY
```

The client catches yt-dlp exceptions and re-raises as application-specific exceptions:
- `yt_dlp.utils.DownloadError` with "Sign in" → `YouTubeBotDetectedError`
- `yt_dlp.utils.DownloadError` with "429" → `YouTubeRateLimitError`
- `yt_dlp.utils.DownloadError` with "unavailable" → `VideoUnavailableError`
- All others → `ExtractionFailedError`

**`transcript_client.py`** — Wrapper for youtube-transcript-api.

Methods:
- `fetch_transcript(video_id: str, lang: str = "en") -> dict` → `{segments, full_text, language, is_auto_generated}`
- `list_transcripts(video_id: str) -> list[dict]` → available languages
- `fetch_with_fallback(video_id: str, lang: str) -> dict` — try manual first, auto-generated as fallback

Catches `TranscriptsDisabled`, `NoTranscriptFound` → raises `TranscriptNotAvailableError`.

**`bot_mitigation.py`** — Player client rotation logic.

Maintains a list of client options to try in order: `["ios", "web_safari", "android", "web_embedded"]`. When `YouTubeBotDetectedError` is raised, the client rotates to the next option. Rotation state is stored in Redis (key: `ytdlp:current_client`). Resets to primary after 24 hours.

### 6.7 Background Workers (Celery)

Celery workers are started separately from the Flask application. The Celery app is defined in `backend/app/jobs/celery_app.py` and configured with the same Redis URL as the Flask app.

**Worker startup command:**
```
celery -A app.jobs.celery_app worker --concurrency=2 --loglevel=info
```

**Beat scheduler startup command:**
```
celery -A app.jobs.celery_app beat --loglevel=info
```

**Task categories and their retry policies:**

| Task Category | Max Retries | Initial Delay | Max Delay | On Failure |
|---|---|---|---|---|
| metadata_extract | 3 | 5s | 60s | Mark job failed |
| transcript_extract | 3 | 5s | 30s | Mark job failed; set has_transcript=false |
| comment_extract | 3 | 30s | 120s | Mark job failed; leave comment table empty |
| download | 2 | 10s | 30s | Mark job failed; clean temp file |
| channel_crawl | 2 | 10s | 60s | Mark job failed |
| snapshot | 0 | N/A | N/A | Log warning; skip |
| rss_check | 0 | N/A | N/A | Log warning; try next cycle |

**Progress reporting:**
All long-running tasks update the `ProcessingQueue` table's progress fields and publish to Redis channel `job:{job_id}:progress` for SSE delivery.

**Beat schedule (periodic tasks):**
```python
CELERY_BEAT_SCHEDULE = {
    "rss-monitor": {
        "task": "app.jobs.rss_jobs.check_all_rss_feeds",
        "schedule": crontab(minute="*/60"),   # configurable via RSS_POLL_INTERVAL
    },
    "daily-channel-snapshots": {
        "task": "app.jobs.snapshot_jobs.snapshot_all_channels",
        "schedule": crontab(hour=2, minute=0),  # 2 AM daily
    },
    "daily-video-snapshots": {
        "task": "app.jobs.snapshot_jobs.snapshot_tracked_videos",
        "schedule": crontab(hour=3, minute=0),  # 3 AM daily
    },
    "weekly-ytdlp-check": {
        "task": "app.jobs.maintenance_jobs.check_ytdlp_version",
        "schedule": crontab(day_of_week=0, hour=4, minute=0),
    },
    "cleanup-expired-cache": {
        "task": "app.jobs.maintenance_jobs.cleanup_expired_search_cache",
        "schedule": crontab(hour=1, minute=0),
    },
}
```

### 6.8 Caching Layer

Redis serves dual duty as Celery broker and application cache. All cache keys follow the pattern `{resource}:{id}:{field}` with TTL set per resource type.

Cache operations are handled by a `CacheService` utility class that wraps Redis operations with JSON serialization and TTL management.

See Section 11 for the complete caching strategy.

### 6.9 Download Manager

The download system tracks all downloads through the `DownloadHistory` table and a Celery worker queue. The `DownloadService` orchestrates this flow:

1. Validate video exists and is available
2. Check if already downloaded (check `download_history` for matching video_id + type + quality)
3. Check available disk space (`file_manager.get_available_space()`)
4. Create `DownloadHistory` record with `status=pending`
5. Queue Celery task (`download_jobs.download_video_task`)
6. Return job_id immediately

The Celery download task:
1. Updates status to `downloading`
2. Constructs output path: `{DOWNLOAD_DIR}/{type}/{video_id}/{video_id}_{quality}.{ext}`
3. Calls `ytdlp_client.download_video()` with progress_hook that:
   - Updates `DownloadHistory.progress_percent`
   - Publishes progress to Redis for SSE
4. On completion: updates `DownloadHistory` with file_path, file_size_bytes, status=complete
5. On failure: deletes partial temp file; updates status=failed with error_message

Maximum concurrent downloads: enforced via Celery worker concurrency and a Redis semaphore (`download:semaphore` with max count from settings).

### 6.10 SSE (Server-Sent Events) Implementation

SSE is implemented using Flask's streaming response pattern. The job controller has a route:

```
GET /api/jobs/{job_id}/stream
```

This route:
1. Opens a Redis Pub/Sub subscription to channel `job:{job_id}:progress`
2. Streams events to the client until `complete` or `error` event
3. Sends a heartbeat comment (`: keepalive\n\n`) every 15 seconds to prevent proxy timeouts
4. Closes cleanly on client disconnect (via generator `try/finally`)

Response headers: `Content-Type: text/event-stream`, `Cache-Control: no-cache`, `X-Accel-Buffering: no` (disables Nginx buffering for SSE).

### 6.11 Logging

All logging uses Python's standard `logging` module with a JSON formatter configured in `create_app()`. The formatter outputs one JSON object per line to stdout.

Log record fields:
```json
{
  "timestamp": "2026-07-28T12:00:00.000Z",
  "level": "INFO",
  "logger": "app.services.channel_service",
  "message": "Channel crawl completed",
  "job_id": "abc123",
  "channel_id": "UCxxxxxx",
  "video_count": 247,
  "duration_ms": 45231
}
```

yt-dlp output is captured by setting `quiet=True` and providing a custom logger that routes yt-dlp's internal messages to the application logger at DEBUG level.

### 6.12 Global Error Handling

Registered in `middleware/error_handlers.py` via `app.register_error_handler()`.

| Exception | HTTP Status | Response Body |
|---|---|---|
| `ValidationError` (Marshmallow) | 422 | `{"errors": {field: [messages]}}` |
| `VideoUnavailableError` | 404 | `{"error": "Video unavailable", "code": "VIDEO_UNAVAILABLE"}` |
| `TranscriptNotAvailableError` | 409 | `{"error": "No transcript available", "available_languages": [...]}` |
| `YouTubeRateLimitError` | 503 | `{"error": "YouTube rate limit hit", "retry_after": 30}` |
| `YouTubeBotDetectedError` | 503 | `{"error": "Bot detection triggered", "code": "BOT_DETECTED"}` |
| `ExtractionFailedError` | 500 | `{"error": "Extraction failed", "detail": "..."}` |
| `404` (Flask default) | 404 | `{"error": "Not found"}` |
| `Exception` (unhandled) | 500 | `{"error": "Internal server error"}` (hides stack trace in production) |

All error responses include a `request_id` field (UUID generated per request in `request_logger.py`).
