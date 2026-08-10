# YouTube Analyzer — Implementation Blueprint

**Document Type:** Implementation Blueprint  
**Version:** 1.0  
**Date:** July 2026  
**Status:** Final — Ready for Implementation  
**Prepared For:** Antigravity (AI Coding Agent)  
**Input Documents:** Engineering Research v1.0 · Architecture & Planning Specification v1.0

---

> **To the implementing agent:** This document is the final layer before code. Every screen, component, interaction, state, API call, chart, filter, and user flow is specified here. When this document is silent on a detail, defer to the Architecture Specification. When both are silent, use the simplest approach consistent with the established patterns. Do not invent new libraries, patterns, or abstractions not described in these three documents.

---

## Table of Contents

1. [Complete User Journey](#1-complete-user-journey)
2. [Complete Page Inventory](#2-complete-page-inventory)
3. [Component Library](#3-component-library)
4. [Dashboard Planning](#4-dashboard-planning)
5. [Channel Page](#5-channel-page)
6. [Video Page](#6-video-page)
7. [Downloader UX](#7-downloader-ux)
8. [Search Experience](#8-search-experience)
9. [Charts](#9-charts)
10. [Database Blueprint](#10-database-blueprint)
11. [API Blueprint](#11-api-blueprint)
12. [State Management](#12-state-management)
13. [File Storage](#13-file-storage)
14. [Error UX](#14-error-ux)
15. [Design System](#15-design-system)
16. [Implementation Order](#16-implementation-order)
17. [Developer Guidelines](#17-developer-guidelines)
18. [Final Implementation Checklist](#18-final-implementation-checklist)

---

## 1. Complete User Journey

This section maps every path a user takes through the application, from first launch to completion of every major workflow. Each journey step specifies what the user sees, what they can do, and what happens next.

---

### 1.1 First Launch Journey

```
App opens in browser (http://localhost:3000)
        ↓
AppShell renders: Sidebar (collapsed on mobile) + TopBar + Content area
        ↓
Route: / → redirect to /dashboard
        ↓
Dashboard loads with empty state:
  - Stat cards show: Channels: 0 | Videos: 0 | Transcripts: 0 | Downloads: 0
  - Active Jobs: "No active jobs"
  - Recent Activity: "No recent activity"
  - RSS Discoveries: "No channels monitored yet"
  - Storage: "0 B used"
        ↓
User sees "Add Your First Channel" CTA button in the Channels stat card
        ↓
→ Journey branches to: Add Channel, Search YouTube, or Direct Video URL
```

---

### 1.2 Add Channel Journey

```
User clicks "Add Channel" (from sidebar nav or dashboard CTA)
        ↓
Route: /channels
  Empty state: "No channels tracked yet" + "Add Channel" button
        ↓
User clicks "Add Channel"
        ↓
AddChannelModal opens
  Input field: "YouTube channel URL or @handle"
  Checkbox: "Crawl all videos after adding" (unchecked by default)
  Button: "Add Channel" (primary) | "Cancel" (ghost)
        ↓
User types: https://youtube.com/@mkbhd  OR  @mkbhd
        ↓
User clicks "Add Channel"
        ↓
Button shows spinner, becomes disabled
Frontend calls: POST /api/channels {url: "https://youtube.com/@mkbhd", crawl_videos: false}
        ↓
Response 202: {channel_id: "UCxxxxxx", job_id: "uuid", status: "created"}
        ↓
Modal closes
Toast: "Channel added — extracting metadata..." (info, persists until job complete)
        ↓
Frontend polls GET /api/jobs/{job_id} every 3 seconds
JobStatusBadge appears on TopBar (pulsing dot + "1 job")
        ↓
Job completes (5–10 seconds)
Toast: "Channel metadata extracted successfully" (success, auto-dismisses)
        ↓
Channel card appears in /channels grid
  Avatar | Display name | Handle | Subscriber count | Video count | Verified badge
        ↓
User clicks channel card → /channels/:channelId
        ↓
Channel Detail page loads (see Section 5)
```

---

### 1.3 Channel Video Crawl Journey

```
User is on /channels/:channelId (Channel Detail page)
        ↓
User clicks "Crawl Videos" button
        ↓
CrawlConfirmModal opens:
  "This will extract metadata for all videos in this channel."
  "Estimated: {video_count} videos. This may take several minutes."
  Options: Max videos (unlimited / 100 / 500 / 1000)
  Button: "Start Crawl" | "Cancel"
        ↓
User clicks "Start Crawl"
        ↓
POST /api/channels/{channelId}/crawl {max_videos: 0, crawl_type: "all"}
Response 202: {job_id: "uuid"}
        ↓
Modal closes
Toast: "Channel crawl started — this may take several minutes"
        ↓
JobProgressPanel appears on Channel Detail page (collapses when job ends)
  Shows: "Crawling channel videos..."
  Progress bar + percentage
  Real-time via SSE: "Extracted 47 of 342 video stubs"
        ↓
Job completes
Toast: "Crawl complete — 342 videos discovered"
Videos tab on Channel Detail now populated with stubs
        ↓
Stub videos show title, thumbnail, upload date, duration
  (Full metadata extracted in background at low priority)
Full metadata appears progressively as individual jobs complete
```

---

### 1.4 Video Analysis Journey

```
User navigates to a video (from channel video list, search results, or direct URL)
        ↓
Route: /videos/:videoId
        ↓
[If video already fully extracted]
Video Detail page loads immediately with all metadata
        ↓
[If video is a stub (title only)]
Video Detail page shows skeleton for missing fields
Background extraction job runs automatically
Fields populate as data arrives (polling GET /api/videos/:videoId every 5s until complete)
        ↓
User sees:
  - Thumbnail (full width, 16:9)
  - Title + channel link + upload date + duration
  - Stats: Views | Likes | Comments
  - Action buttons: Download Video | Download Audio | Extract Transcript | Extract Comments | Refresh
  - Tabs: Description | Formats | Chapters | Transcript | Comments
        ↓
User clicks "Description" tab (default active):
  Full description text displayed
  Tags shown as chips
  Categories shown as chips
        ↓
User clicks "Transcript" tab:
  [If transcript not extracted]
    Empty state: "No transcript stored yet"
    Button: "Extract Transcript"
    Language selector (default: English)
  [If transcript exists]
    TranscriptViewer: timed segments
    Search input at top
    Language selector
    Export button (txt/srt/json)
        ↓
User clicks "Extract Transcript"
        ↓
POST /api/transcripts/{videoId} {lang: "en"}
Response 202: {job_id: "uuid"}
Toast: "Extracting transcript..."
Progress shown via SSE
On complete: Transcript tab auto-refreshes with content
        ↓
User searches transcript: types "climate change" in TranscriptSearch
  Matching segments highlighted in yellow
  Scroll-to-first-match
  Match count shown: "3 matches"
        ↓
User clicks "Download Video"
        ↓
DownloadModal opens (see Section 7 for full UX)
```

---

### 1.5 Search Journey

```
User clicks "Search" in sidebar  OR  types in TopBar search input
        ↓
Route: /search
        ↓
Search page loads:
  Large search bar (centered, prominent)
  Mode toggle: ● Search YouTube  ○ Search My Library
  Submit button
        ↓
[YouTube Search mode]
User types "python tutorial beginner" → clicks Search or presses Enter
        ↓
GET /api/search/youtube?q=python+tutorial+beginner&type=video&max_results=20
Loading: skeleton cards (6 placeholders)
        ↓
Results appear:
  VideoCard grid (3 columns desktop)
  Each card: thumbnail, title, channel, duration, view count, upload date
  Each card: "Add to Library" button
        ↓
User clicks "Add to Library" on a result
  POST /api/videos {"url": "https://youtube.com/watch?v=..."}
  Button becomes "Added ✓" (disabled)
  Toast: "Video added to library"
        ↓
[My Library mode]
User switches to "Search My Library"
Additional filters appear:
  Entity type: Videos | Channels | Transcripts
  Has transcript: toggle
  Is Short: toggle
  Date range: from / to pickers
  Channel filter: dropdown of tracked channels
        ↓
User types "machine learning" → searches
GET /api/search/internal?q=machine+learning&type=video&page=1&per_page=20
Results show videos from local DB with FULLTEXT match highlighting
Pagination at bottom
```

---

### 1.6 Download Journey

```
[Entry point A: from Video Detail page]
User clicks "Download Video" on /videos/:videoId
        ↓
DownloadModal opens:
  Video title shown at top
  Quality selector: Best | 1080p | 720p | 480p | 360p | Worst
  Format selector: MP4 | WebM
  Estimated size shown when quality selected (from formats_available)
  Button: "Download" | "Cancel"
        ↓
User selects 1080p MP4 → clicks Download
        ↓
POST /api/downloads/video {video_id: "xxx", quality: "1080p", format: "mp4"}
        ↓
[If already downloaded] → Response 409: "Already downloaded"
  Modal shows: "File already exists: /downloads/videos/xxx/xxx_1080p.mp4"
  Buttons: "Open Location" | "Download Again" | "Close"
        ↓
[If new download] → Response 202: {download_id: 42, job_id: "uuid"}
  Modal closes
  Toast: "Download queued"
        ↓
Active downloads section appears on Downloader page (accessible from sidebar)
Progress card shows:
  Thumbnail + Title
  Type: Video | Quality: 1080p | Format: MP4
  Progress bar (0→100%)
  Speed: "12.4 MB/s" | ETA: "0:45"
  Cancel button (X)
        ↓
Download completes
Toast: "Download complete: {video title}"
Progress card shows green "Complete" state for 5 seconds, then moves to history
        ↓
[Entry point B: from Downloader page direct URL]
User navigates to /downloader
Quick Download form at top:
  URL input: "Paste YouTube URL"
  Type: Video | Audio | Subtitle | Thumbnail
  [Type-specific options appear below]
  Download button
        ↓
User pastes URL + selects Audio + MP3 + 192k
POST /api/downloads/audio {video_id: (extracted from URL), format: "mp3", quality: "192k"}
Same progress flow as above
```

---

### 1.7 Transcript Export Journey

```
User is viewing a transcript on /videos/:videoId (Transcript tab)
        ↓
User clicks "Export" button
        ↓
ExportDropdown appears (inline, not a modal):
  ● Plain Text (.txt)
  ● SRT Subtitles (.srt)
  ● JSON (.json)
        ↓
User clicks "Plain Text (.txt)"
        ↓
GET /api/transcripts/{videoId}/export?format=txt&lang=en
Browser downloads file: {video_title}.en.txt
Toast: "Transcript exported"
```

---

### 1.8 Analytics Journey

```
User is on /channels/:channelId → clicks "Analytics" tab
        ↓
[If no snapshots yet (channel just added)]
Empty state:
  "Growth data will appear here after daily snapshots run."
  "First snapshot collected at 2:00 AM UTC."
  Info banner: "Snapshots are collected automatically every 24 hours."
        ↓
[If snapshots exist]
Analytics tab shows:

1. Growth Chart (full width)
   Title: "Subscriber Growth"
   Date range selector: 7d | 30d | 90d | 1y
   LineChart: date (x) × subscriber count (y)
   Second line toggle: View Count (right y-axis)

2. Upload Frequency Chart
   BarChart: month (x) × videos published (y)
   Last 12 months shown

3. Top Videos by Views (horizontal bar chart)
   Top 10 videos, bars show relative view counts
   Click bar → navigate to /videos/:videoId

4. Duration Distribution
   BarChart: duration buckets × video count
   Buckets: <1m | 1-5m | 5-10m | 10-20m | 20-60m | >60m

5. Stats Summary row
   Total Views Tracked | Average Views/Video | Shorts % | Transcripts %
```

---

### 1.9 Settings Journey

```
User clicks Settings icon (gear) in TopBar or sidebar
        ↓
Route: /settings
        ↓
Settings page with sectioned cards:

Card 1: Download Settings
  Download directory: /data/downloads [text input]
  Default video quality: [dropdown: best / 1080p / 720p / 480p / 360p / worst]
  Default audio format: [dropdown: mp3 / m4a / opus / wav]
  Default audio quality: [dropdown: best / 320k / 192k / 128k / worst]
  Max concurrent downloads: [number 1-5]
  [Save] button

Card 2: Extraction Settings
  Auto-extract transcript on video add: [toggle]
  Auto-extract comments on video add: [toggle]
  Auto-extract thumbnail on video add: [toggle, default ON]
  Max comments per video: [number input, default 500]
  [Save] button

Card 3: yt-dlp / Bot Detection
  Player client: [dropdown: ios / web_safari / android / mweb]
  Download rate limit: [text input: "500K"]
  Proxy URL: [text input, placeholder: "socks5://127.0.0.1:1080"]
  PoToken provider URL: [text input, placeholder: "http://localhost:4416"]
  Cookies file:
    [If no cookie] "No cookies file configured"
    Upload button: [Choose File] (accepts .txt)
    [If cookie exists] Shows file path + "Test Cookies" button + "Delete" button
  [Save] button

Card 4: Monitoring
  RSS poll interval: [number input] minutes
  Daily snapshots enabled: [toggle]
  [Save] button

Card 5: System Info (read-only)
  yt-dlp version: 2026.07.04
  FFmpeg available: ✓ Yes
  Database: MySQL 8.0
  Videos in DB: 3,847
  Transcripts in DB: 2,910
  Storage used: 48.5 GB
```

---

### 1.10 Jobs Monitoring Journey

```
User notices pulsing dot on TopBar (active jobs indicator)
        ↓
User clicks the indicator OR navigates to /jobs
        ↓
Jobs page:
  Filter bar: [All] [Queued] [Processing] [Complete] [Failed] [Cancelled]
  Job type filter: [All types] [Metadata] [Channel Crawl] [Download] [Transcript] [Comments]
  Date range: [Last 24h ▾]
        ↓
Jobs table:
  Columns: Type | Target | Status | Progress | Created | Duration | Actions
  
  Row example (processing):
    📺 Channel Crawl | MrBeast | ● Processing | ████░░ 68% | 2 min ago | 1m 23s | [Cancel]
  
  Row example (failed):
    📄 Transcript | "Python Tutorial" | ✗ Failed | — | 10 min ago | 0m 8s | [Retry]
  
  Row example (complete):
    ⬇ Download | "Study Music Mix" | ✓ Complete | ████████ 100% | 1h ago | 4m 12s | —
        ↓
User clicks a failed job row
        ↓
Job Detail Modal opens:
  Job ID: abc-def-123
  Type: Transcript Extract
  Target: "Python Tutorial for Beginners" (link to video)
  Status: Failed (after 3 retries)
  Error:
    [code block]
    TranscriptNotAvailableError: No transcript available for video xxxxxxxxxxx
    Available languages: []
    [/code block]
  Timeline: Created 10:30:01 → Started 10:30:03 → Failed 10:30:09
  Retry count: 3/3
  [Close] button
```

---

### 1.11 RSS Monitoring Journey

```
User is on /channels/:channelId
        ↓
User clicks "Monitor" toggle (currently OFF → turns ON)
        ↓
PATCH /api/channels/{channelId} {rss_monitoring: true}
Toggle turns ON (indigo)
Toast: "RSS monitoring enabled — new videos will be detected automatically"
        ↓
[60 minutes later, background job runs]
RSS feed checked for this channel
        ↓
[If new video found]
New video stub created in DB
Job queued: extract_video_metadata (priority=3, high)
        ↓
Next time user visits Dashboard:
"RSS Discoveries" card shows:
  "3 new videos discovered in the last 24 hours"
  List: [thumbnail] "New Video Title" — MrBeast — 2h ago [Extract Metadata]
```

---

## 2. Complete Page Inventory

Each page below specifies every element, state, and behavior. Nothing should be inferred.

---

### 2.1 Dashboard Page (`/dashboard`)

**Purpose:** Command center showing platform health, recent activity, and quick actions.

**Layout:** 2-column grid on desktop (lg:grid-cols-3), stacked on mobile.

---

**Section A: Stats Bar** — Full width, 4 cards in a row (grid-cols-2 sm:grid-cols-4)

| Card | Icon | Value | Label | Color accent |
|---|---|---|---|---|
| Channels | `Tv` | DB count | "Channels Tracked" | Indigo |
| Videos | `Play` | DB count | "Videos Tracked" | Blue |
| Transcripts | `FileText` | DB count | "Transcripts" | Green |
| Downloads | `Download` | DB count | "Downloads" | Amber |

Each stat card: white background, rounded-xl, p-6, shadow-sm. Icon in colored circle (bg-indigo-50). Large number (text-3xl font-bold text-gray-900). Label (text-sm text-gray-500). Click → navigates to relevant list page.

**Loading state:** Skeleton — gray rectangle matching number size, pulse animation.

---

**Section B: Active Jobs Panel** — Left column, top

Title: "Active Jobs" (text-lg font-semibold) + animated pulsing dot if jobs active.

**If jobs active:** List of JobCard components (max 5 shown, "View all →" link to /jobs).

Each JobCard:
- Icon for job type (📺 channel crawl, ⬇ download, 📄 transcript, etc.)
- Job type label + target name (truncated to 40 chars)
- Status badge
- Progress bar (thin, colored by status)
- Age: "Started 2m ago"
- Cancel button (X icon, small)

**If no active jobs:** EmptyState — "No active jobs" (muted, no icon, no CTA).

---

**Section C: Recent Discoveries** — Left column, below jobs

Title: "RSS Discoveries (24h)"

**If RSS discoveries exist:** List of up to 5 entries:
- Thumbnail (40×40, rounded)
- Video title (truncated 50 chars)
- Channel name (text-xs text-gray-500)
- Age: "2h ago"
- "Extract Metadata" button (ghost, xs)

**If no discoveries:** "No new videos discovered. Enable RSS monitoring on a channel."

---

**Section D: Recent Activity** — Right column, top

Title: "Recent Activity"

Timeline list (last 10 completed/failed jobs):
Each item:
- Icon (✓ green for complete, ✗ red for failed, ⏳ amber for retrying)
- Job type + target name
- "Completed 5m ago" or "Failed 12m ago"
- Duration: "took 1m 23s"

**If no activity:** "No recent activity."

---

**Section E: Storage Usage** — Right column, bottom

Title: "Storage"

Progress bar: indigo fill, full width.
Labels: "48.5 GB used of 500 GB" (right-aligned percentages)
Sub-items breakdown:
- Videos: 45.2 GB
- Audio: 2.1 GB
- Thumbnails: 0.8 GB
- Subtitles: 0.4 GB

**If storage unquantifiable (VPS without disk info):** Show "N/A — storage info unavailable"

---

**Section F: Monitored Channels** — Right column (below storage), compact list

Title: "Monitored Channels" + count badge

List of channels with RSS monitoring enabled:
- Avatar (24px) + display name + "● Active" indicator
- Last checked: "15m ago"
- "View" link

**If none:** "No channels monitored. Enable on a channel page."

---

**Dashboard responsive behavior:**
- Mobile (< 640px): All sections stack vertically; stats bar is 2×2 grid
- Tablet (640–1024px): Stats bar is 4-col; rest is 1-col stack
- Desktop (1024px+): Left column (2/3) contains jobs + discoveries; right column (1/3) contains activity + storage

---

### 2.2 Channel List Page (`/channels`)

**Purpose:** Browse all tracked channels, add new ones.

**Header row:** "Channels" (h1) + count badge ("12 channels") + "Add Channel" button (indigo, right-aligned)

**Toolbar:** Search input (w-64) + Sort dropdown + Monitoring filter toggle

- Search: placeholder "Search by name or @handle", filters grid in real-time (debounced 300ms)
- Sort: Name A–Z | Name Z–A | Subscribers (high→low) | Last Crawled | Date Added
- Monitoring filter: "All" | "Monitored only" | "Not monitored"

**Channel Grid:** `grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6`

**ChannelCard anatomy:**
```
┌─────────────────────────────────┐
│  [Avatar 56px]  Display Name    │
│                 @handle         │
│                 ✓ Verified      │
│─────────────────────────────────│
│  👥 1.5M subs   📹 342 videos  │
│  🔴 Monitoring   🕐 2h ago     │
│─────────────────────────────────│
│  [View]    [↻ Refresh]  [🗑️]   │
└─────────────────────────────────┘
```

- Avatar: 56px circle, gray background fallback if no avatar
- Display name: font-semibold text-gray-900
- Handle: text-sm text-gray-500
- Verified badge: blue checkmark (Lucide `BadgeCheck`) if is_verified
- Stats row: subscriber count (formatted: 1.5M, 342K, etc.) + video count
- Monitoring indicator: red pulsing dot if rss_monitoring=true
- Last crawled: relative time ("2h ago", "Never")
- View button: navigates to /channels/:channelId
- Refresh button: icon-only, triggers refresh job, shows spinner while pending
- Delete button: icon-only (trash), opens ConfirmDialog

**Add Channel Modal:**
- Title: "Add YouTube Channel"
- Input: full width, placeholder "https://youtube.com/@channelname or @handle"
- Validation: shows inline red error if format invalid
- Checkbox: "Crawl all videos immediately after adding"
- Buttons: "Add Channel" (indigo, full width) | "Cancel" (ghost, full width)
- Loading state: button shows spinner, input disabled

**Empty state (no channels):**
```
[TV icon, large, gray]
"No channels tracked yet"
"Add a YouTube channel to start analyzing content"
[Add Your First Channel] button
```

**Loading state:** 6 skeleton cards matching ChannelCard dimensions.

**Error state:** Red banner "Failed to load channels — [Try Again]"

**Pagination:** Shown only if >20 channels. Standard Pagination component.

---

### 2.3 Channel Detail Page (`/channels/:channelId`)

**Purpose:** Complete channel profile with all metadata, videos, playlists, analytics, and links.

**Full specification in Section 5.**

---

### 2.4 Video Detail Page (`/videos/:videoId`)

**Purpose:** Complete video analysis hub.

**Full specification in Section 6.**

---

### 2.5 Playlist Detail Page (`/playlists/:playlistId`)

**Purpose:** Show playlist metadata and all member videos in order.

**Header:**
- Thumbnail (left, 160×90, rounded-lg)
- Title (text-2xl font-bold)
- Uploader name (link to channel if known)
- Video count badge + Privacy status badge (Public/Unlisted)
- Last crawled: "Crawled 2h ago"
- Buttons: "Refresh Playlist" | "Delete Playlist"

**Stats row:** 3 cards — Total Videos | Tracked Videos | Total Duration

**Video list:**
Ordered table (not a grid — preserves ordinal position):

| # | Thumbnail | Title | Duration | Views | Upload Date | Actions |
|---|---|---|---|---|---|---|
| 1 | [img] | Video Title | 10:23 | 1.2M | Jan 15, 2026 | View |
| 2 | [img] | Video Title | 5:44 | 847K | Jan 8, 2026 | View |

- Position number (bold, gray, fixed width)
- Thumbnail (60×34, rounded)
- Title links to /videos/:videoId
- "Not extracted" label if video is a stub (title only, no metadata)
- Pagination: 20 videos per page

**Empty state:** Playlist with 0 videos: "This playlist appears to be empty."

**Loading state:** Skeleton header + 5 skeleton table rows.

**Responsive:** On mobile, table collapses to card list (position + thumbnail + title only).

---

### 2.6 Search Page (`/search`)

**Purpose:** Search YouTube and local database.

**Full specification in Section 8.**

---

### 2.7 Downloader Page (`/downloader`)

**Purpose:** Download management hub.

**Full specification in Section 7.**

---

### 2.8 Jobs Page (`/jobs`)

**Purpose:** Monitor all background jobs.

**Header:** "Jobs" (h1) + active count badge (pulsing if > 0)

**Filter bar:**
- Status tabs: All | Queued | Processing | Complete | Failed | Cancelled
- Job type filter: dropdown (All Types | Metadata | Channel Crawl | Transcript | Comments | Download | Snapshot | RSS Check)
- Date filter: Last 1h | Last 24h | Last 7 days | All time

**Jobs table:**

| Column | Width | Content |
|---|---|---|
| Type | 140px | Icon + label ("Channel Crawl", "Download", etc.) |
| Target | flex | Video/channel title (link to detail page) |
| Status | 120px | StatusBadge component |
| Progress | 140px | Thin progress bar + "68%" |
| Created | 100px | "2m ago" (relative time) |
| Duration | 80px | "1m 23s" or "—" if not started |
| Actions | 80px | Context-dependent buttons |

**Actions column logic:**
- status=queued → [Cancel] button
- status=processing → [Cancel] button
- status=failed → [Retry] button
- status=complete → no button
- status=cancelled → no button

**Row click → Job Detail Modal:**

```
Modal title: "Job Details"
Body:
  Job ID: [monospace text, copy button]
  Type: Channel Crawl
  Status: [StatusBadge]
  Target: "MrBeast" [link]
  Created: 2026-07-28 12:00:01 UTC
  Started: 2026-07-28 12:00:03 UTC
  Completed: 2026-07-28 12:01:26 UTC
  Duration: 1m 23s
  Retries: 0 of 3

  [If failed]
  Error Details:
  ┌──────────────────────────────────────┐
  │ YouTubeBotDetectedError: Bot check   │
  │ triggered on player client 'ios'.    │
  │ All retry attempts exhausted.        │
  └──────────────────────────────────────┘

  [If payload useful]
  Parameters: {max_videos: 0, crawl_type: "all"}

Footer: [Retry] (if failed) | [Close]
```

**Loading state:** Skeleton table rows (8 placeholders).

**Empty state:** "No jobs match your filters." (if filtered) or "No jobs yet — add a channel to get started." (if no jobs at all)

**Pagination:** 20 per page.

**Auto-refresh:** Jobs list polls GET /api/jobs every 10 seconds while any job is processing. Stops polling when no processing jobs visible.

---

### 2.9 Settings Page (`/settings`)

**Purpose:** All configurable platform settings.

**Full specification in Section 1.9 (Journey) and 14.9 (Architecture Spec).**

**Additional detail — Cookie section flow:**

**State A: No cookies:**
```
[No cookies file configured]
[Upload Cookies File] button → opens file picker (accepts .txt only)
Hint text: "Export from browser using EditThisCookie or similar extension (Netscape format)"
```

**State B: Uploading:**
```
[Uploading... ████░░░░ 60%]
```

**State C: Cookies uploaded:**
```
File: /config/youtube_cookies.txt (uploaded Jul 28, 2026)
[Test Cookies] [Delete Cookies]
```

**After clicking Test Cookies:**
- Button shows spinner
- POST /api/settings/cookies/test
- Result shows inline: "✓ Cookies are valid" (green) or "✗ Cookies appear expired" (red)

---

### 2.10 Not Found Page (`*` route)

```
Centered content (vertically and horizontally):
  [Large "404" text, text-8xl font-bold text-gray-200]
  "Page Not Found"
  "The page you're looking for doesn't exist."
  [Go to Dashboard] button (indigo)
```

AppShell still renders (sidebar + topbar visible).

---

### 2.11 Error Pages

**500 / Unexpected Error (ErrorBoundary):**
```
Centered content:
  [AlertCircle icon, large, red]
  "Something went wrong"
  "An unexpected error occurred. The error has been logged."
  [↻ Reload Page] button
  [text-xs text-gray-400] "Error ID: {request_id if available}"
```

---

## 3. Component Library

Every reusable component is specified below with purpose, props, variants, states, and reuse locations.

---

### 3.1 Layout: `AppShell`

**Purpose:** Root layout wrapper providing sidebar, topbar, and content area for all pages.

**Props:** `children: ReactNode`

**Structure:**
```
<div class="flex h-screen bg-gray-50 overflow-hidden">
  <Sidebar />
  <div class="flex-1 flex flex-col overflow-hidden">
    <TopBar />
    <main class="flex-1 overflow-y-auto p-6">
      <div class="max-w-[1400px] mx-auto">
        {children}
      </div>
    </main>
  </div>
</div>
```

**States:** No special states. Always renders.

---

### 3.2 Layout: `Sidebar`

**Purpose:** Left navigation with all main routes.

**Width:** 240px (desktop), 0px hidden (mobile, toggled by hamburger in TopBar).

**Navigation items** (in order):
```
[YTA Logo + "YouTube Analyzer" text]
──────────────────────
Dashboard        /dashboard      [LayoutDashboard icon]
──────────────────────
Channels         /channels       [Tv icon]
Search           /search         [Search icon]
Downloader       /downloader     [Download icon]
Jobs             /jobs           [Activity icon]  [job count badge]
──────────────────────
Settings         /settings       [Settings icon]
──────────────────────
[Collapse ‹] button at bottom
```

**Active state:** Active route item has `bg-indigo-50 text-indigo-700 font-medium rounded-lg`.

**Inactive state:** `text-gray-600 hover:bg-gray-100 rounded-lg`.

**Job count badge:** Small red circle with number, shown on Jobs item when active jobs > 0.

**Responsive:**
- Desktop: always visible, fixed
- Mobile: hidden, toggled via TopBar hamburger button; slides in over content with backdrop

---

### 3.3 Layout: `TopBar`

**Purpose:** Top navigation bar with search, job indicator, and user actions.

**Height:** 64px, fixed.

**Left:** Hamburger menu button (mobile only) + breadcrumb (current page title)

**Center:** Search input bar
- Placeholder: "Search YouTube or type a URL..."
- On focus: expands width slightly, shows dropdown with recent searches
- On enter (if URL detected): navigates to /videos extract flow
- On enter (if text): navigates to /search?q={term}

**Right:**
- Jobs indicator: animated pulsing dot (red if failed jobs, amber if processing, none if idle) + job count
- Settings icon button (navigates to /settings)

---

### 3.4 `ChannelCard`

**Purpose:** Summary card for a channel in list views.

**Props:**
```javascript
{
  channel: {
    channel_id, handle, display_name, subscriber_count,
    video_count, avatar_url, is_verified, rss_monitoring,
    last_crawled_at, created_at
  },
  onRefresh: () => void,
  onDelete: () => void
}
```

**Variants:** Default (list), Compact (used in TopVideos lists on analytics)

**States:**
- Default: static card
- Refreshing: refresh button shows spinner icon (spin animation), card slightly dimmed
- Deleting: skeleton overlay, then card removed from grid

**Sub-elements:**
- Avatar: `<img loading="lazy">` with gray circle fallback (first letter of display_name)
- Subscriber count formatted: `formatNumber(1500000)` → "1.5M"
- Monitoring badge: red pulsing `●` dot + "Monitoring" text (text-xs)
- Last crawled: `formatRelativeTime(last_crawled_at)` → "2h ago"

**Reuse:** `/channels` grid, any future comparison views.

---

### 3.5 `VideoCard`

**Purpose:** Thumbnail-first card for a video in grid views.

**Props:**
```javascript
{
  video: {
    video_id, title, channel, channel_id, thumbnail_url,
    duration_seconds, view_count, like_count, upload_date,
    is_short, availability, has_transcript
  },
  onAddToLibrary?: () => void,  // shown for search results
  showChannel?: boolean          // default true
}
```

**Variants:**
- `grid` (default): 16:9 thumbnail + metadata below
- `horizontal`: thumbnail left + metadata right (used in search results)
- `stub`: dimmed overlay with "Loading..." on thumbnail (for incomplete metadata)

**Card anatomy:**
```
┌─────────────────────────────────┐
│  [Thumbnail 16:9]               │
│  [is_short badge] [duration]    │
├─────────────────────────────────┤
│  Title (2 lines max, truncate)  │
│  Channel name                   │
│  👁 1.2M  ·  📅 Jan 15, 2026  │
│  [transcript badge if exists]   │
└─────────────────────────────────┘
```

- Duration overlay: bottom-right of thumbnail, black semi-transparent pill
- Shorts badge: top-left of thumbnail, red "Shorts" pill
- Transcript badge: small "T" badge (green) if has_transcript=true
- Unavailable overlay: gray overlay + "Unavailable" text if availability≠public

**Click behavior:** Navigate to /videos/:videoId

**Reuse:** Channel detail videos tab, search results, playlist detail.

---

### 3.6 `VideoTable`

**Purpose:** Dense tabular view of videos with sortable columns. Used when user needs to compare many videos efficiently.

**Props:**
```javascript
{
  videos: Video[],
  sortBy: string,
  sortOrder: 'asc' | 'desc',
  onSort: (column) => void,
  onRowClick: (videoId) => void,
  loading: boolean,
  emptyMessage: string
}
```

**Columns (all sortable):**
| Column | Width | Format |
|---|---|---|
| Thumbnail | 60px | Small 60×34 img |
| Title | flex | Text, truncated, links to video |
| Duration | 70px | "10:23" |
| Views | 90px | "1.2M" |
| Likes | 80px | "45K" or "—" |
| Upload Date | 110px | "Jan 15, 2026" |
| Transcript | 80px | ✓ or — |
| Actions | 60px | "View" link |

**Sort indicator:** ▲▼ arrows on active column header.

**Loading state:** 8 skeleton rows.

**Reuse:** Channel detail videos tab (when switched from grid view), search results (list mode).

---

### 3.7 `TranscriptViewer`

**Purpose:** Display a video's timed transcript with search and navigation.

**Props:**
```javascript
{
  segments: [{text: string, start: number, duration: number}],
  fullText: string,
  languageCode: string,
  isAutoGenerated: boolean,
  availableLanguages: [{language_code, name}],
  onLanguageChange: (code) => void,
  onExport: (format) => void
}
```

**Layout:**
```
[Language selector ▾]  [Auto-generated badge]  [Export ▾]
[Search input: "Search transcript..."]  [3 matches ▾ ▲]
─────────────────────────────────────────────────────────
00:00  Hello everyone, welcome back to the channel...
00:08  Today we're going to be talking about...
00:15  [highlighted] climate change and its effects on...
00:23  the global ecosystem. Let me show you...
```

**Segment format:** `{start_time}  {text}`

Start time formatted as MM:SS or HH:MM:SS.

**Search behavior:**
- Debounced 300ms
- Case-insensitive substring match
- Highlights matching text in segments (yellow `<mark>` background)
- Shows match count: "3 matches"
- Up/down arrows scroll to prev/next match
- Non-matching segments dimmed (opacity-40)

**Language selector:** Dropdown listing all available languages. On change: re-fetch transcript for new language.

**Export dropdown:** Plain Text | SRT | JSON — triggers GET /api/transcripts/{id}/export

**Auto-generated badge:** Amber badge "Auto-generated" shown if is_autoGenerated=true.

**Empty state:** No segments → "Transcript is empty."

**Reuse:** Video Detail page (Transcript tab), full-screen transcript view.

---

### 3.8 `CommentThread`

**Purpose:** Display threaded comment with nested replies.

**Props:**
```javascript
{
  comment: {
    comment_id, author_display_name, text, like_count,
    reply_count, is_creator_comment, is_pinned, published_at,
    replies: Comment[]
  }
}
```

**Top-level comment anatomy:**
```
[Author Avatar 32px]  Author Name  [Creator badge]  [Pinned badge]
                      Comment text (full, no truncation)
                      👍 1.2K  ·  Jan 15, 2026
                      [Show 12 replies ▾]
```

**Replies (indented 48px):**
```
  [Avatar 24px]  Author Name  [Creator badge]
                 Reply text
                 👍 234  ·  Jan 16, 2026
```

**Creator badge:** "Creator" in indigo pill.

**Pinned badge:** "Pinned" in gray pill with 📌 icon.

**Show replies toggle:** Collapses/expands replies. Default: collapsed if > 3 replies.

**Reuse:** Video Detail Comments tab.

---

### 3.9 `JobProgressBar`

**Purpose:** Visual progress indicator for background jobs.

**Props:**
```javascript
{
  percent: number,      // 0–100
  status: 'queued' | 'processing' | 'complete' | 'failed' | 'cancelled',
  operation?: string,   // e.g. "Extracting video 47 of 342"
  speed?: string,       // e.g. "12.4 MB/s"
  eta?: string          // e.g. "0:45"
}
```

**Variants by status:**
- `queued`: Gray bar, 0%, "Waiting in queue..."
- `processing`: Indigo animated bar, shows percent
- `complete`: Green bar, 100%, "Complete"
- `failed`: Red bar, shows last percent, "Failed"
- `cancelled`: Gray bar, shows last percent, "Cancelled"

**Bar anatomy:** Full-width container, 6px height, rounded. Inner fill with transition (duration-300).

**Operation text:** Below bar, text-xs text-gray-500, truncated.

**Speed + ETA:** Shown right-aligned below bar during downloads only.

**Reuse:** Jobs page table, active downloads panel, Dashboard active jobs panel.

---

### 3.10 `DataTable`

**Purpose:** Generic sortable table for any tabular data.

**Props:**
```javascript
{
  columns: [{
    key: string,
    header: string,
    render: (row) => ReactNode,
    sortable?: boolean,
    width?: string
  }],
  data: object[],
  sortBy?: string,
  sortOrder?: 'asc' | 'desc',
  onSort?: (key) => void,
  onRowClick?: (row) => void,
  loading?: boolean,
  emptyMessage?: string,
  emptyIcon?: LucideIcon,
  stickyHeader?: boolean
}
```

**States:**
- Loading: skeleton rows (count = Math.min(data.length || 5, 8))
- Empty: EmptyState component centered in table body
- Error: not handled here — parent handles before passing data

**Header:** Sortable columns show ▲▼ sort indicator. Active column highlighted.

**Row hover:** `hover:bg-gray-50` + optional cursor-pointer if onRowClick provided.

**Reuse:** Jobs page, Downloads page (history), Video formats tab, Playlist video list.

---

### 3.11 `Modal`

**Purpose:** Portal-based overlay modal for all dialogs.

**Props:**
```javascript
{
  isOpen: boolean,
  onClose: () => void,
  title: string,
  size?: 'sm' | 'md' | 'lg' | 'xl',  // default: 'md'
  children: ReactNode,
  footer?: ReactNode
}
```

**Sizes:** sm=384px | md=512px | lg=672px | xl=800px

**Behavior:**
- Rendered in React Portal (appended to `document.body`)
- Backdrop: fixed inset-0, bg-black/50, backdrop-blur-sm
- Click backdrop → closes modal (calls onClose)
- Escape key → closes modal
- Focus trapped inside modal (accessibility)
- Entrance animation: scale 0.95 → 1.0, opacity 0 → 1 (duration-150)
- Exit animation: reversed

**Reuse:** AddChannelModal, DownloadModal, ConfirmDialog, Job Detail, Export dialogs.

---

### 3.12 `ConfirmDialog`

**Purpose:** Standardized destructive action confirmation.

**Props:**
```javascript
{
  isOpen: boolean,
  onClose: () => void,
  onConfirm: () => void,
  title: string,
  message: string,
  confirmLabel?: string,  // default: "Confirm"
  confirmVariant?: 'danger' | 'warning',  // default: 'danger'
  loading?: boolean
}
```

**Layout:** Modal (sm size). Warning/danger icon at top. Title. Message. Two buttons: [Cancel] [Confirm] (danger=red).

**Loading state:** Confirm button shows spinner, both buttons disabled.

**Reuse:** Delete channel, delete video, delete playlist, delete download, delete cookies.

---

### 3.13 `Toast`

**Purpose:** Temporary notification overlay.

**Props:**
```javascript
{
  id: string,
  message: string,
  type: 'success' | 'error' | 'warning' | 'info',
  duration?: number,  // ms, default: 4000; 0 = persistent
  action?: { label: string, onClick: () => void }
}
```

**Visual:**
- Container: fixed bottom-right, z-50, flex-col gap-2
- Each toast: rounded-lg, shadow-lg, p-4, flex items-start gap-3
- Icon: CheckCircle (success), XCircle (error), AlertTriangle (warning), Info (info)
- Colors: green-50/green-800, red-50/red-800, amber-50/amber-800, blue-50/blue-800
- Close button: X icon, right side
- Entrance: slide in from right (translate-x-full → 0) with opacity
- Auto-dismiss: countdown bar at bottom of toast

**Triggered via:** `useToast()` hook → Zustand uiStore.toasts

---

### 3.14 `Badge`

**Purpose:** Small status/category label chip.

**Props:**
```javascript
{
  children: ReactNode,
  variant: 'success' | 'error' | 'warning' | 'info' | 'neutral' | 'indigo',
  size?: 'sm' | 'md'  // default: 'sm'
}
```

**Styles:**
- success: `bg-green-100 text-green-800`
- error: `bg-red-100 text-red-800`
- warning: `bg-amber-100 text-amber-800`
- info: `bg-blue-100 text-blue-800`
- neutral: `bg-gray-100 text-gray-700`
- indigo: `bg-indigo-100 text-indigo-800`

**Reuse:** Job status badges, availability status, transcript type (auto-generated), verification, monitoring status.

---

### 3.15 `EmptyState`

**Purpose:** Consistent zero-data placeholder with optional CTA.

**Props:**
```javascript
{
  icon?: LucideIcon,
  title: string,
  description: string,
  action?: { label: string, onClick: () => void }
}
```

**Layout:** Centered flex-col, py-16. Icon (48px, text-gray-300). Title (text-lg font-medium text-gray-900). Description (text-sm text-gray-500, max-w-sm, centered). Action button (indigo, mt-4).

**Reuse:** Every list page, every empty tab, download history when empty.

---

### 3.16 `Skeleton`

**Purpose:** Loading placeholder matching content shape.

**Variants:**
- `line`: `h-4 w-full rounded animate-pulse bg-gray-200`
- `line-short`: `h-4 w-2/3 rounded animate-pulse bg-gray-200`
- `circle`: `rounded-full animate-pulse bg-gray-200`
- `rect`: `rounded-lg animate-pulse bg-gray-200` (custom h/w via className)
- `card`: Full ChannelCard/VideoCard shaped skeleton

**Usage pattern:** Each loading state renders domain-specific skeleton matching the final content layout. Never show generic spinners alone.

---

### 3.17 `Pagination`

**Purpose:** Page navigation for list endpoints.

**Props:**
```javascript
{
  total: number,
  page: number,
  perPage: number,
  onChange: (page: number) => void
}
```

**Layout:** `flex items-center justify-between` — left: "Showing 1–20 of 247 results" — right: prev/page buttons/next.

**Page buttons:** Show current page ±2 with ellipsis for large ranges. Max 7 buttons visible.

**Behavior:** Clicking page calls `onChange(n)`. Parent updates query params and refetches.

---

### 3.18 `FormatSelector`

**Purpose:** Select download format and quality for video/audio downloads.

**Props:**
```javascript
{
  type: 'video' | 'audio',
  formats: Format[],   // from /api/videos/{id}/formats
  value: { quality: string, format: string },
  onChange: ({ quality, format }) => void
}
```

**Video mode:** Quality dropdown (best/1080p/720p/480p/360p/worst) + Format dropdown (mp4/webm) + estimated size display.

**Audio mode:** Format dropdown (mp3/m4a/opus/wav) + Quality dropdown (best/320k/192k/128k/worst).

**Estimated size:** When quality selected, calculates from formats array. Shows "~1.2 GB" or "Unknown" if estimate unavailable.

---

### 3.19 `ErrorBanner`

**Purpose:** Inline error message with retry action for API errors.

**Props:**
```javascript
{
  message: string,
  onRetry?: () => void,
  details?: string  // collapsible technical detail
}
```

**Layout:** red-50 bg, red-200 border, rounded-lg, p-4. `XCircle` icon + message + optional Retry button. Optional "Show details ▾" link.

**Reuse:** Any data fetching failure within a page section (not full-page errors).

---

## 4. Dashboard Planning

The Dashboard is specified completely in Section 2.1. This section adds the layout grid specification.

### 4.1 Grid Layout

```
Desktop (lg+):
┌──────────────────────┬────────────────┐
│  Stats Bar (4 cols)                   │  ← full width
├──────────────────────┬────────────────┤
│  Active Jobs         │ Recent Activity│
│  (2/3 width)         │ (1/3 width)    │
├──────────────────────┤                │
│  RSS Discoveries     │                │
│                      ├────────────────┤
│                      │ Storage Usage  │
│                      ├────────────────┤
│                      │ Monitored      │
└──────────────────────┴────────────────┘

Mobile (< 640px):
┌────────────────────────┐
│ Stats (2×2 grid)       │
├────────────────────────┤
│ Active Jobs            │
├────────────────────────┤
│ RSS Discoveries        │
├────────────────────────┤
│ Recent Activity        │
├────────────────────────┤
│ Storage + Monitored    │
└────────────────────────┘
```

### 4.2 Data Dependencies

| Section | API Call | Refresh |
|---|---|---|
| Stats Bar | GET /api/analytics/dashboard | On mount, every 60s |
| Active Jobs | GET /api/jobs?status=queued,processing | Every 10s while jobs active |
| RSS Discoveries | GET /api/analytics/dashboard | On mount |
| Recent Activity | GET /api/jobs?status=complete,failed&per_page=10 | On mount, every 30s |
| Storage | GET /api/analytics/dashboard | On mount |
| Monitored | GET /api/channels?monitoring=true&per_page=5 | On mount |

### 4.3 Quick Actions

"Add Channel" button appears in Channels stat card (below count). Clicking it opens AddChannelModal without navigating to /channels.

---

## 5. Channel Page

### 5.1 Page Header

```
┌──────────────────────────────────────────────────────────┐
│  [Banner image, full width, h-48, gradient fallback]     │
│                                                          │
│  [Avatar 80px,  Display Name                   [Monitor toggle]
│   circular,     @handle  [✓ verified]          [↻ Refresh]
│   overlaps      1.5M subscribers · 342 videos  [⬆ Crawl Videos]
│   banner]       🌍 United States · Since Jan 2015        │
└──────────────────────────────────────────────────────────┘
```

**Banner:** `object-cover w-full h-48 rounded-t-xl`. If no banner_url: indigo-to-purple gradient.

**Avatar:** `absolute -bottom-6 left-6`, 80px circle, ring-4 ring-white, rounded-full. Gray initials fallback.

**Monitor toggle:** `<Switch>` component (Tailwind-styled). When ON: indigo fill, shows pulsing dot indicator. PATCH /api/channels/{id} {rss_monitoring: true/false}.

**Refresh button:** Ghost button, refresh icon. On click: POST /api/channels/{id}/refresh, shows job toast.

**Crawl Videos button:** Opens CrawlOptionsModal (see Section 1.3).

**Stats display:**
- Subscriber count: formatted ("1.5M subscribers" or "Subscribers: N/A" if null)
- Video count from DB: "342 videos tracked"
- Join date: "Since Jan 2015" or "Join date unknown"
- Country: flag emoji + country name if available

### 5.2 Stats Row (below header)

4 stat cards in a row:

| Card | Value | Source |
|---|---|---|
| Videos Tracked | Count from videos table for this channel | DB query |
| Average Views | avg(view_count) from channel's videos | DB aggregate |
| Total Duration | sum(duration_seconds) → formatted "47h 23m" | DB aggregate |
| Shorts | Count where is_short=true | DB aggregate |

### 5.3 Tabs

Tab bar: `Videos | Playlists | Analytics | External Links`

Active tab: indigo bottom border + indigo text. Default active: Videos.

**Videos Tab:**

Controls row: [Search videos...] [Sort ▾] [Filter ▾] [Grid/List toggle] [Crawl All Videos]

Sort options: Upload Date (newest) | Upload Date (oldest) | Views (high-low) | Duration | Title A–Z

Filter dropdown: Type (All / Videos / Shorts / Live) | Has Transcript (Any / Yes / No) | Availability (Public / All)

Grid mode: VideoCard grid (grid-cols-2 md:grid-cols-3 lg:grid-cols-4)

List mode: VideoTable component

Pagination: 20 per page (grid) or 50 per page (table)

Empty state: "No videos tracked yet" + "Crawl Channel" button

**Playlists Tab:**

Playlist cards in a 2-column grid:

```
┌──────────────────────┐
│ [Thumbnail 160×90]   │
│ Playlist Title       │
│ 24 videos · Public   │
│ Last crawled: 2h ago │
│ [View] [↻] [🗑️]     │
└──────────────────────┘
```

Add Playlist row at bottom: Input "Playlist URL" + "Add" button.

**Analytics Tab:**

See Section 9 for full chart specifications.

Layout: Stacked cards, each chart in its own card.

1. Subscriber Growth Line Chart (date range: 7d/30d/90d/1y selector)
2. Upload Frequency Bar Chart (last 12 months)
3. Top 10 Videos Bar Chart (horizontal)
4. Duration Distribution Histogram

If no snapshots: EmptyState with "No growth data yet" + explanation.

**External Links Tab:**

List of external links from channel About section:
```
[🔗] Twitter         @channelhandle     twitter.com/...
[🔗] Instagram       @channelhandle     instagram.com/...
[🔗] Website         channelsite.com    https://...
```

If no external links: "No external links available for this channel."

### 5.4 State Management

- Channel detail data: TanStack Query with key `['channel', channelId]`
- Videos list: separate query `['channel', channelId, 'videos', {page, sort, filters}]`
- Analytics data: separate query `['channel', channelId, 'analytics', days]`
- Refetch after refresh job completes (invalidate channel query)

---

## 6. Video Page

### 6.1 Video Header

```
┌──────────────────────────────────────────────────────────┐
│  [Thumbnail, full width, 16:9 aspect ratio, rounded-lg]  │
│  [Shorts badge if applicable]                            │
├──────────────────────────────────────────────────────────┤
│  Title (text-2xl font-bold, text-gray-900)               │
│  [Channel name link] · [Upload date] · [Duration]        │
│  [Availability badge] [Live badge] [Age restriction]     │
│  [↗ Open on YouTube]                                     │
└──────────────────────────────────────────────────────────┘
```

**Thumbnail:** If thumbnail_url exists: `<img>` with loading="lazy", object-cover. If absent: dark gray placeholder with `Play` icon centered.

**Channel name:** Link → /channels/:channelId (if channel in DB) or external YouTube link.

**Duration:** Formatted "10:23" or "1:02:45".

**Upload date:** "January 15, 2026" (long format).

**Badges:** Availability (public=none, unlisted=gray, premium=amber), Live (red if is_live), Shorts (red if is_short), Age restricted (red "18+" if age_limit=18).

### 6.2 Stats Row

3 stat cards:

| Card | Value | Note |
|---|---|---|
| Views | Formatted view_count | "1.2M views" |
| Likes | Formatted like_count | "45K likes" or "Hidden" if null |
| Comments | Formatted comment_count | "3.2K comments" or "Disabled" if comments_disabled |

### 6.3 Action Buttons Row

Horizontal scrollable row on mobile:

```
[⬇ Download Video] [♪ Download Audio] [📄 Extract Transcript] [💬 Extract Comments] [↻ Refresh]
```

Each button: ghost variant with icon. On click:

- **Download Video:** Opens DownloadModal with video type pre-selected
- **Download Audio:** Opens DownloadModal with audio type pre-selected
- **Extract Transcript:** Checks if already extracting; if not, queues job, shows progress toast
- **Extract Comments:** Checks settings max_comments; queues job
- **Refresh:** Queues metadata refresh job

### 6.4 Tabs

`Description | Formats | Chapters | Transcript | Comments`

Default active: Description.

**Description Tab:**

```
[Full description text, pre-wrap, text-sm text-gray-700]

Tags:
[python] [tutorial] [beginner] [programming] ...

Categories:
[Education] [Science & Technology]

Language: English (en)
License: Standard YouTube License
```

Description: max-height 200px with "Show more" expand if longer. Full-text, no truncation of links.

Tags: rendered as Badge (neutral variant) chips.

**Formats Tab:**

DataTable with columns: Resolution | FPS | Video Codec | Audio Codec | Estimated Size | Format ID

Best options highlighted: "Best video+audio" row in indigo-50 background.

Row click: selects format, pre-populates DownloadModal.

"Download Selected Format" button below table.

If formats_available is null or empty: "Format list not available — refresh metadata to update."

**Chapters Tab:**

Timeline list:
```
00:00  Introduction
02:15  What is Python?
08:40  Installing Python
15:22  Your First Program
```

Each row: time marker (monospace) + chapter title. Click → opens YouTube link at timestamp.

If no chapters: EmptyState "No chapters defined for this video."

**Transcript Tab:**

TranscriptViewer component (full spec in Section 3.7).

If transcript not extracted:
```
[FileText icon]
"No transcript stored yet"
"Extract the transcript to view and search the video's content"
[Language: English ▾]  [Extract Transcript] button
```

If has_transcript=false (confirmed unavailable):
```
[XCircle icon, amber]
"Transcript not available"
"This video doesn't have captions on YouTube"
```

**Comments Tab:**

Controls: Sort [Top Comments ▾] [Newest ▾] | "Extract Comments" button (if none stored)

If comments not extracted:
```
[MessageCircle icon]
"No comments stored yet"
"{comment_count} comments on YouTube"
[Extract {comment_count} Comments] button (shows settings cap)
```

If extracted: CommentThread list, paginated 50/page.

If comments_disabled: "Comments are disabled for this video."

### 6.5 Technical Information Panel

Collapsible card below tabs (collapsed by default):

"Technical Details ▾" toggle

When expanded:
```
Video ID:        xxxxxxxxxxx [copy button]
Channel ID:      UCxxxxxx [copy button]
Uploader ID:     @handle
Last Extracted:  July 28, 2026 at 12:00 UTC
Heatmap:         Available (47 data points)
Was Live:        No
Live Status:     not_live
```

---

## 7. Downloader UX

### 7.1 Quick Download Form

Located at top of /downloader page:

```
┌─────────────────────────────────────────────────────────┐
│  YouTube URL                                            │
│  [https://youtube.com/watch?v=... ____________________] │
│                                                         │
│  Type: ● Video  ○ Audio  ○ Subtitle  ○ Thumbnail       │
│                                                         │
│  [Type-specific options row]                            │
│                                                         │
│  [Queue Download]                                       │
└─────────────────────────────────────────────────────────┘
```

**Type: Video options:**
Quality: [Best ▾] | Format: [MP4 ▾] | Estimated size: "~1.2 GB"

**Type: Audio options:**
Format: [MP3 ▾] | Quality: [192k ▾]

**Type: Subtitle options:**
Language: [English (en) ▾] | Format: [SRT ▾]

**Type: Thumbnail options:**
Resolution: [Max Resolution ▾]

**Submission flow:**
1. URL validation (client-side regex for YouTube URL)
2. If invalid: inline red error under input
3. If valid: POST to appropriate endpoint
4. On 202: toast "Download queued", form resets
5. On 409 (already downloaded): yellow warning "Already downloaded — [View in history]"
6. On 507 (disk full): red error "Insufficient disk space"

### 7.2 Active Downloads Panel

Below quick download form. Only shown when downloads in progress.

Title: "Active Downloads ({count})"

Each active download card:
```
┌──────────────────────────────────────────────┐
│ [Thumbnail 60×34]  Video Title               │
│                    🎬 Video · 1080p · MP4    │
│ ████████░░░░░░░░░░ 52% · 12.4 MB/s · 0:45  │
│                                    [✕ Cancel]│
└──────────────────────────────────────────────┘
```

SSE connection per active download (via useJobProgress hook).

**Cancel flow:**
- Click X → ConfirmDialog: "Cancel this download? Partial files will be deleted."
- Confirm → POST /api/downloads/{downloadId}/cancel
- Card transitions to "Cancelled" state for 2s, then removed

**Completion:**
- Bar fills to 100%, turns green
- Shows "✓ Complete" for 3 seconds
- Card moves to Download History below

### 7.3 Download History Table

Below active downloads. Filterable.

Filter controls: Status [All ▾] | Type [All ▾] | Search [video title...]

DataTable columns:
| Column | Format |
|---|---|
| Thumbnail | 60×34 img |
| Title | Link to /videos/:id |
| Type | Badge (Video/Audio/Subtitle/Thumbnail) |
| Quality | "1080p", "192k", etc. |
| Size | "1.2 GB", "4.3 MB" |
| Status | StatusBadge |
| Date | "Jul 28, 2026" |
| Actions | [Open folder icon] [Delete icon] |

**Open folder:** Opens file path in OS file manager. Only shown if file exists. Shows tooltip "Open file location" on hover.

**Delete:** ConfirmDialog: "Delete this download record?" with optional "Also delete file from disk" checkbox.

### 7.4 Playlist / Channel Download

These are accessible from Channel Detail and Playlist Detail pages, not the quick download form.

**Channel download:** On Channel Detail, the "Crawl Videos" flow + then user selects videos and bulk downloads them. Not a single-click channel download — too risky for disk space.

**Playlist download:** On Playlist Detail page, "Download All" button opens a modal:
- Format and quality selectors (applied to all)
- Warning: "This will download {N} videos ({estimated_size_estimate})"
- Queues individual download jobs for each video (not a batch operation)

### 7.5 Download Failure UX

When a download fails:

Status badge: "Failed" (red)

Actions column: [Retry] button

On retry click: POST /api/jobs/{jobId}/retry → new job queued.

Error detail: hover over "Failed" badge → tooltip shows abbreviated error. Full error in Job Detail modal.

---

## 8. Search Experience

### 8.1 Search Page Layout

```
┌────────────────────────────────────────────────────────┐
│  Search YouTube or your library                        │
│  ┌──────────────────────────────────────┐  [Search]   │
│  │ 🔍  Enter search query...            │             │
│  └──────────────────────────────────────┘             │
│  ○ Search YouTube   ● Search My Library               │
└────────────────────────────────────────────────────────┘
```

The search bar is the visual center of the page when empty. After first search, it moves to the top.

### 8.2 YouTube Search Mode

**On submit:**
- GET /api/search/youtube?q={query}&type={type}&max_results=20
- Loading: "Searching YouTube..." with spinner
- Results appear as VideoCard grid (3 columns)

**Result card additions (vs standard VideoCard):**
- "Add to Library" button (below card, full width)
- When added: button becomes "In Library ✓" (green, disabled)

**No results state:**
```
[SearchX icon]
"No YouTube results found for '{query}'"
"Try different keywords or check your spelling"
```

**Search YouTube error (503):**
```
[AlertTriangle icon, amber]
"YouTube search temporarily unavailable"
"yt-dlp couldn't reach YouTube. This may be a rate limit or bot detection issue."
[Try Again] button
```

**Cached results indicator:** When serving cached results: small amber banner "Results from cache · Refreshed 23m ago · [Refresh Now]"

### 8.3 My Library Mode

**Additional filters appear below mode toggle:**
```
[Videos ▾] [Has Transcript ▾] [Is Short ▾] [Upload Date ▾] [Channel ▾]
```

Each filter is a dropdown:
- Videos: Videos | Channels | Transcripts
- Has Transcript: Any | Yes | No
- Is Short: Any | Yes | No
- Upload Date: Any | Last 7 days | Last 30 days | Last year | Custom range
- Channel: All channels | {channel dropdown from DB}

Results show with FULLTEXT match highlighting (if searching text).

**Transcript search results:** Special display:
```
[Thumbnail 60×34]  "Video Title"
                   Channel Name · 10:23
                   
                   "...we talk about [climate change] and its
                    effects on the global ecosystem..."
                   
                   Timestamp: 14:03  [Jump to timestamp ↗]
```

### 8.4 Recent Searches

When search input is focused with no text: dropdown shows recent searches (last 5 from local storage, not DB):
```
🕐  python tutorial
🕐  machine learning beginner
🕐  react hooks explanation
```

Click → populates input and submits.

### 8.5 Search History Panel

Separate section below results (collapsed by default):

"Recent Searches ▾" toggle

Table: Query | Type | Results | Searched | Cache status

---

## 9. Charts

All charts use Recharts wrapped in `<ResponsiveContainer width="100%" height={300}>`.

### 9.1 Subscriber Growth Line Chart (`GrowthChart`)

**Type:** `<LineChart>`

**Data:** channel_snapshots ordered by snapshot_date

**X-axis:** Date (formatted: "Jul 28", "Jun 1", etc., depends on range)

**Y-axis (left):** Subscriber count (formatted: "1.5M", "800K")

**Y-axis (right):** Total view count (formatted: "90M")

**Lines:**
- Subscribers: `stroke="#6366f1"` (indigo-500), `strokeWidth=2`, dot hidden unless hovered
- Views: `stroke="#10b981"` (emerald-500), `strokeWidth=2`, dashed (`strokeDasharray="5 5"`), dot hidden

**Tooltip:**
```
Jul 28, 2026
Subscribers: 1,500,234
Views:        90,500,000
```

**Date range selector:** Button group above chart: 7D | 30D | 90D | 1Y. Changes query parameter `days`.

**Zoom:** No zoom in Phase 1. Future enhancement.

**Empty/insufficient data:** If < 2 snapshots: "Not enough data to show chart. Growth charts require at least 2 days of snapshots."

**Interactions:** Hover shows tooltip + highlights dots. Legend toggles line visibility on click.

---

### 9.2 Upload Frequency Bar Chart

**Type:** `<BarChart>`

**Data:** Videos grouped by upload month, counted

**X-axis:** Month abbreviation ("Jan", "Feb") — last 12 months

**Y-axis:** Video count (integer)

**Bars:** `fill="#6366f1"` (indigo-500), rounded corners (`radius={[4,4,0,0]}`)

**Tooltip:** "July 2026: 8 videos"

**Interactions:** Hover shows tooltip. Click bar → navigates to /channels/:id/videos with date filter for that month.

---

### 9.3 Top Videos Bar Chart (Horizontal)

**Type:** `<BarChart layout="vertical">`

**Data:** Top 10 videos by view count for a channel

**X-axis:** View count

**Y-axis:** Video title (truncated to 35 chars)

**Bars:** `fill="#6366f1"`, full bar with view count label at end

**Tooltip:** Full title + exact view count + upload date

**Interactions:** Click bar → navigates to /videos/:videoId

---

### 9.4 Duration Distribution Histogram

**Type:** `<BarChart>`

**Data:** Video count bucketed by duration

**Buckets:** "< 1m" | "1–5m" | "5–10m" | "10–20m" | "20–60m" | "> 60m"

**X-axis:** Bucket labels

**Y-axis:** Video count

**Bars:** `fill="#6366f1"`

**Tooltip:** "10–20m: 98 videos (28.6%)"

---

### 9.5 Video View Growth Chart

**Type:** `<LineChart>` (same as Subscriber Growth but for video snapshots)

**Data:** video_snapshots for one video

**Lines:**
- Views: indigo
- Likes: emerald (if available)

**Used on:** Video Detail page (future analytics section) and video snapshots endpoint.

---

### 9.6 Download History Chart

**Type:** `<BarChart>`

**Data:** Downloads grouped by date + type

**Stacked bars:** Video (indigo) + Audio (emerald) + Subtitle (amber) + Thumbnail (gray)

**Used on:** Downloader page (summary section, Phase 2 enhancement)

---

### 9.7 Storage Usage Chart

**Type:** `<PieChart>` with inner label

**Data:** Storage breakdown by type (videos/audio/subtitles/thumbnails)

**Colors:** Indigo, emerald, amber, gray

**Center label:** Total size ("48.5 GB")

**Used on:** Dashboard storage card

---

## 10. Database Blueprint

This section consolidates and finalizes all database decisions. The Architecture Spec (Section 8) is the primary reference. This section adds implementation-level detail.

### 10.1 Connection Configuration

```python
SQLALCHEMY_ENGINE_OPTIONS = {
    "pool_pre_ping": True,
    "pool_recycle": 3600,
    "pool_size": 10,
    "max_overflow": 5,
    "connect_args": {
        "charset": "utf8mb4",
        "connect_timeout": 10
    }
}
```

MySQL URL format: `mysql+pymysql://user:pass@host:3306/dbname?charset=utf8mb4`

### 10.2 Model Base Class

All models inherit from a `BaseModel` mixin providing:
```python
class TimestampMixin:
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, 
                        onupdate=datetime.utcnow, nullable=False)
```

### 10.3 Field Type Decisions

**JSON fields in MySQL:** All JSON arrays (tags, categories, thumbnails, formats, segments, external_links) are stored as `TEXT` with application-level JSON serialization via `@property` accessors on models. MySQL 8.0 `JSON` type is used for simple JSON objects only.

**Rationale:** `TEXT` works across all MySQL versions and avoids JSON path query complexity we don't need.

**Accessor pattern:**
```python
# In Video model:
_tags = Column('tags', Text, nullable=True)

@property
def tags(self):
    return json.loads(self._tags) if self._tags else []

@tags.setter
def tags(self, value):
    self._tags = json.dumps(value) if value else None
```

### 10.4 Cascade Rules

```
channels → videos: CASCADE DELETE
channels → playlists: SET NULL (channel_id)
channels → channel_snapshots: CASCADE DELETE
videos → transcripts: CASCADE DELETE
videos → comments: CASCADE DELETE
videos → video_snapshots: CASCADE DELETE
videos → download_history: CASCADE DELETE (keep record, set video_id=NULL alternative)
playlists → playlist_videos: CASCADE DELETE
comments → comments (replies): CASCADE DELETE (parent deleted → replies deleted)
```

**Design note on download_history:** When a video is deleted, its download history entries are also deleted. The files remain on disk. Users can manually clean up via the file system.

### 10.5 Indexes Not in Architecture Spec

Additional compound indexes for common query patterns:

```sql
-- Channel video list, sorted by upload date
INDEX idx_videos_channel_upload (channel_id, upload_date DESC)

-- Channel video list, sorted by views
INDEX idx_videos_channel_views (channel_id, view_count DESC)

-- Shorts filter
INDEX idx_videos_channel_shorts (channel_id, is_short)

-- Download history filter by video+type
INDEX idx_downloads_video_type (video_id, download_type, status)

-- Snapshot range queries
INDEX idx_channel_snapshots_range (channel_id, snapshot_date DESC)
INDEX idx_video_snapshots_range (video_id, snapshot_date DESC)

-- Queue: next jobs to process
INDEX idx_queue_status_priority (status, priority, created_at)
```

### 10.6 Data Retention Policy

| Table | Retention | Method |
|---|---|---|
| processing_queue (complete/cancelled) | 30 days | Maintenance job |
| processing_queue (failed) | 90 days | Maintenance job |
| search_history | Until expires_at | Maintenance job |
| channel_snapshots | Forever | No deletion |
| video_snapshots | Forever | No deletion |
| comments | Forever (until video deleted) | Cascade |
| transcripts | Forever (until video deleted) | Cascade |

### 10.7 Initial Data Seed

On first run, the application seeds `user_settings` (id=1) with all defaults via `SettingsService.initialize()` called in `create_app()`. Uses `INSERT IGNORE` to avoid overwriting existing settings.

---

## 11. API Blueprint

This section provides implementation-level detail supplementing the Architecture Spec Section 9. All endpoints are already fully specified there. This section adds implementation notes.

### 11.1 Request/Response Standards

**Content-Type:** All requests and responses use `application/json` except:
- `POST /api/settings/cookies/upload`: `multipart/form-data`
- `GET /api/transcripts/{id}/export`: returns file (Content-Type varies by format)
- `GET /api/jobs/{id}/stream`: `text/event-stream`

**Authentication:** None in Phase 1. All endpoints are open. CORS restricts access to configured origins only.

**Request ID:** Every response includes `X-Request-ID` header (UUID). The error response body also includes `request_id`.

**Timestamps:** All timestamps in ISO 8601 UTC: `"2026-07-28T12:00:00Z"`.

**Number formatting:** All numbers returned as raw integers/floats, not pre-formatted strings. Frontend handles display formatting.

### 11.2 URL Validation Rules

Accepted YouTube URL patterns (validated in `url_parser.py`):

```
Videos:
- https://www.youtube.com/watch?v=xxxxxxxxxxx
- https://youtu.be/xxxxxxxxxxx
- https://youtube.com/shorts/xxxxxxxxxxx
- https://www.youtube.com/live/xxxxxxxxxxx

Channels:
- https://www.youtube.com/channel/UCxxxxxxxxxxxxxxxxxxxxxxxxxx
- https://www.youtube.com/c/channelname
- https://www.youtube.com/@handle
- @handle (bare handle, no URL)
- youtube.com/@handle (no protocol)

Playlists:
- https://www.youtube.com/playlist?list=PLxxxxxx
- https://www.youtube.com/watch?v=xxx&list=PLxxxxxx (extract list param)
```

The `url_parser.py` utility extracts the canonical form before passing to yt-dlp.

### 11.3 Pagination Implementation

All list endpoints use cursor-based counting:
```
SELECT COUNT(*) FROM {table} WHERE {filters}  → total
SELECT * FROM {table} WHERE {filters} ORDER BY {sort} LIMIT {per_page} OFFSET {(page-1)*per_page}
```

Max per_page: 100. Default per_page: 20. Exceeding max → HTTP 422.

### 11.4 Rate Limiting Configuration

Flask-Limiter rules:

```python
EXTRACTION_LIMITS = "30/minute"   # POST /channels, POST /videos, POST /transcripts
DOWNLOAD_LIMITS = "10/minute"     # POST /downloads/*
SEARCH_LIMITS = "20/minute"       # GET /search/youtube
GENERAL_LIMITS = "200/minute"     # All other endpoints
```

On limit exceeded: HTTP 429 with `{"error": "Rate limit exceeded", "retry_after": 60}`.

### 11.5 SSE Implementation Detail

The SSE endpoint (`GET /api/jobs/{job_id}/stream`) is implemented as a Flask streaming response:

```python
def event_stream(job_id):
    pubsub = redis_client.pubsub()
    pubsub.subscribe(f"job:{job_id}:progress")
    try:
        # Send initial state
        job = queue_repository.get_by_id(job_id)
        yield f"event: init\ndata: {json.dumps(job_to_dict(job))}\n\n"
        
        for message in pubsub.listen():
            if message['type'] == 'message':
                yield f"event: progress\ndata: {message['data']}\n\n"
                data = json.loads(message['data'])
                if data.get('type') in ('complete', 'error'):
                    break
            # Heartbeat every 15 seconds
            yield ": keepalive\n\n"
    finally:
        pubsub.unsubscribe()
        pubsub.close()
```

Response headers:
```
Content-Type: text/event-stream
Cache-Control: no-cache
X-Accel-Buffering: no
Connection: keep-alive
```

### 11.6 File Download Endpoint

`GET /api/transcripts/{video_id}/export`:

```python
response = make_response(file_content)
response.headers['Content-Type'] = content_type  # text/plain, text/srt, application/json
response.headers['Content-Disposition'] = f'attachment; filename="{filename}"'
return response
```

Filename format: `{sanitized_title}.{lang}.{format}` (title sanitized: alphanumeric + spaces + hyphens, max 100 chars).

---
