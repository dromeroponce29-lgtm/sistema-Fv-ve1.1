#!/usr/bin/env bash
# ════════════════════════════════════════════════════════════════════════
#   FV Chile — Launcher de un click
# ════════════════════════════════════════════════════════════════════════
# Doble clic sobre este archivo en Finder. macOS lo abre en Terminal,
# arranca el backend FastAPI y abre tu navegador en http://localhost:8000.
# Para cerrar: Ctrl+C en la ventana del Terminal (o cerrar la ventana).
# ════════════════════════════════════════════════════════════════════════

set -e
cd "$(dirname "$0")"

# Colores para output (ANSI)
G='\033[0;32m'  # verde
O='\033[0;33m'  # naranja
R='\033[0;31m'  # rojo
B='\033[1m'     # negrita
N='\033[0m'     # reset

clear
echo ""
echo -e "${O}${B}╔══════════════════════════════════════════════════════════════╗${N}"
echo -e "${O}${B}║         FV Chile — Sistemas Fotovoltaicos                    ║${N}"
echo -e "${O}${B}║         Launcher v1.0                                        ║${N}"
echo -e "${O}${B}╚══════════════════════════════════════════════════════════════╝${N}"
echo ""

# 1. Verificar Python
if ! command -v python3 >/dev/null 2>&1; then
    echo -e "${R}✗ Python 3 no está instalado en este Mac.${N}"
    echo ""
    echo "Tienes dos opciones para instalarlo:"
    echo "  A) Descargar desde: https://www.python.org/downloads/"
    echo "  B) Si tienes Homebrew:  brew install python@3.11"
    echo ""
    echo "Presiona cualquier tecla para cerrar..."
    read -n 1
    exit 1
fi

PY_VER=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
echo -e "${G}✓${N} Python $PY_VER detectado"

# 2. Verificar/crear venv
if [ ! -d ".venv" ]; then
    echo -e "${O}→${N} Primera ejecución: creando entorno virtual (tarda ~30 segundos)"
    python3 -m venv .venv
fi
echo -e "${G}✓${N} Entorno virtual listo"

# 3. Activar venv
# shellcheck disable=SC1091
source .venv/bin/activate

# 4. Instalar/actualizar dependencias (silencioso, solo muestra si hay errores)
echo -e "${O}→${N} Verificando dependencias…"
pip install -q --upgrade pip 2>/dev/null
if ! pip install -q -r requirements.txt 2>/tmp/fv-chile-pip.log; then
    echo -e "${R}✗ Error instalando dependencias. Detalles:${N}"
    cat /tmp/fv-chile-pip.log
    echo ""
    echo "Presiona cualquier tecla para cerrar..."
    read -n 1
    exit 1
fi
echo -e "${G}✓${N} Dependencias instaladas"

# 5. Crear .env si no existe
if [ ! -f ".env" ] && [ -f ".env.example" ]; then
    cp .env.example .env
fi

# 6. Verificar puerto libre
PORT=8000
if lsof -i :$PORT >/dev/null 2>&1; then
    echo -e "${O}⚠${N}  El puerto $PORT está en uso (¿ya arrancaste el backend antes?)."
    echo "    Intentando usar el puerto 8001…"
    PORT=8001
    if lsof -i :$PORT >/dev/null 2>&1; then
        echo -e "${R}✗ Puertos 8000 y 8001 ambos ocupados. Cierra el proceso anterior.${N}"
        echo "Procesos activos en estos puertos:"
        lsof -i :8000 -i :8001 | head -5
        read -n 1
        exit 1
    fi
fi

# 7. Mostrar info y arrancar
echo ""
echo -e "${G}${B}════════════════════════════════════════════════════════════════${N}"
echo -e "${G}${B}  Backend arrancando en http://localhost:$PORT${N}"
echo -e "${G}${B}════════════════════════════════════════════════════════════════${N}"
echo ""
echo "  App web    : http://localhost:$PORT/"
echo "  API docs   : http://localhost:$PORT/docs"
echo "  Health     : http://localhost:$PORT/api/health"
echo ""
echo -e "  ${O}Para detener: Ctrl+C o cerrar esta ventana${N}"
echo ""

# 8. Abrir navegador después de 3 segundos (en background)
(sleep 3 && open "http://localhost:$PORT/") &

# 9. Arrancar uvicorn en foreground (mantiene la terminal viva)
exec python3 -m uvicorn app.main:app --host 127.0.0.1 --port "$PORT"
