@echo off
powershell -NoProfile -Command "try { Invoke-WebRequest -UseBasicParsing -Method Post -Uri 'http://127.0.0.1:47821/shutdown' -TimeoutSec 3 | Out-Null } catch {}"
