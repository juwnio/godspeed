@echo off
:loop
git add .
git commit -m "Auto sync: %date% %time%"
git push
timeout /t 30
goto loop
