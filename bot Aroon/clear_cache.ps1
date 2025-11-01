# Limpiar caché de Python
Write-Host "Limpiando caché de Python..." -ForegroundColor Yellow
Get-ChildItem -Path . -Include __pycache__ -Recurse -Force | Remove-Item -Force -Recurse -ErrorAction SilentlyContinue
Get-ChildItem -Path . -Filter *.pyc -Recurse -Force | Remove-Item -Force -ErrorAction SilentlyContinue
Write-Host "Caché limpiada!" -ForegroundColor Green
