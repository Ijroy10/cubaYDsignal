@echo off
chcp 65001 > nul
echo ================================================================================
echo 🧪 SUITE COMPLETA DE TESTS - CubaYDSignal Bot
echo ================================================================================
echo.
echo Este script ejecutará TODOS los tests de diagnóstico en secuencia:
echo.
echo   1. ✅ Test de Diagnóstico Completo
echo   2. 💰 Test de Comparación de Payouts
echo   3. 🔬 Test de Flujo de Estrategias
echo.
echo Tiempo estimado: 5-10 minutos
echo.
echo ⚠️  IMPORTANTE: Asegúrate de tener configurado .env con tus credenciales
echo.
pause

echo.
echo ================================================================================
echo 📋 TEST 1/3: DIAGNÓSTICO COMPLETO
echo ================================================================================
echo.
python test_diagnostico_completo.py
if errorlevel 1 (
    echo.
    echo ❌ ERROR en Test 1
    echo.
    pause
    exit /b 1
)

echo.
echo ✅ Test 1 completado
echo.
echo Presiona cualquier tecla para continuar con el Test 2...
pause > nul

echo.
echo ================================================================================
echo 📋 TEST 2/3: COMPARACIÓN DE PAYOUTS
echo ================================================================================
echo.
python test_comparacion_payouts.py
if errorlevel 1 (
    echo.
    echo ❌ ERROR en Test 2
    echo.
    pause
    exit /b 1
)

echo.
echo ✅ Test 2 completado
echo.
echo Presiona cualquier tecla para continuar con el Test 3...
pause > nul

echo.
echo ================================================================================
echo 📋 TEST 3/3: FLUJO DE ESTRATEGIAS
echo ================================================================================
echo.
python test_flujo_estrategias.py
if errorlevel 1 (
    echo.
    echo ❌ ERROR en Test 3
    echo.
    pause
    exit /b 1
)

echo.
echo ✅ Test 3 completado
echo.

echo.
echo ================================================================================
echo ✅ TODOS LOS TESTS COMPLETADOS
echo ================================================================================
echo.
echo 📊 RESUMEN:
echo    ✅ Test 1: Diagnóstico Completo - OK
echo    ✅ Test 2: Comparación de Payouts - OK
echo    ✅ Test 3: Flujo de Estrategias - OK
echo.
echo 🎉 El bot CubaYDSignal está funcionando correctamente con datos 100%% reales
echo.
echo 💡 Si todos los tests pasaron:
echo    - El bot se conecta correctamente a Quotex
echo    - Los payouts son reales y consistentes
echo    - Las velas (candles) son reales y válidas
echo    - Todas las estrategias funcionan correctamente
echo    - Las señales se generan con efectividad ≥80%%
echo.
echo 📝 Revisa el output arriba para ver los detalles de cada test
echo.
pause
