---

## 12. State Management

### 12.1 Server State (TanStack Query)

All data fetched from the API is server state managed by TanStack Query. No server data lives in Zustand.

**Query Key Conventions:**

```javascript
// Channel queries
['channels']                           // list
['channels', {page, search, sort}]     // filtered list
['channel', channelId]                 // single
['channel', channelId, 'videos', params]  // channel videos
['channel', channelId, 'analytics', days] // analytics
['channel', channelId, 'stats']        // aggregate stats

// Video queries
['videos', params]                     // global list
['video', videoId]                     // single
['video', videoId, 'formats']
['video', videoId, 'snapshots', days]

// Transcript queries
['transcript', videoId, lang]
['transcript', videoId, 'languages']

// Comment queries
['comments', videoId, params]

// Playlist queries
['playlists', params]
['playlist', playlistId]

// Download queries
['downloads', params]

// Job queries
['jobs', params]
['job', jobId]

// Search queries
['search', 'youtube', {q, type, max_results}]
['search', 'internal', {q, type, ...filters}]

// Settings
['settings']

// Analytics / Dashboard
['dashboard', 'stats']
```

**Mutation invalidation rules:**

```javascript
// After adding a channel → invalidate channels list + dashboard stats
onSuccess: () => {
  queryClient.invalidateQueries({ queryKey: ['channels'] })
  queryClient.invalidateQueries({ queryKey: ['dashboard', 'stats'] })
}

// After deleting a channel → remove from cache + invalidate list
onSuccess: () => {
  queryClient.removeQueries({ queryKey: ['channel', channelId] })
  queryClient.invalidateQueries({ queryKey: ['channels'] })
}

// After transcript extraction completes → invalidate transcript + video
onSuccess: () => {
  queryClient.invalidateQueries({ queryKey: ['transcript', videoId] })
  queryClient.invalidateQueries({ queryKey: ['video', videoId] })
}
```

**Stale time configuration:**
```javascript
{
  defaultOptions: {
    queries: {
      staleTime: 60_000,      // 1 minute default
      gcTime: 300_000,        // 5 minutes garbage collection
      retry: 1,
      refetchOnWindowFocus: false,
    }
  }
}
```

**Per-query overrides:**
- Jobs list: `staleTime: 0` (always fresh while jobs running)
- Dashboard stats: `staleTime: 15_000` (15 seconds)
- Transcripts: `staleTime: Infinity` (transcripts don't change)
- Settings: `staleTime: 300_000` (5 minutes)

---

### 12.2 Client/UI State (Zustand)

Three Zustand stores handle UI-only state.

**`uiStore.js`:**
```javascript
{
  // Sidebar
  sidebarOpen: boolean,           // default: true on desktop, false on mobile
  toggleSidebar: () => void,

  // Toasts
  toasts: Toast[],
  addToast: (toast) => void,
  removeToast: (id) => void,

  // Active job count (for badge)
  activeJobCount: number,
  setActiveJobCount: (n) => void,
}
```

**`settingsStore.js`:**
```javascript
{
  settings: Settings | null,
  isLoaded: boolean,
  loadSettings: (settings) => void,  // called after GET /api/settings on app mount
  updateSettings: (partial) => void, // called after successful PATCH /api/settings
}
```

**`jobStore.js`:**
```javascript
{
  // Jobs submitted in this browser session
  activeJobs: Map<job_id, {
    job_id: string,
    job_type: string,
    target_id: string,
    target_name: string,
    status: string,
    progress_percent: number,
    current_operation: string,
    speed: string | null,
    eta: string | null
  }>,
  
  addJob: (job_id, metadata) => void,
  updateJob: (job_id, progress) => void,
  completeJob: (job_id) => void,
  failJob: (job_id, error) => void,
  removeJob: (job_id) => void,     // called 5s after complete/fail
  getActiveCount: () => number,
}
```

---

### 12.3 Local Storage (Minimal Use)

Only two items stored in browser localStorage:

- `recent_searches`: Array of last 5 search queries (strings). Max 5 items. Updated on every search submit.
- `sidebar_collapsed`: Boolean. Persists sidebar state across refreshes.

No server data is stored in localStorage.

---

### 12.4 Job Progress State Flow

```
User submits action → API returns job_id
       ↓
jobStore.addJob(job_id, {type, target, status: 'queued'})
uiStore.setActiveJobCount(count + 1)
       ↓
useJobProgress(job_id) hook opens EventSource
       ↓
SSE events received:
  'init' → jobStore.updateJob(job_id, initialState)
  'progress' → jobStore.updateJob(job_id, {percent, operation, speed, eta})
  'complete' → jobStore.completeJob(job_id)
             → TanStack Query invalidation (via hook callback)
             → uiStore.setActiveJobCount(count - 1)
             → addToast (success)
             → setTimeout(5000, () => jobStore.removeJob(job_id))
  'error' → jobStore.failJob(job_id, error)
           → uiStore.setActiveJobCount(count - 1)
           → addToast (error)
```

---

### 12.5 Download Queue State

Downloads use the same job state flow. The Downloader page polls `GET /api/downloads?status=downloading,pending` every 5 seconds as a fallback if SSE is unavailable.

Active download count is stored in `jobStore` (filtered by job_type='download').

---

### 12.6 Settings State Bootstrap

On app mount (in `App.jsx`), a `useEffect` fires:
```javascript
useEffect(() => {
  GET /api/settings → settingsStore.loadSettings(data)
}, [])
```

All components that need settings read from `settingsStore.settings`. This avoids N parallel settings API calls.

---

### 12.7 Theme State

Dark mode is **not implemented in Phase 1**. No theme store exists. Tailwind's `dark:` classes are added to components as implementation-time prep but the toggle is not exposed in the UI.

---

## 13. File Storage

### 13.1 Directory Structure

All user-generated files are stored under two configurable base directories:

```
$DOWNLOAD_DIR/
├── videos/
│   └── {video_id}/
│       └── {video_id}_{quality}.{ext}
│           Example: xxxxxxxxxxx_1080p.mp4
├── audio/
│   └── {video_id}/
│       └── {video_id}_{quality}.{ext}
│           Example: xxxxxxxxxxx_192k.mp3
├── subtitles/
│   └── {video_id}/
│       └── {video_id}.{lang}.{ext}
│           Example: xxxxxxxxxxx.en.srt
│           Example: xxxxxxxxxxx.es.srt (multiple languages)
└── thumbnails/
    └── {video_id}/
        └── maxres.jpg
        └── high.jpg
        └── medium.jpg

$THUMBNAIL_DIR/  (separate mount for faster access)
└── {channel_id}/
    └── avatar.jpg
    └── banner.jpg
```

### 13.2 Naming Conventions

**Video files:** `{video_id}_{quality}.{ext}`
- quality: sanitized string (`1080p`, `720p`, `best`, `worst`)
- ext: `mp4` or `webm`
- Example: `dQw4w9WgXcQ_1080p.mp4`

**Audio files:** `{video_id}_{quality}.{ext}`
- quality: `192k`, `128k`, `best`
- ext: `mp3`, `m4a`, `opus`, `wav`
- Example: `dQw4w9WgXcQ_192k.mp3`

**Subtitle files:** `{video_id}.{lang}.{ext}`
- lang: BCP-47 language code (`en`, `es`, `fr-CA`)
- ext: `srt`, `vtt`, `json`
- Example: `dQw4w9WgXcQ.en.srt`

**Thumbnail files:** `{resolution}.jpg`
- resolution: `maxres`, `high`, `medium`, `default`
- Example: `maxres.jpg`

**Channel assets:** `avatar.jpg`, `banner.jpg`

### 13.3 Temporary Files

yt-dlp creates `.part` files during download: `{video_id}_{quality}.mp4.part`

On download failure: `FileManager.cleanup_partial(output_path)` — deletes `{output_path}.part` if exists.

On application restart: check for orphaned `.part` files in download directories. Schedule cleanup job on startup.

### 13.4 Path Validation (Security)

Before any file operation, `FileManager.validate_path(path, base_dir)` checks:

```python
resolved = os.path.realpath(path)
base = os.path.realpath(base_dir)
if not resolved.startswith(base + os.sep):
    raise PathTraversalError(f"Path {path} outside base directory")
```

This prevents directory traversal attacks if a malicious video_id were somehow injected.

### 13.5 Disk Space Check

Before queuing a download:

```python
def check_disk_space(required_bytes: int, directory: str) -> None:
    stat = os.statvfs(directory)
    available = stat.f_bavail * stat.f_frsize
    # Require 20% buffer beyond estimated size
    if available < required_bytes * 1.2:
        raise InsufficientDiskSpaceError(required_bytes, available)
```

`required_bytes` comes from `filesize_approx` in formats. If absent, estimate from bitrate × duration.

### 13.6 Cleanup Policy

**Orphaned thumbnails:** Thumbnails for videos not in DB are not auto-deleted. Manual cleanup via scripts/export_data.py.

**Download directory:** Never auto-deleted. User manages manually. Dashboard shows current usage.

**Cache files:** None. yt-dlp temp cache is disabled (`--no-cache-dir` flag in yt-dlp options).

### 13.7 Storage Calculation

`FileManager.get_storage_stats(download_dir)`:

```python
def get_storage_stats(base_dir):
    stats = {"videos": 0, "audio": 0, "subtitles": 0, "thumbnails": 0, "total": 0}
    for root, dirs, files in os.walk(base_dir):
        for file in files:
            filepath = os.path.join(root, file)
            size = os.path.getsize(filepath)
            stats["total"] += size
            if "/videos/" in root: stats["videos"] += size
            elif "/audio/" in root: stats["audio"] += size
            elif "/subtitles/" in root: stats["subtitles"] += size
    return stats
```

This is called by `GET /api/analytics/dashboard`. Cached in Redis for 15 minutes (`storage:stats`).

### 13.8 File Existence Check

Before returning file paths in API responses, `FileManager.file_exists(path) -> bool` checks:

```python
return path is not None and os.path.isfile(path)
```

If file no longer exists (manually deleted), the download_history record shows `file_exists: false` in the API response and the "Open" button is hidden in the frontend.

---

## 14. Error UX

Every error scenario has a defined user experience. No error should leave the user confused about what happened or what to do next.

### 14.1 Network / Connectivity Errors

**Scenario:** Backend server unreachable (not running, crashed)

**Detection:** Axios network error (no response received)

**UI behavior:**
- Toast: "Cannot reach server — is the application running?" (error, persistent, no auto-dismiss)
- All loading states hang (skeletons remain)
- Toast has "Retry" action that re-attempts the last failed request

**Retry:** After 5 seconds: auto-retry the failed request. If successful: dismiss toast. If still failing: show toast again with "Server still unreachable."

---

### 14.2 Private / Deleted Videos

**Scenario:** User submits URL of a private or deleted video

**Backend behavior:**
- yt-dlp raises `VideoUnavailableError`
- If during job: job marked failed, video marked `availability='unavailable'`
- If during API call: HTTP 404 returned immediately

**UI behavior:**
- Modal/form: inline error "This video is private or has been deleted on YouTube."
- If video is in DB with status=unavailable: Video Detail page shows:
  ```
  [AlertCircle icon, amber]
  "Video Unavailable"
  "This video was available when added but is no longer accessible."
  "It may have been made private or deleted."
  [Try Refreshing] button
  ```

---

### 14.3 No Transcript Available

**Scenario:** Video has no captions on YouTube

**Backend behavior:**
- `TranscriptNotAvailableError` raised
- `videos.has_transcript` set to `false`
- Job completes (not failed)

**UI behavior on Transcript tab:**
```
[XCircle icon, amber]
"No Transcript Available"
"This video doesn't have captions or subtitles on YouTube."
"Auto-generated captions are also unavailable."
```

No retry button (no point — YouTube doesn't have captions for this video).

---

### 14.4 Bot Detection / Rate Limiting

**Scenario:** YouTube blocks extraction request

**Backend behavior:**
- `YouTubeBotDetectedError` or `YouTubeRateLimitError` raised
- Celery retries with exponential backoff
- Bot detection: rotates player client before retry
- If all retries exhausted: job marked failed

**UI behavior (job failed after retries):**
- Job status shows "Failed" with detail: "YouTube blocked this request after 3 retries. This may be a rate limit or bot detection issue."
- Suggested actions shown in Job Detail modal:
  1. "Wait 15–30 minutes and try again"
  2. "Upload YouTube cookies in Settings"
  3. "Configure a proxy in Settings"
- [Retry] button available

**UI behavior (while retrying):**
- Job status shows "Retrying (2/3)" in amber
- Progress note: "Waiting before retry..."

---

### 14.5 Failed Downloads

**Scenario:** Download fails mid-way (network drop, YouTube block, disk full)

**Backend behavior:**
- Celery task catches exception
- Partial `.part` file deleted
- `download_history.status = 'failed'`
- `download_history.error_message = str(exception)`
- Semaphore released

**UI behavior:**
- Active download card turns red: "Download Failed"
- Error summary shown below progress bar: "Connection interrupted" / "YouTube blocked request" / "Disk full"
- [Retry] button
- Download history entry shows "Failed" badge + hover tooltip with error

---

### 14.6 Playlist / Channel Not Found

**Scenario:** URL resolves to a private playlist or deleted channel

**UI behavior:**
- Form shows inline error: "This playlist/channel could not be found on YouTube. It may be private or deleted."
- No job is queued.

---

### 14.7 Browser / SSE Connection Failures

**Scenario:** SSE connection drops (user's browser closed tab temporarily, network hiccup)

**Detection:** EventSource `onerror` event

**UI behavior:**
- `useJobProgress` hook attempts reconnect with 3s delay
- If reconnect successful: progress resumes
- If reconnect fails 3 times: hook falls back to polling `GET /api/jobs/{id}` every 5 seconds
- User sees no visible change (progress bar continues updating via polling)

---

### 14.8 Corrupted / Invalid Cookie File

**Scenario:** User uploads an invalid cookies.txt file

**Backend behavior:**
- `POST /api/settings/cookies/upload` validates file format (checks for Netscape cookie header)
- Returns HTTP 422 if invalid

**UI behavior:**
- File picker shows inline error: "Invalid cookies file format. Please use Netscape format (exported from your browser)."
- Link: "How to export cookies ?"

---

### 14.9 Timeouts

**Scenario:** yt-dlp hangs (network timeout, YouTube slow response)

**Backend behavior:**
- yt-dlp has internal timeout of 30s per request
- If job takes > 10 minutes: Celery soft time limit triggers `SoftTimeLimitExceeded`
- Job marked failed: "Extraction timed out after 10 minutes"

**UI behavior:**
- Job shows "Failed" with error "Operation timed out. YouTube may be slow or blocking requests."
- [Retry] button

---

### 14.10 Disk Full

**Scenario:** Download attempted when disk has insufficient space

**Backend behavior:**
- `InsufficientDiskSpaceError` raised before download starts
- HTTP 507 returned
- No job queued

**UI behavior:**
- Form shows: "⚠️ Insufficient disk space — {X} GB needed, {Y} GB available"
- Dashboard storage card highlighted in red
- Link: "Manage storage →" (to downloader history for cleanup)

---

### 14.11 Error Boundaries

React ErrorBoundary wraps each page route. If a React render error occurs:

```
[AlertCircle icon, red, large]
"This page encountered an error"
"Something went wrong rendering this page."
[↻ Reload this page] button
```

The error is logged to console. In production, it would go to an error tracking service (not in Phase 1).

---

## 15. Design System

### 15.1 Typography Scale

| Token | Class | Usage |
|---|---|---|
| Display | `text-4xl font-bold text-gray-900` | Page hero numbers (stat cards) |
| H1 | `text-2xl font-semibold text-gray-900` | Page titles |
| H2 | `text-lg font-semibold text-gray-900` | Card titles, section headers |
| H3 | `text-base font-medium text-gray-900` | Sub-section headers |
| Body | `text-sm text-gray-700` | Default body text |
| Secondary | `text-sm text-gray-500` | Helper text, labels |
| Caption | `text-xs text-gray-400` | Timestamps, meta info |
| Code | `font-mono text-sm text-gray-800 bg-gray-100 px-1 rounded` | IDs, technical data |

**Font:** Inter, loaded from Google Fonts CDN in `index.html`:
```html
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
```

Fallback: `font-family: Inter, system-ui, -apple-system, sans-serif`

---

### 15.2 Color Palette

All colors from Tailwind's default palette. No custom colors.

**Primary (Indigo):**
- Active/selected: `indigo-600` (#4F46E5)
- Hover: `indigo-700` (#4338CA)
- Light background: `indigo-50` (#EEF2FF)
- Text on light: `indigo-700`

**Semantic colors:**
- Success: `green-600` / `green-100` / `green-800`
- Error/Danger: `red-600` / `red-100` / `red-800`
- Warning: `amber-500` / `amber-100` / `amber-800`
- Info: `blue-600` / `blue-100` / `blue-800`

**Neutral:**
- Page background: `gray-50`
- Card/surface: `white`
- Border: `gray-200`
- Row hover: `gray-50`
- Disabled: `gray-300` background, `gray-500` text
- Icon muted: `gray-400`

**Chart colors** (in order of priority):
1. `#6366f1` (indigo-500) — primary series
2. `#10b981` (emerald-500) — secondary series
3. `#f59e0b` (amber-500) — tertiary
4. `#3b82f6` (blue-500) — quaternary
5. `#ef4444` (red-500) — negative/alert series

---

### 15.3 Spacing Scale

Follow Tailwind's 4px base unit. Standard spacings used:

- `p-4` (16px): Card inner padding (compact)
- `p-6` (24px): Card inner padding (default)
- `gap-4` (16px): Grid gap (compact)
- `gap-6` (24px): Grid gap (default)
- `mb-6` (24px): Section spacing
- `mb-4` (16px): Element spacing

Page content padding: `p-6` on all sides.

---

### 15.4 Card System

Standard card anatomy:
```
<div class="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
  {/* Card title */}
  <h2 class="text-lg font-semibold text-gray-900 mb-4">{title}</h2>
  {/* Card content */}
</div>
```

**Variants:**
- Default: `shadow-sm border-gray-100`
- Elevated: `shadow-md border-gray-200`
- Inset: `bg-gray-50 border border-gray-200` (used for code/technical sections)
- Interactive (hover): `hover:shadow-md transition-shadow duration-150 cursor-pointer`

---

### 15.5 Button System

```
Variants:
- primary:   bg-indigo-600 hover:bg-indigo-700 text-white
- secondary: bg-white hover:bg-gray-50 text-gray-700 border border-gray-300
- ghost:     hover:bg-gray-100 text-gray-700
- danger:    bg-red-600 hover:bg-red-700 text-white
- success:   bg-green-600 hover:bg-green-700 text-white

Sizes:
- xs:  px-2.5 py-1.5 text-xs rounded-md
- sm:  px-3 py-2 text-sm rounded-md
- md:  px-4 py-2 text-sm rounded-lg  (default)
- lg:  px-6 py-3 text-base rounded-lg

States:
- disabled: opacity-50 cursor-not-allowed (applied to all variants)
- loading:  shows spinner icon (left of text), text unchanged, disabled
- icon-only: square padding (p-2 for md), uses title attribute for accessibility

Focus ring: focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2
```

All buttons use `transition-colors duration-150`.

---

### 15.6 Input System

```
Base input class:
  block w-full rounded-lg border border-gray-300 px-3 py-2 text-sm text-gray-900
  placeholder-gray-400 shadow-sm
  focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 focus:outline-none
  transition-colors duration-150

States:
- default: border-gray-300
- focus:   border-indigo-500 + ring
- error:   border-red-500 + ring-red-500
- disabled: bg-gray-50 text-gray-400 cursor-not-allowed

Error message below input:
  <p class="mt-1 text-xs text-red-600">{error}</p>
```

Label: `block text-sm font-medium text-gray-700 mb-1`

---

### 15.7 Table System

```
Table wrapper:  overflow-x-auto (handles narrow screens)
Table:          w-full text-sm text-left

Header row:     bg-gray-50 text-xs font-medium text-gray-500 uppercase tracking-wider
Header cell:    px-6 py-3

Body row:       bg-white hover:bg-gray-50 transition-colors
Body cell:      px-6 py-4 text-sm text-gray-700

Divider:        divide-y divide-gray-200 (on tbody)
```

---

### 15.8 Responsive Breakpoints

Tailwind defaults:
- `sm`: 640px — tablet portrait
- `md`: 768px — tablet landscape
- `lg`: 1024px — laptop
- `xl`: 1280px — desktop
- `2xl`: 1536px — wide desktop

**Layout rules:**
| Breakpoint | Sidebar | Content | Grid cols |
|---|---|---|---|
| < sm | Hidden (hamburger) | Full width | 1 |
| sm–lg | Hidden (hamburger) | Full width | 2 |
| lg+ | Fixed 240px | Full minus sidebar | 2–4 |

**Channel card grid:** `grid-cols-1 sm:grid-cols-2 lg:grid-cols-3`

**Video card grid:** `grid-cols-2 md:grid-cols-3 lg:grid-cols-4`

**Stats bar:** `grid-cols-2 sm:grid-cols-4`

---

### 15.9 Icon System

All icons from `lucide-react`. Size conventions:

- Navigation icons: 18px (`h-[18px] w-[18px]`)
- Action button icons: 16px (`h-4 w-4`)
- Empty state icon: 48px (`h-12 w-12`)
- Stat card icon: 24px (`h-6 w-6`)
- Toast icon: 20px (`h-5 w-5`)

**Icon-only buttons always include** `title` attribute and `aria-label`.

---

### 15.10 Animations and Transitions

| Animation | Class | Usage |
|---|---|---|
| Pulse skeleton | `animate-pulse` | Loading placeholders |
| Spin | `animate-spin` | Button loading spinners |
| Fade in | `transition-opacity duration-150` | Modal backdrop |
| Scale in | `transition-transform duration-150 scale-95→100` | Modal entrance |
| Color transition | `transition-colors duration-150` | Buttons, inputs |
| Shadow transition | `transition-shadow duration-150` | Card hover |
| Progress bar fill | `transition-all duration-300` | Progress bars |

**Pulsing dot (active jobs):** Red circle with `animate-ping` for the outer ring.

---

### 15.11 Accessibility Requirements

- All icon-only buttons: `aria-label` + `title`
- All form inputs: `<label>` with `htmlFor` linking to input `id`
- All modals: `role="dialog"`, `aria-modal="true"`, `aria-labelledby` pointing to title
- Focus trap: modals trap focus using tabindex management
- Skip link: `<a href="#main-content" class="sr-only focus:not-sr-only">Skip to content</a>` at top of AppShell
- Live regions: `<div aria-live="polite" aria-atomic="true" class="sr-only">` for toast announcements
- Color: never convey meaning by color alone — always pair with text/icon
- Loading states: `aria-busy="true"` on loading containers
- Error messages: `aria-describedby` links input to its error message

**Keyboard navigation:**
- Tab: moves between interactive elements
- Enter/Space: activates buttons
- Escape: closes modals and dropdowns
- Arrow keys: navigates dropdown/tab options

---

### 15.12 Focus States

All interactive elements have visible focus rings:
```css
focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2
```

Never use `outline: none` without a replacement focus indicator.

---

## 16. Implementation Order

### Milestone 1: Foundation (Days 1–2)

**Goal:** Working skeleton with all infrastructure in place.

**Backend:**
- [ ] `docker-compose.yml` with all 5 services (mysql, redis, backend, celery-worker, celery-beat, frontend)
- [ ] `backend.Dockerfile` (Python 3.12 slim + FFmpeg)
- [ ] `frontend.Dockerfile` (Node 20 + Nginx)
- [ ] `nginx.conf` (proxy /api/ + serve React)
- [ ] Flask app factory (`create_app()`) with config classes
- [ ] All 13 SQLAlchemy models defined
- [ ] Alembic initial migration (`flask db migrate -m "initial"`)
- [ ] Celery app instance connected to Redis
- [ ] `GET /api/health` endpoint → `{"status":"ok","db":"ok","redis":"ok"}`
- [ ] JSON logging configured
- [ ] Global error handlers registered
- [ ] `.env.example` with all variables documented

**Frontend:**
- [ ] React + Vite project scaffold (`npm create vite@latest`)
- [ ] Tailwind CSS configured (`tailwind.config.js`)
- [ ] Inter font loaded in `index.html`
- [ ] `AppShell` component (sidebar + topbar + content area)
- [ ] All sidebar navigation items (routes link to placeholder pages)
- [ ] All page files created with placeholder content
- [ ] `constants.js` with API base URL
- [ ] `client.js` Axios instance

**Acceptance test:** `docker compose up` → all containers start → `GET /api/health` → 200 → `http://localhost:3000` shows AppShell with placeholder pages → database tables exist in MySQL → Celery worker shows "Ready."

---

### Milestone 2: Channel Module (Days 3–5)

**Goal:** Add and view channels.

**Backend:**
- [ ] `url_parser.py` (YouTube URL normalization)
- [ ] `YtdlpClient.extract_channel_metadata()`
- [ ] `ChannelRepository` (CRUD + list with filters/sort/pagination)
- [ ] `CacheService` (Redis wrapper with JSON serialization)
- [ ] `QueueService` (create job, update job status)
- [ ] `ChannelService` (add_channel, refresh, delete, list)
- [ ] `channel_controller` Blueprint (all endpoints from spec Section 9.1)
- [ ] Marshmallow schemas (ChannelInputSchema, ChannelOutputSchema)
- [ ] Celery task: `extract_channel_metadata`
- [ ] Channel metadata cached in Redis (1 hour TTL)

**Frontend:**
- [ ] `api/channels.js` (all channel API functions)
- [ ] `useChannel.js` hook (useChannels, useChannel, useAddChannel, useDeleteChannel, useRefreshChannel)
- [ ] `ChannelCard` component (full spec)
- [ ] `ChannelList` page (grid + Add Channel modal + filters)
- [ ] `ChannelDetail` page (header + stats row + tab shell — Videos tab empty for now)
- [ ] `AddChannelModal` component
- [ ] `ConfirmDialog` component
- [ ] `Badge` component
- [ ] `EmptyState` component
- [ ] `Skeleton` components
- [ ] `Toast` + `useToast` hook
- [ ] `uiStore` (Zustand)
- [ ] Job polling (simple: poll GET /api/jobs/{id} every 3s via TanStack Query)

**Acceptance test:** Add channel by URL → channel appears in list → channel detail shows all available metadata → refresh works → delete removes from list.

---

### Milestone 3: Video Module (Days 6–8)

**Goal:** Extract and display video metadata. Crawl channel videos.

**Backend:**
- [ ] `YtdlpClient.extract_video_metadata()`
- [ ] `YtdlpClient.extract_flat_playlist()` (channel crawl)
- [ ] `VideoRepository` (CRUD + list with all filters/sort + aggregate stats)
- [ ] `VideoService` (extract, refresh, delete, list)
- [ ] `video_controller` Blueprint (all video + channel video endpoints)
- [ ] Marshmallow video schemas
- [ ] Celery tasks: `extract_video_metadata`, `crawl_channel_videos`
- [ ] `thumbnail_utils.py` (download thumbnail via httpx)
- [ ] Celery task: `download_thumbnail`

**Frontend:**
- [ ] `api/videos.js`
- [ ] `useVideo.js` hook
- [ ] `VideoCard` component (grid and horizontal variants)
- [ ] `VideoGrid` component (responsive grid wrapper)
- [ ] `VideoTable` component (DataTable-based)
- [ ] `DataTable` component (generic)
- [ ] `Pagination` component
- [ ] `VideoDetail` page (header + stats + action buttons + Description/Formats/Chapters tabs)
- [ ] Channel Detail page: Videos tab populated
- [ ] `formatters.js` (formatNumber, formatDuration, formatRelativeTime, formatDate)
- [ ] `jobStore` (Zustand)

**Acceptance test:** Add video by URL → video detail renders all metadata → channel crawl discovers all video stubs → videos tab shows populated grid → video list sortable and filterable.

---

### Milestone 4: Search (Days 9–10)

**Goal:** YouTube search and internal library search.

**Backend:**
- [ ] `YtdlpClient.extract_search_results()` (`ytsearch{n}:` prefix)
- [ ] `SearchRepository` (cache lookup + FULLTEXT search query)
- [ ] `SearchService` (cache-first YouTube search + internal FULLTEXT search)
- [ ] `search_controller` Blueprint
- [ ] Marshmallow search schemas
- [ ] Search caching (Redis, 1 hour TTL)
- [ ] FULLTEXT indexes verified on `videos(title, description)` and `transcripts(full_text)`

**Frontend:**
- [ ] `api/search.js`
- [ ] `useSearch.js` hook
- [ ] `Search` page (dual mode: YouTube / My Library)
- [ ] Recent searches (localStorage)
- [ ] Search filters panel (My Library mode)
- [ ] TopBar search input (navigates to /search?q=)

**Acceptance test:** Search YouTube → results appear → "Add to Library" works → My Library search finds videos by title → cached search returns within 1 hour.

---

### Milestone 5: Transcript Module (Days 11–12)

**Goal:** Extract, display, search, and export transcripts.

**Backend:**
- [ ] `TranscriptClient` (youtube-transcript-api wrapper with yt-dlp fallback)
- [ ] `TranscriptRepository` (CRUD + FULLTEXT search)
- [ ] `TranscriptService` (extract with fallback, list languages)
- [ ] `transcript_controller` Blueprint (all transcript endpoints)
- [ ] Celery task: `extract_transcript`
- [ ] Transcript export (txt/srt/json formatter in `utils/`)
- [ ] `has_transcript` field updated on video after extraction

**Frontend:**
- [ ] `api/transcripts.js`
- [ ] `useTranscript.js` hook
- [ ] `TranscriptViewer` component (timed segments + search + language selector + export)
- [ ] `TranscriptSearch` component (inline search within viewer)
- [ ] Video Detail page: Transcript tab functional
- [ ] Export dropdown component

**Acceptance test:** Extract transcript → viewer shows timed segments → search highlights matches → export downloads correct format → videos without captions show graceful empty state.

---

### Milestone 6: Download Module (Days 13–15)

**Goal:** Full download system with real-time progress.

**Backend:**
- [ ] `YtdlpClient.download_video()` (with progress hook)
- [ ] `YtdlpClient.download_audio()` (with progress hook)
- [ ] `YtdlpClient.download_subtitles()`
- [ ] `FileManager` (path construction, validation, disk space check, cleanup)
- [ ] `DownloadRepository`
- [ ] `DownloadService` (semaphore, duplicate check, space check, orchestration)
- [ ] `download_controller` Blueprint (all download endpoints)
- [ ] Celery tasks: `download_video`, `download_audio`, `download_subtitle`, `download_thumbnail`
- [ ] Redis semaphore for concurrent download limit
- [ ] SSE endpoint (`GET /api/jobs/{id}/stream`)
- [ ] Redis pub/sub for SSE progress events

**Frontend:**
- [ ] `api/downloads.js`
- [ ] `useDownload.js` hook
- [ ] `useJobProgress.js` hook (SSE via EventSource)
- [ ] `FormatSelector` component
- [ ] `QualityPicker` component
- [ ] `DownloadButton` component
- [ ] `JobProgressBar` component (with SSE updates)
- [ ] `Downloader` page (quick form + active downloads + history)
- [ ] `DownloadModal` (opened from Video Detail)
- [ ] Video Detail page: Download Video/Audio buttons functional

**Acceptance test:** Queue video download → SSE progress bar updates in real-time → download completes → history shows entry → cancel mid-download cleans partial file → disk space check prevents download when full.

---

### Milestone 7: Playlist Module (Day 16)

**Goal:** Add and crawl playlists.

**Backend:**
- [ ] `PlaylistRepository`, `PlaylistService`
- [ ] `playlist_controller` Blueprint
- [ ] Celery task: `crawl_playlist`

**Frontend:**
- [ ] `api/playlists.js`
- [ ] `usePlaylist` hook
- [ ] `PlaylistDetail` page
- [ ] Channel Detail: Playlists tab functional

**Acceptance test:** Add playlist → ordered video list shown → refresh detects added/removed videos.

---

### Milestone 8: Comment Module (Day 17)

**Goal:** Extract and display comments.

**Backend:**
- [ ] `YtdlpClient.extract_comments()`
- [ ] `CommentRepository`, `CommentService`
- [ ] `comment_controller` Blueprint
- [ ] Celery task: `extract_comments`

**Frontend:**
- [ ] `api/comments.js`
- [ ] `CommentThread` component
- [ ] `CommentCard` component
- [ ] Video Detail page: Comments tab functional

**Acceptance test:** Extract comments → threaded view shows replies → Creator/Pinned badges correct → comments_disabled handled gracefully.

---

### Milestone 9: Analytics + Snapshots (Days 18–19)

**Goal:** Growth charts and scheduled data collection.

**Backend:**
- [ ] `SnapshotRepository`, `SnapshotService`
- [ ] `analytics_controller` Blueprint
- [ ] Celery Beat schedule configured
- [ ] Celery tasks: `snapshot_all_channels`, `snapshot_tracked_videos`
- [ ] `GET /api/analytics/dashboard` endpoint
- [ ] Storage stats calculation

**Frontend:**
- [ ] `api/analytics.js`
- [ ] `GrowthChart` component (Recharts LineChart)
- [ ] `ViewsBarChart` component (Recharts BarChart horizontal)
- [ ] `DurationHistogram` component
- [ ] `UploadFrequencyChart` component
- [ ] Channel Detail: Analytics tab functional
- [ ] Dashboard: All sections functional (stats, jobs, activity, storage)

**Acceptance test:** Wait 24h (or mock snapshot data) → growth chart shows 2 data points → channel stats shows aggregate metrics → dashboard shows accurate counts.

---

### Milestone 10: RSS Monitoring (Day 20)

**Goal:** Automatic new video detection.

**Backend:**
- [ ] `RssClient` (feedparser wrapper)
- [ ] `rss_service.py`
- [ ] `rss_jobs.py` (Celery task)
- [ ] Beat schedule: RSS check every N minutes
- [ ] PATCH /api/channels/{id} handles rss_monitoring toggle

**Frontend:**
- [ ] Channel Detail: Monitor toggle functional
- [ ] Dashboard: RSS Discoveries card functional

**Acceptance test:** Enable monitoring → wait for RSS poll → new video detected → metadata extraction queued → dashboard shows discovery.

---

### Milestone 11: Settings Module (Day 21)

**Goal:** Full settings management.

**Backend:**
- [ ] `SettingsRepository`, `SettingsService`
- [ ] `settings_controller` Blueprint (all settings endpoints)
- [ ] Cookie file upload/test/delete
- [ ] Settings cached in Redis; invalidated on PATCH
- [ ] yt-dlp options updated from settings at job runtime

**Frontend:**
- [ ] `api/settings.js`
- [ ] `useSettings.js` hook
- [ ] `settingsStore.js` (Zustand)
- [ ] `Settings` page (all 5 sections)
- [ ] Cookie upload/test/delete UI
- [ ] Settings loaded on app boot

**Acceptance test:** Change player client → next yt-dlp call uses new client → upload cookies → test shows "valid" → settings persist after restart.

---

### Milestone 12: Polish + Error Handling + Testing (Days 22–24)

**Goal:** Production-quality application.

**Backend:**
- [ ] All custom exceptions wired to global error handlers
- [ ] Bot detection client rotation fully tested
- [ ] All API integration tests written and passing
- [ ] All service unit tests written and passing
- [ ] yt-dlp mock fixtures created
- [ ] 80%+ code coverage on service + repository layers
- [ ] `check_ytdlp_version` maintenance job
- [ ] `cleanup_expired_cache` maintenance job

**Frontend:**
- [ ] All empty states on all pages
- [ ] All loading skeletons on all data-fetching pages
- [ ] ErrorBoundary on all route components
- [ ] Mobile responsiveness verified: 375px, 768px, 1024px, 1440px
- [ ] Keyboard navigation tested
- [ ] ARIA labels on all icon-only buttons
- [ ] All error scenarios produce correct UI state
- [ ] Vitest + React Testing Library tests for ChannelCard, TranscriptViewer, JobProgressBar

**Deployment:**
- [ ] `docker compose up` smoke test (all 12 milestones verified)
- [ ] `DEPLOYMENT.md` written
- [ ] `README.md` complete (setup + usage + troubleshooting)
- [ ] `.env.example` complete and accurate
- [ ] `docs/API.md` generated or hand-written

---

## 17. Developer Guidelines

### 17.1 Naming Conventions

**Python:**
- Files: `snake_case.py`
- Classes: `PascalCase`
- Functions/methods: `snake_case`
- Constants: `UPPER_SNAKE_CASE`
- Private methods: `_snake_case` (single underscore prefix)
- Test files: `test_{module_name}.py`

**JavaScript/React:**
- Files: `PascalCase.jsx` for components, `camelCase.js` for utilities/hooks
- Components: `PascalCase`
- Hooks: `useCamelCase`
- Constants: `UPPER_SNAKE_CASE`
- Event handlers in components: `handleEventName` (`handleSubmit`, `handleDelete`)
- API function names: `getChannels`, `addChannel`, `deleteChannel` (verb + noun)

**CSS/Tailwind:** No custom CSS class names. Tailwind utilities only. If a pattern is repeated 3+ times, extract it into a React component, not a CSS class.

**URL routes (backend):** `kebab-case` — `/api/channel-snapshots`, NOT `/api/channelSnapshots`

**Database:** `snake_case` for table and column names. Consistent with SQLAlchemy conventions.

---

### 17.2 Folder Conventions

**One file, one responsibility.** No `utils.py` catch-all files. Each utility file has a clear domain: `url_parser.py`, `file_manager.py`, `time_utils.py`.

**No circular imports.** Dependency direction: `controllers → services → repositories → models`. Never reverse.

**Test files mirror source:** `backend/tests/unit/test_services/test_channel_service.py` mirrors `backend/app/services/channel_service.py`.

---

### 17.3 Coding Standards

**Python:**
- Black formatting: `black .` before commit
- Ruff linting: `ruff check .` must pass with zero warnings
- All functions have docstrings (even one-liners)
- Type hints on all function signatures
- Maximum function length: 50 lines (extract helpers if approaching)
- No bare `except:` — always catch specific exceptions

**JavaScript/React:**
- Prettier formatting
- ESLint must pass
- React components use function declarations (not arrow functions for top-level components)
- Props destructuring in function signature: `function ChannelCard({ channel, onDelete })`
- No prop drilling beyond 2 levels — use hooks or context
- Every `useEffect` has a dependency array (never omit it)

**SQL:**
- Never use raw SQL f-strings: `f"SELECT * FROM {table}"` — always use SQLAlchemy ORM
- All queries must have WHERE clauses (never `SELECT *` without filter in production code)
- All inserts use ORM model instances

---

### 17.4 Error Handling Standards

**Python — service layer:**
```python
def add_channel(self, url: str) -> dict:
    """Add a channel to the platform.
    
    Args:
        url: YouTube channel URL or handle
        
    Returns:
        dict with channel_id, job_id, status
        
    Raises:
        ValidationError: if URL format is invalid
        ExtractionFailedError: if yt-dlp extraction fails
    """
    # Implementation
```

Services always raise typed exceptions. Never return error strings or None to indicate failure.

**Python — controller layer:**
Controllers never catch exceptions directly. Global error handlers in `error_handlers.py` convert all exceptions to HTTP responses.

**Python — job layer:**
Celery tasks catch all exceptions at the outermost level, update job status to 'failed', then re-raise (to trigger Celery's retry mechanism if configured).

**JavaScript — hook layer:**
All mutations use `onError` callback to show toasts. Never swallow errors silently.

---

### 17.5 Logging Standards

**Python:** All logging via `logger = logging.getLogger(__name__)` — never `print()`.

Log levels:
- `DEBUG`: yt-dlp raw output, cache hits/misses, SQL queries (dev only)
- `INFO`: job start/complete, channel added, settings changed
- `WARNING`: job retry, deprecated usage, missing optional data
- `ERROR`: job failed after all retries, unexpected exception, bot detection

Always include context in log messages:
```python
logger.info("Channel crawl completed", extra={
    "channel_id": channel_id,
    "video_count": count,
    "duration_ms": int((time.time() - start) * 1000)
})
```

Never log: cookie file contents, proxy credentials, access tokens, user PII.

---

### 17.6 Testing Standards

**Test naming convention:**
```python
def test_{function_name}_{scenario}_{expected_result}():
    # test_add_channel_valid_url_returns_job_id
    # test_add_channel_invalid_url_raises_validation_error
    # test_add_channel_duplicate_returns_existing
```

**Test structure (AAA pattern):**
```python
def test_add_channel_valid_url_returns_job_id(mock_ytdlp, client, db):
    # Arrange
    mock_ytdlp.return_value = load_fixture('ytdlp_channel_response.json')
    url = "https://youtube.com/@mkbhd"
    
    # Act
    response = client.post('/api/channels', json={"url": url})
    
    # Assert
    assert response.status_code == 202
    assert "job_id" in response.json
    assert Channel.query.count() == 1
```

**No real network calls in tests.** All yt-dlp, transcript-api, and RSS calls are mocked via fixtures.

**Fixture files** (`backend/tests/fixtures/`):
- `ytdlp_video_response.json` — realistic yt-dlp output for a video
- `ytdlp_channel_response.json` — realistic channel output
- `ytdlp_flat_playlist_response.json` — array of flat video stubs
- `ytdlp_search_response.json` — search results
- `transcript_response.json` — youtube-transcript-api output

---

### 17.7 Git Workflow

**Branch naming:** `feat/{milestone-number}-{short-description}` — `feat/02-channel-module`

**Commit format (Conventional Commits):**
```
feat(channels): add channel crawl with progress reporting
fix(downloads): clean up partial files on cancellation
chore(deps): update yt-dlp to 2026.07.04
docs(api): document /api/channels endpoints
test(channels): add integration tests for channel CRUD
```

**No direct commits to main.** All work via feature branches + PR.

**One commit per logical unit.** Do not squash everything into one commit. Each meaningful change gets its own commit.

---

### 17.8 Dependency Management

**Python:** All dependencies pinned in `requirements.txt` with exact versions for production:
```
Flask==3.1.1
yt-dlp==2026.07.04
```

Dev dependencies in `requirements-dev.txt`:
```
black==24.7.0
ruff==0.5.6
pytest==8.3.2
```

**Never add a Python dependency without:**
1. Verifying it solves a problem not solvable with existing deps
2. Checking its maintenance status
3. Updating `requirements.txt`

**JavaScript:** `package.json` uses exact versions (no `^` or `~` for production):
```json
"react": "18.3.1",
```

**Adding a new npm package:** `npm install --save-exact {package}`.

---

### 17.9 Configuration Management

All configuration via environment variables. No hardcoded values in code.

The `config.py` BaseConfig reads from environment with explicit defaults:
```python
YTDLP_PLAYER_CLIENT = os.getenv('YTDLP_PLAYER_CLIENT', 'ios')
```

Sensitive values (passwords, secret keys) never have defaults in production config. `ProductionConfig` raises `ValueError` if `SECRET_KEY` is not set.

Configuration is consumed via Flask's `current_app.config` or via the `Settings` model from the database (for user-configurable settings like download quality).

---

## 18. Final Implementation Checklist

This checklist represents every deliverable. Implementation is complete when every item is checked.

### 18.1 Infrastructure

- [ ] `docker-compose.yml` — 6 services: mysql, redis, backend, celery-worker, celery-beat, frontend
- [ ] `docker/backend.Dockerfile` — Python 3.12-slim + FFmpeg
- [ ] `docker/frontend.Dockerfile` — Node 20 + Nginx multi-stage
- [ ] `docker/nginx.conf` — API proxy + React SPA routing
- [ ] `docker-compose.dev.yml` — volume mounts for hot reload
- [ ] `.env.example` — all 18 environment variables documented with defaults
- [ ] `docker compose up` cold start works with zero configuration

### 18.2 Backend Core

- [ ] `create_app()` factory function
- [ ] Config classes: Development, Production, Testing
- [ ] All 13 SQLAlchemy models
- [ ] All Alembic migrations (initial + any subsequent)
- [ ] Celery app instance
- [ ] Global error handlers (all 8 exception types)
- [ ] Request logging middleware (JSON format)
- [ ] Rate limiter (Flask-Limiter, Redis-backed)
- [ ] CORS configuration
- [ ] `GET /api/health` endpoint
- [ ] `wsgi.py` entry point for Gunicorn
- [ ] `run.py` entry point for development

### 18.3 Extraction Layer

- [ ] `YtdlpClient` with all 8 methods
- [ ] `TranscriptClient` with primary/fallback logic
- [ ] `RssClient` (feedparser)
- [ ] `CookieManager`
- [ ] `BotMitigation` (player client rotation via Redis)
- [ ] All yt-dlp base options applied (quiet, player_client, ratelimit, cookiefile, proxy)
- [ ] All yt-dlp exceptions mapped to custom exceptions
- [ ] Custom exception hierarchy (all 10 exception classes)

### 18.4 Service Layer (one per domain)

- [ ] `ChannelService` — add, refresh, delete, list, crawl
- [ ] `VideoService` — extract, refresh, delete, list, stats
- [ ] `TranscriptService` — extract (with fallback), list languages, export
- [ ] `CommentService` — extract, list
- [ ] `PlaylistService` — add, refresh, delete, crawl
- [ ] `DownloadService` — queue video/audio/subtitle/thumbnail, cancel
- [ ] `SearchService` — YouTube search (cached), internal FULLTEXT search
- [ ] `AnalyticsService` — dashboard stats, channel stats
- [ ] `SnapshotService` — create channel snapshot, create video snapshot
- [ ] `RssService` — check channel RSS, detect new videos
- [ ] `SettingsService` — read, update, cookie upload/test/delete, initialize defaults
- [ ] `QueueService` — create job, update status, cancel, retry
- [ ] `CacheService` — Redis wrapper (get, set, delete, delete_pattern)

### 18.5 Repository Layer (one per entity)

- [ ] `ChannelRepository`
- [ ] `VideoRepository` (with aggregate queries)
- [ ] `TranscriptRepository` (with FULLTEXT search)
- [ ] `CommentRepository`
- [ ] `PlaylistRepository`
- [ ] `DownloadRepository`
- [ ] `SearchRepository`
- [ ] `SnapshotRepository` (channel + video)
- [ ] `QueueRepository`
- [ ] `SettingsRepository`

### 18.6 Controllers / API Endpoints

- [ ] Channel: 8 endpoints (GET list, POST, GET detail, PATCH, DELETE, POST refresh, POST crawl, GET videos, GET analytics, GET stats)
- [ ] Video: 6 endpoints (GET list, POST, GET detail, POST refresh, DELETE, GET formats, GET snapshots)
- [ ] Transcript: 5 endpoints (GET, POST extract, GET search, GET export, GET languages)
- [ ] Comment: 2 endpoints (GET, POST extract)
- [ ] Playlist: 5 endpoints (GET list, POST, GET detail, POST refresh, DELETE)
- [ ] Download: 8 endpoints (GET list, POST video, POST audio, POST subtitle, POST thumbnail, DELETE, POST cancel, {download_id}/cancel)
- [ ] Search: 2 endpoints (GET youtube, GET internal)
- [ ] Analytics: 1 endpoint (GET dashboard)
- [ ] Jobs: 5 endpoints (GET list, GET detail, GET stream SSE, POST cancel, POST retry)
- [ ] Settings: 5 endpoints (GET, PATCH, POST cookies/upload, POST cookies/test, DELETE cookies)

### 18.7 Background Jobs

- [ ] `extract_video_metadata` task
- [ ] `extract_channel_metadata` task
- [ ] `crawl_channel_videos` task (streaming flat-playlist)
- [ ] `extract_transcript` task
- [ ] `extract_comments` task
- [ ] `download_video` task (with progress hook + Redis pub/sub)
- [ ] `download_audio` task
- [ ] `download_subtitle` task
- [ ] `download_thumbnail` task
- [ ] `check_all_rss_feeds` task (Beat scheduled)
- [ ] `snapshot_all_channels` task (Beat scheduled, daily 2 AM)
- [ ] `snapshot_tracked_videos` task (Beat scheduled, daily 3 AM)
- [ ] `check_ytdlp_version` task (Beat scheduled, weekly)
- [ ] `cleanup_expired_cache` task (Beat scheduled, daily 1 AM)
- [ ] All retry policies configured per task category
- [ ] Redis pub/sub progress events published by all long-running tasks

### 18.8 Frontend — Pages

- [ ] `Dashboard.jsx` — all 6 sections (stats, jobs, discoveries, activity, storage, monitored)
- [ ] `ChannelList.jsx` — grid + search + sort + Add modal + pagination
- [ ] `ChannelDetail.jsx` — header + stats + 4 tabs (Videos, Playlists, Analytics, Links)
- [ ] `VideoDetail.jsx` — header + stats + actions + 5 tabs (Description, Formats, Chapters, Transcript, Comments)
- [ ] `PlaylistDetail.jsx` — header + ordered video table
- [ ] `Search.jsx` — dual mode + filters + results
- [ ] `Downloader.jsx` — quick form + active downloads + history
- [ ] `Jobs.jsx` — filter bar + table + detail modal
- [ ] `Settings.jsx` — 5 sections + cookie management
- [ ] `NotFound.jsx`

### 18.9 Frontend — Components

- [ ] Layout: `AppShell`, `Sidebar`, `TopBar`
- [ ] Channel: `ChannelCard`, `ChannelHeader`, `ChannelStats`
- [ ] Video: `VideoCard`, `VideoGrid`, `VideoTable`, `VideoMetaPanel`
- [ ] Transcript: `TranscriptViewer`, `TranscriptSearch`
- [ ] Comments: `CommentThread`, `CommentCard`
- [ ] Charts: `GrowthChart`, `ViewsBarChart`, `DurationHistogram`, `UploadFrequencyChart`
- [ ] Jobs: `JobStatusBadge`, `JobProgressBar`, `JobCard`
- [ ] Download: `FormatSelector`, `QualityPicker`, `DownloadButton`
- [ ] Common: `Button`, `Input`, `Modal`, `Toast`, `Spinner`, `EmptyState`, `ErrorBoundary`, `Pagination`, `Badge`, `Tooltip`, `ConfirmDialog`, `DataTable`, `Skeleton`

### 18.10 Frontend — Hooks

- [ ] `useChannel` (useChannels, useChannel, useAddChannel, useRefreshChannel, useCrawlChannel, useDeleteChannel, useChannelAnalytics, useChannelStats)
- [ ] `useVideo` (useVideos, useVideo, useAddVideo, useRefreshVideo, useDeleteVideo, useVideoFormats, useVideoSnapshots)
- [ ] `useTranscript` (useTranscript, useExtractTranscript, useTranscriptSearch, useTranscriptLanguages)
- [ ] `useComments` (useComments, useExtractComments)
- [ ] `usePlaylist` (usePlaylists, usePlaylist, useAddPlaylist, useRefreshPlaylist, useDeletePlaylist)
- [ ] `useDownload` (useDownloads, useQueueVideoDownload, useQueueAudioDownload, useCancelDownload, useDeleteDownload)
- [ ] `useSearch` (useYouTubeSearch, useInternalSearch)
- [ ] `useJobs` (useJobs, useJob, useCancelJob, useRetryJob)
- [ ] `useSettings` (useSettings, useUpdateSettings, useCookieUpload, useCookieTest, useCookieDelete)
- [ ] `useJobProgress` (SSE via EventSource)
- [ ] `useToast` (add/remove toasts)
- [ ] `useDashboard` (dashboard stats query)

### 18.11 Frontend — State (Zustand + TanStack Query)

- [ ] `uiStore` (sidebarOpen, toasts, activeJobCount)
- [ ] `settingsStore` (settings cached, isLoaded)
- [ ] `jobStore` (activeJobs Map, CRUD methods)
- [ ] TanStack Query client configured with all global defaults
- [ ] All query key conventions followed
- [ ] All mutation invalidation rules implemented
- [ ] Settings loaded on app boot (bootstrap)

### 18.12 File Storage

- [ ] Directory structure created on app startup
- [ ] `FileManager` class (path construction, validation, space check, cleanup)
- [ ] `PathTraversalError` check on all file operations
- [ ] Storage stats calculation function
- [ ] Disk space check before download starts
- [ ] Partial file cleanup on download failure/cancel
- [ ] Thumbnail CDN URL expiry handling (re-fetch and retry)

### 18.13 Caching

- [ ] `CacheService` implemented (get, set, delete, delete_pattern)
- [ ] Redis DB allocation (0: Celery broker, 1: results, 2: app cache, 3: rate limiter)
- [ ] All 10 cache key patterns implemented with correct TTLs
- [ ] Cache invalidation after every mutation (all 9 invalidation rules)
- [ ] Redis `maxmemory 512mb` + `maxmemory-policy allkeys-lru` configured

### 18.14 Error Handling

- [ ] All 10 exception classes implemented
- [ ] Global error handlers for all exception types
- [ ] Retry logic on Celery tasks (autoretry_for + retry_backoff + retry_jitter)
- [ ] Bot detection rotation (5 client options, Redis state)
- [ ] Download failure cleanup (partial file deleted, semaphore released)
- [ ] SSE reconnect logic (EventSource onerror → 3 retry attempts → polling fallback)
- [ ] All 11 error UX scenarios produce correct UI state (Section 14)

### 18.15 Testing

- [ ] `conftest.py` with all 7 fixtures (app, db, client, mock_ytdlp, mock_transcript, sample_channel, sample_video, sample_transcript)
- [ ] 4 fixture JSON files in `tests/fixtures/`
- [ ] Unit tests for: ChannelService (6 cases), VideoService (6 cases), TranscriptService (4 cases), DownloadService (5 cases), SearchService (4 cases)
- [ ] Unit tests for: url_parser.py, file_manager.py
- [ ] Integration tests for all 9 controller modules (success + error cases for each endpoint)
- [ ] All 10 edge cases from spec Section 16.6 tested
- [ ] Frontend: Vitest tests for ChannelCard, TranscriptViewer, JobProgressBar
- [ ] No test makes real network calls
- [ ] Coverage ≥ 80% on service and repository layers

### 18.16 Deployment

- [ ] Docker Compose `docker compose up` works cold (no pre-configuration)
- [ ] Alembic migrations run automatically on backend container start
- [ ] Celery worker starts and connects to Redis automatically
- [ ] Frontend served correctly on port 3000 via Nginx
- [ ] `/api/` requests proxied to backend correctly
- [ ] All React routes work on direct browser access (Nginx try_files)
- [ ] Volume mounts persist data across container restarts
- [ ] `bgutil-pot` Docker profile available (opt-in)
- [ ] Render deployment guide written
- [ ] Railway deployment guide written
- [ ] VPS deployment guide written
- [ ] Windows local dev guide written

### 18.17 Documentation

- [ ] `README.md` — project overview, quick start, feature list, screenshots placeholder
- [ ] `docs/DEPLOYMENT.md` — all 4 deployment targets
- [ ] `docs/CONFIGURATION.md` — all 18 environment variables with types, defaults, examples
- [ ] `docs/API.md` — all endpoints with request/response examples
- [ ] `docs/LEGAL.md` — usage disclaimer, ToS notice, legal considerations summary
- [ ] Code: all Python functions/classes have docstrings
- [ ] Code: all React components have JSDoc comment at top with props description

### 18.18 Performance Verification

- [ ] API response time for DB-only queries < 200ms (test with `wrk` or similar)
- [ ] No `SELECT *` queries in repositories
- [ ] All FK columns have indexes confirmed in migration
- [ ] FULLTEXT indexes created and verified working
- [ ] Large channel crawl (100+ videos) uses streaming (not memory accumulation)
- [ ] Downloads use streaming (not memory accumulation)
- [ ] TanStack Query deduplication verified (multiple components don't cause multiple API calls)
- [ ] Thumbnails use `loading="lazy"` attribute

### 18.19 Accessibility Verification

- [ ] All icon-only buttons have `aria-label`
- [ ] All form inputs have associated `<label>`
- [ ] All modals have `role="dialog"` + `aria-modal` + `aria-labelledby`
- [ ] Focus trapping works in modals
- [ ] Keyboard navigation works through all interactive elements
- [ ] Color contrast ≥ 4.5:1 verified for all text (use Lighthouse or similar)
- [ ] `aria-live` region exists for toast announcements
- [ ] Screen reader can navigate primary user flows

### 18.20 Final Smoke Test Checklist

Run through this sequence after a cold `docker compose up`:

- [ ] `http://localhost:3000` loads AppShell
- [ ] `http://localhost:5000/api/health` returns 200
- [ ] Add channel by URL → metadata appears within 10 seconds
- [ ] Navigate to Channel Detail → all fields render
- [ ] Crawl channel videos (small channel, < 50 videos) → videos appear
- [ ] Add video by URL → Video Detail renders all tabs
- [ ] Extract transcript → TranscriptViewer shows timed segments
- [ ] Search YouTube → results appear → Add to Library works
- [ ] Queue video download → progress bar updates → file exists on disk
- [ ] Queue audio download → MP3 file created
- [ ] Settings page loads → all fields populate from defaults
- [ ] Upload test cookies → test shows valid/invalid result
- [ ] Jobs page shows all completed jobs
- [ ] Delete a channel → cascading delete removes all associated data
- [ ] Docker containers survive `docker compose restart` with data intact

---

*End of YouTube Analyzer Implementation Blueprint*  
*Document Version: 1.0 | July 2026*  
*Status: Final — Implementation Ready*  
*Next step: Implementation begins with Milestone 1 (Foundation)*
