# Despliegue en Render - Mapa del Alma

## Comando

Render puede usar `render.yaml` automáticamente.

Si lo configuras manualmente:

- Build command: `pip install -r requirements.txt`
- Start command: `python -m waitress --listen=0.0.0.0:$PORT run:app`
- Health check path: `/health`

## Variables obligatorias

Configura estas variables en Render antes de vender:

```text
PUBLIC_BASE_URL=https://tu-servicio.onrender.com
SECRET_KEY=valor_largo_aleatorio
FLASK_ADMIN_PASSWORD=contrasena_admin_segura
DATABASE_URL=postgresql://...

STRIPE_PUBLIC_KEY=pk_live_...
STRIPE_SECRET_KEY=sk_live_...
STRIPE_WEBHOOK_SECRET=whsec_...

OPENAI_API_KEY=sk-...
OPENAI_ENABLE_REAL_ORDERS=true
MAX_OPENAI_CALLS_PER_ORDER=3
OPENAI_MODEL=gpt-4o-mini

EMAIL_SENDER=tu_correo@gmail.com
EMAIL_PASSWORD=contrasena_de_aplicacion_gmail
ADMIN_EMAIL=tu_correo_admin@gmail.com
# Opcional/recomendado en Render:
BREVO_API_KEY=xkeysib-...

GOOGLE_DRIVE_FOLDER_ID=id_de_la_carpeta
```

Para Google Drive usa una de estas opciones:

```text
GOOGLE_DRIVE_SERVICE_ACCOUNT_JSON={...json completo...}
```

Esta opción solo funciona para subir archivos si la carpeta está en una unidad compartida de Google Drive.

o:

```text
GOOGLE_DRIVE_OAUTH_CLIENT_JSON={...json completo...}
GOOGLE_DRIVE_TOKEN_JSON={...json completo...}
```

Para generar/renovar esas variables OAuth desde tu computadora:

```powershell
.\.venv\Scripts\python.exe scripts\google_drive_reauthorize.py
```

El script deja las variables listas en:

```text
secrets/render_google_drive_oauth_env.txt
```

## Variables recomendadas en Render

```text
FLASK_DEBUG=0
TRUSTED_PROXY_COUNT=1
SESSION_COOKIE_SECURE=1
ENFORCE_HTTPS=0
HSTS_MAX_AGE=15552000
DISABLE_GOOGLE_DRIVE=0
```

## Importante

- No subas `.env` ni la carpeta `secrets/`.
- Usa PostgreSQL/Supabase en producción. SQLite local puede perder datos en Render si no hay disco persistente.
- Stripe debe estar todo en el mismo modo: claves `live` con webhook `live`.
- Antes de anunciar la tienda, haz una compra real pequeña y confirma: Stripe, PDF, Google Drive, email y panel admin.

## Verificación final

Antes de vender, ejecuta:

```powershell
.\.venv\Scripts\python.exe scripts\production_check.py --strict-live
```

Para probar también Google Drive:

```powershell
.\.venv\Scripts\python.exe scripts\production_check.py --strict-live --external
```

Si aparece `FAIL`, corrige esa variable o servicio antes de aceptar pagos reales.
