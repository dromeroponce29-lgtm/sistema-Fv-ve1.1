# Deploy a Render — Guía paso a paso

Tu app FV Chile en una URL pública gratis, lista para pruebas reales con clientes.
Resultado final: `https://fv-chile.onrender.com` (o el nombre que elijas).

## Resumen del plan

```
1. Crear repo en GitHub  →  10 min
2. Subir el código       →   5 min
3. Conectar Render       →   3 min
4. Esperar primer build  →   5 min
                          ──────
                         ≈ 25 min al primer despliegue
```

Después, cada `git push` redeploya automáticamente (~2 min).

---

## Paso 1 — Crear repo en GitHub

Si no tienes cuenta GitHub, créala gratis en <https://github.com/signup>.

Después en el sitio: **New repository** (botón verde arriba derecha):

- **Repository name**: `sistemas-fotovoltaicos-chile` (o el que prefieras)
- **Visibility**: **Private** si tienes cuenta paga, **Public** si no
  (con cuenta gratis solo los públicos pueden conectarse a Render gratis)
- **NO marques** "Add README", "Add .gitignore", ni "License" (ya los tienes)
- Click **Create repository**

GitHub te muestra una pantalla con instrucciones. Quédate ahí, copia la URL del repo
(algo como `https://github.com/dromero/sistemas-fotovoltaicos-chile.git`).

---

## Paso 2 — Subir el código

Abre Terminal en macOS y corre estos comandos uno por uno:

```bash
# Ir a la carpeta del proyecto
cd "/Users/mac/Documents/Claude/Projects/SISTEMAS FOTOVOLTAICOS"

# Si nunca usaste git, configurar tu identidad (una sola vez)
git config --global user.name "Daniel Romero"
git config --global user.email "dromeroponce29@gmail.com"

# Inicializar el repo
git init -b main

# Agregar todos los archivos (respeta .gitignore)
git add .

# Primer commit
git commit -m "Initial commit: FV Chile v1.0-beta"

# Conectar con GitHub (REEMPLAZA la URL con la tuya)
git remote add origin https://github.com/TU_USUARIO/sistemas-fotovoltaicos-chile.git

# Subir
git push -u origin main
```

La primera vez te pedirá autenticarte. macOS abre una ventana para login GitHub.
Si te pide un "Personal Access Token" en vez de contraseña, créalo en
<https://github.com/settings/tokens> (Generate new token classic → scope: `repo`).

---

## Paso 3 — Conectar Render

1. Ve a <https://render.com> y haz **Sign up** (puedes usar tu cuenta de GitHub directo).
2. Una vez dentro, click **+ New** (arriba derecha) → **Blueprint**.
3. Click **Connect a repository**.
4. Autoriza a Render para acceder a tus repos (botón verde).
5. Selecciona `sistemas-fotovoltaicos-chile` de la lista.
6. Render detecta el archivo `render.yaml` automáticamente y muestra el servicio
   `fv-chile`. Confirma con **Apply** o **Create New Services**.

---

## Paso 4 — Esperar el primer build

Render comienza el build:

1. **Cloning repo…** (10s)
2. **Installing Python 3.11.10…** (1 min)
3. **Running `pip install -r requirements.txt`** (2-3 min, son ~20 paquetes incluido pvlib y openpyxl)
4. **Starting service…** (10s)
5. **Health check passing** (cuando responde `/api/health`)

Cuando termina vas a ver el estado **Live** en verde. La URL aparece arriba:
`https://fv-chile.onrender.com` (o el nombre que Render asigne — puedes cambiarlo
en Settings → Name).

---

## Paso 5 — Probarla

Abre la URL en tu navegador. Vas a ver la app web exactamente igual que en localhost,
pero accesible desde cualquier lugar.

**Cosas que funcionan en Render gratis:**

- ✅ Toda la app web HTML + JS
- ✅ Cálculos en vivo (RIC, FV, económico, layout)
- ✅ Generación de reportes XLSX, DOCX, PDF en vivo
- ✅ Importación de plantilla Excel desde cliente
- ✅ Parser DXF/PDF de planos
- ✅ APIs PVGIS, NASA POWER, OpenStreetMap (todas externas)
- ✅ Mapa satelital Leaflet con tiles ESRI

**Limitaciones del plan free de Render:**

- 💤 **El servicio se duerme tras 15 minutos sin tráfico**
  Cuando alguien hace el primer request después de eso, tarda ~30 segundos en despertar.
  Para evitarlo: pagar plan Starter ($7 USD/mes) o usar un servicio que pinguee
  cada 14 min (UptimeRobot tiene plan gratis para esto).
- 💾 **No hay persistencia de archivos entre deploys**
  Los proyectos creados por los usuarios viven en localStorage del navegador, así
  que esto no afecta. Si quieres persistencia compartida, agregamos PostgreSQL
  (también gratis en Render).
- 🚦 **750 horas/mes** — suficiente para 1 servicio corriendo 24/7 (730 hrs/mes).

---

## Cómo seguir trabajando con deploy automático

Una vez configurado, **cada push a `main` redeploya solo**:

```bash
# Hacés cambios al código…
# (en VS Code, editás archivos, guardas)

cd "/Users/mac/Documents/Claude/Projects/SISTEMAS FOTOVOLTAICOS"
git add .
git commit -m "Mejora: agregué módulo X"
git push
```

Render detecta el push, hace el build de nuevo (~2 min) y reemplaza la versión
en producción sin downtime. Vas a recibir email cuando esté listo.

---

## Compartir con clientes para la beta

Cuando todo esté arriba:

1. Envía la URL `https://fv-chile.onrender.com` a tus clientes/colegas
2. Pueden navegar sin instalar nada
3. Crear sus propios proyectos con el wizard
4. Subir sus cuadros de carga (plantilla Excel)
5. Descargar reportes generados

Para feedback estructurado, agrega Google Forms (link en footer) o
[Hotjar](https://hotjar.com) (heatmaps y grabaciones).

---

## Tu propio dominio (opcional)

Si tienes un dominio (ej. `fv-chile.cl`), en Render:

1. Settings → Custom Domains → Add Custom Domain
2. Pon `fv.tudominio.cl`
3. Render te da un CNAME para apuntar desde tu DNS
4. En tu proveedor de DNS (NameCheap, GoDaddy, etc.) agregas el CNAME
5. ~30 min después Render certifica SSL automáticamente (Let's Encrypt)

Custom domain con SSL es gratis en Render.

---

## Si algo falla

| Problema | Solución |
|---|---|
| Build falla por dep | Render muestra el log; busca el `pip install` que rompió y compara con local |
| App responde 502 | Servicio durmiendo (esperar 30s) o falló al arrancar (ver logs) |
| Health check no pasa | Verifica que `/api/health` responda con 200 y `{"status":"ok"}` |
| CORS error | Ya está permisivo en `app/main.py` con `allow_origins=["*"]` |
| Memoria > 512 MB | Plan free limita 512 MB RAM; revisar imports pesados (matplotlib, opencv) |

Para ver logs en vivo: Render dashboard → tu servicio → **Logs** tab.

---

## Costo

**Hoy: $0 USD/mes** (plan free de Render).

**Cuando crezca** (clientes pagando, no podés permitirte que se duerma):

- Plan Starter Render: **$7 USD/mes** — siempre activo, deploy ilimitado
- Custom domain + SSL: gratis
- PostgreSQL Starter: **$7 USD/mes** si necesitas DB compartida
- Total estimado producción: **~$15 USD/mes**

---

## Contacto

dromeroponce29@gmail.com
