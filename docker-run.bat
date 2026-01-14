@echo off
REM Docker helper script for RegosPartnerBot (Windows)

setlocal enabledelayedexpansion

REM Check if .env file exists
if not exist .env (
    echo [WARN] .env file not found. Creating from env.example...
    copy env.example .env
    echo [INFO] Please edit .env file and set your configuration before continuing.
    exit /b 1
)

REM Create necessary directories
echo [INFO] Creating data directories...
if not exist data mkdir data
if not exist exports mkdir exports

REM Main command handler
if "%1"=="" goto help
if "%1"=="start" goto start
if "%1"=="stop" goto stop
if "%1"=="restart" goto restart
if "%1"=="logs" goto logs
if "%1"=="rebuild" goto rebuild
if "%1"=="status" goto status
if "%1"=="help" goto help
if "%1"=="--help" goto help
if "%1"=="-h" goto help

echo [ERROR] Unknown command: %1
goto help

:start
echo [INFO] Starting Docker containers...
docker-compose up -d
echo [INFO] Containers started. Use 'docker-compose logs -f' to view logs.
goto end

:stop
echo [INFO] Stopping Docker containers...
docker-compose down
echo [INFO] Containers stopped.
goto end

:restart
echo [INFO] Restarting Docker containers...
docker-compose restart
echo [INFO] Containers restarted.
goto end

:logs
echo [INFO] Viewing container logs...
docker-compose logs -f %2 %3 %4 %5
goto end

:rebuild
echo [INFO] Rebuilding and restarting containers...
docker-compose up -d --build
echo [INFO] Containers rebuilt and restarted.
goto end

:status
echo [INFO] Container status:
docker-compose ps
goto end

:help
echo Usage: %0 [command]
echo.
echo Commands:
echo   start      Start Docker containers
echo   stop       Stop Docker containers
echo   restart    Restart Docker containers
echo   logs       View container logs (add service name for specific service)
echo   rebuild    Rebuild and restart containers
echo   status     Show container status
echo   help       Show this help message
echo.
echo Examples:
echo   %0 start
echo   %0 logs backend
echo   %0 rebuild
goto end

:end
endlocal
