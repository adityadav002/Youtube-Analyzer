# YouTube Video Analyzer 📊

A full-stack premium application for tracking, analyzing, and scraping YouTube channel metrics, videos, shorts, live streams, transcripts, and chapters. It features interactive graphs, detailed search caching, a video/audio/thumbnail downloader, and seamless PoToken integration to bypass YouTube's automated scraper bot detection.

## Project Architecture

The application is split into three main components:

1. **PoToken Provider (`bgutil-ytdlp-pot-provider`)**: A lightweight Node.js-based HTTP server that generates Proof of Token (PO Token) values to bypass YouTube bot detection when scraping metadata or downloading files.
2. **Backend**: Python Flask API backed by a SQL database (MySQL/SQLite) that manages database queries, coordinates async crawl jobs, and interfaces with the YouTube Data API v3 and `yt-dlp`.
3. **Frontend**: React (Vite) dashboard built using vanilla CSS, Lucide icons, TailwindCSS, and TanStack Query (React Query) for smooth and responsive UI states.

---

## Prerequisites

Ensure you have the following installed on your system before proceeding:

- **Node.js**: v18.x or higher (npm v9.x+)
- **Python**: v3.12 or higher
- **MySQL**: v8.x or higher (running locally on port `3306`)
- **FFmpeg**: Required on the system PATH for merging video and audio files or extracting audio formats.

---

## Getting Started: 3-Step Setup

Follow these steps in separate terminal shells to set up and launch each service in order.

### Step 1: Run the PO Token Provider Server

Since YouTube implements rigorous bot-detection challenges, you must run the PoToken generator server locally.

1. Navigate to the server folder:
   ```bash
   cd c:\Users\adity\bgutil-ytdlp-pot-provider\server
   ```
2. Install the required Node.js dependencies (if not already done):
   ```bash
   npm install
   ```
3. Run the generator server:
   ```bash
   node build/main.js
   ```
   *The server runs locally, typically binding to port `4416`.*

---

### Step 2: Install & Run the Flask Backend

The backend stores crawled data, manages the background thread dispatcher, and handles API requests.

1. Navigate to the `backend` folder:
   ```bash
   cd .\backend\
   ```
2. Create and activate a Python virtual environment:
   - **Windows (PowerShell)**:
     ```powershell
     python -m venv .venv
     .\.venv\Scripts\Activate.ps1
     ```
   - **macOS / Linux**:
     ```bash
     python3 -m venv .venv
     source .venv/bin/activate
     ```
3. Install the backend Python dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Set up your environment file:
   - Copy the example environment template:
     ```bash
     cp .env.example .env
     ```
   - Open `.env` and fill in the required variables (see **Environment Variables** section below). Make sure your local MySQL credentials match and you have created a database named `youtube_analyzer` in MySQL:
     ```sql
     CREATE DATABASE youtube_analyzer CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
     ```
5. Run the database migrations to set up schema tables:
   ```bash
   flask db upgrade
   ```
6. Start the Flask application server:
   ```bash
   flask run
   ```
   *The backend runs at `http://localhost:5000`.*

---

### Step 3: Install & Run the Vite Frontend

The React frontend provides the UI interface for analyzing channels and tracking jobs.

1. Navigate to the `frontend` folder:
   ```bash
   cd .\frontend\
   ```
2. Install npm package dependencies:
   ```bash
   npm install
   ```
3. Set up the frontend environment configuration:
   - Copy the example environment template:
     ```bash
     cp .env.example .env
     ```
   - Check that `VITE_API_BASE_URL` matches your local Flask API endpoint (default: `http://localhost:5000/api`).
4. Start the frontend Vite dev server:
   ```bash
   npm run dev
   ```
   *The frontend dashboard will be accessible at `http://localhost:5173`.*

---

## Required Environment Variables

### Backend Environment Variables (`backend/.env`)

Configure these values inside `backend/.env`:

| Variable Name | Description | Example Value |
| :--- | :--- | :--- |
| `FLASK_ENV` | Environment stage | `development` / `production` |
| `SECRET_KEY` | Secret key used for session cryptographic signatures | `any-random-string` |
| `LOG_LEVEL` | Logging detail verbosity | `DEBUG` / `INFO` / `WARNING` |
| `MYSQL_HOST` | Local MySQL server host | `localhost` |
| `MYSQL_PORT` | Local MySQL connection port | `3306` |
| `MYSQL_USER` | MySQL database user name | `root` |
| `MYSQL_PASSWORD` | MySQL database user password | `your_mysql_password` |
| `MYSQL_DATABASE` | Targeted database name | `youtube_analyzer` |
| `USE_CELERY` | Disable celery to run async tasks in background thread | `false` |
| `YOUTUBE_API_KEY` | **Google/YouTube Data API v3 Key** (Required for metadata scans) | `AIzaSy...` |
| `BGUTIL_URL` | URL path of the local PoToken server (Step 1) | `http://127.0.0.1:4416` |
| `POT_PROVIDER_URL` | Alternate PO Token provider url | `http://127.0.0.1:4416` |
| `FRONTEND_URL` | Allowed CORS client origins | `http://localhost:5173,http://localhost:3000` |
| `AUTO_EXTRACT_TRANSCRIPT` | Auto-crawl video transcript subtitles on import | `false` |
| `AUTO_EXTRACT_THUMBNAIL` | Auto-download and save local copies of thumbnails | `true` |
| `YTDLP_RATE_LIMIT` | Rate limits downloads to avoid server throttle | `500K` |

### Frontend Environment Variables (`frontend/.env`)

Configure these values inside `frontend/.env`:

| Variable Name | Description | Example Value |
| :--- | :--- | :--- |
| `VITE_API_BASE_URL` | URL of the running backend Flask API | `http://localhost:5000/api` |

---

## Troubleshooting & Verification

- **Refreshing Metadata**: If you have fetched a very new video (e.g. less than 2 hours old) showing low views, you can click **Refresh Videos** on the Channel detail page to pull the latest 50 videos and update their views, likes, and description metadata in your database.
- **PowerShell Script Blocking**: If PowerShell blocks the activation script `.venv\Scripts\Activate.ps1`, open PowerShell as Administrator and execute:
  ```powershell
  Set-ExecutionPolicy -ExecutionPolicy Bypass -Scope Process -Force
  ```
- **FFmpeg missing**: If downloads or format merging fail with exceptions, verify that `ffmpeg` is installed and registered on your system environment variables.