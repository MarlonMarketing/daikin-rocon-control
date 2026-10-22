@echo off
setlocal
cd /d "%~dp0"
echo Diagnostica Daikin in sola lettura.
echo Inserire le credenziali dell'app. La password resta nascosta.
echo.
py -3 -m rocon_local.cli cloud --output "_private\cloud-%RANDOM%-%RANDOM%.json"
echo.
pause
