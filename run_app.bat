@echo off
title Sistema de Requisiciones - Industria SIGRAMA
chcp 65001 > nul
cls

echo =====================================================================
echo    SISTEMA DE CONTROL Y SEGUIMIENTO DE REQUISICIONES DE COMPRA
echo                   INDUSTRIA SIGRAMA S.A. DE C.V.
echo =====================================================================
echo.

set VENV_PYTHON=C:\Users\albertol\.gemini\antigravity\scratch\test_venv\Scripts\python.exe

if exist "%VENV_PYTHON%" (
    echo [INFO] Iniciando Streamlit usando el entorno virtual configurado...
    "%VENV_PYTHON%" -m streamlit run app.py --server.port 8501 --browser.gatherUsageStats false
) else (
    echo [INFO] Iniciando Streamlit usando Python del sistema...
    python -m streamlit run app.py --server.port 8501 --browser.gatherUsageStats false
)

pause
