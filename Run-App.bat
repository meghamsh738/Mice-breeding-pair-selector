@echo off
setlocal
set "WSL_PATH='<PROJECTS_DIR>/Mice-breeding-pair-selector/modern-app'"
start "Mice breeding servers" wsl -e bash -lc "cd %WSL_PATH% && npm run dev:full"
timeout /t 4 >nul
start "" http://localhost:5174
endlocal
