@echo off
echo === Step 1: Installing yt-dlp[default] ===
call .venv\Scripts\pip.exe install -U "yt-dlp[default]"
echo.
echo === Step 2: Installing bgutil-ytdlp-pot-provider ===
call .venv\Scripts\pip.exe install -U bgutil-ytdlp-pot-provider
echo.
echo === Step 3: Verifying installations ===
call .venv\Scripts\pip.exe show yt-dlp yt-dlp-ejs bgutil-ytdlp-pot-provider
echo.
echo === Step 4: Testing yt-dlp verbose diagnostics ===
call .venv\Scripts\python.exe -m yt_dlp -v --js-runtimes node --simulate "https://www.youtube.com/watch?v=Pot3dbxfwaM" 2>&1
echo.
echo === DONE ===
pause
