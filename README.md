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
