# YouTube Analyzer Platform — Engineering Research Document

**Version:** 1.0  
**Date:** July 2026  
**Classification:** Internal Architecture Document  
**Status:** Final — Ready for Implementation Phase

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Research Methodology](#2-research-methodology)
3. [Complete Library Analysis](#3-complete-library-analysis)
4. [Library Comparison Matrix](#4-library-comparison-matrix)
5. [Feature Matrix](#5-feature-matrix)
6. [Complete Data Matrix](#6-complete-data-matrix)
7. [Unsupported Features (What Cannot Be Built)](#7-unsupported-features)
8. [Deployment Analysis](#8-deployment-analysis)
9. [Performance Analysis](#9-performance-analysis)
10. [Legal and Ethical Considerations](#10-legal-and-ethical-considerations)
11. [Recommended Final Stack](#11-recommended-final-stack)
12. [Database Design](#12-database-design)
13. [High-Level Architecture](#13-high-level-architecture)
14. [Dependency Tree](#14-dependency-tree)
15. [Future Roadmap](#15-future-roadmap)
16. [Final Recommendation](#16-final-recommendation)

---

## 1. Executive Summary

This document is the single source of truth for the YouTube Analyzer Platform — a production-quality application that extracts, analyzes, and presents publicly available YouTube data using only open-source libraries, with no dependency on the official YouTube Data API, Google OAuth, or any paid services.

### Core Findings

After deep research across GitHub, PyPI, Reddit, Hacker News, StackOverflow, and developer communities, the following conclusions were reached:

**The minimum viable library stack for a production YouTube Analyzer is three libraries:**

| Library | Role | Verdict |
|---|---|---|
| `yt-dlp` | Metadata, downloads, comments, transcripts | **KEEP — Primary engine** |
| `youtube-transcript-api` | Transcript extraction (faster, more reliable) | **KEEP — Specialized supplement** |
| `FFmpeg` (binary) | Audio/video processing and muxing | **KEEP — Required for downloads** |

**Three candidate libraries should be rejected:**

| Library | Verdict | Reason |
|---|---|---|
| `pytubefix` | **REJECT** | Redundant — yt-dlp does everything it does, better |
| `scrapetube` | **REJECT** | Functionally superseded by yt-dlp channel extraction |
| `youtube-search-python` | **REJECT** | Officially retired in 2022; dead project |
| `Playwright` | **CONDITIONAL** | Only needed as a last-resort fallback, not a core dependency |

### Critical 2025–2026 Landscape Change

YouTube introduced **Proof-of-Origin Tokens (PoToken)** in 2025, creating a systemic challenge for all non-API extraction tools. Every video request now requires a session-bound, video-bound token with a lifespan as short as 12 hours. This is the single most important architectural constraint for the platform and must be planned for explicitly. The `bgutil-ytdlp-pot-provider` sidecar service (Node.js) addresses this today, but the arms race continues.

---

## 2. Research Methodology

### Sources Consulted

- **GitHub** — Repository health, commit frequency, open issues, contributor count, fork activity
- **PyPI** — Download statistics, release history, Python version compatibility
- **Snyk Advisor** — Maintenance health scores for Python packages
- **Hacker News** — Community discussions on YouTube scraping challenges in 2025–2026
- **Reddit** (r/learnpython, r/webdev, r/DataHoarder) — Real-world experience reports
- **StackOverflow** — Specific technical questions, known failure modes
- **Dev.to and Medium** — Production case studies and current methodology guides
- **Official GitHub Issues Trackers** — Understanding active failure modes (particularly yt-dlp #12482, #14307, #14390, #16082, #13968 relating to PoToken and SABR)
- **Legal analysis sources** — Web scraping legality research (2025–2026 case law)
- **arXiv** — Academic research on YouTube extraction at scale (arXiv:2603.18071)

### Evaluation Criteria

Every library was scored on:
- **Maintenance Status** — Last commit date, release frequency, issue response time
- **Community Health** — GitHub stars, contributor count, fork count
- **Feature Completeness** — What it covers relative to the project needs
- **Deployment Compatibility** — Docker, Linux, Windows, macOS, cloud platforms
- **Overlap** — Whether its functionality duplicates another library in the stack
- **Failure Surface** — How often it breaks due to YouTube changes and how quickly it recovers
- **Long-term Viability** — Likelihood of continued maintenance over 3–5 years

---

## 3. Complete Library Analysis

---

### 3.1 yt-dlp

| Property | Value |
|---|---|
| **GitHub** | github.com/yt-dlp/yt-dlp |
| **PyPI** | pypi.org/project/yt-dlp |
| **License** | Unlicense (public domain) |
| **Stars** | 181,000+ (July 2026) |
| **Last Commit** | July 4, 2026 (latest release: 2026.07.04) |
| **Release Frequency** | Every 2–6 weeks |
| **Monthly PyPI Downloads** | 12 million+ |
| **Python Compatibility** | 3.9+ (3.11+ recommended; 3.10 EOL October 2026) |
| **Contributors** | 200+ active |
| **Forks** | 7,373+ |
| **License** | Unlicense (effectively public domain) |

#### What It Does

yt-dlp is the definitive fork of youtube-dl, born in late 2020 when the original project's maintenance velocity slowed. It is now the community standard for programmatic YouTube data extraction. It supports 1,800+ sites through an extractor plugin system and is included in Ubuntu (22.04+) and replaced youtube-dl in Debian 12.

**Extractable YouTube data via yt-dlp:**
- Complete video metadata (title, description, tags, categories, language, upload date, duration)
- View count, like count, comment count
- Channel metadata (name, ID, subscriber count `channel_follower_count`, description)
- Thumbnail URLs (all resolutions)
- Available formats (codecs, resolution, bitrate, filesize estimates)
- Subtitle/caption tracks (all languages, auto-generated and manual)
- Chapter markers
- Video download (all formats and qualities)
- Audio extraction
- Playlist metadata and all video IDs in a playlist
- Channel uploads (all video IDs)
- Shorts detection
- Live stream status (`is_live`, `was_live`, `live_status`)
- Comments (paginated, threaded) via `getcomments=True`
- Heatmap data (most-replayed timestamps)
- Sponsorship segments (via SponsorBlock integration)

#### 2025–2026 Critical Issues

**PoToken Requirement:** YouTube's BotGuard system now requires a Proof-of-Origin Token for video requests. Tokens are:
- Bound to both the visitor session and the video ID
- Expire in as little as 12 hours
- Generated by BotGuard (Web), DroidGuard (Android), or iOSGuard (iOS)
- Not transferable between platforms

**Mitigation:** The `bgutil-ytdlp-pot-provider` plugin (Node.js sidecar service, dockerized) generates tokens on-demand. It hooks into yt-dlp via the POT plugin framework. This is currently the only reliable production mitigation. Note: As of mid-2026, passing PO tokens no longer fully bypasses bot checks in all cases (see `bgutil-ytdlp-pot-provider` issue #37). The situation is actively evolving.

**SABR (Server-side Adaptive Bitrate):** YouTube began serving SABR-only formats through the `web` extractor in 2025. Mitigation: use `--extractor-args "youtube:player_client=web_safari"` or similar flags, plus fresh browser cookies from a logged-in session.

**Datacenter IP Blocking:** Cloud IPs (AWS, GCP, Azure egress ranges) are flagged faster than residential IPs. For large-scale use, residential proxies or cookie injection from a real browser session are required.

#### Deployment

- Docker: Yes — installs via pip, zero compiled dependencies
- Windows: Yes — native or WSL
- Linux: Yes — included in Ubuntu/Debian repos
- macOS: Yes — via pip or Homebrew
- FFmpeg: Optional for metadata extraction; required for muxing video/audio streams
- Browser: Not required (except for cookie extraction to mitigate bot detection)

#### **Verdict: YES — Keep. Primary engine for the entire platform.**

---

### 3.2 youtube-transcript-api

| Property | Value |
|---|---|
| **GitHub** | github.com/jdepoix/youtube-transcript-api |
| **PyPI** | pypi.org/project/youtube-transcript-api |
| **License** | MIT |
| **Stars** | ~6,500 |
| **Last Commit** | Active (v1.2.3 released January 29, 2026) |
| **Release Frequency** | Monthly during active periods |
| **Maintenance Score** | Healthy (Snyk Advisor) |
| **Python Compatibility** | 3.6+ |
| **Contributors** | Small team (~10), single primary maintainer |

#### What It Does

A dedicated Python library for fetching YouTube transcripts and subtitles without requiring an API key or headless browser. It fetches the transcript XML endpoint directly. It handles:
- Manual transcripts (all available languages)
- Auto-generated transcripts
- Transcript translation (if YouTube provides it)
- Returns structured data: `[{text, start, duration}]`
- v1.0+ introduced the `YouTubeTranscriptApi()` class with proxy support

#### Why Keep It Despite yt-dlp Overlap

yt-dlp can also fetch transcripts, but `youtube-transcript-api` is:
1. **Faster** — No format enumeration overhead; fetches transcript XML directly
2. **Simpler API** — Single method call, returns clean structured data
3. **More granular** — Better control over language selection and translation
4. **Lighter** — No FFmpeg, no format selection, no download machinery

For a platform that processes transcripts at scale (e.g., AI analysis pipeline), using `youtube-transcript-api` for transcripts and yt-dlp only for metadata/downloads is the architecturally cleaner split.

**Important limitation:** This library hits YouTube's transcript endpoint directly. If YouTube changes the endpoint (as happened in early 2025, triggering the v1.0 rewrite), it breaks until the maintainer patches it. Recovery time has historically been days to weeks.

#### **Verdict: YES — Keep. Specialized for transcript extraction; faster and simpler than yt-dlp for this purpose. Use as the primary transcript source, with yt-dlp as fallback.**

---

### 3.3 FFmpeg (Binary)

| Property | Value |
|---|---|
| **Website** | ffmpeg.org |
| **License** | LGPL 2.1+ / GPL 2+ |
| **Latest Version** | 8.1.2 (July 2026) |
| **Platforms** | Windows, Linux, macOS, all architectures |
| **Docker Image** | linuxserver/ffmpeg (active, maintained) |
| **Bundled option** | `imageio-ffmpeg` (includes binary in wheel) |

#### What It Does

FFmpeg is not a Python library — it is a system binary. It is required by yt-dlp when:
- Downloading video and audio as separate streams (DASH) and muxing them
- Converting formats (e.g., MP4, WebM, MP3, M4A)
- Extracting audio from video
- Processing subtitles for embedding
- Thumbnail embedding in audio files

For **metadata-only extraction** (no downloads), FFmpeg is not required. yt-dlp warns when FFmpeg is absent but still functions for metadata and single-stream downloads.

#### Deployment

- **Docker:** `apt-get install -y ffmpeg` in Dockerfile — simple, standard
- **Python bundled:** `imageio-ffmpeg` pip package bundles the binary (60 MB but zero OS dependency)
- **Render/Railway:** Available via apt or Docker build
- **Windows:** Pre-built binary from ffmpeg.org; `winget install ffmpeg`
- **macOS:** `brew install ffmpeg`

#### FFmpeg Python Wrappers (Not Recommended as Core Dependency)

| Wrapper | Notes | Verdict |
|---|---|---|
| `ffmpeg-python` | Fluent API for FFmpeg subprocess calls | Optional — only if complex FFmpeg pipelines needed |
| `imageio-ffmpeg` | Bundles FFmpeg binary; useful for no-apt environments | Optional — useful for Render deployment |
| `PyAV` | C-level FFmpeg bindings; faster but complex | Not needed for this project |

For this platform, FFmpeg is invoked by yt-dlp automatically. No Python wrapper is needed unless the platform adds custom post-processing.

#### **Verdict: YES — Keep. Required for download functionality. Install as system binary via Dockerfile; do not add a Python wrapper unless custom post-processing is needed.**

---

### 3.4 pytubefix

| Property | Value |
|---|---|
| **GitHub** | github.com/JuanBindez/pytubefix |
| **PyPI** | pypi.org/project/pytubefix |
| **License** | MIT |
| **Stars** | ~1,100 |
| **Last Commit** | Active (v10.3.6+ as of June 2026) |
| **Python Compatibility** | 3.7+ |

#### What It Does

pytubefix is an actively maintained fork of the abandoned `pytube` library. It provides:
- Video/audio download
- Progressive and DASH stream access
- Caption/subtitle extraction in SRT format
- Channel video listing
- Progress callbacks
- OAuth support (optional)
- Zero third-party dependencies

It was created because the original `pytube` is effectively abandoned.

#### Why Reject It

**Complete functional overlap with yt-dlp.** Every feature pytubefix provides is covered by yt-dlp, which additionally has:
- 10x larger community and faster YouTube break recovery
- Better format selection
- Comment extraction
- SponsorBlock integration
- Heatmap extraction
- Better proxy support
- More reliable bot evasion

pytubefix stars (~1,100) versus yt-dlp stars (~181,000) tells the adoption story clearly. When YouTube makes breaking changes, yt-dlp patches within hours; pytubefix may take days or longer.

The only theoretical advantage of pytubefix is its zero-dependency nature (no FFmpeg required for some operations), but this is not sufficient to justify carrying a redundant library.

#### **Verdict: NO — Reject. Completely redundant with yt-dlp. Adds maintenance surface with no unique capability. Do not include.**

---

### 3.5 scrapetube

| Property | Value |
|---|---|
| **GitHub** | github.com/dermasmid/scrapetube |
| **PyPI** | pypi.org/project/scrapetube |
| **License** | MIT |
| **Stars** | ~477 |
| **Last Commit** | Unclear — multiple open issues from 2024 with no response (issues #53–#65 unresolved) |
| **Maintenance Score** | Uncertain / declining |

#### What It Does

scrapetube scrapes YouTube channel videos, playlist videos, and search results without Selenium. It uses YouTube's internal InnerTube API endpoints (`/youtubei/v1/browse`) and returns basic video metadata (videoId, title, thumbnails, viewCountText, publishedTimeText).

#### Why Reject It

1. **Maintenance uncertainty** — Issues filed throughout 2024 remain unresolved with no maintainer engagement. The project shows signs of slowing maintenance.
2. **Functional overlap** — yt-dlp extracts channel video lists with `--flat-playlist`. Example: `yt-dlp --flat-playlist --dump-json "https://www.youtube.com/@channelname"` returns structured JSON for every video.
3. **Less data** — scrapetube returns only basic stub data (videoId, title, thumbnail, view count text). yt-dlp's `--flat-playlist` returns richer data including duration, upload date, and more.
4. **Not a bottleneck** — Channel crawling is not a frequent real-time operation in this platform; yt-dlp's approach is adequate.

The InnerTube approach that scrapetube implements is actually useful, but it is better implemented directly or via yt-dlp's existing channel extractor.

#### **Verdict: NO — Reject. Uncertain maintenance status; functionally superseded by yt-dlp's `--flat-playlist` channel extraction. Do not include.**

---

### 3.6 youtube-search-python

| Property | Value |
|---|---|
| **GitHub** | github.com/alexmercerind/youtube-search-python |
| **PyPI** | pypi.org/project/youtube-search-python |
| **License** | MIT |
| **Last Commit** | 2022 |
| **Retirement Announcement** | June 21, 2022 (Issue #189) |

#### What It Does

youtube-search-python provided YouTube search without an API key, returning video metadata from search results.

#### Why Reject It

**This project was officially retired by its author on June 23, 2022.** The retirement was publicly announced in Issue #189 of the GitHub repository. The library has received no updates since retirement. Using a project the author has officially retired is an unacceptable risk for a production system.

**Alternative:** YouTube search functionality can be achieved via:
1. yt-dlp: `yt-dlp "ytsearch10:query" --dump-json --no-download` (reliable, maintained)
2. YouTube RSS feeds: `https://www.youtube.com/feeds/videos.xml?channel_id=UCXXX` (official, no bot risk, returns last 15 videos)
3. Direct InnerTube API calls to `/youtubei/v1/search` (fragile, not recommended)

#### **Verdict: NO — Reject. Officially dead since June 2022. Do not include under any circumstances.**

---

### 3.7 Playwright

| Property | Value |
|---|---|
| **GitHub** | github.com/microsoft/playwright |
| **PyPI** | pypi.org/project/playwright |
| **License** | Apache 2.0 |
| **Stars** | 72,000+ |
| **Maintained by** | Microsoft |
| **Python Compatibility** | 3.8+ |
| **Browser Required** | Yes — Chromium, Firefox, or WebKit |

#### What It Does

Playwright is a browser automation library that controls real browsers (Chromium, Firefox, Safari/WebKit). It can navigate any JavaScript-heavy page and extract rendered HTML, fill forms, click elements, and take screenshots.

For YouTube, it could be used to:
- Render pages that require JavaScript
- Extract data from dynamically loaded content
- Simulate human-like browsing to evade bot detection

#### Why Playwright Is a Conditional Decision

**Do not include Playwright as a core dependency.**

Playwright dramatically increases:
- Docker image size (adds Chromium: ~500 MB)
- Deployment complexity
- Memory usage (300–500 MB per browser instance)
- Fragility (browser versions must be kept in sync)
- CPU usage

For 95%+ of YouTube data extraction tasks, yt-dlp performs the same function without a browser.

**When Playwright IS appropriate:**
- As a fallback mechanism when yt-dlp is blocked (rare)
- For extracting cookies from a logged-in YouTube session to pass to yt-dlp
- For scraping YouTube Studio analytics (requires login — owner-only data)
- As a tool used by developers/ops, not run in the production request path

**Architecture recommendation:** If Playwright is needed, run it as a separate isolated microservice or background worker, not as a library imported into the main Flask/FastAPI application.

#### **Verdict: CONDITIONAL — Do not include in the core stack. Architect as an optional background worker microservice for cookie generation and fallback scraping only.**

---

### 3.8 YouTube RSS Feeds (No Library Required)

YouTube provides official Atom RSS feeds for channels. This is a frequently overlooked capability that requires no library:

```
https://www.youtube.com/feeds/videos.xml?channel_id=UCxxxxxxxxxxxxxxxxxxxxxx
```

**Characteristics:**
- Official YouTube feature (no scraping, no bot detection)
- Returns last 15 videos only
- Contains: video ID, title, description (truncated), published date, channel name
- No API key required
- No quota limits
- Extremely reliable — has been stable for years
- Can be parsed with Python's standard `feedparser` or `xml.etree.ElementTree`

**Use case in this platform:** Channel monitoring and new video detection. Poll the RSS feed every 15–60 minutes to detect new uploads. When a new video is detected, trigger yt-dlp for full metadata extraction.

**Limitation:** Only last 15 videos. Not suitable for full channel crawl (use yt-dlp for that).

#### **Verdict: YES — Include as a lightweight channel monitoring mechanism (no library dependency; use Python stdlib xml parsing or add `feedparser`).**

---

### 3.9 Rejected Libraries (Not in Candidate List)

The following libraries were evaluated during research and explicitly rejected:

| Library | Reason for Rejection |
|---|---|
| `youtube-dl` (original) | Superseded by yt-dlp; last stable release December 2021; Debian removed it in favor of yt-dlp |
| `pytube` (original) | Abandoned; replaced by pytubefix which is also redundant with yt-dlp |
| `youtube-comment-downloader` | Redundant — yt-dlp handles comments natively |
| `tubescrape` | Very new (March 2026), minimal adoption, unproven stability |
| `py-yt-search` | Minimal adoption (~0.7.2), unclear maintenance trajectory |
| `moviepy` | Overkill for this project; heavy dependency on FFmpeg; use FFmpeg directly |
| `Selenium` | Superseded by Playwright for browser automation; heavyweight and fragile |
| `BeautifulSoup4 + requests` | Useful for HTML scraping but YouTube's JavaScript rendering makes raw HTML parsing unreliable |
| `PyAV` | C-level FFmpeg bindings; too complex for this use case; yt-dlp handles A/V via subprocess |
| `yt-dlp-transcripts` | Thin wrapper around yt-dlp for transcripts; adds no value over direct yt-dlp use |

---

## 4. Library Comparison Matrix

| Library | Purpose | Pros | Cons | Maintenance | Performance | Docker | Win | Linux | macOS | Recommended |
|---|---|---|---|---|---|---|---|---|---|---|---|
| **yt-dlp** | Everything | 181k stars; 12M PyPI/mo; fastest patches to YouTube changes; 1800+ extractors; metadata + download + comments + transcripts | PoToken complexity; SABR issues; datacenter IP blocking | Excellent | High | Yes | Yes | Yes | Yes | **YES** |
| **youtube-transcript-api** | Transcripts | Fast; clean API; no FFmpeg; handles auto-generated; translation support | Single maintainer; breaks when YouTube changes transcript endpoint | Good | Very High (lightweight) | Yes | Yes | Yes | Yes | **YES** |
| **FFmpeg** | A/V processing | Industry standard; required for DASH muxing; extensive format support | System binary (not pip); adds ~200MB to Docker | Excellent | Excellent | Yes | Yes | Yes | Yes | **YES (as system binary)** |
| **pytubefix** | Download | Zero dependencies; drop-in pytube replacement; active maintenance | 1,100 stars; same capability as yt-dlp but weaker; slower break recovery | Moderate | Moderate | Yes | Yes | Yes | Yes | **NO** |
| **scrapetube** | Channel crawl | Simple API; no Selenium; channel/playlist/search | 477 stars; stalled issues; superseded by yt-dlp flat-playlist | Uncertain | Low | Yes | Yes | Yes | Yes | **NO** |
| **youtube-search-python** | Search | Was clean API | Retired June 2022; dead project | Dead | N/A | N/A | N/A | N/A | N/A | **NO** |
| **Playwright** | Browser automation | Microsoft-backed; reliable JS rendering; multi-browser | 500MB+ Docker overhead; 300-500MB RAM per instance; deployment complexity | Excellent | Low (slow) | Partial | Yes | Yes | Yes | **CONDITIONAL** |
| **feedparser** | RSS parsing | Lightweight; parses YouTube RSS feeds; stdlib alternative exists | Only last 15 videos from YouTube RSS | Good | Excellent | Yes | Yes | Yes | Yes | **YES (optional, lightweight)** |

---

## 5. Feature Matrix

| Feature | Best Library | Alternative | Reliability | Deployment | Maintenance |
|---|---|---|---|---|---|
| Video metadata (title, description, tags) | yt-dlp | pytubefix | High | All platforms | Excellent |
| View count | yt-dlp | RSS feed (limited) | High | All platforms | Excellent |
| Like count | yt-dlp | None without API | Moderate (may be absent) | All platforms | Excellent |
| Comment count | yt-dlp | None without API | Moderate | All platforms | Excellent |
| Upload date | yt-dlp | RSS feed | High | All platforms | Excellent |
| Duration | yt-dlp | feedparser/RSS | High | All platforms | Excellent |
| Video ID | yt-dlp | RSS feed | High | All platforms | Excellent |
| Thumbnail URLs | yt-dlp | Direct URL construction | High | All platforms | Excellent |
| Available formats/qualities | yt-dlp | None | High | All platforms | Excellent |
| Codecs (video/audio) | yt-dlp | None | High | All platforms | Excellent |
| File size estimates | yt-dlp | None | Moderate | All platforms | Excellent |
| Video download (MP4, WebM) | yt-dlp + FFmpeg | pytubefix | High | All platforms | Excellent |
| Audio extraction (MP3, M4A) | yt-dlp + FFmpeg | pytubefix | High | All platforms | Excellent |
| Subtitle/caption download | yt-dlp | youtube-transcript-api | High | All platforms | Excellent |
| Auto-generated captions | yt-dlp | youtube-transcript-api | High | All platforms | Excellent |
| Transcript text (structured) | youtube-transcript-api | yt-dlp (subtitles) | High | All platforms | Good |
| Caption translation | youtube-transcript-api | None | Moderate | All platforms | Good |
| Chapter markers | yt-dlp | None | High | All platforms | Excellent |
| Video categories | yt-dlp | None | High | All platforms | Excellent |
| Video language | yt-dlp | None | Moderate | All platforms | Excellent |
| Heatmap (most replayed) | yt-dlp | None | Moderate | All platforms | Excellent |
| SponsorBlock segments | yt-dlp (plugin) | None | High | All platforms | Excellent |
| Comments (paginated) | yt-dlp | youtube-comment-downloader | Moderate (bot detection) | All platforms | Excellent |
| Comment replies | yt-dlp | None | Moderate | All platforms | Excellent |
| Live stream status | yt-dlp | None | High | All platforms | Excellent |
| Live stream download | yt-dlp | None | Moderate | All platforms | Excellent |
| Channel name | yt-dlp | RSS feed | High | All platforms | Excellent |
| Channel ID | yt-dlp | RSS feed | High | All platforms | Excellent |
| Channel description | yt-dlp | None | Moderate | All platforms | Excellent |
| Subscriber count | yt-dlp (`channel_follower_count`) | None without API | Moderate (sometimes absent) | All platforms | Excellent |
| Channel upload count | yt-dlp | None | Moderate | All platforms | Excellent |
| Channel total views | yt-dlp | None | Moderate | All platforms | Excellent |
| Channel join date | yt-dlp | None | Moderate (may be absent) | All platforms | Excellent |
| Channel banner URL | yt-dlp (channel page) | None | Moderate | All platforms | Excellent |
| Channel avatar/icon URL | yt-dlp | None | Moderate | All platforms | Excellent |
| Channel external links | yt-dlp | None | Moderate | All platforms | Excellent |
| Channel verification status | yt-dlp | None | Moderate | All platforms | Excellent |
| Playlist metadata | yt-dlp | scrapetube (rejected) | High | All platforms | Excellent |
| Playlist video list | yt-dlp | None | High | All platforms | Excellent |
| Playlist video count | yt-dlp | None | High | All platforms | Excellent |
| Channel video list (all) | yt-dlp (`--flat-playlist`) | RSS (last 15) | High | All platforms | Excellent |
| Channel playlists list | yt-dlp | None | Moderate | All platforms | Excellent |
| Shorts detection | yt-dlp | None | Moderate | All platforms | Excellent |
| Shorts download | yt-dlp + FFmpeg | None | High | All platforms | Excellent |
| YouTube Search (by query) | yt-dlp `ytsearch:` | None | Moderate | All platforms | Excellent |
| New video monitoring | YouTube RSS Feed | yt-dlp (polling) | High | All platforms | Stable |

---

## 6. Complete Data Matrix

### 6.1 Video-Level Data

| Data Field | Source | Library | Method | Deployable | Reliable | Limitations |
|---|---|---|---|---|---|---|
| Video Title | YouTube | yt-dlp | `extract_info(url)` → `title` | YES | High | None |
| Video ID | YouTube | yt-dlp | `extract_info(url)` → `id` | YES | High | None |
| Video URL | YouTube | yt-dlp | `extract_info(url)` → `webpage_url` | YES | High | None |
| Description (full) | YouTube | yt-dlp | `extract_info(url)` → `description` | YES | High | None |
| Upload Date | YouTube | yt-dlp | `extract_info(url)` → `upload_date` (YYYYMMDD) | YES | High | None |
| Duration (seconds) | YouTube | yt-dlp | `extract_info(url)` → `duration` | YES | High | None |
| View Count | YouTube | yt-dlp | `extract_info(url)` → `view_count` | YES | High | May lag real-time |
| Like Count | YouTube | yt-dlp | `extract_info(url)` → `like_count` | YES | Moderate | Absent on some videos |
| Dislike Count | YouTube | None (removed) | N/A — removed by YouTube in 2021 | NO | N/A | Permanently gone |
| Comment Count | YouTube | yt-dlp | `extract_info(url)` → `comment_count` | YES | Moderate | May be absent |
| Tags | YouTube | yt-dlp | `extract_info(url)` → `tags` (list) | YES | High | None |
| Categories | YouTube | yt-dlp | `extract_info(url)` → `categories` (list) | YES | High | None |
| Language | YouTube | yt-dlp | `extract_info(url)` → `language` | YES | Moderate | May be absent |
| Age Restriction | YouTube | yt-dlp | `extract_info(url)` → `age_limit` | YES | High | None |
| Is Live | YouTube | yt-dlp | `extract_info(url)` → `is_live` | YES | High | None |
| Was Live | YouTube | yt-dlp | `extract_info(url)` → `was_live` | YES | High | None |
| Live Status | YouTube | yt-dlp | `extract_info(url)` → `live_status` | YES | High | None |
| Availability | YouTube | yt-dlp | `extract_info(url)` → `availability` | YES | High | None |
| Thumbnail URL (default) | YouTube | yt-dlp | `extract_info(url)` → `thumbnail` | YES | High | CDN URL expires |
| Thumbnail URLs (all sizes) | YouTube | yt-dlp | `extract_info(url)` → `thumbnails` (list) | YES | High | CDN URLs expire |
| Channel Name | YouTube | yt-dlp | `extract_info(url)` → `channel` | YES | High | None |
| Channel ID | YouTube | yt-dlp | `extract_info(url)` → `channel_id` | YES | High | None |
| Channel URL | YouTube | yt-dlp | `extract_info(url)` → `channel_url` | YES | High | None |
| Uploader | YouTube | yt-dlp | `extract_info(url)` → `uploader` | YES | High | None |
| Uploader ID | YouTube | yt-dlp | `extract_info(url)` → `uploader_id` | YES | High | None |
| Subscriber Count | YouTube | yt-dlp | `extract_info(url)` → `channel_follower_count` | YES | Moderate | Sometimes absent |
| Available Formats | YouTube | yt-dlp | `extract_info(url)` → `formats` (list) | YES | High | None |
| Best Video Format | YouTube | yt-dlp | Format selection via `-f bestvideo+bestaudio` | YES | High | Requires FFmpeg for mux |
| Best Audio Format | YouTube | yt-dlp | `-f bestaudio` | YES | High | None |
| Filesize Approximate | YouTube | yt-dlp | `formats[n].get('filesize_approx')` | YES | Moderate | Estimate only |
| Chapter Markers | YouTube | yt-dlp | `extract_info(url)` → `chapters` | YES | High | Absent if none set |
| Heatmap Data | YouTube | yt-dlp | `extract_info(url)` → `heatmap` | YES | Moderate | Not all videos |
| Subtitles (all languages) | YouTube | yt-dlp | `extract_info(url)` → `subtitles` | YES | High | None |
| Auto-Captions (all langs) | YouTube | yt-dlp | `extract_info(url)` → `automatic_captions` | YES | High | None |
| Transcript (structured) | YouTube | youtube-transcript-api | `ytt_api.fetch(video_id)` | YES | High | Requires captions to exist |
| Comments (all, threaded) | YouTube | yt-dlp | `getcomments=True` in opts | YES | Moderate | Slow; bot detection risk |
| Playability Status | YouTube | yt-dlp | `extract_info(url)` → `playability_status` | YES | High | None |
| License | YouTube | yt-dlp | `extract_info(url)` → `license` | YES | Moderate | May be absent |
| Creators | YouTube | yt-dlp | `extract_info(url)` → `creators` | YES | Moderate | May be absent |
| Release Date | YouTube | yt-dlp | `extract_info(url)` → `release_date` | YES | Moderate | May be absent |

### 6.2 Channel-Level Data

| Data Field | Source | Library | Method | Deployable | Reliable | Limitations |
|---|---|---|---|---|---|---|
| Channel Name | YouTube | yt-dlp | Channel URL extraction | YES | High | None |
| Channel ID | YouTube | yt-dlp | Channel URL extraction → `id` | YES | High | None |
| Channel Handle (@name) | YouTube | yt-dlp | Channel URL extraction | YES | High | None |
| Channel Description | YouTube | yt-dlp | Channel extraction → `description` | YES | Moderate | May be truncated |
| Subscriber Count | YouTube | yt-dlp | Channel extraction → `channel_follower_count` | YES | Moderate | Sometimes absent or rounded |
| Total Video Count | YouTube | yt-dlp | Channel extraction → `playlist_count` | YES | Moderate | May be absent |
| Total View Count | YouTube | yt-dlp | Channel extraction (available in channel info) | YES | Moderate | May be absent |
| Channel Join Date | YouTube | yt-dlp | Channel extraction (where available) | YES | Low | Frequently absent |
| Channel Avatar URL | YouTube | yt-dlp | Channel extraction → thumbnails | YES | Moderate | CDN URL expires |
| Channel Banner URL | YouTube | yt-dlp | Channel extraction (where available) | YES | Moderate | May be absent |
| Verification Status | YouTube | yt-dlp | Channel extraction → `channel_is_verified` | YES | Moderate | May be absent |
| Channel URL | YouTube | yt-dlp | Channel extraction → `channel_url` | YES | High | None |
| External Links | YouTube | yt-dlp | Channel extraction → `channel_url` links section | YES | Low | Limited data |
| All Video IDs (channel) | YouTube | yt-dlp | `--flat-playlist "https://youtube.com/@channel/videos"` | YES | High | Rate limited at scale |
| New Videos (monitoring) | YouTube | RSS feed | `feeds/videos.xml?channel_id=...` | YES | High | Last 15 only |

### 6.3 Playlist-Level Data

| Data Field | Source | Library | Method | Deployable | Reliable | Limitations |
|---|---|---|---|---|---|---|
| Playlist Title | YouTube | yt-dlp | Playlist URL extraction → `title` | YES | High | None |
| Playlist ID | YouTube | yt-dlp | Playlist URL extraction → `id` | YES | High | None |
| Playlist Description | YouTube | yt-dlp | Playlist URL extraction → `description` | YES | Moderate | May be absent |
| Playlist Video Count | YouTube | yt-dlp | Playlist extraction → `playlist_count` | YES | High | None |
| All Video IDs | YouTube | yt-dlp | `--flat-playlist` on playlist URL | YES | High | None |
| Playlist Uploader | YouTube | yt-dlp | Playlist extraction → `uploader` | YES | High | None |
| Playlist Thumbnail | YouTube | yt-dlp | Playlist extraction → `thumbnails` | YES | Moderate | May be absent |

### 6.4 Transcript/Caption Data

| Data Field | Source | Library | Method | Deployable | Reliable | Limitations |
|---|---|---|---|---|---|---|
| Full transcript text | YouTube | youtube-transcript-api | `ytt_api.fetch(video_id)` | YES | High | Must have captions |
| Timed transcript segments | YouTube | youtube-transcript-api | Returns `[{text, start, duration}]` | YES | High | None |
| Available transcript languages | YouTube | youtube-transcript-api | `ytt_api.list(video_id)` | YES | High | None |
| Auto-generated transcript | YouTube | youtube-transcript-api | `fetch()` with auto-generated flag | YES | High | Quality varies |
| Translated transcript | YouTube | youtube-transcript-api | `fetch()` with translate_to param | YES | Moderate | Translation quality varies |
| Subtitle file (SRT/VTT) | YouTube | yt-dlp | `--write-subs --skip-download` | YES | High | None |
| Subtitle file (all langs) | YouTube | yt-dlp | `--all-subs --skip-download` | YES | High | None |

---

## 7. Unsupported Features

The following data **cannot be obtained** without the official YouTube API, OAuth login as the channel owner, or paid services. These represent the firm limits of open-source extraction.

### 7.1 Analytics (Channel Owner Only)

| Data | Why Impossible | Workaround Exists? |
|---|---|---|
| Watch time | YouTube Analytics API; requires OAuth as channel owner | No |
| Average view duration | Channel Analytics; requires OAuth | No |
| Audience retention curve | Channel Analytics; requires OAuth | No |
| Click-through rate (CTR) | Channel Analytics; requires OAuth | No |
| Impressions | Channel Analytics; requires OAuth | No |
| Card click rate | Channel Analytics; requires OAuth | No |
| End screen click rate | Channel Analytics; requires OAuth | No |
| Revenue / RPM / CPM | YouTube Studio; requires channel monetization data | No |
| Ad revenue | YouTube Studio + monetization; requires OAuth | No |
| Super Chat revenue | YouTube Studio; requires OAuth | No |
| Membership revenue | YouTube Studio; requires OAuth | No |

### 7.2 Traffic Source Data

| Data | Why Impossible | Workaround Exists? |
|---|---|---|
| Traffic sources (search vs suggested) | Analytics API; OAuth required | No |
| External traffic sources | Analytics API; OAuth required | No |
| YouTube search keywords driving traffic | Analytics API; OAuth required | No |
| Browse features breakdown | Analytics API; OAuth required | No |

### 7.3 Audience Demographics

| Data | Why Impossible | Workaround Exists? |
|---|---|---|
| Audience age breakdown | Analytics API; OAuth required | No |
| Audience gender breakdown | Analytics API; OAuth required | No |
| Audience geography | Analytics API; OAuth required | No |
| Subscriber vs non-subscriber views | Analytics API; OAuth required | No |
| New vs returning viewers | Analytics API; OAuth required | No |

### 7.4 Historical Data

| Data | Why Impossible | Workaround Exists? |
|---|---|---|
| Historical subscriber count | Not exposed publicly; third-party estimates (Social Blade) only | Approximate via Social Blade scraping (fragile) |
| Historical view count per video | Not publicly available | Approximate via Wayback Machine snapshots (unreliable) |
| Historical like count | Not available | No |
| Subscriber gain/loss over time | Not public | Third-party estimate via Social Blade (not precise) |

### 7.5 Private / Restricted Data

| Data | Why Impossible | Workaround Exists? |
|---|---|---|
| Private video metadata | Requires authentication as owner | No |
| Unlisted video discovery | URL required (can't search for them) | No |
| Member-only content | Requires YouTube membership + OAuth | No |
| YouTube Studio recommendations | Private; requires channel owner auth | No |

### 7.6 Dislike Count

| Data | Why Impossible | Workaround Exists? |
|---|---|---|
| Dislike count | YouTube removed public dislike counts in November 2021 | Return Dislike API (community estimation — not accurate) |

**Note on Return Dislike:** The third-party extension/API "Return YouTube Dislike" provides *estimated* dislike counts based on historical API data and a sampling model. These are estimates, not actual counts, and cannot be presented as factual data.

---

## 8. Deployment Analysis

### 8.1 Per-Library Deployment Matrix

| Library | Docker | Render | Railway | VPS | Offline | Browser Needed | Chromium | FFmpeg Binary | System Packages | Win | Linux | macOS |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| yt-dlp | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ | Optional | None | ✅ | ✅ | ✅ |
| youtube-transcript-api | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | None | ✅ | ✅ | ✅ |
| FFmpeg (binary) | ✅ | ✅* | ✅ | ✅ | ✅ | ❌ | ❌ | IS binary | libavcodec, etc. | ✅ | ✅ | ✅ |
| Playwright | ⚠️ | ⚠️ | ⚠️ | ✅ | ❌ | ✅ | ✅ | ❌ | Chromium deps | ✅ | ✅ | ✅ |

*Render: FFmpeg available via Dockerfile `apt-get install -y ffmpeg`; or use `imageio-ffmpeg` pip package which bundles the binary.

### 8.2 Docker Deployment Notes

**Recommended base Dockerfile approach:**

```
FROM python:3.12-slim
RUN apt-get update && apt-get install -y ffmpeg && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip install yt-dlp youtube-transcript-api feedparser
```

This produces a lean image without Playwright. Total image size estimate:
- `python:3.12-slim` base: ~150 MB
- FFmpeg via apt: ~80 MB
- Python dependencies (yt-dlp + transcript-api + feedparser): ~30 MB
- Application code: ~10 MB
- **Total estimated image size: ~270 MB**

Contrast with adding Playwright:
- Playwright + Chromium: +500 MB
- **Total with Playwright: ~770 MB** — avoid unless strictly necessary

### 8.3 Render / Railway Specific Notes

- Both platforms support Docker deployments — use Dockerfile approach above
- Memory: minimum 512 MB RAM; 1 GB recommended for yt-dlp operations
- For background jobs (scheduled downloads, channel crawls): use Celery with Redis, or a simple scheduler with `APScheduler`
- Render free tier restricts long-running processes; use paid tier for background workers
- yt-dlp operations that hit YouTube may be slow from Render/Railway IPs — consider proxy configuration

### 8.4 PoToken / Bot Detection in Deployment

This is the most critical deployment challenge as of 2026.

**Option A: Cookie injection (Recommended for small-medium scale)**
- Extract YouTube cookies from a signed-in Chrome/Firefox browser
- Pass cookies file to yt-dlp: `--cookies cookies.txt`
- Rotate cookies periodically (weekly or when bot detection triggers)
- Store cookies as a Docker secret or environment variable

**Option B: bgutil-ytdlp-pot-provider sidecar (Recommended for production)**
- Deploy as a separate Docker container: `docker run -d -p 4416:4416 brainicism/bgutil-ytdlp-pot-provider`
- yt-dlp automatically uses the sidecar for PoToken generation
- Requires Node.js 18+ in the sidecar container
- Caveat: As of mid-2026, this does not bypass all bot checks in all cases

**Option C: Player client switching (Quick mitigation)**
- Use `--extractor-args "youtube:player_client=ios"` or `web_safari` to use a different player client
- Different clients have different bot detection profiles
- Rotate through clients when one starts failing

**Option D: No mitigation (Acceptable for low-volume metadata-only)**
- For metadata extraction (`--skip-download --dump-json`) from public videos at low rates, yt-dlp often works without any mitigation
- Risk: eventual IP blocking, especially on cloud IPs

---

## 9. Performance Analysis

### 9.1 Memory Usage

| Operation | Estimated RAM | Notes |
|---|---|---|
| Single video metadata extraction | 50–100 MB | yt-dlp process overhead |
| Transcript extraction | 20–40 MB | youtube-transcript-api is lightweight |
| Large playlist extraction (1000 videos) | 200–400 MB | yt-dlp loads all entries |
| Channel crawl (flat, 5000 videos) | 300–600 MB | Depends on metadata volume |
| Video download (streaming) | 50–100 MB | Streams to disk; not memory-bound |
| Comment extraction (deep thread) | 150–300 MB | JSON accumulates in memory |
| Playwright browser instance | 300–500 MB each | Avoid in main request path |

### 9.2 CPU Usage

| Operation | CPU Profile | Notes |
|---|---|---|
| Metadata extraction | Low — network-bound | CPU <10% during extraction |
| Transcript extraction | Very Low | Lightweight HTTP + XML parsing |
| Video download | Low — I/O bound | CPU <20% during download |
| FFmpeg muxing | High — CPU bound | Multi-core utilization during mux |
| FFmpeg audio extraction | Moderate | Faster than video mux |
| Comment extraction | Low — network-bound | Slow due to pagination |

### 9.3 Speed Benchmarks (Estimates)

| Operation | Expected Speed |
|---|---|
| Single video metadata | 2–5 seconds |
| Transcript (youtube-transcript-api) | 0.5–2 seconds |
| Transcript (yt-dlp) | 3–8 seconds |
| Playlist metadata (100 videos, flat) | 10–30 seconds |
| Channel crawl (1000 videos, flat) | 60–180 seconds |
| Audio download (5-minute video) | 5–15 seconds |
| Video download (1080p, 10 minutes) | 30–120 seconds (bandwidth dependent) |
| Comment extraction (1000 comments) | 20–60 seconds |
| Full metadata + transcript (single video) | 5–10 seconds |

### 9.4 Bottlenecks

1. **YouTube rate limiting** — Most significant bottleneck. YouTube throttles requests from the same IP. Mitigation: rate limiting in the application, request queuing, proxy rotation.
2. **PoToken generation** — Each request requires a fresh token; the bgutil sidecar adds 0.5–2 seconds per request.
3. **Comment pagination** — Deep comment extraction (10,000+ comments) requires many API round trips.
4. **FFmpeg muxing** — CPU bottleneck for high-resolution downloads; can be parallelized across workers.
5. **Large channel crawls** — yt-dlp must paginate through YouTube's internal browse endpoint. A 10,000-video channel may take 15–30 minutes.

### 9.5 Scalability Recommendations

- **Queue all extraction jobs** — Never extract synchronously in HTTP request handlers
- **Use Celery + Redis** for background job management
- **Rate limit to 1 request/3–5 seconds** per IP to avoid YouTube blocking
- **Cache extracted metadata aggressively** — YouTube metadata changes infrequently; cache for 1–24 hours
- **Parallelize across multiple IPs** for scale — not on a single cloud IP
- **Pre-fetch and store transcripts** — Do not re-fetch on every request

---

## 10. Legal and Ethical Considerations

> **Disclaimer:** This section summarizes engineering-relevant implications of the current legal landscape. It does not constitute legal advice. Consult qualified legal counsel for specific situations.

### 10.1 YouTube Terms of Service

YouTube's Terms of Service explicitly prohibit:
- Automated access to YouTube content without prior written permission
- Circumventing technical measures that control access
- Downloading content except where YouTube provides an official download feature
- Accessing content other than through YouTube's official interfaces or APIs

YouTube's robots.txt restricts crawling of core sections including `/watch`, `/channel`, and `/playlist` for all non-whitelisted user agents.

**Practical engineering implications:**
- These restrictions exist and are clearly stated
- Violations can result in IP banning, account termination, or legal action from Google
- The legal enforceability of ToS provisions and robots.txt restrictions against automated tools continues to be litigated and is jurisdiction-dependent

### 10.2 Current Legal Landscape (2025–2026)

**Key precedents:**

- **LinkedIn v. hiQ Labs** — The Ninth Circuit confirmed that scraping publicly accessible data does not automatically violate the Computer Fraud and Abuse Act (CFAA). This is favorable precedent for scraping *public* data.
- **Ziff Davis v. OpenAI** — Court ruled that ignoring robots.txt does not automatically violate DMCA anti-circumvention rules (17 USC 1201). robots.txt is a request, not a technical access control.
- **Reddit v. Perplexity** — Commercial scraping that bypasses an available authorized API creates stronger legal exposure. When an official API exists (which YouTube Data API is), courts may view bypassing it unfavorably.

**The key risk factors for this project:**

| Risk Factor | Level | Notes |
|---|---|---|
| Commercial scale scraping | High | Google more likely to pursue commercial actors |
| Downloading copyrighted content | High | Copyright infringement risk independent of ToS |
| Personal/research use only | Low | Less legal exposure |
| Respecting rate limits | Reduces risk | Shows good faith |
| Metadata extraction only (no downloads) | Lower risk | Data itself may not be copyrightable |
| Re-publishing scraped content | High | Clear copyright risk |

### 10.3 Engineering Best Practices to Reduce Exposure

1. **Rate limit all requests** — Implement minimum 3–5 second delays between requests per IP
2. **Do not redistribute copyrighted content** — Store analysis results, not downloaded video files, unless for personal/archival use
3. **Do not extract personal data** — Comment scraping collects user-generated content; handle with GDPR/CCPA awareness in applicable jurisdictions
4. **Implement robots.txt respect** — While not legally required, it demonstrates good faith
5. **Provide clear attribution** — Credit YouTube as the data source in any displayed results
6. **Do not circumvent login walls** — Only extract publicly accessible content
7. **Consider official API for commercial deployments** — For production commercial applications serving paying users, the YouTube Data API is the legally safer path
8. **Include appropriate disclosures** — Be transparent about data sources with end users

### 10.4 Safe Usage Scenarios (Lower Legal Risk)

- Personal research and data analysis
- Academic research and archival
- Personal backup of videos you have rights to
- Building tools for content creators to analyze their own channels
- Non-commercial educational platforms
- AI training datasets (increasingly contested, but generally lower risk for metadata vs. video content)

---

## 11. Recommended Final Stack

After complete research, the recommended final dependency stack is **minimal by design**:

### Core Dependencies

```
yt-dlp>=2026.07.04
youtube-transcript-api>=1.2.3
feedparser>=6.0.11          # Lightweight; for RSS channel monitoring
```

### System Dependencies (via Dockerfile)

```
ffmpeg                      # Via apt-get in Dockerfile
```

### Optional / Conditional Dependencies

```
bgutil-ytdlp-pot-provider   # Separate Docker sidecar — for PoToken generation
playwright                  # Separate worker only — for cookie extraction and fallback
```

### Why Each Library Survived

**yt-dlp** — The single most powerful and actively maintained YouTube extraction tool available. With 181,000 GitHub stars, 12 million monthly PyPI downloads, releases every 2–6 weeks, and a response time of hours to YouTube breaking changes, it is the only reasonable choice as the platform's primary extraction engine. It covers video metadata, channel metadata, playlist extraction, downloads, comments, transcripts, and search — all without an API key. Chosen over every alternative because no other tool matches its breadth, reliability, or community support.

**youtube-transcript-api** — While yt-dlp can extract transcripts, `youtube-transcript-api` is purpose-built for this task and is significantly faster and more API-friendly for high-volume transcript work. At 6,500 stars, MIT licensed, with regular releases through 2025–2026, it is a healthy supplementary library. For an AI-powered analysis platform that processes transcripts at scale, the dedicated library is the right choice. Chosen over yt-dlp for transcript-only operations due to speed and API clarity.

**FFmpeg (binary)** — There is no alternative for video/audio muxing and format conversion. yt-dlp requires FFmpeg for downloading separate video and audio streams and merging them. It is the industry-standard video processing tool and is trivially installable via apt in Docker. Not a Python library — a system binary. No Python wrapper is recommended; yt-dlp calls it directly.

**feedparser (optional)** — A lightweight, stable Python library for parsing Atom/RSS feeds. Needed only for the YouTube RSS channel monitoring feature (`feeds/videos.xml?channel_id=...`). Alternatively, Python's stdlib `xml.etree.ElementTree` can parse the feed without an additional dependency. Include `feedparser` only if its convenience outweighs the dependency.

### What Was Excluded and Why

| Library | Excluded Because |
|---|---|
| pytubefix | 100% functional overlap with yt-dlp; smaller community; slower break recovery |
| scrapetube | Uncertain maintenance; functionally covered by yt-dlp `--flat-playlist` |
| youtube-search-python | Officially retired June 2022; dead project |
| Playwright (core) | 500 MB Docker overhead; not needed for primary use cases |
| ffmpeg-python | Unnecessary wrapper; yt-dlp calls FFmpeg directly |
| imageio-ffmpeg | Only needed if apt-get FFmpeg is unavailable; add only for specific deployments |
| Selenium | Superseded by Playwright; not recommended for any use case |
| moviepy | Overkill; adds heavy dependencies for no additional capability vs FFmpeg |

---

## 12. Database Design

This section defines the logical data model for the YouTube Analyzer Platform. SQL is not written here — only entity definitions, relationships, and rationale.

### 12.1 Entity: Channel

**Purpose:** Stores a YouTube channel's public profile data at a point in time.

**Fields:**
- `channel_id` (PK) — YouTube's UC-prefixed channel ID
- `handle` — @handle username
- `display_name` — Channel display name
- `description` — Full channel description
- `subscriber_count` — Last known subscriber count (nullable)
- `video_count` — Total videos published
- `total_view_count` — Lifetime views (if extractable)
- `join_date` — Channel creation date (nullable)
- `country` — Channel country (nullable)
- `avatar_url` — Channel profile image URL (CDN; expires)
- `banner_url` — Channel banner image URL (CDN; expires)
- `is_verified` — Verification badge status
- `external_links` — JSON array of linked external URLs
- `last_crawled_at` — Timestamp of last data extraction
- `created_at` / `updated_at`

**Rationale:** Channel is the root entity. Many videos belong to one channel. Snapshots track historical changes.

---

### 12.2 Entity: Video

**Purpose:** Stores all publicly extractable metadata for a YouTube video.

**Fields:**
- `video_id` (PK) — YouTube's 11-character video ID
- `channel_id` (FK → Channel)
- `title`
- `description` (full text)
- `upload_date` — Date published
- `duration_seconds`
- `view_count`
- `like_count` (nullable)
- `comment_count` (nullable)
- `tags` — JSON array
- `categories` — JSON array
- `language` (nullable)
- `age_limit` — 0 for none; 18 for restricted
- `availability` — public, unlisted, private, premium, etc.
- `is_live` / `was_live` / `live_status`
- `is_short` — Boolean (Shorts detection)
- `chapter_data` — JSON array of chapters
- `heatmap_data` — JSON array of heatmap points
- `thumbnail_url` — Highest-res thumbnail URL
- `thumbnail_urls` — JSON array of all sizes
- `formats_available` — JSON array of available format specs
- `last_extracted_at`
- `created_at` / `updated_at`

**Rationale:** Videos are the core unit of analysis. Most features operate at the video level.

---

### 12.3 Entity: Transcript

**Purpose:** Stores the full, time-aligned transcript for a video.

**Fields:**
- `id` (PK)
- `video_id` (FK → Video)
- `language_code` — e.g., "en", "es"
- `is_auto_generated` — Boolean
- `is_translated` — Boolean
- `source_language_code` — If translated, original language
- `segments` — JSON array of `{text, start, duration}`
- `full_text` — Concatenated plaintext of all segments
- `word_count`
- `extracted_at`

**Rationale:** Transcripts are large and variable per video. Stored separately to avoid bloating the Video entity. Full text enables full-text search. Segments enable time-linked analysis (e.g., linking comments to transcript moments).

---

### 12.4 Entity: Comment

**Purpose:** Stores individual video comments and reply relationships.

**Fields:**
- `comment_id` (PK) — YouTube's comment ID
- `video_id` (FK → Video)
- `parent_comment_id` (FK → Comment, nullable) — For replies
- `author_display_name`
- `author_channel_id` (nullable)
- `author_channel_url` (nullable)
- `text` — Comment text
- `like_count`
- `reply_count` (nullable; only on top-level comments)
- `is_creator_comment` — Boolean
- `is_pinned` — Boolean
- `published_at`
- `updated_at`

**Rationale:** Comments are separate entities because each video may have thousands. Threaded structure requires parent/child relationship. Enables sentiment analysis and keyword extraction.

---

### 12.5 Entity: Playlist

**Purpose:** Stores YouTube playlist metadata and its video membership.

**Fields:**
- `playlist_id` (PK)
- `channel_id` (FK → Channel, nullable — some playlists are from Watch Later or mix lists)
- `title`
- `description` (nullable)
- `thumbnail_url` (nullable)
- `video_count`
- `privacy_status` — public, unlisted
- `last_crawled_at`
- `created_at` / `updated_at`

---

### 12.6 Entity: PlaylistVideo (Junction)

**Purpose:** Many-to-many relationship between Playlist and Video, preserving order.

**Fields:**
- `playlist_id` (FK → Playlist)
- `video_id` (FK → Video)
- `position` — Ordinal position in playlist

---

### 12.7 Entity: DownloadHistory

**Purpose:** Tracks all file downloads performed by the platform.

**Fields:**
- `id` (PK)
- `video_id` (FK → Video)
- `download_type` — video, audio, subtitle, thumbnail
- `format_id` — yt-dlp format identifier
- `quality` — e.g., "1080p", "bestaudio"
- `file_extension`
- `file_path` — Local storage path
- `file_size_bytes`
- `status` — pending, downloading, complete, failed
- `error_message` (nullable)
- `started_at`
- `completed_at`
- `requested_by` — User or system job ID

**Rationale:** Prevents redundant downloads; enables resumable downloads; provides audit trail.

---

### 12.8 Entity: SearchHistory

**Purpose:** Caches YouTube search queries and their results.

**Fields:**
- `id` (PK)
- `query`
- `result_video_ids` — JSON array of video IDs
- `result_count`
- `search_type` — video, channel, playlist
- `executed_at`
- `expires_at` — Cache expiry

**Rationale:** Prevents hitting YouTube repeatedly for the same search. Rate limiting protection.

---

### 12.9 Entity: ChannelSnapshot

**Purpose:** Time-series record of channel metrics for historical tracking.

**Fields:**
- `id` (PK)
- `channel_id` (FK → Channel)
- `subscriber_count`
- `video_count`
- `total_view_count`
- `snapshot_date` — Date of this observation

**Rationale:** Enables subscriber/view growth charts over time. One row per channel per day.

---

### 12.10 Entity: VideoSnapshot

**Purpose:** Time-series record of video metrics.

**Fields:**
- `id` (PK)
- `video_id` (FK → Video)
- `view_count`
- `like_count`
- `comment_count`
- `snapshot_date`

**Rationale:** Enables view velocity tracking ("views gained in last 7 days"). One row per video per snapshot interval.

---

### 12.11 Entity: ProcessingQueue

**Purpose:** Job queue for background extraction and download tasks.

**Fields:**
- `id` (PK)
- `job_type` — metadata_extract, transcript_extract, comment_extract, download, channel_crawl
- `target_url` — YouTube URL being processed
- `target_id` — Video/Channel/Playlist ID
- `priority` — 1–10
- `status` — queued, processing, complete, failed, retrying
- `retry_count`
- `max_retries`
- `error_message` (nullable)
- `job_payload` — JSON of additional parameters
- `created_at`
- `started_at`
- `completed_at`
- `next_retry_at`

**Rationale:** Decouples user requests from slow YouTube extraction operations. Supports retry logic for rate-limited or failed requests.

---

### 12.12 Entity: AIAnalysis

**Purpose:** Stores AI-generated analysis results for videos.

**Fields:**
- `id` (PK)
- `video_id` (FK → Video)
- `analysis_type` — summary, sentiment, topics, keywords, qa
- `model_used` — e.g., "claude-sonnet-4-6", "gpt-4o"
- `input_source` — transcript, comments, metadata
- `result` — JSON containing analysis output
- `token_count_input`
- `token_count_output`
- `analyzed_at`
- `version` — Analysis schema version (for migrations)

**Rationale:** AI analysis results are expensive to produce; cache them. Version field enables re-analysis when models improve.

---

### 12.13 Entity: UserSettings

**Purpose:** Stores user-specific platform preferences.

**Fields:**
- `id` (PK)
- `user_id` (if multi-user) or singleton
- `default_video_quality`
- `default_audio_format`
- `auto_transcript_extraction` — Boolean
- `auto_comment_extraction` — Boolean
- `monitored_channels` — JSON array of channel IDs to poll via RSS
- `rss_poll_interval_minutes`
- `proxy_settings` — JSON (optional proxy configuration)
- `storage_path` — Base path for downloads
- `updated_at`

---

## 13. High-Level Architecture

### 13.1 System Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                        CLIENT LAYER                              │
│  React Frontend (SPA)  ←→  Chrome Extension (optional)         │
└──────────────────────────────┬──────────────────────────────────┘
                               │ HTTP/WebSocket
┌──────────────────────────────▼──────────────────────────────────┐
│                       API GATEWAY LAYER                          │
│         FastAPI (Python 3.12)  ─  REST + WebSocket              │
│   Auth Middleware  │  Rate Limiter  │  Request Validator         │
└──────────┬─────────────────────────────────┬────────────────────┘
           │                                 │
┌──────────▼──────────┐         ┌────────────▼────────────────┐
│   SERVICE LAYER      │         │      BACKGROUND WORKERS      │
│                     │         │                              │
│ VideoService         │         │  Celery Workers (N instances)│
│ ChannelService       │         │  ├── MetadataWorker          │
│ TranscriptService    │         │  ├── TranscriptWorker        │
│ SearchService        │         │  ├── CommentWorker           │
│ PlaylistService      │         │  ├── DownloadWorker          │
│ AnalyticsService     │         │  ├── ChannelCrawlWorker      │
│ AIAnalysisService    │         │  └── RSSMonitorWorker        │
└──────────┬──────────┘         └────────────┬────────────────┘
           │                                 │
┌──────────▼─────────────────────────────────▼────────────────────┐
│                    REPOSITORY LAYER (Data Access)                │
│   VideoRepository  │  ChannelRepository  │  TranscriptRepository │
│   PlaylistRepository  │  SearchRepository  │  QueueRepository    │
└──────────┬──────────────────────────────────┬────────────────────┘
           │                                  │
┌──────────▼───────────┐           ┌──────────▼───────────────────┐
│   PRIMARY DATABASE    │           │      CACHE LAYER             │
│   PostgreSQL          │           │      Redis                   │
│   (or SQLite for      │           │   ├── API response cache     │
│    local/small deploy)│           │   ├── Job queue (Celery)     │
└──────────────────────┘           │   └── Rate limit counters    │
                                   └──────────────────────────────┘
```

### 13.2 Extraction Engine Layer

```
┌─────────────────────────────────────────────────────────────────┐
│                    EXTRACTION ENGINE                             │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │                    yt-dlp Core                            │  │
│  │  VideoExtractor │ ChannelExtractor │ PlaylistExtractor    │  │
│  │  CommentExtractor │ SearchExtractor │ FormatExtractor      │  │
│  └──────────────────────┬───────────────────────────────────┘  │
│                         │                                       │
│  ┌──────────────────────▼───────────────────────────────────┐  │
│  │              youtube-transcript-api                        │  │
│  │         TranscriptFetcher │ LanguageDetector              │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │              YouTube RSS Feed Parser                      │  │
│  │           ChannelMonitor │ FeedParser (stdlib)            │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │            Bot Detection Mitigation Layer                 │  │
│  │  CookieManager │ PoTokenProvider │ ProxyRotator          │  │
│  │  (bgutil sidecar via HTTP)                               │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

### 13.3 Frontend Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    REACT FRONTEND                                │
│                                                                 │
│  Pages:                          Components:                    │
│  ├── Dashboard                   ├── VideoCard                 │
│  ├── VideoAnalyzer               ├── ChannelCard               │
│  ├── ChannelAnalyzer             ├── TranscriptViewer          │
│  ├── PlaylistAnalyzer            ├── CommentsList              │
│  ├── SearchPage                  ├── MetricsChart              │
│  ├── DownloadManager             ├── FormatSelector            │
│  ├── TranscriptViewer            ├── ProgressBar               │
│  ├── AIAnalysis                  ├── JobStatusBadge            │
│  └── Settings                   └── ErrorBoundary             │
│                                                                 │
│  State: React Query (server state) + Zustand (UI state)        │
│  Styling: Tailwind CSS                                         │
│  Charts: Recharts                                              │
│  WebSocket: for real-time job progress                         │
└─────────────────────────────────────────────────────────────────┘
```

### 13.4 Background Job Architecture

```
User Request → API → Queue Job (Redis) → Celery Worker → Extract (yt-dlp/transcript-api)
                                                        → Store (PostgreSQL)
                                                        → Notify (WebSocket)
                                                        → Return Result

Scheduler (APScheduler/Celery Beat):
  Every 15 minutes → RSS Feed Check → New Video Detection → Queue Metadata Job
  Every 24 hours   → Channel Snapshot → Store metrics delta
  Every 7 days     → Cookie refresh reminder
```

### 13.5 Storage Architecture

```
PostgreSQL: Structured metadata, relationships, history
Redis: Job queues, cache, rate limit state, WebSocket pub/sub
File System / S3-compatible: Downloaded video/audio files, thumbnails
         └── /downloads/videos/{video_id}/
         └── /downloads/audio/{video_id}/
         └── /downloads/subtitles/{video_id}/
         └── /thumbnails/{video_id}/
```

### 13.6 Error Handling Architecture

Every extraction operation wraps the following error classes:

- `YouTubeRateLimitError` — HTTP 429 or extraction timeout → retry with backoff
- `YouTubeBotDetectedError` — Bot detection triggered → rotate cookie/proxy, re-queue
- `VideoUnavailableError` — Private/deleted/geo-blocked → mark as unavailable in DB
- `TranscriptNotAvailableError` — No captions exist → mark `has_transcript=False`
- `ExtractionFailedError` — Generic yt-dlp failure → log, retry up to N times
- `PoTokenExpiredError` — PoToken stale → request fresh token from sidecar

All errors are logged to a structured logging backend (e.g., stdout JSON for Docker → Loki/Papertrail).

---

## 14. Dependency Tree

### 14.1 Python Dependencies (requirements.txt)

```
# Web Framework
fastapi>=0.115.0
uvicorn[standard]>=0.30.0

# Extraction Core
yt-dlp>=2026.07.04
youtube-transcript-api>=1.2.3
feedparser>=6.0.11

# Database
sqlalchemy>=2.0.0
alembic>=1.13.0
asyncpg>=0.30.0          # PostgreSQL async driver (or psycopg[binary])
aiosqlite>=0.20.0        # SQLite async (for local dev)

# Task Queue
celery>=5.4.0
redis>=5.0.0
flower>=2.0.0            # Celery monitoring (optional)

# Caching
redis>=5.0.0             # Shared with Celery

# Scheduling
apscheduler>=3.10.0      # Or Celery Beat

# Utilities
httpx>=0.27.0            # Async HTTP client
pydantic>=2.0.0          # Data validation (FastAPI uses this)
python-dotenv>=1.0.0     # Environment variable management
structlog>=24.0.0        # Structured logging

# Testing
pytest>=8.0.0
pytest-asyncio>=0.23.0
httpx>=0.27.0            # Test client
```

### 14.2 System Dependencies (Dockerfile)

```dockerfile
# System packages
ffmpeg
# Optionally for building Python packages:
build-essential
libpq-dev        # PostgreSQL client library
```

### 14.3 Optional Sidecar Dependencies (separate container)

```
Node.js 18+              # For bgutil-ytdlp-pot-provider
brainicism/bgutil-ytdlp-pot-provider (Docker image)
```

### 14.4 Frontend Dependencies (package.json)

```json
{
  "dependencies": {
    "react": "^18.3.0",
    "react-dom": "^18.3.0",
    "react-router-dom": "^6.26.0",
    "@tanstack/react-query": "^5.56.0",
    "zustand": "^4.5.0",
    "recharts": "^2.12.0",
    "tailwindcss": "^3.4.0",
    "axios": "^1.7.0",
    "lucide-react": "^0.383.0"
  }
}
```

### 14.5 What Is Intentionally Absent

| Absent Dependency | Why Excluded |
|---|---|
| Playwright / Selenium | Not a core dependency; optional background sidecar only |
| pytubefix | Redundant with yt-dlp |
| scrapetube | Redundant with yt-dlp |
| youtube-search-python | Dead project |
| moviepy | Redundant with FFmpeg |
| ffmpeg-python | Unnecessary wrapper |
| Scrapy | Overkill; yt-dlp does what's needed |
| Any paid API SDK | Project requirement: zero paid services |

---

## 15. Future Roadmap

### 15.1 Official YouTube API Integration (Future Phase)

**How to add without changing core architecture:**

The Repository Layer is the correct integration point. Add a `YouTubeAPIRepository` that implements the same interface as `yt-dlp`-based repositories but uses the official Data API.

Pattern:
```
VideoRepository (interface)
  ├── YtdlpVideoRepository (current: no API key)
  └── YouTubeAPIVideoRepository (future: uses Data API v3)
```

The ServiceLayer calls `VideoRepository` without knowing which implementation is active. Switching is a configuration change, not a code change.

**Data available via official API but not yt-dlp:**
- Structured caption tracks with accurate timestamps
- Batch video fetching (up to 50 per request)
- Reliable comment threading and moderation metadata
- Cleaner, more stable response format

### 15.2 OAuth / Channel Owner Analytics

Add an `OAuthProvider` service that handles Google OAuth 2.0 token management. Once authenticated, a `YouTubeAnalyticsRepository` can fetch owner-only data (watch time, CTR, revenue estimates) via the YouTube Analytics API.

This integrates into the existing `AnalyticsService` layer. No architectural change required.

### 15.3 Social Blade / ViewStats Integration

Add a `ThirdPartyStatsService` that fetches from Social Blade's public pages or API (if available) to supplement historical subscriber and view count data. This fills the gap in historical metrics that YouTube does not expose publicly.

Store in `ChannelSnapshot` with a `source` field (`yt-dlp`, `youtube-api`, `socialblade`).

### 15.4 AI Analysis and LLM Integration

The `AIAnalysis` entity and `AIAnalysisService` are already designed to accommodate this.

**Transcript → LLM pipeline:**
1. Fetch transcript via `youtube-transcript-api`
2. Chunk transcript by token count
3. Send to LLM (Claude, GPT-4, or local Ollama) for summary/sentiment/topics
4. Store result in `AIAnalysis` table

**Future: RAG (Retrieval-Augmented Generation)**
- Embed transcript chunks using an embedding model (OpenAI `text-embedding-3-small`, `nomic-embed-text`, or local)
- Store vectors in a vector database (pgvector extension on PostgreSQL, or Qdrant/Chroma)
- Enable semantic search across transcripts: "Find videos where X is discussed"

**Future: Agentic YouTube Research**
- Implement an AI agent that receives a research question, autonomously searches YouTube, fetches transcripts, and synthesizes an answer
- Tool-calling architecture: tools = `search_youtube`, `get_transcript`, `get_channel_info`, `compare_channels`

### 15.5 Vector Database / Semantic Search

Add `pgvector` to PostgreSQL (zero new service) or deploy a dedicated Qdrant instance. The `Transcript` entity gains a `embedding_vector` field. `SearchService` gains a `semantic_search(query)` method alongside the existing text search.

No changes to the core architecture — additive extension to existing services.

### 15.6 Multi-User / SaaS Mode

The current architecture is single-user. To add multi-tenancy:
- Add `User` and `Organization` entities
- Add JWT authentication middleware to FastAPI
- Add `user_id` foreign keys to tracked entities
- Add per-user rate limiting in the queue layer
- Add role-based access control to the API layer

The architecture supports this without structural changes.

---

## 16. Final Recommendation

### The Three-Library Answer

A production-quality YouTube Analyzer Platform requires exactly three external dependencies for its core extraction functionality:

```
yt-dlp          ←  Everything YouTube, maintained daily by a global community
youtube-transcript-api  ←  Fastest, cleanest transcript extraction
FFmpeg          ←  Required for A/V processing (system binary, not Python package)
```

Every other candidate library either duplicates these capabilities (pytubefix, scrapetube), is dead (youtube-search-python), or should be an optional isolated component rather than a core dependency (Playwright).

### The Critical Warning for 2026

YouTube's PoToken requirement is a permanent architectural constraint, not a temporary bug. Any production deployment must plan for:
1. Cookie management from a logged-in browser session
2. The `bgutil-ytdlp-pot-provider` sidecar (Node.js) or equivalent PoToken generation
3. Periodic refreshing of authentication artifacts
4. Fallback strategies when YouTube changes its bot detection

This is not optional. A yt-dlp installation without PoToken handling will fail on datacenter IPs under load.

### Architecture Principle

> **Extract at the edge; store in the center.**

Never query YouTube in the synchronous request path. Every YouTube extraction must go through the job queue. Cache aggressively. Store results permanently. Re-extract only when necessary (staleness thresholds: video metadata every 24 hours, channel snapshots daily, transcripts once and cache forever).

### On the Legal Question

This platform should be designed for personal research, developer tooling, and educational purposes. The safest path is:
1. Respect rate limits
2. Do not redistribute downloaded video content
3. Use the official YouTube API for commercial, customer-facing products
4. Acknowledge YouTube's ToS in your own product documentation

The open-source community has maintained yt-dlp for over 5 years despite legal pressure, and the US 9th Circuit's LinkedIn v. hiQ precedent establishes that scraping publicly accessible data does not automatically violate the CFAA. However, operating at scale commercially warrants qualified legal review.

### Maturity Assessment

This platform, built on the stack above, can reliably support:

**Fully Supported:** Video metadata extraction, transcript extraction, channel analysis, playlist management, video/audio downloads, comment analysis, search, channel monitoring via RSS, YouTube search, format selection, multi-language subtitle extraction, chapter analysis.

**Partially Supported (with caveats):** Subscriber count (sometimes absent or rounded), channel join date (frequently absent), comment extraction at scale (bot detection risk), very large channel crawls (rate limiting), historical metrics (point-in-time only).

**Not Supported:** Revenue data, watch time, CTR, audience demographics, traffic source analytics, historical view/subscriber trends (accurate), any owner-authenticated analytics, private video metadata.

This document is the complete foundation for the system architecture and implementation phases that follow.

---

*End of YouTube Analyzer Platform Engineering Research Document*  
*Research Date: July 2026 | Document Version: 1.0*
