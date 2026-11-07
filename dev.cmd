@echo off
rem Alternativa al Makefile para equipos sin make: dev up, dev status, dev server-stop...
rem Las variables se pasan como en cmd: set SERVER_PORT=8081 && dev up
rem Para instalar make: dev install-make
setlocal
if "%~1"=="" (set "DEV_ACTION=help") else (set "DEV_ACTION=%~1")
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0tools\dev\dev.ps1" %DEV_ACTION%
exit /b %ERRORLEVEL%
