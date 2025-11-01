# Script de instalación para Python 3.12+
# Ejecutar con: .\install_py312.ps1

Write-Host "=== Instalación de CubaYDSignal Bot con Python 3.12 ===" -ForegroundColor Cyan
Write-Host ""

# Verificar versión de Python
Write-Host "Verificando versión de Python..." -ForegroundColor Yellow
$pythonVersion = python --version 2>&1
Write-Host "Versión detectada: $pythonVersion" -ForegroundColor Green

if ($pythonVersion -notmatch "3\.12") {
    Write-Host "ADVERTENCIA: Se requiere Python 3.12 o superior" -ForegroundColor Red
    Write-Host "Por favor instala Python 3.12+ desde https://www.python.org/downloads/" -ForegroundColor Yellow
    exit 1
}

Write-Host ""
Write-Host "Actualizando pip..." -ForegroundColor Yellow
python -m pip install --upgrade pip

Write-Host ""
Write-Host "Instalando dependencias desde requirements.txt..." -ForegroundColor Yellow
python -m pip install -r requirements.txt

Write-Host ""
Write-Host "=== Instalación completada ===" -ForegroundColor Green
Write-Host ""
Write-Host "Próximos pasos:" -ForegroundColor Cyan
Write-Host "1. Configura tus credenciales en el archivo .env" -ForegroundColor White
Write-Host "2. Ejecuta el script de prueba: python scripts\test_pyquotex.py" -ForegroundColor White
Write-Host "3. Si la prueba es exitosa, ejecuta el bot: python run_bot.py" -ForegroundColor White
Write-Host ""
