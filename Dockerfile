# Imagen base liviana con Python 3.11
FROM python:3.11-slim

# Sistema base + Tesseract (OCR opcional para PDFs escaneados)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libgl1 libglib2.0-0 \
    tesseract-ocr tesseract-ocr-spa \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Instalar deps Python (cache layer si requirements.txt no cambia)
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copiar código
COPY app/ ./app/
COPY app_fv_chile.html ./
COPY reportes/ ./reportes/
COPY .env.example ./.env

# Puerto del backend
EXPOSE 8000

# Healthcheck interno
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/health')" || exit 1

# Arranque del servidor
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
