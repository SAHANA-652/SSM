@echo off
REM Launch the Streamlit dashboard for the project
cd /d "%~dp0"
python -m streamlit run app.py
pause
