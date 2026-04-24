$ErrorActionPreference = "Stop"

if (-not (Test-Path ".\.venv\Scripts\python.exe")) {
    python -m venv .venv
}

.\.venv\Scripts\python -m pip install -r requirements.txt

if (-not $env:PORT) {
    $env:PORT = "5000"
}

# Producción (HTTPS normalmente lo termina Nginx/Cloudflare delante de Waitress):
# - TRUSTED_PROXY_COUNT=1 (típico con 1 proxy)
# - SESSION_COOKIE_SECURE=1
# - ENFORCE_HTTPS=1 (opcional; solo si tu proxy ya sirve HTTPS correctamente)
# Ejemplo (descomenta/ajusta según tu despliegue):
# $env:TRUSTED_PROXY_COUNT = "1"
# $env:SESSION_COOKIE_SECURE = "1"
# $env:ENFORCE_HTTPS = "1"

$listen = "0.0.0.0:$($env:PORT)"
.\.venv\Scripts\python -m waitress --listen=$listen run:app
