@echo off
echo ========================================
echo DIAGNOSTICO COMPLETO - CubaYDSignal Bot
echo ========================================
echo.
echo Este script verificara:
echo - Conexion a Quotex
echo - Obtencion de payouts reales
echo - Obtencion de velas (candles) reales
echo - Ejecucion de estrategias
echo - Generacion de senales
echo.
echo Presiona cualquier tecla para continuar...
pause > nul

echo.
echo Ejecutando diagnostico...
echo.

python test_diagnostico_completo.py

echo.
echo ========================================
echo Diagnostico completado
echo ========================================
echo.
echo Revisa el output arriba para ver los resultados.
echo.
pause
