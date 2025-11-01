# Script para probar la conexión con pyquotex
Write-Host "=== Prueba de Conexión pyquotex ===" -ForegroundColor Cyan
Write-Host ""

# Activar entorno virtual
Write-Host "Activando entorno virtual Python 3.12..." -ForegroundColor Yellow
& .\.venv312\Scripts\Activate.ps1

# Verificar versión
Write-Host ""
Write-Host "Verificando versión de Python:" -ForegroundColor Yellow
python --version

# Verificar pyquotex instalado
Write-Host ""
Write-Host "Verificando instalación de pyquotex..." -ForegroundColor Yellow
python -c "import pyquotex; print('✅ pyquotex instalado correctamente')"

# Ejecutar test
Write-Host ""
Write-Host "Ejecutando prueba de conexión..." -ForegroundColor Yellow
python scripts\test_pyquotex.py

Write-Host ""
Write-Host "=== Prueba completada ===" -ForegroundColor Green
