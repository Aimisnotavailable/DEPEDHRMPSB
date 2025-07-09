@echo off
rem -- Ensure working directory is script’s folder
pushd "%~dp0"

rem -- Run first script and return to this wrapper
call "setup.bat"

rem -- Run second script after the first completes
call "run.bat"

popd

pause
