#!/usr/bin/env bash
# ════════════════════════════════════════════════════════════════════════
#   Script automatizado de primer deploy a GitHub
#   Uso:  bash deploy-init.sh TU_USUARIO_GITHUB
#   Ej:   bash deploy-init.sh dromero-cl
# ════════════════════════════════════════════════════════════════════════

set -e

# Colores
G='\033[0;32m'; O='\033[0;33m'; R='\033[0;31m'; B='\033[1m'; N='\033[0m'

# Validar argumento
if [ -z "$1" ]; then
    echo -e "${R}✗ Falta tu username de GitHub${N}"
    echo ""
    echo "Uso: bash deploy-init.sh TU_USUARIO"
    echo "Ej:  bash deploy-init.sh dromero-cl"
    exit 1
fi

USUARIO="$1"
REPO_URL="https://github.com/${USUARIO}/sistemas-fotovoltaicos-chile.git"

cd "$(dirname "$0")"

clear
echo -e "${O}${B}╔══════════════════════════════════════════════════════════════╗${N}"
echo -e "${O}${B}║      FV Chile — Deploy automatizado a GitHub                 ║${N}"
echo -e "${O}${B}╚══════════════════════════════════════════════════════════════╝${N}"
echo ""
echo -e "Username GitHub: ${B}${USUARIO}${N}"
echo -e "Repo destino:    ${B}${REPO_URL}${N}"
echo ""

# 1. Confirmar
read -p "$(echo -e "${O}¿Es correcto? [s/N]: ${N}")" CONFIRM
if [[ "$CONFIRM" != "s" ]] && [[ "$CONFIRM" != "S" ]]; then
    echo "Cancelado."
    exit 0
fi
echo ""

# 2. Limpiar .git zombi
echo -e "${O}→ Limpiando estado previo de git…${N}"
rm -rf .git 2>/dev/null
echo -e "${G}✓${N} .git limpio"

# 3. Configurar identidad si no existe
if [ -z "$(git config --global user.name)" ]; then
    git config --global user.name "Daniel Romero"
fi
if [ -z "$(git config --global user.email)" ]; then
    git config --global user.email "dromeroponce29@gmail.com"
fi
echo -e "${G}✓${N} Identidad git: $(git config --global user.name) <$(git config --global user.email)>"

# 4. Init
echo ""
echo -e "${O}→ Inicializando repo (branch main)…${N}"
git init -b main >/dev/null
echo -e "${G}✓${N} Repo inicializado"

# 5. Add
echo ""
echo -e "${O}→ Agregando archivos (respetando .gitignore)…${N}"
git add . 2>&1 | grep -v "^$" || true
N_ARCHIVOS=$(git status --short | wc -l | tr -d ' ')
echo -e "${G}✓${N} ${N_ARCHIVOS} archivos preparados"

# 6. Verificar que NO se subirá .venv ni _legacy
if git status --short | grep -qE "\.venv|_legacy/"; then
    echo -e "${R}⚠ Advertencia: .venv o _legacy aparece en el staging.${N}"
    echo "  Verifica el .gitignore antes de continuar."
    git status --short | grep -E "\.venv|_legacy/" | head -5
fi

# 7. Commit
echo ""
echo -e "${O}→ Creando primer commit…${N}"
git commit -m "Initial commit: FV Chile v1.0-beta" --quiet
HASH=$(git rev-parse --short HEAD)
echo -e "${G}✓${N} Commit ${B}${HASH}${N} creado"

# 8. Configurar remote
echo ""
echo -e "${O}→ Conectando con repo de GitHub…${N}"
git remote remove origin 2>/dev/null || true
git remote add origin "$REPO_URL"
echo -e "${G}✓${N} Remote 'origin' apunta a ${REPO_URL}"

# 9. Push
echo ""
echo -e "${O}${B}════════════════════════════════════════════════════════════════${N}"
echo -e "${O}${B}  Push a GitHub (te pedirá autenticarte)${N}"
echo -e "${O}${B}════════════════════════════════════════════════════════════════${N}"
echo ""
echo "Si te pide login:"
echo "  • Username: ${USUARIO}"
echo "  • Password: NO tu contraseña, sino un Personal Access Token"
echo "    (créalo en https://github.com/settings/tokens → Generate new"
echo "     classic token → scope: repo)"
echo ""
echo "Si abre el navegador automáticamente: click Authorize y vuelve aquí."
echo ""
read -p "Presiona ENTER para continuar con el push…"
echo ""

if git push -u origin main; then
    echo ""
    echo -e "${G}${B}╔══════════════════════════════════════════════════════════════╗${N}"
    echo -e "${G}${B}║  ✓ ¡PUSH EXITOSO!                                            ║${N}"
    echo -e "${G}${B}╚══════════════════════════════════════════════════════════════╝${N}"
    echo ""
    echo "Tu código está en: https://github.com/${USUARIO}/sistemas-fotovoltaicos-chile"
    echo ""
    echo -e "${O}PRÓXIMO PASO:${N} Ir a https://render.com y:"
    echo "  1. Sign up con GitHub (mismo usuario)"
    echo "  2. + New → Blueprint"
    echo "  3. Conectar el repo 'sistemas-fotovoltaicos-chile'"
    echo "  4. Apply"
    echo ""
    echo "Render lee el render.yaml automáticamente y despliega en ~5 min."
    echo "Tu app quedará en: https://fv-chile.onrender.com (o similar)"
    echo ""
else
    echo ""
    echo -e "${R}${B}✗ Push falló${N}"
    echo ""
    echo "Causas comunes:"
    echo "  • No autorizaste GitHub en el navegador"
    echo "  • Token inválido o sin scope 'repo'"
    echo "  • El repo no existe en GitHub (créalo primero):"
    echo "    → https://github.com/new"
    echo "    → Name: sistemas-fotovoltaicos-chile"
    echo "    → Public, sin README/gitignore/license"
    echo ""
    echo "Una vez creado el repo en GitHub, vuelve a correr este script."
    exit 1
fi
