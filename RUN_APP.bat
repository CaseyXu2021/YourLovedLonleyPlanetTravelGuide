@echo off
REM Run the improved Lonely Planet app from app_simplified_original.py

echo.
echo 🌍 Starting Your Loved Lonely Planet - Improved Version
echo ========================================================
echo.

REM Activate virtual environment
call .venv\Scripts\activate.bat

REM Run the app
echo Opening app_simplified_original.py on http://localhost:8501
echo.
streamlit run app_simplified_original.py

pause
