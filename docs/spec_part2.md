---

## 7. Frontend Architecture

### 7.1 Application Entry Point

The React application is bootstrapped in `frontend/src/main.jsx`. It wraps the root `App` component with:
1. `QueryClientProvider` (TanStack Query) — configured with global defaults
2. `BrowserRouter` (React Router) — SPA routing
3. `ToastProvider` — global notification context

TanStack Query global configuration:
- `staleTime`: 60,000ms (1 minute) — server data considered fresh for 1 minute before background refetch
- `gcTime`: 300,000ms (5 minutes) — unused cache entries retained for 5 minutes
- `retry`: 1 — failed queries retried once before showing error
- `refetchOnWindowFocus`: false — prevents refetch on tab switch

### 7.2 Routing Structure

All routes defined in `App.jsx` using React Router v6 `<Routes>` and `<Route>` elements. The `AppShell` layout wraps all authenticated routes, providing the sidebar and top navigation.

```
/                           → Dashboard (redirect to /dashboard)
/dashboard                  → Dashboard.jsx
/channels                   → ChannelList.jsx
/channels/:channelId        → ChannelDetail.jsx
/channels/:channelId/videos → ChannelDetail.jsx (videos tab active)
/videos/:videoId            → VideoDetail.jsx
/playlists                  → PlaylistList.jsx (inline on Channel pages)
/playlists/:playlistId      → PlaylistDetail.jsx
/search                     → Search.jsx
/downloader                 → Downloader.jsx
/jobs                       → Jobs.jsx
/settings                   → Settings.jsx
*                           → NotFound.jsx
```

### 7.3 State Management Architecture

Two distinct state layers are used and kept separate:

**Server State — TanStack Query:**
All data fetched from the backend API. TanStack Query manages loading, error, caching, background refetching, and invalidation. Custom hooks in `frontend/src/hooks/` wrap TanStack Query `useQuery` and `useMutation` calls. No server data is stored in Zustand.

**Client/UI State — Zustand:**
UI state that is not server data. Three stores:

`uiStore.js`:
- `sidebarOpen: boolean` — sidebar collapsed state on mobile
- `activeJobCount: number` — badge count on Jobs nav item
- `toasts: Toast[]` — active toast notifications queue

`settingsStore.js`:
- `settings: object` — cached copy of user settings (fetched once on app load; invalidated on settings update)
- `isLoaded: boolean`

`jobStore.js`:
- `activeJobs: { [job_id]: JobProgress }` — tracks jobs the current browser session submitted
- Methods: `addJob(job_id, type)`, `updateJob(job_id, progress)`, `removeJob(job_id)`

### 7.4 API Layer

All API calls live in `frontend/src/api/`. A single Axios instance is configured in `client.js` with:
- `baseURL`: from `constants.js` (defaults to `http://localhost:5000/api`)
- Request interceptor: attaches `Content-Type: application/json`
- Response interceptor: on 5xx error → shows error toast; on 422 → surfaces field errors; on network error → shows "Server unavailable" toast

Each resource file exports named async functions. Example from `channels.js`:
```
getChannels(params)         → GET /channels
getChannel(channelId)       → GET /channels/:id
addChannel(data)            → POST /channels
refreshChannel(channelId)   → POST /channels/:id/refresh
crawlChannel(channelId, opts) → POST /channels/:id/crawl
deleteChannel(channelId)    → DELETE /channels/:id
getChannelAnalytics(id, range) → GET /channels/:id/analytics
```

### 7.5 Custom Hooks

Every domain entity has a corresponding hook file. Hooks encapsulate all TanStack Query `useQuery`/`useMutation` calls for that entity.

**`useChannel.js`** exports:
- `useChannels(filters, pagination)` — paginated channel list query
- `useChannel(channelId)` — single channel detail query
- `useAddChannel()` — mutation; invalidates channel list on success
- `useRefreshChannel()` — mutation; invalidates channel detail on success
- `useCrawlChannel()` — mutation; adds job to jobStore on success
- `useDeleteChannel()` — mutation; invalidates channel list on success
- `useChannelAnalytics(channelId, dateRange)` — analytics time-series query

**`useJobProgress.js`** — Special hook for SSE:
- Accepts `job_id`
- Opens `EventSource` to `/api/jobs/{job_id}/stream`
- Returns `{progress, status, error, isComplete}`
- Cleans up EventSource on unmount
- Updates `jobStore` with progress data

### 7.6 Component Architecture

Components follow these rules:
- Components are pure UI renderers — no direct API calls
- All data comes from hooks (which call the API layer)
- Components receive data and callbacks as props
- Complex components are broken into sub-components in the same domain directory
- No component file exceeds 200 lines; extract sub-components if approaching limit

**Component categories:**

*Layout components* (`components/layout/`):
`AppShell` renders the full application chrome: `<TopBar>` (search bar, job indicator, settings link) + `<Sidebar>` (navigation links with icons) + `<main>` content area. The sidebar is collapsible. Active route is detected via React Router's `useLocation`.

*Common components* (`components/common/`):
All generic UI primitives. These have no knowledge of the domain (channels, videos, etc.). They are styled with Tailwind. Key components:

`DataTable` — A flexible table component accepting `columns` (array of `{key, header, render, sortable}`) and `data` (array). Handles empty state, loading skeleton rows, and optional row click handler.

`Pagination` — Page number navigation; accepts `total`, `page`, `perPage`, `onChange`.

`EmptyState` — Centered illustration + title + description + optional CTA button. Used on every list page when no data exists.

`ErrorBoundary` — Class component; catches render errors; displays error message + "Reload" button.

`Modal` — Portal-based modal dialog with backdrop. Accepts `isOpen`, `onClose`, `title`, `children`.

`ConfirmDialog` — Specialization of Modal for destructive actions. Accept/Cancel buttons.

`Toast` — Individual toast notification. Severity: success (green), error (red), warning (yellow), info (blue). Auto-dismisses after 4 seconds. `useToast` hook triggers them.

`Badge` — Small status pill. Variants: `success`, `error`, `warning`, `neutral`, `blue`.

### 7.7 Page Architecture

Each page component follows this structure:
1. Call hooks to fetch data and get mutation functions
2. Define event handlers that call mutations
3. Render layout with components, passing data and handlers as props
4. Handle loading state (show skeleton or spinner)
5. Handle error state (show error message with retry button)
6. Handle empty state (show EmptyState component)

Pages never make direct API calls. All API interaction goes through hooks.

### 7.8 Theme and Styling

**Tailwind CSS** is the only styling mechanism. No CSS modules, no styled-components, no inline style objects (except for dynamic values like chart colors).

**Color palette** defined in `tailwind.config.js`:
- Primary: Indigo (`indigo-600` active, `indigo-700` hover)
- Danger: Red (`red-600`)
- Success: Green (`green-600`)
- Warning: Amber (`amber-500`)
- Neutral backgrounds: `gray-50` (page), `white` (card), `gray-100` (row hover)
- Text: `gray-900` (primary), `gray-600` (secondary), `gray-400` (placeholder)
- Border: `gray-200`

**Dark mode:** Not implemented in Phase 1. Tailwind `dark:` classes may be added in future phases without architectural change.

**Typography:**
- Font family: `Inter` (loaded via Google Fonts in `index.html`)
- Heading: `text-2xl font-semibold text-gray-900`
- Subheading: `text-lg font-medium text-gray-800`
- Body: `text-sm text-gray-700`
- Secondary: `text-xs text-gray-500`

### 7.9 Loading and Error States

Every data-fetching page must handle three states:

**Loading:** Show skeleton UI (gray animated placeholder blocks matching the shape of the loaded content). Use Tailwind `animate-pulse` on placeholder elements. Never show a full-page spinner.

**Error:** Show an inline error panel with the error message and a "Try Again" button that calls `refetch()` from TanStack Query.

**Empty:** Show the `EmptyState` component with an appropriate icon, title, description, and CTA button (e.g., "Add Your First Channel").

### 7.10 Notifications

Toast notifications are triggered via `useToast()` hook anywhere in the component tree. The `ToastProvider` in `main.jsx` renders the toast queue in a fixed overlay (bottom-right corner).

Success toasts are shown:
- Channel added successfully
- Download queued successfully
- Settings saved
- Transcript extracted

Error toasts are shown:
- API errors (from Axios response interceptor)
- Validation errors (listed as bullet points)
- Job failures (detected via SSE stream)

### 7.11 Charts

All charts use **Recharts**. Charts are wrapped in `components/charts/` with consistent styling applied inside the wrapper.

**GrowthChart.jsx:** `<LineChart>` with `<XAxis>` (date), `<YAxis>` (value), `<Tooltip>`, `<Legend>`, `<Line>`. Used for subscriber and view count over time.

**ViewsBarChart.jsx:** `<BarChart>` showing top videos by views. Horizontal bars. Tooltip on hover shows full title and view count.

**DurationHistogram.jsx:** `<BarChart>` with buckets: 0-1min, 1-5min, 5-10min, 10-20min, 20-60min, 60min+. Shows distribution of video lengths for a channel.

All chart containers set `width="100%"` and fixed `height` (300px default). Charts are wrapped in `<ResponsiveContainer>` for responsive sizing.

---

## 8. Database Design

### 8.1 Engine and Configuration

**Database:** MySQL 8.0  
**ORM:** SQLAlchemy 2.0 (declarative base)  
**Driver:** PyMySQL 1.1+  
**Migrations:** Alembic via Flask-Migrate

MySQL connection options applied globally:
- `charset=utf8mb4` — full Unicode including emoji
- `collation=utf8mb4_unicode_ci` — case-insensitive Unicode collation
- `pool_pre_ping=True` — verify connections before use (handles dropped connections)
- `pool_recycle=3600` — recycle connections after 1 hour (MySQL default timeout is 8 hours)
- `pool_size=10` — connection pool size
- `max_overflow=5` — burst connections above pool_size

### 8.2 Table: `channels`

**Purpose:** Stores all extracted public metadata for a YouTube channel.

| Column | Type | Nullable | Constraints | Notes |
|---|---|---|---|---|
| `channel_id` | VARCHAR(64) | NO | PRIMARY KEY | YouTube UC-prefixed ID |
| `handle` | VARCHAR(100) | YES | INDEX | @handle username |
| `display_name` | VARCHAR(255) | NO | — | Channel display name |
| `description` | MEDIUMTEXT | YES | FULLTEXT INDEX | Full channel description |
| `subscriber_count` | BIGINT | YES | — | Nullable: sometimes absent/rounded |
| `video_count` | INT | YES | — | Total public videos |
| `total_view_count` | BIGINT | YES | — | Lifetime channel views |
| `join_date` | DATE | YES | — | Channel creation date; frequently absent |
| `country` | VARCHAR(10) | YES | — | ISO country code |
| `avatar_url` | TEXT | YES | — | CDN URL; expires |
| `banner_url` | TEXT | YES | — | CDN URL; expires; may be absent |
| `is_verified` | BOOLEAN | NO | DEFAULT FALSE | Verification badge |
| `external_links` | JSON | YES | — | Array of {title, url} objects |
| `rss_monitoring` | BOOLEAN | NO | DEFAULT FALSE | Whether RSS monitoring is active |
| `last_crawled_at` | DATETIME | YES | INDEX | Timestamp of last full crawl |
| `created_at` | DATETIME | NO | DEFAULT CURRENT_TIMESTAMP | — |
| `updated_at` | DATETIME | NO | ON UPDATE CURRENT_TIMESTAMP | — |

**Indexes:** PRIMARY KEY on `channel_id`; INDEX on `handle`; INDEX on `last_crawled_at`; FULLTEXT on `description` (for internal search); INDEX on `rss_monitoring` (for monitoring queries).

**Relationships:** One channel has many videos, playlists, channel_snapshots.

---

### 8.3 Table: `videos`

**Purpose:** Stores all publicly extractable metadata for a YouTube video.

| Column | Type | Nullable | Constraints | Notes |
|---|---|---|---|---|
| `video_id` | VARCHAR(20) | NO | PRIMARY KEY | YouTube 11-char video ID |
| `channel_id` | VARCHAR(64) | YES | FK → channels; INDEX | Nullable for orphan videos |
| `title` | VARCHAR(500) | NO | FULLTEXT INDEX | — |
| `description` | MEDIUMTEXT | YES | FULLTEXT INDEX | Full video description |
| `upload_date` | DATE | YES | INDEX | — |
| `duration_seconds` | INT | YES | — | — |
| `view_count` | BIGINT | YES | INDEX | — |
| `like_count` | BIGINT | YES | — | Nullable; hidden on some videos |
| `comment_count` | INT | YES | — | Nullable |
| `tags` | JSON | YES | — | Array of strings |
| `categories` | JSON | YES | — | Array of strings |
| `language` | VARCHAR(10) | YES | — | BCP-47 language code |
| `age_limit` | INT | NO | DEFAULT 0 | 0=none, 18=restricted |
| `availability` | VARCHAR(50) | YES | INDEX | public, unlisted, private, premium |
| `is_live` | BOOLEAN | NO | DEFAULT FALSE | — |
| `was_live` | BOOLEAN | NO | DEFAULT FALSE | — |
| `live_status` | VARCHAR(30) | YES | — | not_live, is_live, post_live, etc. |
| `is_short` | BOOLEAN | NO | DEFAULT FALSE | INDEX; YouTube Shorts |
| `chapter_data` | JSON | YES | — | Array of {title, start_time, end_time} |
| `heatmap_data` | JSON | YES | — | Array of {start_time, end_time, value} |
| `thumbnail_url` | TEXT | YES | — | Highest resolution CDN URL |
| `thumbnail_urls` | JSON | YES | — | All available sizes |
| `formats_available` | JSON | YES | — | Array of format specs from yt-dlp |
| `has_transcript` | BOOLEAN | YES | INDEX | NULL=unknown, TRUE/FALSE=checked |
| `comments_disabled` | BOOLEAN | NO | DEFAULT FALSE | — |
| `last_extracted_at` | DATETIME | YES | INDEX | — |
| `created_at` | DATETIME | NO | DEFAULT CURRENT_TIMESTAMP | — |
| `updated_at` | DATETIME | NO | ON UPDATE CURRENT_TIMESTAMP | — |

**Indexes:** PRIMARY KEY on `video_id`; FK INDEX on `channel_id`; INDEX on `upload_date`; INDEX on `view_count`; INDEX on `availability`; INDEX on `is_short`; INDEX on `has_transcript`; INDEX on `last_extracted_at`; FULLTEXT INDEX on `(title, description)` combined.

**Relationships:** Belongs to one channel (nullable); has many transcripts, comments, download_history entries, video_snapshots; belongs to many playlists via playlist_videos.

---

### 8.4 Table: `transcripts`

**Purpose:** Time-aligned transcript segments for a video in a specific language.

| Column | Type | Nullable | Constraints | Notes |
|---|---|---|---|---|
| `id` | BIGINT | NO | PRIMARY KEY AUTO_INCREMENT | — |
| `video_id` | VARCHAR(20) | NO | FK → videos; INDEX | — |
| `language_code` | VARCHAR(10) | NO | — | e.g. "en", "es-419" |
| `is_auto_generated` | BOOLEAN | NO | DEFAULT FALSE | — |
| `is_translated` | BOOLEAN | NO | DEFAULT FALSE | — |
| `source_language_code` | VARCHAR(10) | YES | — | Original language if translated |
| `segments` | MEDIUMTEXT | NO | — | JSON array of {text, start, duration} stored as TEXT for MySQL |
| `full_text` | MEDIUMTEXT | NO | FULLTEXT INDEX | Concatenated transcript text |
| `word_count` | INT | YES | — | — |
| `extracted_at` | DATETIME | NO | — | — |

**Unique constraint:** `UNIQUE(video_id, language_code, is_translated, source_language_code)` — prevents duplicate transcripts for same video+language combination.

**Indexes:** FK INDEX on `video_id`; FULLTEXT INDEX on `full_text`; Composite INDEX on `(video_id, language_code)`.

**Note on segments storage:** MySQL JSON column type would be ideal but MEDIUMTEXT with application-level JSON parsing is used for maximum compatibility across MySQL versions. The service layer handles serialization/deserialization.

---

### 8.5 Table: `comments`

**Purpose:** Individual comments and replies for a video.

| Column | Type | Nullable | Constraints | Notes |
|---|---|---|---|---|
| `comment_id` | VARCHAR(64) | NO | PRIMARY KEY | YouTube comment ID |
| `video_id` | VARCHAR(20) | NO | FK → videos; INDEX | — |
| `parent_comment_id` | VARCHAR(64) | YES | FK → comments(comment_id); INDEX | NULL for top-level |
| `author_display_name` | VARCHAR(255) | YES | — | — |
| `author_channel_id` | VARCHAR(64) | YES | INDEX | — |
| `author_channel_url` | TEXT | YES | — | — |
| `text` | TEXT | NO | FULLTEXT INDEX | Comment text |
| `like_count` | INT | NO | DEFAULT 0 | — |
| `reply_count` | INT | YES | — | Only on top-level comments |
| `is_creator_comment` | BOOLEAN | NO | DEFAULT FALSE | — |
| `is_pinned` | BOOLEAN | NO | DEFAULT FALSE | — |
| `published_at` | DATETIME | YES | INDEX | — |
| `updated_at` | DATETIME | YES | — | — |
| `created_at` | DATETIME | NO | DEFAULT CURRENT_TIMESTAMP | — |

**Indexes:** PRIMARY KEY on `comment_id`; FK INDEX on `video_id`; FK INDEX on `parent_comment_id`; INDEX on `author_channel_id`; INDEX on `published_at`; FULLTEXT INDEX on `text`.

---

### 8.6 Table: `playlists`

| Column | Type | Nullable | Constraints | Notes |
|---|---|---|---|---|
| `playlist_id` | VARCHAR(64) | NO | PRIMARY KEY | YouTube PL-prefixed playlist ID |
| `channel_id` | VARCHAR(64) | YES | FK → channels; INDEX | Nullable for non-channel playlists |
| `title` | VARCHAR(500) | NO | — | — |
| `description` | MEDIUMTEXT | YES | — | — |
| `thumbnail_url` | TEXT | YES | — | — |
| `video_count` | INT | YES | — | Last known count |
| `privacy_status` | VARCHAR(20) | YES | — | public, unlisted |
| `uploader` | VARCHAR(255) | YES | — | Channel display name |
| `last_crawled_at` | DATETIME | YES | — | — |
| `created_at` | DATETIME | NO | DEFAULT CURRENT_TIMESTAMP | — |
| `updated_at` | DATETIME | NO | ON UPDATE CURRENT_TIMESTAMP | — |

---

### 8.7 Table: `playlist_videos`

**Purpose:** Junction table preserving ordinal video positions within a playlist.

| Column | Type | Nullable | Constraints | Notes |
|---|---|---|---|---|
| `id` | BIGINT | NO | PRIMARY KEY AUTO_INCREMENT | — |
| `playlist_id` | VARCHAR(64) | NO | FK → playlists; INDEX | — |
| `video_id` | VARCHAR(20) | NO | FK → videos; INDEX | — |
| `position` | INT | NO | — | 0-indexed ordinal position |
| `added_at` | DATETIME | NO | DEFAULT CURRENT_TIMESTAMP | — |

**Unique constraint:** `UNIQUE(playlist_id, video_id)`.  
**Index:** Composite INDEX on `(playlist_id, position)` for ordered retrieval.

---

### 8.8 Table: `download_history`

| Column | Type | Nullable | Constraints | Notes |
|---|---|---|---|---|
| `id` | BIGINT | NO | PRIMARY KEY AUTO_INCREMENT | — |
| `video_id` | VARCHAR(20) | NO | FK → videos; INDEX | — |
| `download_type` | ENUM('video','audio','subtitle','thumbnail') | NO | INDEX | — |
| `format_id` | VARCHAR(50) | YES | — | yt-dlp format ID |
| `quality` | VARCHAR(20) | YES | — | e.g. "1080p", "best", "192k" |
| `file_extension` | VARCHAR(10) | YES | — | mp4, mp3, srt, etc. |
| `file_path` | TEXT | YES | — | Absolute path on disk |
| `file_size_bytes` | BIGINT | YES | — | Final file size |
| `status` | ENUM('pending','downloading','complete','failed','cancelled') | NO | INDEX | — |
| `progress_percent` | TINYINT | YES | — | 0–100 |
| `error_message` | TEXT | YES | — | Full error if status=failed |
| `job_id` | VARCHAR(64) | YES | FK → processing_queue(id); INDEX | Celery task ID |
| `started_at` | DATETIME | YES | — | — |
| `completed_at` | DATETIME | YES | — | — |
| `created_at` | DATETIME | NO | DEFAULT CURRENT_TIMESTAMP | — |

**Indexes:** FK INDEX on `video_id`; INDEX on `status`; INDEX on `download_type`; INDEX on `created_at` DESC.

---

### 8.9 Table: `search_history`

| Column | Type | Nullable | Constraints | Notes |
|---|---|---|---|---|
| `id` | BIGINT | NO | PRIMARY KEY AUTO_INCREMENT | — |
| `query` | VARCHAR(500) | NO | INDEX | — |
| `search_type` | ENUM('video','channel','playlist') | NO | — | — |
| `result_video_ids` | TEXT | YES | — | JSON array of video_id strings |
| `result_count` | INT | YES | — | — |
| `executed_at` | DATETIME | NO | INDEX | — |
| `expires_at` | DATETIME | NO | INDEX | Cache expiry; 1 hour default |

**Composite unique index:** `UNIQUE(query, search_type)` — ensures one cached result per query+type combination.

---

### 8.10 Table: `channel_snapshots`

| Column | Type | Nullable | Constraints | Notes |
|---|---|---|---|---|
| `id` | BIGINT | NO | PRIMARY KEY AUTO_INCREMENT | — |
| `channel_id` | VARCHAR(64) | NO | FK → channels; INDEX | — |
| `subscriber_count` | BIGINT | YES | — | — |
| `video_count` | INT | YES | — | — |
| `total_view_count` | BIGINT | YES | — | — |
| `snapshot_date` | DATE | NO | INDEX | Date of observation |

**Unique constraint:** `UNIQUE(channel_id, snapshot_date)` — one snapshot per channel per day. INSERT IGNORE on duplicate.

**Index:** Composite INDEX on `(channel_id, snapshot_date)` for range queries.

---

### 8.11 Table: `video_snapshots`

| Column | Type | Nullable | Constraints | Notes |
|---|---|---|---|---|
| `id` | BIGINT | NO | PRIMARY KEY AUTO_INCREMENT | — |
| `video_id` | VARCHAR(20) | NO | FK → videos; INDEX | — |
| `view_count` | BIGINT | YES | — | — |
| `like_count` | BIGINT | YES | — | — |
| `comment_count` | INT | YES | — | — |
| `snapshot_date` | DATE | NO | INDEX | — |

**Unique constraint:** `UNIQUE(video_id, snapshot_date)`.

**Note:** Not all videos are snapshot-tracked. The scheduler tracks only videos belonging to monitored channels plus any video explicitly bookmarked by the user (future feature). Initially: snapshot all videos from channels with `rss_monitoring=TRUE`.

---

### 8.12 Table: `processing_queue`

| Column | Type | Nullable | Constraints | Notes |
|---|---|---|---|---|
| `id` | VARCHAR(64) | NO | PRIMARY KEY | Celery task UUID |
| `job_type` | VARCHAR(50) | NO | INDEX | metadata_extract, transcript_extract, comment_extract, download, channel_crawl, playlist_crawl |
| `target_url` | TEXT | YES | — | YouTube URL being processed |
| `target_id` | VARCHAR(64) | YES | INDEX | video_id, channel_id, or playlist_id |
| `priority` | TINYINT | NO | DEFAULT 5 | 1=highest, 10=lowest |
| `status` | ENUM('queued','processing','complete','failed','cancelled','retrying') | NO | INDEX | — |
| `progress_percent` | TINYINT | YES | — | 0–100 |
| `current_operation` | VARCHAR(255) | YES | — | Human-readable progress description |
| `retry_count` | TINYINT | NO | DEFAULT 0 | — |
| `max_retries` | TINYINT | NO | DEFAULT 3 | — |
| `error_message` | MEDIUMTEXT | YES | — | Full error + traceback |
| `job_payload` | TEXT | YES | — | JSON: additional parameters passed to task |
| `result_data` | TEXT | YES | — | JSON: task result summary |
| `created_at` | DATETIME | NO | DEFAULT CURRENT_TIMESTAMP | INDEX |
| `started_at` | DATETIME | YES | — | — |
| `completed_at` | DATETIME | YES | — | — |
| `next_retry_at` | DATETIME | YES | INDEX | For retry scheduling |

**Indexes:** INDEX on `status`; INDEX on `job_type`; INDEX on `target_id`; INDEX on `created_at` DESC; INDEX on `next_retry_at`.

**Retention policy:** Jobs with status=complete or status=cancelled older than 30 days are deleted by the weekly maintenance job. Jobs with status=failed are retained for 90 days.

---

### 8.13 Table: `user_settings`

| Column | Type | Nullable | Constraints | Notes |
|---|---|---|---|---|
| `id` | INT | NO | PRIMARY KEY DEFAULT 1 | Single-row table; always id=1 |
| `download_dir` | VARCHAR(500) | NO | DEFAULT '/data/downloads' | — |
| `default_video_quality` | VARCHAR(10) | NO | DEFAULT '1080p' | — |
| `default_audio_format` | VARCHAR(10) | NO | DEFAULT 'mp3' | — |
| `default_audio_quality` | VARCHAR(10) | NO | DEFAULT '192k' | — |
| `auto_extract_transcript` | BOOLEAN | NO | DEFAULT FALSE | — |
| `auto_extract_comments` | BOOLEAN | NO | DEFAULT FALSE | — |
| `auto_extract_thumbnail` | BOOLEAN | NO | DEFAULT TRUE | — |
| `rss_poll_interval_minutes` | INT | NO | DEFAULT 60 | — |
| `max_concurrent_downloads` | INT | NO | DEFAULT 2 | — |
| `max_comments_per_video` | INT | NO | DEFAULT 500 | — |
| `yt_dlp_rate_limit` | VARCHAR(20) | NO | DEFAULT '500K' | — |
| `yt_dlp_cookies_path` | VARCHAR(500) | YES | — | — |
| `yt_dlp_proxy` | VARCHAR(500) | YES | — | — |
| `yt_dlp_player_client` | VARCHAR(20) | NO | DEFAULT 'ios' | — |
| `pot_provider_url` | VARCHAR(500) | YES | — | — |
| `metadata_cache_ttl_hours` | INT | NO | DEFAULT 24 | — |
| `snapshot_enabled` | BOOLEAN | NO | DEFAULT TRUE | — |
| `updated_at` | DATETIME | NO | ON UPDATE CURRENT_TIMESTAMP | — |

**Design:** Single-row table (always id=1). Application upserts this row on startup if absent with all defaults. SettingsService reads this row and caches it in Redis for 1 hour.

---

### 8.14 Table: `ai_analysis`

**Purpose:** Future-ready table for AI-generated analysis of videos. Not used in Phase 1 but present in schema from initial migration.

| Column | Type | Nullable | Constraints | Notes |
|---|---|---|---|---|
| `id` | BIGINT | NO | PRIMARY KEY AUTO_INCREMENT | — |
| `video_id` | VARCHAR(20) | NO | FK → videos; INDEX | — |
| `analysis_type` | VARCHAR(50) | NO | INDEX | summary, sentiment, topics, keywords, qa |
| `model_used` | VARCHAR(100) | YES | — | e.g. "claude-sonnet-4-6" |
| `input_source` | VARCHAR(20) | YES | — | transcript, comments, metadata |
| `result` | MEDIUMTEXT | YES | — | JSON analysis output |
| `token_count_input` | INT | YES | — | — |
| `token_count_output` | INT | YES | — | — |
| `analyzed_at` | DATETIME | NO | — | — |
| `schema_version` | INT | NO | DEFAULT 1 | For result schema migrations |

**Unique constraint:** `UNIQUE(video_id, analysis_type, model_used)`.

---

## 9. API Design

All endpoints are prefixed with `/api`. All responses are JSON. All list endpoints support pagination. All timestamps in ISO 8601 format (UTC).

**Standard pagination parameters:** `?page=1&per_page=20` (max per_page: 100)

**Standard paginated response envelope:**
```json
{
  "items": [...],
  "total": 247,
  "page": 1,
  "per_page": 20,
  "pages": 13
}
```

**Standard error response:**
```json
{
  "error": "Human-readable message",
  "code": "MACHINE_READABLE_CODE",
  "details": {},
  "request_id": "uuid"
}
```

---

### 9.1 Channel Endpoints

#### `GET /api/channels`
List all tracked channels.

**Query params:** `page`, `per_page`, `search` (name/handle), `sort` (name|subscriber_count|last_crawled_at), `order` (asc|desc), `monitoring` (boolean filter)

**Response 200:**
```json
{
  "items": [
    {
      "channel_id": "UCxxxxxx",
      "handle": "@channelname",
      "display_name": "Channel Name",
      "subscriber_count": 1500000,
      "video_count": 342,
      "avatar_url": "https://...",
      "is_verified": true,
      "rss_monitoring": false,
      "last_crawled_at": "2026-07-28T12:00:00Z",
      "created_at": "2026-07-01T10:00:00Z"
    }
  ],
  "total": 12,
  "page": 1,
  "per_page": 20,
  "pages": 1
}
```

**Errors:** None expected.

---

#### `POST /api/channels`
Add a channel to the platform.

**Request body:**
```json
{
  "url": "https://youtube.com/@channelname",
  "crawl_videos": false
}
```

**Validation:** `url` required; must match YouTube channel URL pattern; `crawl_videos` optional boolean.

**Response 202:**
```json
{
  "channel_id": "UCxxxxxx",
  "display_name": "Channel Name",
  "job_id": "celery-task-uuid",
  "status": "created"
}
```

**Response 200** (if channel already exists):
```json
{
  "channel_id": "UCxxxxxx",
  "status": "existing",
  "job_id": null
}
```

**Errors:** 422 (invalid URL), 503 (yt-dlp failure)

---

#### `GET /api/channels/{channel_id}`
Get full channel detail.

**Response 200:** Full channel object including all fields from `channels` table.

**Errors:** 404 (not found)

---

#### `PATCH /api/channels/{channel_id}`
Update mutable channel settings (not YouTube data).

**Request body:** `{"rss_monitoring": true}` — only `rss_monitoring` is user-settable.

**Response 200:** Updated channel object.

**Errors:** 404, 422

---

#### `DELETE /api/channels/{channel_id}`
Delete channel and all associated data.

**Query params:** `confirm=true` (required)

**Response 204:** No content.

**Errors:** 404, 422 (confirm not provided)

---

#### `POST /api/channels/{channel_id}/refresh`
Re-extract channel metadata.

**Response 202:** `{"job_id": "uuid"}`

**Errors:** 404

---

#### `POST /api/channels/{channel_id}/crawl`
Crawl all channel videos.

**Request body:** `{"max_videos": 0, "crawl_type": "all"}` — 0 means unlimited.

**Response 202:** `{"job_id": "uuid", "estimated_video_count": 342}`

**Errors:** 404

---

#### `GET /api/channels/{channel_id}/videos`
List videos for a channel.

**Query params:** `page`, `per_page`, `sort` (upload_date|view_count|like_count|duration_seconds), `order`, `is_short` (boolean), `has_transcript` (boolean), `availability`

**Response 200:** Paginated video list (same format as `/api/videos` list).

---

#### `GET /api/channels/{channel_id}/analytics`
Get channel growth time-series data.

**Query params:** `days` (default: 30, options: 7|30|90|365)

**Response 200:**
```json
{
  "channel_id": "UCxxxxxx",
  "range_days": 30,
  "snapshots": [
    {"date": "2026-07-01", "subscriber_count": 1480000, "video_count": 340, "total_view_count": 89000000},
    {"date": "2026-07-02", "subscriber_count": 1481500, "video_count": 340, "total_view_count": 89200000}
  ],
  "current": {"subscriber_count": 1500000, "video_count": 342, "total_view_count": 90500000},
  "delta": {"subscriber_count": 20000, "video_count": 2}
}
```

**Errors:** 404

---

#### `GET /api/channels/{channel_id}/stats`
Aggregate video statistics for a channel.

**Response 200:**
```json
{
  "channel_id": "UCxxxxxx",
  "total_videos_tracked": 342,
  "total_views_tracked": 150000000,
  "average_views_per_video": 438596,
  "total_duration_seconds": 847200,
  "shorts_count": 45,
  "live_count": 12,
  "has_transcript_count": 280,
  "top_videos_by_views": [...5 video objects...],
  "duration_distribution": {"0-1m": 45, "1-5m": 120, "5-10m": 98, "10-20m": 60, "20-60m": 17, "60m+": 2},
  "uploads_per_month": [{"month": "2026-06", "count": 8}, ...]
}
```

---

### 9.2 Video Endpoints

#### `GET /api/videos`
List all tracked videos (global, across all channels).

**Query params:** `page`, `per_page`, `channel_id`, `search` (title fulltext), `sort`, `order`, `is_short`, `has_transcript`, `availability`, `upload_date_after`, `upload_date_before`, `min_views`, `max_views`

**Response 200:** Paginated video list.

---

#### `POST /api/videos`
Extract and store a video by URL.

**Request body:** `{"url": "https://youtube.com/watch?v=xxxxx"}`

**Response 202:**
```json
{
  "video_id": "xxxxxxxxxxx",
  "job_id": "celery-uuid",
  "status": "created"
}
```

**Errors:** 422 (invalid URL), 404 (video unavailable)

---

#### `GET /api/videos/{video_id}`
Get full video detail.

**Response 200:** Full video object including all database fields.

**Errors:** 404

---

#### `POST /api/videos/{video_id}/refresh`
Re-extract video metadata.

**Response 202:** `{"job_id": "uuid"}`

---

#### `DELETE /api/videos/{video_id}`
Delete video and all associated data.

**Query params:** `confirm=true`

**Response 204**

---

#### `GET /api/videos/{video_id}/formats`
List available download formats for a video.

**Response 200:**
```json
{
  "video_id": "xxxxxxxxxxx",
  "formats": [
    {
      "format_id": "137",
      "ext": "mp4",
      "resolution": "1920x1080",
      "fps": 30,
      "vcodec": "avc1",
      "acodec": "none",
      "filesize_approx": 524288000,
      "note": "1080p"
    }
  ],
  "best_video": "137+140",
  "best_audio": "140"
}
```

**Note:** If formats not yet extracted or stale, triggers a background refresh. Returns cached data immediately with `{"stale": true}` flag if stale.

---

#### `GET /api/videos/{video_id}/snapshots`
Get view count history for a video.

**Query params:** `days` (default: 30)

**Response 200:**
```json
{
  "video_id": "xxxxxxxxxxx",
  "snapshots": [{"date": "2026-07-01", "view_count": 1000000, "like_count": 45000, "comment_count": 3200}]
}
```

---

### 9.3 Transcript Endpoints

#### `GET /api/transcripts/{video_id}`
Get stored transcript for a video.

**Query params:** `lang` (default: "en")

**Response 200:**
```json
{
  "video_id": "xxxxxxxxxxx",
  "language_code": "en",
  "is_auto_generated": false,
  "word_count": 5420,
  "segments": [{"text": "Hello everyone", "start": 0.0, "duration": 2.4}],
  "full_text": "Hello everyone ...",
  "extracted_at": "2026-07-28T10:00:00Z"
}
```

**Response 404:** Transcript not in DB. Body includes `{"available": true/false}` based on `has_transcript` flag.

---

#### `POST /api/transcripts/{video_id}`
Extract transcript for a video.

**Request body:** `{"lang": "en", "auto_translate_to": null}`

**Response 202:** `{"job_id": "uuid"}`

**Response 409:** `{"error": "No transcript available", "available_languages": []}`

---

#### `GET /api/transcripts/{video_id}/search`
Search within a video's transcript.

**Query params:** `q` (required), `lang` (default: "en"), `context_chars` (default: 100)

**Response 200:**
```json
{
  "video_id": "xxxxxxxxxxx",
  "query": "climate change",
  "matches": [
    {
      "segment_index": 245,
      "start_seconds": 843.2,
      "text": "...we talk about climate change and its effects...",
      "context_before": "In this section",
      "context_after": "on the ecosystem"
    }
  ]
}
```

---

#### `GET /api/transcripts/{video_id}/export`
Export transcript as file.

**Query params:** `format` (txt|srt|json), `lang` (default: "en")

**Response 200:** File download with appropriate Content-Type and Content-Disposition headers.

---

#### `GET /api/transcripts/{video_id}/languages`
List available transcript languages for a video.

**Response 200:**
```json
{
  "video_id": "xxxxxxxxxxx",
  "stored": [{"language_code": "en", "is_auto_generated": false}],
  "available_on_youtube": [{"language_code": "en", "name": "English"}, {"language_code": "es", "name": "Spanish"}]
}
```

Note: `available_on_youtube` requires a live fetch from youtube-transcript-api if not yet extracted.

---

### 9.4 Comment Endpoints

#### `GET /api/comments/{video_id}`
Get paginated comments for a video.

**Query params:** `page`, `per_page` (default: 50), `sort` (top|newest), `top_level_only` (boolean default: false)

**Response 200:** Paginated comment list with nested `replies` array on each top-level comment.

---

#### `POST /api/comments/{video_id}`
Extract comments for a video.

**Request body:** `{"max_comments": 500, "include_replies": true}`

**Response 202:** `{"job_id": "uuid"}`

**Response 409:** `{"error": "Comments are disabled for this video"}`

---

### 9.5 Playlist Endpoints

#### `GET /api/playlists`
List all tracked playlists.

**Query params:** `page`, `per_page`, `channel_id`, `search`

**Response 200:** Paginated playlist list.

---

#### `POST /api/playlists`
Add a playlist.

**Request body:** `{"url": "https://youtube.com/playlist?list=PLxxxxx"}`

**Response 202:** `{"playlist_id": "PLxxxxx", "job_id": "uuid", "status": "created"}`

---

#### `GET /api/playlists/{playlist_id}`
Get playlist detail with video list.

**Query params:** `page`, `per_page` (for videos)

**Response 200:** Playlist metadata + paginated video list.

---

#### `POST /api/playlists/{playlist_id}/refresh`
Re-crawl playlist to detect changes.

**Response 202:** `{"job_id": "uuid"}`

---

#### `DELETE /api/playlists/{playlist_id}`
Delete playlist (not its videos).

**Response 204**

---

### 9.6 Download Endpoints

#### `GET /api/downloads`
List download history.

**Query params:** `page`, `per_page`, `status`, `download_type`, `video_id`

**Response 200:** Paginated download_history records.

---

#### `POST /api/downloads/video`
Queue a video download.

**Request body:**
```json
{
  "video_id": "xxxxxxxxxxx",
  "quality": "1080p",
  "format": "mp4"
}
```

**Response 202:** `{"download_id": 42, "job_id": "uuid"}`

**Errors:** 404 (video not found or unavailable), 409 (already downloaded), 507 (insufficient disk space)

---

#### `POST /api/downloads/audio`
Queue an audio download.

**Request body:**
```json
{
  "video_id": "xxxxxxxxxxx",
  "format": "mp3",
  "quality": "192k"
}
```

**Response 202:** `{"download_id": 43, "job_id": "uuid"}`

---

#### `POST /api/downloads/subtitle`
Queue subtitle download.

**Request body:** `{"video_id": "...", "lang": "en", "format": "srt"}`

**Response 202:** `{"download_id": 44, "job_id": "uuid"}`

---

#### `POST /api/downloads/thumbnail`
Queue thumbnail download.

**Request body:** `{"video_id": "...", "resolution": "maxres"}`

**Response 202:** `{"download_id": 45, "job_id": "uuid"}`

---

#### `DELETE /api/downloads/{download_id}`
Delete a download record.

**Query params:** `delete_file=false`

**Response 204**

---

#### `POST /api/downloads/{download_id}/cancel`
Cancel an in-progress download.

**Response 200:** `{"status": "cancelled"}`

---

### 9.7 Search Endpoints

#### `GET /api/search/youtube`
Search YouTube via yt-dlp.

**Query params:** `q` (required), `type` (video|channel|playlist default: video), `max_results` (10|20|50 default: 20)

**Response 200:**
```json
{
  "query": "python tutorial",
  "type": "video",
  "cached": false,
  "results": [
    {
      "video_id": "xxxxxxxxxxx",
      "title": "Python Tutorial for Beginners",
      "channel": "Tech Channel",
      "channel_id": "UCxxxxxx",
      "thumbnail_url": "https://...",
      "duration_seconds": 3600,
      "view_count": 5000000,
      "upload_date": "2025-01-15"
    }
  ]
}
```

**Errors:** 422 (q missing), 503 (yt-dlp failure)

---

#### `GET /api/search/internal`
Search the local database.

**Query params:** `q` (required), `type` (video|channel|transcript default: video), `channel_id`, `has_transcript`, `is_short`, `upload_after`, `upload_before`, `page`, `per_page`

**Response 200:** Paginated results matching the local database.

---

### 9.8 Analytics Endpoints

#### `GET /api/analytics/dashboard`
Platform overview statistics.

**Response 200:**
```json
{
  "channels_count": 12,
  "videos_count": 3847,
  "transcripts_count": 2910,
  "downloads_count": 145,
  "storage_used_bytes": 48576000000,
  "active_jobs_count": 3,
  "recent_jobs": [...last 5 jobs...],
  "monitored_channels_count": 5,
  "recent_discoveries": [...last 5 new videos from RSS...]
}
```

---

### 9.9 Job Endpoints

#### `GET /api/jobs`
List jobs.

**Query params:** `page`, `per_page`, `status`, `job_type`, `target_id`

**Response 200:** Paginated job list.

---

#### `GET /api/jobs/{job_id}`
Get single job status.

**Response 200:**
```json
{
  "id": "celery-uuid",
  "job_type": "channel_crawl",
  "status": "processing",
  "progress_percent": 45,
  "current_operation": "Extracting video 110 of 247",
  "target_id": "UCxxxxxx",
  "retry_count": 0,
  "error_message": null,
  "created_at": "2026-07-28T12:00:00Z",
  "started_at": "2026-07-28T12:00:05Z",
  "completed_at": null
}
```

---

#### `GET /api/jobs/{job_id}/stream`
SSE stream for real-time job progress.

**Response:** `Content-Type: text/event-stream`

Events:
```
event: progress
data: {"percent": 45, "operation": "Extracting video 110 of 247", "speed": null, "eta": null}

event: complete
data: {"result": {"videos_extracted": 247}, "summary": "Channel crawl completed: 247 videos"}

event: error
data: {"message": "Rate limit hit", "retryable": true}
```

---

#### `POST /api/jobs/{job_id}/cancel`
Cancel a job.

**Response 200:** `{"status": "cancelled"}`

---

#### `POST /api/jobs/{job_id}/retry`
Retry a failed job.

**Response 202:** `{"new_job_id": "new-celery-uuid"}`

---

### 9.10 Settings Endpoints

#### `GET /api/settings`
Get current settings.

**Response 200:** Full settings object (all fields from `user_settings` table).

---

#### `PATCH /api/settings`
Update settings.

**Request body:** Any subset of settings fields.

**Response 200:** Updated settings object.

**Errors:** 422 (invalid values — e.g., negative poll interval, invalid quality string)

---

#### `POST /api/settings/cookies/upload`
Upload a YouTube cookies file.

**Request:** `multipart/form-data` with field `cookies_file` (text/plain, Netscape cookie format)

**Response 200:** `{"message": "Cookies saved", "path": "/config/cookies.txt"}`

**Errors:** 422 (invalid file format), 413 (file too large — max 5 MB)

---

#### `POST /api/settings/cookies/test`
Validate the current cookies file by attempting a lightweight yt-dlp extraction.

**Response 200:** `{"valid": true, "message": "Cookies are valid"}`

**Response 200:** `{"valid": false, "message": "Cookies appear expired or invalid"}`

---

#### `DELETE /api/settings/cookies`
Delete the cookies file.

**Response 204**

---

## 10. Background Jobs

### 10.1 Job: `extract_video_metadata`

**Trigger:** User adds a video URL; channel crawl completes (for each discovered video_id)

**Parameters:** `video_id_or_url: str`, `force_refresh: bool = False`

**Steps:**
1. Check DB: if video exists and `last_extracted_at` within TTL and not `force_refresh`, skip and mark complete
2. Call `ytdlp_client.extract_video_metadata(url)`
3. Map yt-dlp output dict to `Video` model fields
4. Upsert into `videos` table (INSERT or UPDATE)
5. If `user_settings.auto_extract_thumbnail=True`, queue `download_thumbnail` job
6. If `user_settings.auto_extract_transcript=True`, queue `extract_transcript` job
7. If `user_settings.auto_extract_comments=True`, queue `extract_comments` job
8. Update `processing_queue` status to complete

**Progress reporting:** Single-step task; reports 0% at start, 100% at completion.

**On failure:** Bot detection → retry with next player client; rate limit → retry after 30s; video unavailable → mark `availability=unavailable`; update job failed.

---

### 10.2 Job: `extract_channel_metadata`

**Trigger:** User adds a channel URL

**Steps:**
1. Call `ytdlp_client.extract_channel_metadata(url)`
2. Parse and upsert `channels` table
3. If `crawl_videos=True` in payload, queue `crawl_channel_videos` job
4. Mark complete

**On failure:** Same retry policy as video metadata.

---

### 10.3 Job: `crawl_channel_videos`

**Trigger:** User requests channel video crawl; or on channel add with `crawl_videos=True`

**Steps:**
1. Call `ytdlp_client.extract_flat_playlist(channel_videos_url)` with progress callback
2. For each video entry in results: create stub `Video` record if not exists (video_id, title, channel_id, upload_date, duration, thumbnail_url only)
3. Queue individual `extract_video_metadata` jobs for each video at low priority (priority=8)
4. Update `channels.last_crawled_at`
5. Report progress: `"Extracted {n} of {total} video stubs"`

**Progress:** Reports progress in percent based on videos processed vs total discovered.

**On failure:** Partial progress is safe — already-created stubs remain; retry resumes from yt-dlp's last page.

---

### 10.4 Job: `extract_transcript`

**Trigger:** Manual user request; auto-trigger on video add if enabled

**Steps:**
1. Attempt `transcript_client.fetch_transcript(video_id, lang)`
2. If `TranscriptNotAvailableError`:
   - Attempt yt-dlp subtitle fallback: `ytdlp_client.download_subtitles(url, lang="en", format="json")`
   - If both fail: set `videos.has_transcript = False`; mark job failed
3. On success: upsert `transcripts` table; set `videos.has_transcript = True`
4. Mark complete

---

### 10.5 Job: `extract_comments`

**Trigger:** Manual user request; auto-trigger if setting enabled

**Steps:**
1. Call `ytdlp_client.extract_comments(url, max_comments=settings.max_comments_per_video)`
2. If comments disabled: set `videos.comments_disabled = True`; mark job complete (not failed)
3. Batch insert comments into `comments` table (1000 per batch to avoid MySQL packet size issues)
4. Report progress by comment count

**Warning:** This job is slow and subject to bot detection. Priority=9 (lowest). Rate limit between comment requests: 3 seconds between pages.

---

### 10.6 Job: `download_video`

**Trigger:** User request via download API

**Steps:**
1. Acquire download semaphore (Redis; max count from settings)
2. Construct output path: `{download_dir}/videos/{video_id}/{video_id}_{quality}.mp4`
3. Call `ytdlp_client.download_video(url, output_path, quality, format, progress_hook)`
4. Progress hook: publishes download progress (bytes, speed, ETA) to Redis + updates `download_history.progress_percent`
5. On completion: update `download_history` with file_path, file_size_bytes, status=complete
6. Release semaphore

**On failure:** Delete partial `.part` file; update status=failed; release semaphore.

---

### 10.7 Job: `download_audio`

Same as `download_video` but calls `ytdlp_client.download_audio()` and output path is `{download_dir}/audio/{video_id}/{video_id}_{quality}.{format}`.

---

### 10.8 Job: `download_subtitle`

Calls `ytdlp_client.download_subtitles()`. Output: `{download_dir}/subtitles/{video_id}/{video_id}.{lang}.{format}`.

---

### 10.9 Job: `download_thumbnail`

Uses `httpx` to download the thumbnail CDN URL directly. Output: `{thumbnail_dir}/{video_id}/maxres.jpg`. No yt-dlp needed — CDN URL is sufficient.

If CDN URL returns 404 (expired), re-extract via `ytdlp_client.extract_video_metadata()` to get fresh thumbnail URL, then retry download.

---

### 10.10 Scheduled Job: `check_all_rss_feeds`

**Schedule:** Every 60 minutes (configurable via `rss_poll_interval_minutes`)

**Steps:**
1. Query `channels` table for all rows with `rss_monitoring=TRUE`
2. For each channel: construct RSS URL `https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}`
3. Fetch and parse RSS via `feedparser`
4. For each video entry in feed: check if `video_id` exists in `videos` table
5. If not found: create stub video record; queue `extract_video_metadata` job at priority=3 (high)
6. Log: "{n} new videos discovered across {m} channels"

**Error handling:** Individual channel RSS failures are logged and skipped; do not fail the entire job.

---

### 10.11 Scheduled Job: `snapshot_all_channels`

**Schedule:** Daily at 02:00 UTC

**Steps:**
1. Query all channels from DB
2. For each channel: call `ytdlp_client.extract_channel_metadata()` for fresh data (or use cached if within 1 hour)
3. Check if `channel_snapshots` row exists for today — INSERT IGNORE if not
4. Also update `channels` table with fresh subscriber/view counts

---

### 10.12 Scheduled Job: `snapshot_tracked_videos`

**Schedule:** Daily at 03:00 UTC

**Steps:**
1. Query videos belonging to channels with `rss_monitoring=TRUE`
2. For each video: call `ytdlp_client.extract_video_metadata()` for fresh data (or use cached)
3. INSERT IGNORE into `video_snapshots` for today
4. Update `videos` table with fresh counts

**Performance note:** With 10,000 tracked videos, this job may take 4–8 hours at 1 request/3 seconds. Rate limit is enforced.

---

### 10.13 Scheduled Job: `check_ytdlp_version`

**Schedule:** Weekly, Sunday at 04:00 UTC

**Steps:**
1. Call `yt-dlp --version` subprocess to get installed version
2. Fetch latest release version from GitHub API (`api.github.com/repos/yt-dlp/yt-dlp/releases/latest`)
3. Compare versions
4. If update available: log info-level message with version details
5. Do not auto-update (user must update manually or configure auto-update)

---

### 10.14 Scheduled Job: `cleanup_expired_cache`

**Schedule:** Daily at 01:00 UTC

**Steps:**
1. Delete `search_history` rows where `expires_at < NOW()`
2. Delete `processing_queue` rows where `status IN ('complete','cancelled') AND completed_at < (NOW() - INTERVAL 30 DAY)`
3. Delete `processing_queue` rows where `status = 'failed' AND completed_at < (NOW() - INTERVAL 90 DAY)`
4. Log count of rows deleted

---

## 11. Caching Strategy

### 11.1 What Is Cached

| Cache Key Pattern | Content | TTL | Invalidated When |
|---|---|---|---|
| `channel:{channel_id}:meta` | Full channel dict | 1 hour | Channel refresh job completes |
| `channel:{channel_id}:stats` | Aggregate video stats | 6 hours | New video crawl completes |
| `channel:{channel_id}:analytics:{days}` | Snapshot time-series | 1 hour | Snapshot job runs |
| `video:{video_id}:meta` | Full video dict | 24 hours | Video refresh job completes |
| `video:{video_id}:formats` | Available formats list | 6 hours | Video refresh job completes |
| `transcript:{video_id}:{lang}` | Full transcript dict | Forever (no TTL) | Transcript re-extracted |
| `search:{hash(query+type)}` | Search result IDs | 1 hour | TTL expiry only |
| `settings` | User settings dict | 1 hour | Settings PATCH request |
| `dashboard:stats` | Dashboard overview | 15 minutes | Any new job completion |
| `ytdlp:current_client` | Current player client | 24 hours | Bot detection triggers rotation |

### 11.2 Cache Implementation

All cache operations go through `CacheService` in `backend/app/services/`. This class wraps Redis with:
- JSON serialization/deserialization
- Key prefixing with `yta:` (YouTube Analyzer namespace)
- `get(key) -> dict | None`
- `set(key, value, ttl_seconds=None)` — None TTL means no expiry
- `delete(key)`
- `delete_pattern(pattern)` — e.g., delete all `channel:{channel_id}:*`

Services check the cache before calling repositories or extraction layer:
1. Try `cache.get(key)`
2. If hit: return cached value
3. If miss: call repository or extraction
4. Store result in cache with appropriate TTL
5. Return result

### 11.3 Cache Invalidation

Invalidation is explicit (not TTL-only) for high-importance data:

After channel refresh: `cache.delete_pattern(f"channel:{channel_id}:*")`

After video refresh: `cache.delete(f"video:{video_id}:meta")`, `cache.delete(f"video:{video_id}:formats")`

After transcript extraction: `cache.delete(f"transcript:{video_id}:{lang}")`

After settings update: `cache.delete("settings")`

After any job completion: `cache.delete("dashboard:stats")`

### 11.4 Redis Database Allocation

Redis databases are allocated by function:
- `redis://host:6379/0` — Celery broker
- `redis://host:6379/1` — Celery result backend
- `redis://host:6379/2` — Application cache (CacheService)
- `redis://host:6379/3` — Rate limiter counters (Flask-Limiter)

### 11.5 Memory Considerations

Transcripts are the largest cached items. A 3-hour lecture transcript may be 500 KB. With 100 cached transcripts, Redis memory usage for transcripts alone is ~50 MB. Set Redis `maxmemory` to 512 MB with `maxmemory-policy allkeys-lru` to evict least-recently-used cache entries when memory is full. Celery jobs and rate limit counters are small and should not be evicted; application cache can be.

---

## 12. Error Handling

### 12.1 Custom Exception Hierarchy

```
YouTubeAnalyzerError (base)
├── ExtractionError
│   ├── VideoUnavailableError(video_id, reason)
│   ├── ChannelNotFoundError(channel_id)
│   ├── YouTubeRateLimitError(retry_after_seconds)
│   ├── YouTubeBotDetectedError(current_client)
│   ├── PoTokenExpiredError()
│   └── ExtractionFailedError(detail, original_exception)
├── TranscriptError
│   ├── TranscriptNotAvailableError(video_id, available_languages=[])
│   └── TranscriptExtractionError(video_id, detail)
├── DownloadError
│   ├── InsufficientDiskSpaceError(required_bytes, available_bytes)
│   ├── DownloadAlreadyExistsError(download_id)
│   └── DownloadInterruptedError(job_id)
└── StorageError
    ├── PathTraversalError(path)
    └── FileNotFoundError(path)
```

All exceptions accept a `message` string and pass it to the parent `__init__`.

### 12.2 Retry Strategy

Retry logic is implemented at the Celery task level using `autoretry_for` and `retry_backoff`:

```
Task retry configuration:
  autoretry_for = (YouTubeRateLimitError, YouTubeBotDetectedError, ExtractionFailedError)
  max_retries = 3
  retry_backoff = True          # exponential backoff
  retry_backoff_max = 60        # max 60 seconds between retries
  retry_jitter = True           # add random jitter to prevent thundering herd
```

`TranscriptNotAvailableError` is NOT retried — it's a definitive "no captions" response.

`VideoUnavailableError` is NOT retried — it's a definitive "private/deleted" response.

`DownloadAlreadyExistsError` is NOT retried — return existing file path immediately.

### 12.3 Bot Detection Response

When `YouTubeBotDetectedError` is raised:
1. Log warning with current player client
2. Call `bot_mitigation.rotate_client()` — updates Redis `ytdlp:current_client` to next in rotation
3. Celery auto-retries the task with new client
4. If all clients exhausted and still failing: send admin notification (log ERROR level) and fail the job

Player client rotation order: `ios` → `web_safari` → `android` → `mweb` → back to `ios`

### 12.4 Download Failure Handling

When a download task fails at any point:
1. Cancel the yt-dlp subprocess (if running)
2. Delete any partial `.part` file from the output path
3. Update `download_history.status = 'failed'`
4. Update `download_history.error_message` with full exception string
5. Release the download semaphore (critical — prevents semaphore leak)
6. Retry if retries remain; otherwise mark job failed in `processing_queue`

### 12.5 Network Failure Handling

All HTTP requests (RSS fetching, thumbnail downloads, PoToken provider calls) use `httpx` with:
- `timeout=30.0` seconds
- `retry_transport` with 2 retries on connection errors
- Failures are caught and re-raised as `ExtractionFailedError`

### 12.6 Partial Data Handling

yt-dlp sometimes returns partial data (some fields absent). The extraction layer applies this rule: accept partial data rather than fail. Fields that are `None` in the yt-dlp output are stored as `NULL` in the database. The frontend handles `null` fields gracefully by displaying "Not available" rather than crashing.

Fields that are absolutely required and cannot be null: `video_id`, `title`, `channel_id`.

If these are absent from yt-dlp output, raise `ExtractionFailedError`.

### 12.7 Database Error Handling

SQLAlchemy `IntegrityError` (e.g., duplicate key on INSERT) is caught by the repository layer and:
- For channels/videos: treated as "already exists" → return existing record
- For playlists: treated as "already exists" → return existing record
- For snapshots: already handled by `INSERT IGNORE` pattern
- For other tables: re-raised as application error

MySQL `OperationalError` (connection dropped) is handled by `pool_pre_ping=True` which automatically retries the connection.

### 12.8 Frontend Error Handling

The Axios response interceptor handles:
- **HTTP 422:** Parses `errors` dict from response body; surfaces field-level errors in the form or as a toast
- **HTTP 503:** Shows "Service temporarily unavailable" toast with retry suggestion
- **HTTP 404:** Lets the calling component handle (show 404 state)
- **HTTP 5xx:** Shows "An error occurred" toast with request_id for debugging
- **Network error (no response):** Shows "Cannot reach server" toast

React ErrorBoundary catches render-time errors and shows a recovery screen without crashing the full app.

---

## 13. Performance Strategy

### 13.1 Asynchronous-First Design

Every YouTube extraction operation is asynchronous by definition. The Flask application is synchronous (WSGI) but this is acceptable because:
- HTTP request handlers only query the database or queue jobs — both fast operations
- All slow operations (yt-dlp, downloads, RSS) run in Celery workers (separate processes)
- The Flask server is never blocked by YouTube network operations

No operation in the HTTP request path should take more than 500ms. If it would, queue it as a job.

### 13.2 Large Channel Handling

A channel with 10,000 videos requires paginated flat-playlist extraction. Strategy:
1. The `crawl_channel_videos` task streams yt-dlp output as it arrives (using `--print-json` with a subprocess pipe, not loading all into memory)
2. Video stubs are inserted in batches of 100 using SQLAlchemy `bulk_insert_mappings()`
3. Progress is reported every 100 videos
4. The task sets a rate limit of 1 request/3 seconds between yt-dlp pagination calls

Memory budget for 10,000-video crawl: 50 MB (stream processing, not bulk load).

### 13.3 Large Playlist Handling

Same strategy as large channel crawl. Playlist flat-extraction is streamed. Expected time for 1,000-video playlist: 3–5 minutes.

### 13.4 Parallel Downloads

Maximum parallel downloads is configurable (default: 2) to avoid IP rate limiting. Enforced via Redis semaphore:
- `SETNX download:semaphore:{slot_n} 1 EX 86400` — acquire slot
- Worker holds slot during download; releases on complete or failure
- If no slots available, task waits in queue

Within a single download, yt-dlp uses its own internal fragment parallelism for DASH streams. Do not set yt-dlp `--concurrent-fragments` above 4 on shared IPs.

### 13.5 Database Optimization

- All list endpoints use `LIMIT` + `OFFSET` pagination (max 100 per page)
- Avoid `SELECT *` in repositories — select only needed columns
- All foreign key columns have indexes (MySQL does not auto-create FK indexes)
- `upload_date`, `view_count`, `is_short`, `has_transcript` indexed for filtering
- Full-text search on `title + description` (videos table) and `full_text` (transcripts table) uses MySQL FULLTEXT indexes with `MATCH()...AGAINST()` queries
- `processing_queue` is aggressively cleaned by maintenance job to prevent table growth

### 13.6 Frontend Performance

- TanStack Query provides automatic background refetching and deduplication — multiple components requesting the same data result in one API call
- Large video lists use `DataTable` with `per_page=20` — no infinite scroll (avoids DOM bloat)
- Recharts charts use `<ResponsiveContainer>` — no layout recalculation on resize
- Images (thumbnails, avatars) use native `loading="lazy"` attribute
- Vite code splitting: each page is a lazy-loaded chunk via `React.lazy()` and `<Suspense>`
- The app shell (sidebar, topbar) is rendered immediately; page content loads asynchronously

### 13.7 Transcript Search Performance

MySQL FULLTEXT search on `transcripts.full_text` supports natural language search. For datasets with 1 million transcript segments (stored as concatenated text), FULLTEXT index performs adequately. The `segments` column is not indexed — segment-level search is done via application-level substring search after the row is fetched.

For semantic search (future Phase), a vector index (pgvector or Qdrant) would replace this.

---

## 14. UI Planning

### 14.1 Global Layout

All pages use the `AppShell` component with:
- **Sidebar** (left, fixed, 240px wide on desktop, collapsible on tablet, hidden on mobile with hamburger toggle)
- **TopBar** (top, fixed, 64px height): App logo/name, search bar, job status indicator (animated dot + count when jobs active), settings icon link
- **Content area**: scrollable main content; max-width 1400px, centered, padding 24px

---

### 14.2 Dashboard Page (`/dashboard`)

**Purpose:** At-a-glance overview of the entire platform.

**Sections:**

*Stats bar* — 4 stat cards in a row: "Channels Tracked", "Videos Tracked", "Transcripts", "Downloads". Each card shows the count, an icon, and a subtle color background.

*Active Jobs panel* — If any jobs are running/queued, show a card listing them with status badges and progress bars. Show "No active jobs" placeholder when idle.

*Recent Activity* — Timeline of last 10 completed/failed jobs with timestamps.

*RSS Discoveries* — Card listing videos newly discovered via RSS in the last 24 hours, with channel name and video title. "Extract Metadata" button on each.

*Storage* — Disk usage bar showing `used / total` for the downloads directory.

**Actions available:** None directly on dashboard. All items link to relevant detail pages.

---

### 14.3 Channel List Page (`/channels`)

**Purpose:** Browse and manage all tracked channels.

**Sections:**

*Header* — "Channels" heading + "Add Channel" button (opens modal).

*Search + Filter bar* — Search input (by name/handle), sort dropdown (Name / Subscribers / Last Crawled), monitoring filter toggle.

*Channel Grid* — Cards in a 3-column grid (1-col mobile, 2-col tablet). Each `ChannelCard` shows: avatar, display name, handle, subscriber count, video count, verification badge, monitoring indicator, last crawled date.

*ChannelCard actions* — "View" button, "Refresh" button (icon), "Delete" button (icon, opens confirm dialog).

*Add Channel Modal* — Text input for YouTube URL or @handle, "Add" button, "Crawl videos immediately" checkbox. Shows inline error if URL invalid. Shows spinner during submission. On success: closes modal, shows success toast, card appears in grid.

*Pagination* — At bottom of grid.

---

### 14.4 Channel Detail Page (`/channels/:channelId`)

**Purpose:** Full channel profile, stats, and video management.

**Sections:**

*Channel Header* — Banner image (full width, 200px height, fallback gradient if absent), avatar (circular, 80px, overlapping banner bottom), display name, handle, verification badge, subscriber count, video count, total views, join date, country. "Refresh" and "Crawl Videos" action buttons. "Monitor" toggle (RSS).

*Stats Row* — 4 stat cards: Total Videos Tracked, Average Views, Total Duration, Shorts Count.

*Tabs* — "Videos" | "Playlists" | "Analytics" | "External Links"

*Videos Tab* — `VideoGrid` component (same as global video list but pre-filtered by channel_id). Includes search, sort, filter controls. "Crawl All Videos" button at top.

*Playlists Tab* — Playlist cards: title, video count, thumbnail, last crawled. "Refresh" button on each. "Add Playlist" input.

*Analytics Tab* — `GrowthChart` showing subscriber/view trends (date range selector: 7d/30d/90d/1y). `DurationHistogram` showing video length distribution. `ViewsBarChart` showing top 10 videos.

*External Links Tab* — List of all external links extracted from channel About section.

---

### 14.5 Video Detail Page (`/videos/:videoId`)

**Purpose:** All data for a single video.

**Sections:**

*Video Header* — Thumbnail (16:9 aspect ratio, 100% width). Title. Channel link. Upload date. Duration. Availability badge. Shorts badge if applicable. Live badge if applicable. "Open on YouTube" external link.

*Stats Row* — View count, Like count (or "Hidden"), Comment count. Each as a stat card.

*Action Buttons* — "Download Video", "Download Audio", "Extract Transcript", "Extract Comments", "Refresh Metadata". Each opens appropriate modal or queues job.

*Tabs* — "Description" | "Formats" | "Chapters" | "Transcript" | "Comments"

*Description Tab* — Full video description in a pre-styled text block. Tags displayed as badge chips below. Categories as badges. Language if available.

*Formats Tab* — `DataTable` with columns: Format ID, Resolution, FPS, Video Codec, Audio Codec, File Size (estimated). Row click selects format for download.

*Chapters Tab* — Timeline list of chapters with time markers. If no chapters: "No chapters available" empty state.

*Transcript Tab* — `TranscriptViewer`: full text displayed with timestamps on each segment. Search input at top — highlights matching segments. Language selector dropdown if multiple languages available. Export button (txt/srt/json).

*Comments Tab* — Paginated threaded comment list. Sort selector (top/newest). Each comment shows: author, text, like count, timestamp, "Creator" badge if applicable, "Pinned" badge. Replies nested below with indent.

*Download Modal* — Opened by "Download Video" button. Quality selector (dropdown: best/1080p/720p/480p/360p/worst). Format selector (mp4/webm). Download button. Shows estimated file size when format selected.

---

### 14.6 Search Page (`/search`)

**Purpose:** YouTube search and local database search.

**Sections:**

*Search input* — Large search bar, prominently centered. Radio group: "Search YouTube" vs "Search My Library". Submit button.

*Filters (My Library mode)* — Entity type (Videos/Channels/Transcripts), has_transcript toggle, is_short toggle, date range, channel filter.

*Results* — `VideoGrid` (for videos), `ChannelCard` list (for channels). Each YouTube result has an "Add to Library" button.

*Empty state* — "Enter a search query to begin." Before first search.

*No results state* — "No results found for '{query}'" with search tips.

---

### 14.7 Downloader Page (`/downloader`)

**Purpose:** Manage downloads — queue new ones, view history.

**Sections:**

*Quick Download form* — YouTube URL input, Type selector (Video/Audio/Subtitle/Thumbnail), Quality/Format selectors (contextual to type), "Queue Download" button.

*Active Downloads* — Cards for in-progress downloads showing: video title/thumbnail, type, quality, progress bar, speed, ETA. "Cancel" button.

*Download History* — Filterable table: video title, type, quality, file size, status badge, date, "Open File" link (if file exists on disk), "Delete" button.

---

### 14.8 Jobs Page (`/jobs`)

**Purpose:** Monitor all background jobs.

**Sections:**

*Filter bar* — Status filter (All/Queued/Processing/Complete/Failed/Cancelled), Job Type filter, Date range.

*Jobs Table* — Columns: Job Type, Target (video/channel title with link), Status badge, Progress, Created, Duration, Actions (Retry if failed / Cancel if queued).

*Job Detail Modal* — Clicking a job row opens a modal with full job details: payload, error message (formatted with code block), retry history.

---

### 14.9 Settings Page (`/settings`)

**Purpose:** Configure all platform options.

**Sections:**

*Download Settings* — Download directory path, Default video quality, Default audio format, Default audio quality, Max concurrent downloads.

*Extraction Settings* — Auto-extract transcript (toggle), Auto-extract comments (toggle), Auto-extract thumbnail (toggle), Max comments per video (number input).

*yt-dlp Settings* — Player client selector (ios/web_safari/android/mweb), Rate limit input, Cookies file upload/test/delete section, Proxy URL input, PoToken provider URL.

*Monitoring Settings* — RSS poll interval (minutes), Snapshot enabled (toggle).

*Advanced* — Metadata cache TTL, Database info (table counts, sizes).

Each section is a separate Card with a "Save" button. Changes are saved per-section, not globally.

---

### 14.10 Not Found Page (`/404` and `*` route)

Simple centered layout: "404 — Page Not Found" heading, brief message, "Go to Dashboard" button.

---

## 15. Implementation Roadmap

Each phase produces a fully functional application. Later phases add features on top of the working base.

---

### Phase 1 — Project Setup and Infrastructure (1–2 days)

**Goal:** Working Docker Compose stack with all services running; database created; basic health check endpoint.

**Deliverables:**
- `docker-compose.yml` with services: `backend`, `mysql`, `redis`, `celery-worker`, `celery-beat`, `frontend`
- `backend.Dockerfile` with Python 3.12 slim + FFmpeg
- `frontend.Dockerfile` with Node 20 + Nginx
- Flask app factory with database initialized (`db.create_all()`)
- All SQLAlchemy models defined (all 13 tables from Section 8)
- Alembic initial migration generated
- Celery app configured and connected to Redis
- `GET /api/health` endpoint returning `{"status": "ok", "db": "ok", "redis": "ok"}`
- React + Vite project scaffolded with Tailwind configured
- AppShell layout rendered (sidebar + topbar) with placeholder content
- `.env.example` with all environment variables documented
- `README.md` with local setup instructions

**Acceptance criteria:**
- `docker compose up` starts all services
- `GET /api/health` returns 200
- Frontend loads at `http://localhost:5173` showing AppShell
- Database tables exist in MySQL
- Celery worker starts and logs "Ready"

---

### Phase 2 — Channel Module (2–3 days)

**Goal:** Add, view, and delete channels. Extract channel metadata via yt-dlp.

**Deliverables:**
- `ChannelRepository` with all CRUD methods
- `YtdlpClient.extract_channel_metadata()` implemented
- `ChannelService.add_channel()` and supporting methods
- `channel_controller` Blueprint with all channel endpoints from Section 9.1
- Marshmallow schemas for channel input/output validation
- Celery task: `extract_channel_metadata`
- `ChannelList` page with channel cards and Add Channel modal
- `ChannelDetail` page with profile header and stats row
- Job status polling in frontend (simple polling via TanStack Query, not SSE yet)
- `CacheService` implemented; channel metadata cached

**Acceptance criteria:**
- User can add a channel by URL
- Channel profile renders with all available fields
- Refresh triggers re-extraction
- Delete removes channel from DB
- Adding a duplicate channel returns the existing one

---

### Phase 3 — Video Module (2–3 days)

**Goal:** Extract, store, and display video metadata. View video list for channels.

**Deliverables:**
- `VideoRepository` with CRUD, list, and aggregate methods
- `YtdlpClient.extract_video_metadata()` implemented
- `VideoService` with cache-check-first logic
- `video_controller` Blueprint with all endpoints from Section 9.2
- Celery task: `extract_video_metadata`
- Celery task: `crawl_channel_videos` (flat-playlist mode)
- `VideoGrid` and `VideoCard` components
- `VideoDetail` page: all tabs (Description, Chapters, Formats)
- Channel Detail page: Videos tab now populated
- `DataTable` common component implemented
- Pagination common component implemented

**Acceptance criteria:**
- User can add a video by URL
- Video detail page renders all available metadata
- Channel crawl discovers all videos and creates stub records
- Video list is sortable and filterable

---

### Phase 4 — Search Module (1–2 days)

**Goal:** YouTube search and internal database search.

**Deliverables:**
- `YtdlpClient.extract_search_results()` implemented (`ytsearch{n}:`)
- `SearchService` with cache-first logic
- `SearchRepository` with FULLTEXT query support
- `search_controller` Blueprint
- `Search` page with dual mode (YouTube / My Library)
- Internal search results from DB with FULLTEXT matching
- Search history caching (1 hour)

**Acceptance criteria:**
- Searching YouTube returns results without API key
- Same search within 1 hour returns cached results
- Internal search finds videos by title/description text
- "Add to Library" button on YouTube search results triggers video extraction

---

### Phase 5 — Transcript Module (1–2 days)

**Goal:** Extract, store, display, search, and export transcripts.

**Deliverables:**
- `TranscriptClient` wrapping youtube-transcript-api
- `TranscriptService` with primary/fallback extraction logic
- `TranscriptRepository`
- `transcript_controller` Blueprint with all endpoints from Section 9.3
- Celery task: `extract_transcript`
- `TranscriptViewer` component with timestamp display
- `TranscriptSearch` component with in-page text search
- Transcript export endpoint (txt/srt/json)
- Video Detail page: Transcript tab now functional
- `has_transcript` field updated after extraction

**Acceptance criteria:**
- Transcript extracted for video with captions
- Transcript viewer shows timed segments
- In-page search highlights matching segments
- Export downloads transcript as .txt, .srt, or .json
- Videos without captions show "No transcript available" gracefully

---

### Phase 6 — Download Module (2–3 days)

**Goal:** Queue and manage video, audio, subtitle, and thumbnail downloads.

**Deliverables:**
- `DownloadService` with semaphore-based concurrency control
- `DownloadRepository`
- `YtdlpClient.download_video()`, `download_audio()`, `download_subtitles()` implemented
- Celery tasks: `download_video`, `download_audio`, `download_subtitle`, `download_thumbnail`
- SSE endpoint implemented (`GET /api/jobs/{job_id}/stream`)
- `useJobProgress` hook in frontend (EventSource for SSE)
- `JobProgressBar` component updated to use SSE
- `download_controller` Blueprint with all endpoints from Section 9.6
- `Downloader` page with quick-download form and history table
- `FormatSelector` component on Video Detail page
- Disk space check before queuing download

**Acceptance criteria:**
- Video download queued; progress shown in real time via SSE
- Audio download produces MP3/M4A file
- Download history table shows all completed downloads
- Duplicate download detection returns existing file path
- Failed download cleans up partial files

---

### Phase 7 — Playlist Module (1 day)

**Goal:** Add, crawl, and display playlists.

**Deliverables:**
- `PlaylistRepository`, `PlaylistService`
- `playlist_controller` Blueprint
- Celery task: `crawl_playlist`
- `PlaylistDetail` page
- Channel Detail page: Playlists tab now functional

**Acceptance criteria:**
- Playlist added by URL; all video IDs extracted
- Playlist page shows ordered video list
- Refresh detects added/removed videos

---

### Phase 8 — Comment Module (1 day)

**Goal:** Extract and display comments.

**Deliverables:**
- `YtdlpClient.extract_comments()` implemented
- `CommentRepository`, `CommentService`
- `comment_controller` Blueprint
- Celery task: `extract_comments`
- `CommentThread` component with threading
- Video Detail page: Comments tab functional

**Acceptance criteria:**
- Comments extracted for a video
- Threaded view shows replies nested under parent comments
- "Creator" and "Pinned" badges shown correctly
- Videos with comments disabled handled gracefully

---

### Phase 9 — Analytics and Snapshots (1–2 days)

**Goal:** Channel and video growth charts; scheduled snapshot jobs.

**Deliverables:**
- `SnapshotRepository`, `SnapshotService`
- Celery Beat schedule configured for daily snapshots
- `snapshot_jobs.py` tasks implemented
- `analytics_controller` Blueprint with all endpoints from Section 9.8
- `GrowthChart` component (Recharts LineChart)
- `ViewsBarChart` component (Recharts BarChart)
- `DurationHistogram` component
- Channel Detail page: Analytics tab functional
- Dashboard page: stats cards + recent activity

**Acceptance criteria:**
- Running daily for 3+ days produces a visible growth chart
- Channel stats page shows aggregate video metrics
- Dashboard shows accurate platform-wide counts

---

### Phase 10 — RSS Monitoring (1 day)

**Goal:** Automatically detect new videos from monitored channels.

**Deliverables:**
- `RssClient` using feedparser
- `rss_jobs.py` Celery task implemented
- Beat schedule for RSS polling (configurable interval)
- Channel Detail: RSS monitoring toggle (PATCH `/channels/{id}`)
- Dashboard: "Recent Discoveries" card

**Acceptance criteria:**
- Enabling monitoring on a channel causes new videos to appear automatically
- RSS monitor runs every 60 minutes (configurable)
- New video discovery triggers metadata extraction job

---

### Phase 11 — Settings Module (1 day)

**Goal:** Full settings management with cookie upload.

**Deliverables:**
- `SettingsRepository`, `SettingsService`
- `settings_controller` Blueprint with all endpoints from Section 9.10
- `Settings` page with all sections
- Cookie file upload/test/delete
- Settings cached in Redis; invalidated on update
- yt-dlp options updated dynamically from settings

**Acceptance criteria:**
- Changing player client updates all subsequent yt-dlp calls
- Cookie upload saves file and path to settings
- Cookie test returns valid/invalid status
- Settings persist across application restarts

---

### Phase 12 — Polish, Error Handling, and Testing (2–3 days)

**Goal:** Production-quality error states, full test coverage, deployment validation.

**Deliverables:**
- All custom exceptions implemented and wired to global error handlers
- Bot detection client rotation fully operational
- All API endpoints have integration tests (Section 16)
- Unit tests for all service methods
- yt-dlp mock fixture used in all tests (no real YouTube calls in tests)
- Empty states on all list pages
- Loading skeletons on all data-fetching pages
- Error boundary wrapping all page routes
- Mobile responsiveness verified at 375px, 768px, 1024px, 1440px
- `docker compose up` smoke test (all phases verified)
- `DEPLOYMENT.md` written

**Acceptance criteria:**
- All tests pass with no real YouTube network calls
- Platform works end-to-end from `docker compose up`
- All error states render meaningful messages
- All list pages handle empty data gracefully

---

## 16. Testing Strategy

### 16.1 Test Structure

```
backend/tests/
├── conftest.py                    # Fixtures
├── unit/
│   ├── test_services/
│   │   ├── test_channel_service.py
│   │   ├── test_video_service.py
│   │   ├── test_transcript_service.py
│   │   ├── test_download_service.py
│   │   └── test_search_service.py
│   └── test_utils/
│       ├── test_url_parser.py
│       └── test_file_manager.py
└── integration/
    ├── test_channels_api.py
    ├── test_videos_api.py
    ├── test_transcripts_api.py
    ├── test_comments_api.py
    ├── test_playlists_api.py
    ├── test_downloads_api.py
    ├── test_search_api.py
    ├── test_jobs_api.py
    └── test_settings_api.py
```

### 16.2 Test Fixtures (`conftest.py`)

**`app` fixture** — Creates a Flask test app with `TestingConfig` (SQLite in-memory, Celery eager mode).

**`db` fixture** — Creates all tables, yields db, drops all tables on teardown.

**`client` fixture** — Flask test client.

**`mock_ytdlp` fixture** — Patches `YtdlpClient` with a mock that returns pre-recorded JSON from `tests/fixtures/`. Never makes real network calls.

**`mock_transcript` fixture** — Patches `TranscriptClient` similarly.

**`sample_channel` fixture** — Creates a `Channel` record in the test DB.

**`sample_video` fixture** — Creates a `Video` record linked to `sample_channel`.

**`sample_transcript` fixture** — Creates a `Transcript` record for `sample_video`.

### 16.3 Unit Tests

**Service tests** verify business logic in isolation. The service is called with mock repository and extraction layer.

Example unit test cases for `ChannelService`:
- `test_add_channel_new` — new channel URL; ytdlp mock returns channel data; channel inserted; job queued
- `test_add_channel_duplicate` — channel already in DB; returns existing; no job queued
- `test_add_channel_invalid_url` — raises `ValidationError`
- `test_refresh_channel_queues_job` — queues extraction job; returns job_id
- `test_delete_channel_cascades` — channel and all videos deleted
- `test_delete_channel_not_found` — raises `ChannelNotFoundError`

### 16.4 Integration Tests

**API tests** verify the full request/response cycle. The Flask test client sends HTTP requests; responses are checked for status code, body structure, and database side effects.

Example integration test cases for `test_channels_api.py`:
- `test_post_channels_success` — POST with valid URL → 202, job_id in response, channel in DB
- `test_post_channels_invalid_url` → 422, errors dict in response
- `test_get_channels_empty` → 200, items=[], total=0
- `test_get_channels_with_data` → 200, items contains channel
- `test_get_channel_not_found` → 404
- `test_delete_channel_requires_confirm` → 422 without `?confirm=true`
- `test_delete_channel_cascades` → 204; video for this channel also deleted

### 16.5 Frontend Tests

Frontend tests use **Vitest** (included with Vite) and **React Testing Library**.

Test files co-located with components: `ChannelCard.test.jsx` next to `ChannelCard.jsx`.

All API calls are mocked using `msw` (Mock Service Worker) or Vitest's `vi.mock()`.

**Test cases for key components:**

`ChannelCard.test.jsx`:
- Renders channel name, handle, subscriber count
- Shows verification badge when `is_verified=true`
- Shows monitoring indicator when `rss_monitoring=true`
- Calls `onDelete` when delete button clicked

`TranscriptViewer.test.jsx`:
- Renders all segments with timestamps
- Search input filters visible segments
- Export button triggers download with correct format

`JobProgressBar.test.jsx`:
- Shows 0% initially
- Updates when progress prop changes
- Shows "Complete" state with green color
- Shows "Failed" state with red color

### 16.6 Edge Case Tests

These specific edge cases must be tested:

- Empty channel (0 videos) — crawl returns empty list; no error
- Video with no chapters — chapters tab shows empty state
- Video with no transcript — transcript tab shows "not available" with extract button
- Video with comments disabled — comment extraction sets `comments_disabled=true`; no error
- Search with empty query — returns 422
- Download of already-downloaded video — returns 409 with existing file path
- Channel with only Shorts — `is_short=true` on all videos
- Very long transcript (10,000 segments) — stored and retrieved without timeout
- Cookie file upload with invalid format — returns 422
- Settings with negative poll interval — returns 422

---

## 17. Deployment Strategy

### 17.1 Local Development (Without Docker)

**Prerequisites:** Python 3.12, Node.js 20, MySQL 8.0 (local or Docker), Redis 7 (local or Docker), FFmpeg

**Setup steps:**
1. Clone repository
2. Copy `.env.example` to `.env`; set `DATABASE_URL` and `REDIS_URL` for local services
3. Create MySQL database: `CREATE DATABASE youtube_analyzer CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;`
4. `cd backend && pip install -r requirements.txt`
5. `flask db upgrade` — runs migrations
6. `python run.py` — starts Flask dev server on port 5000
7. In separate terminal: `celery -A app.jobs.celery_app worker --concurrency=2 --loglevel=info`
8. In separate terminal: `celery -A app.jobs.celery_app beat --loglevel=info`
9. `cd frontend && npm install && npm run dev` — starts Vite dev server on port 5173

**Flask dev server** runs with hot-reload. Celery workers require manual restart after code changes.

---

### 17.2 Docker Compose (Recommended)

**`docker-compose.yml` services:**

```
services:
  mysql:
    image: mysql:8.0
    environment:
      MYSQL_DATABASE: youtube_analyzer
      MYSQL_USER: ytanalyzer
      MYSQL_PASSWORD: ${MYSQL_PASSWORD}
      MYSQL_ROOT_PASSWORD: ${MYSQL_ROOT_PASSWORD}
    volumes:
      - mysql_data:/var/lib/mysql
    healthcheck:
      test: ["CMD", "mysqladmin", "ping", "-h", "localhost"]
      interval: 10s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    command: redis-server --maxmemory 512mb --maxmemory-policy allkeys-lru
    volumes:
      - redis_data:/data

  backend:
    build:
      context: ./backend
      dockerfile: ../docker/backend.Dockerfile
    env_file: .env
    environment:
      DATABASE_URL: mysql+pymysql://ytanalyzer:${MYSQL_PASSWORD}@mysql:3306/youtube_analyzer
      REDIS_URL: redis://redis:6379/0
    depends_on:
      mysql:
        condition: service_healthy
      redis:
        condition: service_started
    volumes:
      - downloads_data:/data/downloads
      - thumbnails_data:/data/thumbnails
    ports:
      - "5000:5000"
    command: >
      sh -c "flask db upgrade && gunicorn --bind 0.0.0.0:5000 --workers 2 --timeout 120 wsgi:app"

  celery-worker:
    build:
      context: ./backend
      dockerfile: ../docker/backend.Dockerfile
    env_file: .env
    environment:
      DATABASE_URL: mysql+pymysql://ytanalyzer:${MYSQL_PASSWORD}@mysql:3306/youtube_analyzer
      REDIS_URL: redis://redis:6379/0
    depends_on:
      - backend
    volumes:
      - downloads_data:/data/downloads
      - thumbnails_data:/data/thumbnails
    command: celery -A app.jobs.celery_app worker --concurrency=2 --loglevel=info

  celery-beat:
    build:
      context: ./backend
      dockerfile: ../docker/backend.Dockerfile
    env_file: .env
    environment:
      DATABASE_URL: mysql+pymysql://ytanalyzer:${MYSQL_PASSWORD}@mysql:3306/youtube_analyzer
      REDIS_URL: redis://redis:6379/0
    depends_on:
      - backend
    command: celery -A app.jobs.celery_app beat --loglevel=info --scheduler celery.beat:PersistentScheduler

  frontend:
    build:
      context: ./frontend
      dockerfile: ../docker/frontend.Dockerfile
    ports:
      - "3000:80"
    depends_on:
      - backend

  bgutil-pot:
    image: brainicism/bgutil-ytdlp-pot-provider:latest
    ports:
      - "4416:4416"
    profiles:
      - pot          # Only started with: docker compose --profile pot up

volumes:
  mysql_data:
  redis_data:
  downloads_data:
  thumbnails_data:
```

**`docker/backend.Dockerfile`:**
```dockerfile
FROM python:3.12-slim
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
```

**`docker/frontend.Dockerfile`:**
```dockerfile
FROM node:20-alpine AS builder
WORKDIR /app
COPY package*.json .
RUN npm ci
COPY . .
RUN npm run build

FROM nginx:alpine
COPY --from=builder /app/dist /usr/share/nginx/html
COPY ../docker/nginx.conf /etc/nginx/conf.d/default.conf
```

**`docker/nginx.conf`:** Configured to proxy `/api/` to `http://backend:5000/api/` and serve React static files for all other routes (enabling React Router).

---

### 17.3 Render Deployment

Render supports Docker-based deployments.

**Services to create on Render:**

1. **MySQL** — Use Render's managed MySQL service or a MySQL-compatible service (PlanetScale, Railway MySQL). Set `DATABASE_URL` in environment.

2. **Redis** — Use Render's managed Redis (Upstash Redis compatible). Set `REDIS_URL`.

3. **Backend web service** — Docker image from `docker/backend.Dockerfile`. Start command: `flask db upgrade && gunicorn --bind 0.0.0.0:$PORT --workers 2 --timeout 120 wsgi:app`. Set all env vars.

4. **Celery worker** — Same Docker image; start command: `celery -A app.jobs.celery_app worker --concurrency=2 --loglevel=info`. Background worker type on Render (no port needed).

5. **Celery beat** — Same image; start command: `celery -A app.jobs.celery_app beat --loglevel=info`.

6. **Frontend** — Static site. Build command: `cd frontend && npm ci && npm run build`. Publish directory: `frontend/dist`. Set `VITE_API_BASE_URL` to backend service URL.

**Persistent storage:** Render disks for downloads directory (`/data/downloads`). Without a persistent disk, downloads are lost on service restart.

**Memory:** Backend service: 512 MB minimum. Celery worker: 512 MB. Total: ~1.5 GB across services.

---

### 17.4 Railway Deployment

Railway supports Docker Compose partially. Recommended approach:

Deploy each service as a separate Railway service from the same repository, using the same Dockerfiles as the Render deployment. Railway provides managed MySQL and Redis as plugins.

**Environment variables** in Railway dashboard — set `DATABASE_URL` and `REDIS_URL` using Railway's generated service URLs.

**Volumes** — Railway does not provide persistent volumes on the free tier; use Railway's volume feature (paid) or configure S3-compatible storage for downloads.

---

### 17.5 Linux VPS Deployment

**Recommended approach:** Docker Compose on a VPS (Ubuntu 22.04+).

1. Install Docker + Docker Compose: `apt install docker.io docker-compose-v2`
2. Clone repository to `/opt/youtube-analyzer`
3. Copy `.env.example` to `.env`; set all production values
4. `docker compose up -d`
5. Configure Nginx reverse proxy on the host:
   - Port 3000 (frontend) → serve via Nginx at domain root
   - Port 5000 (backend API) → proxy at `/api/`
6. Configure Let's Encrypt SSL via Certbot

**File permissions:** `downloads_data` volume must be writable by the application user (uid 1000 by default in Python Docker images).

**Updates:**
```bash
git pull
docker compose build
docker compose up -d
```

Alembic migrations run automatically on backend container start.

---

### 17.6 Windows Local Development

**Option A (Recommended):** Docker Desktop for Windows — use Docker Compose exactly as Linux.

**Option B (Native):**
- Install Python 3.12 via python.org
- Install MySQL 8.0 via MySQL Installer for Windows
- Install Redis via WSL2 or Windows port
- Install FFmpeg via `winget install ffmpeg` or from ffmpeg.org
- All Python commands work natively in PowerShell/CMD
- Celery works natively on Windows (uses `solo` pool: add `--pool=solo` to worker command on Windows)

**Note on Celery on Windows:** The default prefork pool is not supported on Windows. Use `--pool=solo` for single-worker development: `celery -A app.jobs.celery_app worker --pool=solo --loglevel=info`. This limits concurrency to 1 but works correctly.

---

### 17.7 Environment Variables Reference

All environment variables with defaults:

| Variable | Required | Default | Description |
|---|---|---|---|
| `FLASK_ENV` | No | `production` | Application mode |
| `SECRET_KEY` | YES (prod) | — | Flask secret key; must be random 32+ chars |
| `DATABASE_URL` | YES | — | MySQL connection string |
| `REDIS_URL` | YES | `redis://redis:6379/0` | Redis connection |
| `CELERY_RESULT_BACKEND` | No | `redis://redis:6379/1` | Celery results |
| `DOWNLOAD_DIR` | No | `/data/downloads` | Download directory |
| `THUMBNAIL_DIR` | No | `/data/thumbnails` | Thumbnail cache directory |
| `YTDLP_COOKIES_PATH` | No | — | Path to cookies.txt |
| `YTDLP_PROXY` | No | — | Proxy URL |
| `YTDLP_PLAYER_CLIENT` | No | `ios` | Initial player client |
| `YTDLP_RATE_LIMIT` | No | `500K` | Download rate limit |
| `POT_PROVIDER_URL` | No | — | bgutil sidecar URL |
| `CORS_ORIGINS` | No | `http://localhost:5173` | Allowed CORS origins |
| `LOG_LEVEL` | No | `INFO` | Log verbosity |
| `MAX_CONCURRENT_DOWNLOADS` | No | `2` | Worker concurrency |
| `RSS_POLL_INTERVAL` | No | `60` | Minutes between RSS checks |
| `MYSQL_PASSWORD` | YES (Docker) | — | MySQL password (used in compose) |
| `MYSQL_ROOT_PASSWORD` | YES (Docker) | — | MySQL root password |

---

## 18. Future Extensions

All extensions are designed to be additive — they do not require changes to existing code, only additions.

### 18.1 Official YouTube Data API

**Extension point:** `backend/app/extraction/` and `backend/app/repositories/`

Add `YouTubeDataAPIClient` alongside `YtdlpClient`. Both implement the same interface (Python abstract base class or duck-typing protocol):
```
class ExtractionClientProtocol:
    def extract_video_metadata(url: str) -> dict: ...
    def extract_channel_metadata(url: str) -> dict: ...
    def extract_search_results(query: str, n: int) -> list[dict]: ...
```

`ChannelService` and `VideoService` receive the client via dependency injection. Switching from yt-dlp to the YouTube Data API is a configuration change (`EXTRACTION_BACKEND=youtube_api` env var).

The YouTube Data API supports batch video fetching (up to 50 per request) — significantly faster for channel crawls. This can reduce a 10,000-video channel crawl from hours to minutes.

**No database schema change required.**

---

### 18.2 OAuth and Channel Owner Analytics

Add `OAuthService` in `backend/app/services/` that manages Google OAuth 2.0 token storage and refresh. Tokens stored in a new `oauth_credentials` table (channel_id, access_token, refresh_token, expires_at).

Add `YouTubeAnalyticsClient` that calls YouTube Analytics API v2. Returns watch time, CTR, audience retention, etc.

Add new `analytics_controller` endpoints: `GET /api/analytics/channel/{id}/owner` — only accessible when OAuth credentials exist for that channel.

Frontend: Add "Connect Channel" button on Channel Detail page that initiates OAuth flow. Owner analytics tab shown only when connected.

**Database additions:** `oauth_credentials` table, `owner_analytics` table (for caching Analytics API results).

**No existing code modified.**

---

### 18.3 Social Blade Integration

Add `SocialBladeClient` in `backend/app/extraction/`. Fetches Social Blade's public channel statistics page and parses estimated subscriber history.

Data stored in `channel_snapshots` with `source='socialblade'` (add `source` column to `channel_snapshots`).

Analytics charts display Social Blade data as a separate dashed line with a disclaimer: "Estimates from Social Blade."

**One migration:** Add `source` column to `channel_snapshots`. Existing rows default to `source='ytdlp'`.

---

### 18.4 AI/LLM Analysis

Add `AIAnalysisService` in `backend/app/services/`. It reads from `transcripts` and `comments`, sends to an LLM API (configurable: Claude, OpenAI, or local Ollama), and stores results in `ai_analysis`.

The `ai_analysis` table is already created in Phase 1 migrations (schema in Section 8.14).

New endpoints under `analytics_controller`:
- `POST /api/ai/analyze/{video_id}` — triggers analysis job
- `GET /api/ai/analysis/{video_id}` — returns stored analysis

Supported analysis types (extensible via `analysis_type` field):
- `summary` — 3-paragraph summary of transcript
- `topics` — top 5 topics discussed
- `keywords` — top 20 keywords with frequency
- `sentiment` — overall sentiment + per-section sentiment
- `qa` — question-answering against transcript

Add `AI_PROVIDER`, `AI_API_KEY`, `AI_MODEL` to environment variables. Default `AI_PROVIDER=disabled` — feature does nothing when disabled.

**No existing code modified.**

---

### 18.5 Semantic Search and Vector Database

Add `pgvector` extension to PostgreSQL (or a Qdrant instance as a sidecar) — **note: this requires switching from MySQL to PostgreSQL** for the vector index, OR using a dedicated Qdrant Docker sidecar alongside MySQL.

**Recommended approach for MySQL-based stack:** Add Qdrant sidecar.

Add `VectorService` in `backend/app/services/`:
1. After transcript extraction: chunk transcript into 512-token segments
2. Embed each chunk via embedding model (Ollama `nomic-embed-text`, or OpenAI)
3. Store vectors in Qdrant collection `transcript_chunks`
4. Each vector carries metadata: `video_id`, `segment_start`, `text`

New endpoint: `GET /api/search/semantic?q={query}` — returns video_id + timestamp matches sorted by vector similarity.

`docker-compose.yml` addition:
```
qdrant:
  image: qdrant/qdrant:latest
  volumes:
    - qdrant_data:/qdrant/storage
  profiles:
    - semantic
```

**No existing code modified.**

---

### 18.6 Multi-User Authentication

Add `User` model (id, email, password_hash, created_at). Add `Organization` model for team use.

Add `user_id` foreign key to: `channels`, `videos` (tracked by), `playlists`, `download_history`, `search_history`.

Existing single-user records adopt `user_id=1` (system default user created in migration).

Add JWT authentication middleware: `POST /api/auth/login`, `POST /api/auth/register`, `POST /api/auth/refresh`. JWT stored in httpOnly cookie.

Frontend: Add login page; `axios` interceptor adds JWT to all requests.

All controllers add `@require_auth` decorator; services filter all queries by `current_user.id`.

**Migration:** Add `users` table; add `user_id` columns with default=1 to all affected tables.

---

### 18.7 Cloud Storage for Downloads

Add `StorageBackend` abstraction in `backend/app/utils/file_manager.py`:
```
class LocalStorageBackend:
    def save(path, data): ...
    def get_url(path): ...
    def delete(path): ...

class S3StorageBackend:
    def save(path, data): ...
    def get_url(path): ...   # Returns presigned URL
    def delete(path): ...
```

`DownloadService` uses `StorageBackend` (injected via `STORAGE_BACKEND=local|s3` env var).

Add `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `S3_BUCKET_NAME` to env vars.

**No existing code modified.** Downloads currently saved locally continue to work. S3 mode is activated by env var.

---

### 18.8 Plugin Architecture

For extensibility beyond the above planned features, add a `plugins/` directory in `backend/`. Each plugin is a Python package with a standardized interface:

```python
class PluginBase:
    name: str
    version: str
    
    def on_video_extracted(self, video: dict) -> None: ...
    def on_transcript_extracted(self, transcript: dict) -> None: ...
    def on_channel_added(self, channel: dict) -> None: ...
```

Plugins are discovered via Python entry points or by scanning the `plugins/` directory at startup. The `create_app()` factory loads and registers plugins.

Example plugins: `SponsorBlock` (fetches sponsor segments for extracted videos), `WordCloud` (generates word cloud from transcript), `ReturnYouTubeDislikes` (fetches estimated dislike count).

**No existing code modified.** Plugins are purely additive hooks.

---

*End of YouTube Analyzer Architecture & Planning Specification*  
*Document Version: 1.0 | July 2026*  
*Status: Final — Ready for Implementation*
