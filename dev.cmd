@echo off
rem Alternative to the Makefile on machines without make: dev up, dev status, dev server-stop...
rem Variables are passed the cmd way: set SERVER_PORT=8081 && dev up
rem To install make: dev install-make
setlocal
if "%~1"=="" (set "DEV_ACTION=help") else (set "DEV_ACTION=%~1")
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0tools\dev\dev.ps1" %DEV_ACTION%
exit /b %ERRORLEVEL%
