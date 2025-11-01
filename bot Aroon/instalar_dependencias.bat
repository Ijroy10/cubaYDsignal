@echo off
echo ========================================
echo Instalando dependencias del bot
echo ========================================
echo.

python -m pip install --upgrade pip

echo Instalando dependencias principales...
python -m pip install pandas numpy requests websockets python-telegram-bot

echo Instalando analisis tecnico...
python -m pip install ta scipy scikit-learn

echo Instalando utilidades...
python -m pip install python-dotenv colorama tqdm loguru pytz cryptography

echo Instalando visualizacion...
python -m pip install matplotlib seaborn

echo Instalando soporte async...
python -m pip install aiofiles aiohttp

echo Instalando PDF...
python -m pip install reportlab

echo.
echo ========================================
echo Instalacion completada
echo ========================================
pause
