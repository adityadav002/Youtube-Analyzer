# YouTube Video Analyzer

A full-stack application for analyzing YouTube videos.

## Folder Structure

```
youtube_analyzer/
├── backend/    # Flask REST API
├── frontend/   # React/Vite Frontend
└── docs/       # Project documentation
```

## Prerequisites

- **Python**: 3.12 or higher
- **Node.js**: 18.x or higher
- **MySQL**: 8.x (running locally)

## Database Setup

1. Log in to your local MySQL server:
   ```bash
   mysql -u root -p
   ```
2. Create the database:
   ```sql
   CREATE DATABASE youtube_analyzer CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
   ```

## Installing & Running the Backend

1. **Navigate to the backend directory**
   ```bash
   cd backend
   ```
2. **Create and activate a virtual environment**
   - Windows (PowerShell):
     ```powershell
     python -m venv .venv
     .\.venv\Scripts\Activate.ps1
     ```
   - Mac/Linux:
     ```bash
     python3 -m venv .venv
     source .venv/bin/activate
     ```
3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```
4. **Create the environment file**
   ```bash
   cp .env.example .env
   ```
   *Edit `.env` and fill in `MYSQL_USER`, `MYSQL_PASSWORD`, and API keys.*
5. **Run Database Migrations**
   ```bash
   flask db upgrade
   ```
6. **Start the backend**
   ```bash
   flask run
   ```
   The backend API will be available at `http://localhost:5000`.

## Installing & Running the Frontend

1. **Navigate to the frontend directory**
   ```bash
   cd frontend
   ```
2. **Install dependencies**
   ```bash
   npm install
   ```
3. **Create the environment file**
   ```bash
   cp .env.example .env
   ```
4. **Start the frontend**
   ```bash
   npm run dev
   ```
   The frontend application will be accessible at `http://localhost:5173`.

## Troubleshooting & Common Errors

- **Missing Module Errors**: Ensure your virtual environment is activated before running `flask run` or `pip install`.
- **Database Connection Error**: Ensure your MySQL server is running on the expected port (usually 3306), the `MYSQL_USER` and `MYSQL_PASSWORD` in `backend/.env` are correct, and the database `youtube_analyzer` has been created.
- **PowerShell Script Execution Error**: If you cannot run `Activate.ps1`, you might need to temporarily bypass the execution policy by running:
  ```powershell
  Set-ExecutionPolicy -ExecutionPolicy Bypass -Scope Process -Force
  ```

## Production Deployment on Render

This project is configured for easy deployment on [Render](https://render.com) using the root-level `render.yaml` Blueprint specification.

### Architecture
- **Backend Web Service**: Flask application run with Gunicorn production WSGI server.
- **Frontend Static Site**: React application built with Vite and TailwindCSS, served as static files.

### Render Blueprint Services Setup

You can deploy the entire stack to Render by importing this repository and using the `render.yaml` file:

1. **Backend Web Service**:
   - **Environment**: `Python`
   - **Root Directory**: `backend`
   - **Build Command**: `chmod +x build.sh && ./build.sh` (Downloads Python dependencies and installs a Linux-compatible static build of **FFmpeg**).
   - **Start Command**: `gunicorn --bind 0.0.0.0:$PORT wsgi:app`
   - **Health Check Endpoint**: `/api/health`

2. **Frontend Static Site**:
   - **Environment**: `Static`
   - **Root Directory**: `frontend`
   - **Build Command**: `npm install && npm run build`
   - **Publish Directory**: `dist`

### Required Environment Variables

#### Backend Service:
- `FLASK_ENV`: Set to `production`.
- `SECRET_KEY`: A secure random secret key.
- `DATABASE_URL`: Your production database URL (supports MySQL/PostgreSQL, e.g. `mysql+pymysql://user:pass@host:3306/db` or `postgresql://user:pass@host:5432/db`).
- `CORS_ORIGINS`: Set to your deployed frontend URL (e.g. `https://youtube-analyzer.onrender.com`).
- `USE_CELERY`: Set to `false` to process video/channel crawl tasks on-demand via lightweight background threads.

#### Frontend Service:
- `VITE_API_BASE_URL`: Set to your deployed backend API root (e.g. `https://youtube-analyzer-backend.onrender.com/api`).

### Known Deployment Limitations

1. **Ephemeral File Storage**: Render's Web Services have ephemeral filesystems. Downloader assets (video/audio/thumbnails) stored in `downloads/` or `thumbnails/` will be removed when the service redeploys or restarts. To retain files across restarts, you should configure a **Render Persistent Disk** mounted at `/opt/render/project/src/backend/downloads` (size e.g. 10GB) or integrate an external cloud storage provider.
2. **In-Memory Rate Limiting**: The application uses Flask-Limiter's in-memory rate-limiter. For clustered multi-instance deployments, a shared Redis server should be configured as the storage backend for Flask-Limiter.


# step 1:
PS E:\CODE\06_Data_Science\21_Youtube_Video_Analyzer> cd c:\Users\adity\bgutil-ytdlp-pot-provider\server
PS C:\Users\adity\bgutil-ytdlp-pot-provider\server> node build/main.js

# step 2:
PS E:\CODE\06_Data_Science\21_Youtube_Video_Analyzer> cd .\backend\
PS E:\CODE\06_Data_Science\21_Youtube_Video_Analyzer\backend> .\.venv\Scripts\Activate.ps1         
(.venv) PS E:\CODE\06_Data_Science\21_Youtube_Video_Analyzer\backend> flask run

# step 3:
PS E:\CODE\06_Data_Science\21_Youtube_Video_Analyzer> cd .\frontend\
PS E:\CODE\06_Data_Science\21_Youtube_Video_Analyzer\frontend> npm run dev