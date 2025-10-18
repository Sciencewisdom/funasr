@echo off
rem ** Change directory to the script's own location. **
cd /d %~dp0

rem Set the API Key temporarily for the current session.
set DASHSCOPE_API_KEY=sk-36f12e22e775434db07219a5e7715d3a

rem Install required Python libraries.
echo Checking and installing required Python libraries...
python -m pip install dashscope requests > nul

rem Run the main transcription script.
echo.
echo Starting transcription process (Plan C: Using 0x0.st file hosting)...
echo.

python run_transcription_local.py

echo.
echo Process finished.
pause