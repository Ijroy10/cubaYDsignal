# Script de Inicio Rápido - CubaYDSignal Bot
# Ejecuta este script para iniciar el bot automáticamente

Write-Host "╔══════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║                                                          ║" -ForegroundColor Cyan
Write-Host "║         CUBAYDSIGNAL BOT - INICIO AUTOMÁTICO            ║" -ForegroundColor Cyan
Write-Host "║                                                          ║" -ForegroundColor Cyan
Write-Host "╚══════════════════════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""

# Paso 1: Activar entorno virtual
Write-Host "1️⃣ Activando entorno virtual Python 3.12..." -ForegroundColor Yellow
& .\.venv312\Scripts\Activate.ps1

if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Error activando entorno virtual" -ForegroundColor Red
    Write-Host "Ejecuta manualmente: .\.venv312\Scripts\Activate.ps1" -ForegroundColor Yellow
    pause
    exit 1
}

Write-Host "✅ Entorno virtual activado" -ForegroundColor Green
Write-Host ""

# Paso 2: Verificar Python
Write-Host "2️⃣ Verificando Python..." -ForegroundColor Yellow
python --version
Write-Host ""

# Paso 3: Preguntar si quiere verificar sistema
Write-Host "3️⃣ ¿Deseas verificar el sistema antes de iniciar? (recomendado)" -ForegroundColor Yellow
Write-Host "   Esto verificará dependencias, conexión a Quotex, etc." -ForegroundColor Gray
$verificar = Read-Host "Verificar sistema? (S/N)"

if ($verificar -eq "S" -or $verificar -eq "s") {
    Write-Host ""
    Write-Host "Ejecutando verificación del sistema..." -ForegroundColor Cyan
    python verificar_sistema.py
    
    if ($LASTEXITCODE -ne 0) {
        Write-Host ""
        Write-Host "⚠️ La verificación detectó problemas." -ForegroundColor Red
        Write-Host "¿Deseas continuar de todas formas? (S/N)" -ForegroundColor Yellow
        $continuar = Read-Host
        
        if ($continuar -ne "S" -and $continuar -ne "s") {
            Write-Host "❌ Inicio cancelado. Resuelve los problemas y vuelve a intentar." -ForegroundColor Red
            pause
            exit 1
        }
    }
}

Write-Host ""
Write-Host "4️⃣ Selecciona el modo de ejecución:" -ForegroundColor Yellow
Write-Host "   1) Normal (run_bot.py)" -ForegroundColor White
Write-Host "   2) Robusto con reconexión (run_bot_robust.py)" -ForegroundColor White
Write-Host "   3) Unificado (start_bot_unified.py)" -ForegroundColor White
Write-Host ""
$modo = Read-Host "Selecciona (1/2/3)"

$script_ejecutar = ""
switch ($modo) {
    "1" { $script_ejecutar = "run_bot.py" }
    "2" { $script_ejecutar = "run_bot_robust.py" }
    "3" { $script_ejecutar = "start_bot_unified.py" }
    default { $script_ejecutar = "run_bot.py" }
}

Write-Host ""
Write-Host "╔══════════════════════════════════════════════════════════╗" -ForegroundColor Green
Write-Host "║                                                          ║" -ForegroundColor Green
Write-Host "║              INICIANDO BOT...                            ║" -ForegroundColor Green
Write-Host "║                                                          ║" -ForegroundColor Green
Write-Host "╚══════════════════════════════════════════════════════════╝" -ForegroundColor Green
Write-Host ""
Write-Host "Ejecutando: python $script_ejecutar" -ForegroundColor Cyan
Write-Host ""
Write-Host "📱 IMPORTANTE: Abre Telegram y envía /start a tu bot" -ForegroundColor Yellow
Write-Host "🔑 Ingresa la clave del día que aparecerá en los logs" -ForegroundColor Yellow
Write-Host ""
Write-Host "Para detener el bot: Presiona Ctrl+C" -ForegroundColor Gray
Write-Host ""
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""

# Ejecutar el bot
python $script_ejecutar

# Si el bot termina
Write-Host ""
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "Bot detenido." -ForegroundColor Yellow
Write-Host ""
pause
