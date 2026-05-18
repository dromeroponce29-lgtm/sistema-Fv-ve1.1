#!/usr/bin/env bash
# start.sh — Arranque rápido del backend FastAPI sin Docker
# Uso: bash start.sh

set -e

cd "$(dirname "$0")"

# 1. Verificar Python 3.10+
if ! command -v python3 >/dev/null 2>&1; then
    echo "✗ Python 3 no está instalado. Instalalo desde https://python.org"
    exit 1
fi

PY_VER=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
echo "✓ Python $PY_VER detectado"

# 2. Crear venv si no existe
if [ ! -d ".venv" ]; then
    echo "→ Creando entorno virtual en .venv/"
    python3 -m venv .venv
fi

# 3. Activar venv e instalar deps
echo "→ Activando entorno virtual"
source .venv/bin/activate

echo "→ Instalando dependencias (puede tardar la primera vez)"
pip install -q --upgrade pip
pip install -q -r requirements.txt

# 4. Copiar .env si no existe
if [ ! -f ".env" ] && [ -f ".env.example" ]; then
    cp .env.example .env
    echo "✓ Creado .env desde .env.example"
fi

# 5. Levantar servidor
echo ""
echo "════════════════════════════════════════════════════════════════"
echo "  FV Chile — Backend FastAPI"
echo "════════════════════════════════════════════════════════════════"
echo "  App web    : http://localhost:8000/"
echo "  API docs   : http://localhost:8000/docs"
echo "  Health     : http://localhost:8000/api/health"
echo ""
echo "  Para detener: Ctrl+C"
echo "════════════════════════════════════════════════════════════════"
echo ""

exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
