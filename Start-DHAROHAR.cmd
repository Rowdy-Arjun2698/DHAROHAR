@echo off
powershell.exe -NoProfile -File "%~dp0scripts\Start-DHAROHAR.ps1"
if errorlevel 1 (pause) else (start "" "http://127.0.0.1:8010/")
