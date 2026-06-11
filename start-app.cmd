@echo off
setlocal
set "PROJECT_ROOT=%~dp0"
set "BUNDLED_NODE=%USERPROFILE%\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe"

where node >nul 2>nul
if %ERRORLEVEL% EQU 0 (
  set "NODE_CMD=node"
) else if exist "%BUNDLED_NODE%" (
  set "NODE_CMD=%BUNDLED_NODE%"
) else (
  echo Node.js was not found. Install Node.js from https://nodejs.org/ or run this from Codex where the bundled runtime exists.
  exit /b 1
)

echo Starting Dynamic Bond Allocation Assistant...
echo Open http://localhost:3000 in your browser.
cd /d "%PROJECT_ROOT%"
"%NODE_CMD%" server.js
