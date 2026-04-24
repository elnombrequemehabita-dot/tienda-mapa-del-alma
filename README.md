# El Nombre Que Me Habita — Tienda base (Flask)

Tienda web para tu producto digital **Mapa del Alma**: página de inicio, formulario de pedido, confirmación, almacenamiento en **SQLite**, panel admin con **estados de pedido**, generación de PDF y envío por email.

## Requisitos

- Windows 10 u 11
- [Python 3.11+](https://www.python.org/downloads/) instalado (marca la opción **“Add python.exe to PATH”** en el instalador)

## Pasos exactos en PowerShell (Windows)

1. **Abrir PowerShell**

2. **Ir a la carpeta del proyecto**:

   ```powershell
   cd "C:\Users\yanel\Desktop\Tienda_El_Nombre_Que_Me_Habita"
   ```

3. **Crear un entorno virtual** (solo la primera vez):

   ```powershell
   python -m venv .venv
   ```

4. **Activar el entorno virtual** (cada vez que abras una ventana nueva):

   ```powershell
   .\.venv\Scripts\Activate.ps1
   ```

   Si falla por política de ejecución:

   ```powershell
   Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
   ```

5. **Instalar dependencias**:

   ```powershell
   pip install -r requirements.txt
   ```

6. **Opcional: contraseña del panel admin**

   ```powershell
   $env:FLASK_ADMIN_PASSWORD = "tu_contraseña_segura"
   ```

7. **Arrancar la tienda**:

   ```powershell
   python run.py
   ```

8. **Abrir el navegador**

   - Tienda: [http://127.0.0.1:5000/](http://127.0.0.1:5000/)
   - Admin: [http://127.0.0.1:5000/admin](http://127.0.0.1:5000/admin) (por defecto la contraseña es `admin123` si no defines `FLASK_ADMIN_PASSWORD`)

9. **Parar el servidor**: `Ctrl + C`

## Estados del pedido (columna `estado`)

Cada pedido avanza (o se marca manualmente) mediante un texto fijo en la base de datos:

| Valor en SQLite | Significado breve |
|-----------------|---------------------|
| `pendiente_pago` | Recién creado desde el formulario público (valor inicial) |
| `pagado` | Confirmación de pago (manual o futura pasarela) |
| `generando_pdf` | En proceso de generación del PDF |
| `error_generacion` | Falló la generación; ver `error_message` |
| `pdf_generado` | PDF listo; `pdf_path` apunta a la ruta (ejemplo o real) |
| `enviando_email` | En proceso de envío del correo |
| `error_envio` | Falló el envío; ver `error_message` |
| `completado` | Flujo cerrado con éxito |
| `revision_manual` | Lo gestionas tú a mano fuera del flujo automático |

Campos relacionados:

- `created_at`, `updated_at`: marcas de tiempo en UTC (ISO).
- `pdf_path`: ruta lógica del archivo PDF generado.
- `error_message`: texto del último error registrado en el flujo.

## Cómo probar el flujo desde el admin (navegador)

1. Entra en la tienda pública y crea un pedido desde **Pedir Mapa del Alma** (quedará en `pendiente_pago`).
2. Inicia sesión en **Admin** (`/admin`).
3. En **Pedidos**, revisa columnas de estado, fechas, `pdf_path` y error resumido. Puedes cambiar el estado con el desplegable **Guardar** en la fila.
4. Pulsa **Ver** para abrir el **detalle** del pedido.
5. En el detalle:
   - **Marcar como pagado** → `pagado`
   - **Marcar revisión manual** → `revision_manual`
   - **Marcar completado** → `completado`
  - **Marcar como pagado** → pone el pedido en `pagado`.
  - El flujo post-pago genera PDF y envía email automáticamente cuando Stripe confirma el cobro.
  - Si ocurre un error, el pedido queda en `error_generacion` o `error_envio` con detalle en `error_message`.

## Flujo de PDF y email (desde código)

Las funciones viven en `app/order_services.py`:

- `generar_pdf_automatico(order_id)`
- `enviar_pdf_cliente(order_id, pdf_absolute_path)`
- `procesar_post_pago(order_id, stripe_checkout_session_id=None)`

Estas funciones actualizan `estado`, `pdf_path`, `error_message` y `updated_at` vía `app/db.py`.

## Migración de base de datos antigua

Si ya tenías `instance/tienda.sqlite` de la primera versión, al arrancar la app se ejecuta una migración suave: añade `estado`, `pdf_path`, `error_message`, `updated_at` si faltan y rellena valores por defecto sin borrar pedidos.

## Dónde se guarda la base de datos

`instance/tienda.sqlite`

## Estructura del proyecto (resumen)

```
Tienda_El_Nombre_Que_Me_Habita/
├── app/
│   ├── __init__.py
│   ├── db.py                 # SQLite + migración + updates
│   ├── routes.py             # Rutas tienda + admin (checkout, webhook, panel)
│   ├── order_states.py       # Constantes y etiquetas de estados
│   ├── order_services.py     # Flujo PDF / email post-pago
│   ├── static/css/style.css
│   └── templates/
│       ├── ...
│       └── admin/
│           ├── login.html
│           ├── pedidos.html
│           └── pedido_detail.html
├── instance/
├── requirements.txt
├── run.py
└── README.md
```

## Seguridad (antes de publicar en internet)

- Crea tu `.env` desde `.env.example` y completa todos los valores reales.
- Usa `SECRET_KEY` y `FLASK_ADMIN_PASSWORD` fuertes y únicos.
- HTTPS y servidor WSGI adecuado para producción.
- Si vas detrás de HTTPS, define `SESSION_COOKIE_SECURE=1` en `.env`.
- Valora protección **CSRF** en formularios (Flask-WTF) cuando la web sea pública.

## Arranque recomendado en producción

Con `waitress` (incluida en `requirements.txt`):

```powershell
$env:FLASK_DEBUG = "0"
$env:PORT = "8080"
python -m waitress --listen=0.0.0.0:$env:PORT run:app
```

O con script:

```powershell
.\start_prod.ps1
```

## Licencia

Proyecto personal para tu tienda; ajusta este apartado como prefieras.
