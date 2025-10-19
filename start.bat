@echo off
set PORT=8000
py -m uvicorn app:app --host 0.0.0.0 --port %PORT%
pause